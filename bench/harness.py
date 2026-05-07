"""Benchmark harness for Aether.

Each task lives in `bench/tasks/<task_id>/` with these files:

    prompt.md         The user-facing instruction the model receives.
    grader.json       JSON object with grading config — see TASK_SCHEMA.
    reference.aeth    A reference solution, used to verify the grader works.

A run is invoked as:

    python -m bench.harness run-task <task_id> --candidate <path-to-.aeth>

It compiles the candidate, executes with stdin from `grader.json.stdin`,
captures stdout/stderr/exit_code, and compares against the grader.

Output is structured JSON the agent can consume:

    {
      "task_id": "...",
      "candidate": "...",
      "stage": "parse|emit|exec|grade",
      "ok": true|false,
      "diagnostic": null | {...},
      "stdout": "...",
      "expected": "...",
      "actual": "...",
      "stderr": "...",
      "exit_code": int,
      "elapsed_ms": ...
    }

Wedge-grading mode:
  When `expected_exit_code` or `expected_stderr_pattern` is present in
  grader.json, the harness checks those in addition to expected_stdout.
  This is for "contract-wedge" tasks where the desired outcome is a
  structured failure (Aether catches with E0301/E0302/...) rather than
  a successful stdout output.
"""

from __future__ import annotations
import argparse
import io
import json
import os
import re
import signal
import subprocess
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from typing import Any, Dict, List, Optional

# transpiler must be importable
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "transpiler"))

from aether.diagnostics import AetherError, Diagnostic       # noqa: E402
from aether.parser import parse                              # noqa: E402
from aether.emitter import emit                              # noqa: E402
from aether.runtime import build_namespace                   # noqa: E402


TASK_SCHEMA = {
    "expected_stdout": "str — exact stdout the candidate must produce",
    "stdin": "str | None — optional stdin input fed to the program",
    "timeout_ms": "int — wall-clock timeout (default 5000)",
    "expected_exit_code": "int | None — wedge-grading: required exit code",
    "expected_stderr_pattern": "str | None — wedge-grading: regex match on stderr",
    "tags": "list[str] — categorisation",
    "expected_diagnostic_code": "str | None - wedge-grading: required diagnostic code",
    "expected_diagnostic_category": "str | None - wedge-grading: required diagnostic category",
    "python_equivalent": "str | None - optional path to a Python comparison file",
    "python_expected_exit_code": "int | None - optional documented Python exit code",
    "python_expected_stdout": "str | None - optional documented Python stdout",
    "python_expected_stderr": "str | None - optional documented Python stderr",
    "python_forbidden_stderr_pattern": "str | None - regex that must not match Python stderr",
    "python_timeout_ms": "int | None - optional Python comparison timeout",
    "difficulty": "easy|medium|hard",
}


# ----------------------------------------------------------------------
# Compile + run a candidate program
# ----------------------------------------------------------------------

class _CandidateTimeout(Exception):
    """Raised by the SIGALRM handler when a candidate exceeds timeout_ms."""


def _alarm_handler(signum, frame):
    raise _CandidateTimeout("candidate exceeded timeout_ms")


def _format_diag_as_stderr(diag) -> str:
    """Format a diagnostic the same way cli._emit_error does (non-JSON form)
    so wedge tasks can pattern-match stderr as if running the CLI."""
    if isinstance(diag, Diagnostic):
        d = diag.to_dict()
    elif isinstance(diag, dict):
        d = diag
    else:
        return ""
    code = d.get("code", "?")
    severity = d.get("severity", "error")
    category = d.get("category", "unknown")
    pos = d.get("position") or {}
    line = pos.get("line", 0) if isinstance(pos, dict) else 0
    col = pos.get("column", 0) if isinstance(pos, dict) else 0
    msg = d.get("message", "")
    out = f"[{code}] {severity} ({category}) at line {line}, col {col}: {msg}\n"
    sugg = d.get("suggestion")
    if sugg:
        out += f"  hint: {sugg}\n"
    return out


def compile_and_run(src: str, filename: str, stdin_text: str = "",
                    timeout_ms: int = 5000) -> Dict[str, Any]:
    """Run an Aether candidate and return a structured result.

    Always-present fields:
        stage          one of: parse, emit, emit-compile, exec
        ok             True if execution completed normally; False otherwise
        actual         captured stdout (str)
        stdout         captured stdout (str; alias for actual)
        stderr         formatted diagnostic if any (str; "" on success)
        exit_code      0 success, 2 AetherError, 1 other Python exception, 124 timeout
        elapsed_ms     int
    On failure paths:
        diagnostic     dict
    """
    t0 = time.time()
    elapsed = lambda: int((time.time() - t0) * 1000)

    try:
        ast = parse(src, filename)
    except AetherError as e:
        return {
            "stage": "parse", "ok": False,
            "diagnostic": e.diag.to_dict(),
            "stdout": "",
            "actual": "",
            "stderr": _format_diag_as_stderr(e.diag),
            "exit_code": 2,
            "elapsed_ms": elapsed(),
        }
    try:
        py = emit(ast)
    except Exception as e:
        diag = {"message": str(e), "category": "emit", "code": "E9001"}
        return {
            "stage": "emit", "ok": False,
            "diagnostic": diag,
            "stdout": "",
            "actual": "",
            "stderr": f"emit error: {e}\n",
            "exit_code": 1,
            "elapsed_ms": elapsed(),
        }
    try:
        code = compile(py, filename + ".py", "exec")
    except SyntaxError as e:
        diag = {"message": str(e), "category": "internal", "code": "E9002"}
        return {
            "stage": "emit-compile", "ok": False,
            "diagnostic": diag,
            "stdout": "",
            "actual": "",
            "stderr": f"internal error (emitter produced bad python): {e}\n",
            "exit_code": 1,
            "elapsed_ms": elapsed(),
        }

    g = build_namespace()
    g["__name__"] = "__main__"
    g["__file__"] = filename + ".py"
    buf = io.StringIO()
    err_buf = io.StringIO()
    saved_stdin = sys.stdin
    sys.stdin = io.StringIO(stdin_text)

    have_alarm = hasattr(signal, "SIGALRM")
    prev_handler = None
    if have_alarm and timeout_ms and timeout_ms > 0:
        prev_handler = signal.signal(signal.SIGALRM, _alarm_handler)
        signal.setitimer(signal.ITIMER_REAL, timeout_ms / 1000.0)
    try:
        try:
            with redirect_stdout(buf), redirect_stderr(err_buf):
                exec(code, g)
        except _CandidateTimeout:
            timeout_diag = {
                "code": "E0601", "category": "timeout", "severity": "error",
                "message": f"candidate exceeded timeout_ms={timeout_ms}",
                "suggestion": "check for infinite loops or runaway recursion",
                "position": {"line": 0, "column": 0},
            }
            stdout = buf.getvalue()
            stderr = err_buf.getvalue() + _format_diag_as_stderr(timeout_diag)
            return {
                "stage": "exec", "ok": False,
                "diagnostic": timeout_diag,
                "stdout": stdout,
                "actual": stdout,
                "stderr": stderr,
                "exit_code": 124,
                "elapsed_ms": elapsed(),
            }
        except AetherError as e:
            stdout = buf.getvalue()
            stderr = err_buf.getvalue() + _format_diag_as_stderr(e.diag)
            return {
                "stage": "exec", "ok": False,
                "diagnostic": e.diag.to_dict(),
                "stdout": stdout,
                "actual": stdout,
                "stderr": stderr,
                "exit_code": 2,
                "elapsed_ms": elapsed(),
            }
        except Exception as e:
            stdout = buf.getvalue()
            stderr = err_buf.getvalue() + f"runtime error: {type(e).__name__}: {e}\n"
            return {
                "stage": "exec", "ok": False,
                "diagnostic": {
                    "message": f"{type(e).__name__}: {e}",
                    "category": "runtime", "code": "E9003",
                },
                "stdout": stdout,
                "actual": stdout,
                "stderr": stderr,
                "exit_code": 1,
                "elapsed_ms": elapsed(),
            }
    finally:
        if have_alarm and timeout_ms and timeout_ms > 0:
            signal.setitimer(signal.ITIMER_REAL, 0)
            if prev_handler is not None:
                signal.signal(signal.SIGALRM, prev_handler)
        sys.stdin = saved_stdin

    stdout = buf.getvalue()
    return {
        "stage": "exec", "ok": True,
        "stdout": stdout,
        "actual": stdout,
        "stderr": err_buf.getvalue(),
        "exit_code": 0,
        "elapsed_ms": elapsed(),
    }


# ----------------------------------------------------------------------
# Task loading + grading
# ----------------------------------------------------------------------

def _regex_search(pattern: str, text: str) -> tuple[bool, Optional[str]]:
    try:
        return bool(re.search(pattern, text)), None
    except re.error as e:
        return False, str(e)


def load_task(task_id: str) -> Dict[str, Any]:
    base = os.path.join(HERE, "tasks", task_id)
    if not os.path.isdir(base):
        raise FileNotFoundError(f"task not found: {task_id}")
    with open(os.path.join(base, "grader.json"), "r", encoding="utf-8") as f:
        cfg = json.load(f)
    with open(os.path.join(base, "prompt.md"), "r", encoding="utf-8") as f:
        prompt = f.read()
    return {"id": task_id, "config": cfg, "prompt": prompt, "dir": base}


def grade_task(task: Dict[str, Any], candidate_path: str) -> Dict[str, Any]:
    if not os.path.isfile(candidate_path):
        return {"task_id": task["id"], "candidate": candidate_path,
                "ok": False, "stage": "missing",
                "diagnostic": {"message": "candidate file not found"}}
    with open(candidate_path, "r", encoding="utf-8") as f:
        src = f.read()
    cfg = task["config"]
    result = compile_and_run(
        src,
        candidate_path,
        stdin_text=cfg.get("stdin", "") or "",
        timeout_ms=int(cfg.get("timeout_ms", 5000)),
    )
    out = {"task_id": task["id"], "candidate": candidate_path}
    out.update(result)

    expected_stdout = cfg.get("expected_stdout", "")
    expected_exit_code = cfg.get("expected_exit_code")
    expected_stderr_pattern = cfg.get("expected_stderr_pattern")
    expected_diagnostic_code = cfg.get("expected_diagnostic_code")
    expected_diagnostic_category = cfg.get("expected_diagnostic_category")

    actual_stdout = result.get("stdout", result.get("actual", ""))
    actual_stderr = result.get("stderr", "")
    actual_exit_code = result.get("exit_code", 0 if result.get("ok") else 1)
    actual_diagnostic = result.get("diagnostic") or {}
    if not isinstance(actual_diagnostic, dict):
        actual_diagnostic = {}
    actual_diagnostic_code = actual_diagnostic.get("code")
    actual_diagnostic_category = actual_diagnostic.get("category")

    stdout_ok = (actual_stdout == expected_stdout)
    exit_ok = (expected_exit_code is None) or (actual_exit_code == expected_exit_code)
    stderr_ok = True
    stderr_regex_error = None
    if expected_stderr_pattern:
        stderr_ok, stderr_regex_error = _regex_search(expected_stderr_pattern, actual_stderr)
    diagnostic_code_ok = (
        expected_diagnostic_code is None
        or actual_diagnostic_code == expected_diagnostic_code
    )
    diagnostic_category_ok = (
        expected_diagnostic_category is None
        or actual_diagnostic_category == expected_diagnostic_category
    )

    wedge_mode = (
        expected_exit_code is not None
        or expected_stderr_pattern is not None
        or expected_diagnostic_code is not None
        or expected_diagnostic_category is not None
    )
    if wedge_mode:
        match = (
            stdout_ok
            and exit_ok
            and stderr_ok
            and diagnostic_code_ok
            and diagnostic_category_ok
        )
    else:
        match = bool(result.get("ok")) and stdout_ok

    failure_messages = []
    if not stdout_ok:
        failure_messages.append(
            f"stdout mismatch: expected {expected_stdout!r}, got {actual_stdout!r}"
        )
    if expected_exit_code is not None and not exit_ok:
        failure_messages.append(
            f"exit_code mismatch: expected {expected_exit_code}, got {actual_exit_code}"
        )
    if expected_stderr_pattern and not stderr_ok:
        if stderr_regex_error:
            failure_messages.append(
                f"stderr regex is invalid: {stderr_regex_error}"
            )
        else:
            failure_messages.append(
                f"stderr did not match pattern {expected_stderr_pattern!r}: "
                f"actual stderr was {actual_stderr!r}"
            )
    if expected_diagnostic_code is not None and not diagnostic_code_ok:
        failure_messages.append(
            f"diagnostic code mismatch: expected {expected_diagnostic_code!r}, "
            f"got {actual_diagnostic_code!r}"
        )
    if expected_diagnostic_category is not None and not diagnostic_category_ok:
        failure_messages.append(
            f"diagnostic category mismatch: expected {expected_diagnostic_category!r}, "
            f"got {actual_diagnostic_category!r}"
        )
    if actual_exit_code == 124:
        failure_messages.append(
            f"process timed out after timeout_ms={int(cfg.get('timeout_ms', 5000))}"
        )
    if result.get("stage") in {"parse", "emit", "emit-compile"} and not result.get("ok"):
        failure_messages.append(
            f"compilation failed during {result.get('stage')}"
        )
    if (not wedge_mode) and result.get("stage") == "exec" and not result.get("ok"):
        failure_messages.append(
            f"runtime failed unexpectedly with exit_code={actual_exit_code}"
        )

    out["expected"] = expected_stdout
    out["stdout"] = actual_stdout
    out["match"] = match
    out["ok"] = match
    out["wedge_mode"] = wedge_mode
    out["failure_messages"] = failure_messages
    out["checks"] = {
        "stdout_ok": stdout_ok,
        "exit_code_ok": exit_ok,
        "stderr_pattern_ok": stderr_ok,
        "expected_exit_code": expected_exit_code,
        "expected_stderr_pattern": expected_stderr_pattern,
        "actual_exit_code": actual_exit_code,
        "expected_diagnostic_code": expected_diagnostic_code,
        "expected_diagnostic_category": expected_diagnostic_category,
        "actual_diagnostic_code": actual_diagnostic_code,
        "actual_diagnostic_category": actual_diagnostic_category,
        "diagnostic_code_ok": diagnostic_code_ok,
        "diagnostic_category_ok": diagnostic_category_ok,
    }
    return out


def run_python_equivalent(task: Dict[str, Any]) -> Dict[str, Any]:
    cfg = task["config"]
    rel = cfg.get("python_equivalent")
    if not rel:
        return {
            "task_id": task["id"],
            "ok": False,
            "stage": "python-missing",
            "diagnostic": {"message": "python_equivalent is not configured"},
        }

    path = rel if os.path.isabs(rel) else os.path.join(task["dir"], rel)
    if not os.path.isfile(path):
        return {
            "task_id": task["id"],
            "python_equivalent": path,
            "ok": False,
            "stage": "python-missing",
            "diagnostic": {"message": "python equivalent file not found"},
        }

    timeout_ms = int(cfg.get("python_timeout_ms", cfg.get("timeout_ms", 5000)))
    stdin_text = cfg.get("python_stdin", cfg.get("stdin", "") or "")
    t0 = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, path],
            cwd=task["dir"],
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=timeout_ms / 1000.0 if timeout_ms > 0 else None,
        )
        stdout = proc.stdout
        stderr = proc.stderr
        exit_code = proc.returncode
        stage = "python-exec"
        diagnostic = None
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout or ""
        stderr = e.stderr or ""
        exit_code = 124
        stage = "python-timeout"
        diagnostic = {"message": f"python equivalent exceeded timeout_ms={timeout_ms}"}
    elapsed_ms = int((time.time() - t0) * 1000)

    expected_exit_code = cfg.get("python_expected_exit_code")
    expected_stdout = cfg.get("python_expected_stdout")
    expected_stderr = cfg.get("python_expected_stderr")
    forbidden_stderr_pattern = cfg.get("python_forbidden_stderr_pattern")

    exit_ok = expected_exit_code is None or exit_code == expected_exit_code
    stdout_ok = expected_stdout is None or stdout == expected_stdout
    stderr_ok = expected_stderr is None or stderr == expected_stderr
    forbidden_ok = True
    forbidden_regex_error = None
    if forbidden_stderr_pattern:
        matched, forbidden_regex_error = _regex_search(forbidden_stderr_pattern, stderr)
        forbidden_ok = not matched and forbidden_regex_error is None

    failure_messages = []
    if not exit_ok:
        failure_messages.append(
            f"python exit_code mismatch: expected {expected_exit_code}, got {exit_code}"
        )
    if not stdout_ok:
        failure_messages.append(
            f"python stdout mismatch: expected {expected_stdout!r}, got {stdout!r}"
        )
    if not stderr_ok:
        failure_messages.append(
            f"python stderr mismatch: expected {expected_stderr!r}, got {stderr!r}"
        )
    if forbidden_stderr_pattern and not forbidden_ok:
        if forbidden_regex_error:
            failure_messages.append(
                f"python forbidden stderr regex is invalid: {forbidden_regex_error}"
            )
        else:
            failure_messages.append(
                f"python stderr matched forbidden pattern {forbidden_stderr_pattern!r}"
            )
    if exit_code == 124:
        failure_messages.append(
            f"python equivalent timed out after timeout_ms={timeout_ms}"
        )

    ok = exit_ok and stdout_ok and stderr_ok and forbidden_ok
    return {
        "task_id": task["id"],
        "python_equivalent": path,
        "stage": stage,
        "ok": ok,
        "diagnostic": diagnostic,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "elapsed_ms": elapsed_ms,
        "failure_messages": failure_messages,
        "checks": {
            "expected_exit_code": expected_exit_code,
            "expected_stdout": expected_stdout,
            "expected_stderr": expected_stderr,
            "forbidden_stderr_pattern": forbidden_stderr_pattern,
            "exit_code_ok": exit_ok,
            "stdout_ok": stdout_ok,
            "stderr_ok": stderr_ok,
            "forbidden_stderr_pattern_ok": forbidden_ok,
        },
    }


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def cmd_list_tasks(args) -> int:
    base = os.path.join(HERE, "tasks")
    if not os.path.isdir(base):
        print("[]")
        return 0
    out = []
    for tid in sorted(os.listdir(base)):
        td = os.path.join(base, tid)
        if not os.path.isdir(td):
            continue
        try:
            with open(os.path.join(td, "grader.json")) as f:
                cfg = json.load(f)
            out.append({"id": tid,
                        "tags": cfg.get("tags", []),
                        "difficulty": cfg.get("difficulty", ""),
                        "python_equivalent": cfg.get("python_equivalent") is not None,
                        "expected_diagnostic_code": cfg.get("expected_diagnostic_code"),
                        "wedge": (cfg.get("expected_exit_code") is not None)
                                 or (cfg.get("expected_stderr_pattern") is not None)
                                 or (cfg.get("expected_diagnostic_code") is not None)
                                 or (cfg.get("expected_diagnostic_category") is not None)})
        except Exception:
            continue
    print(json.dumps(out, indent=2))
    return 0


def cmd_show_prompt(args) -> int:
    task = load_task(args.task_id)
    print(task["prompt"])
    return 0


def cmd_run_task(args) -> int:
    task = load_task(args.task_id)
    out = grade_task(task, args.candidate)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if out.get("ok") else 1


def cmd_run_python(args) -> int:
    task = load_task(args.task_id)
    out = run_python_equivalent(task)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if out.get("ok") else 1


def cmd_run_reference(args) -> int:
    base = os.path.join(HERE, "tasks")
    summary = []
    for tid in sorted(os.listdir(base)):
        td = os.path.join(base, tid)
        if not os.path.isdir(td):
            continue
        ref = os.path.join(td, "reference.aeth")
        if not os.path.isfile(ref):
            summary.append({"id": tid, "ok": False, "note": "no reference.aeth"})
            continue
        try:
            task = load_task(tid)
        except Exception as e:
            summary.append({"id": tid, "ok": False, "note": f"load: {e}"})
            continue
        out = grade_task(task, ref)
        summary.append({"id": tid, "ok": out.get("ok", False),
                        "stage": out.get("stage"),
                        "exit_code": out.get("exit_code"),
                        "wedge_mode": out.get("wedge_mode", False),
                        "elapsed_ms": out.get("elapsed_ms"),
                        "failure_messages": out.get("failure_messages", [])})
    print(json.dumps(summary, indent=2))
    n_ok = sum(1 for s in summary if s.get("ok"))
    print(f"# {n_ok}/{len(summary)} reference solutions pass", file=sys.stderr)
    return 0 if n_ok == len(summary) else 1


def cmd_run_python_equivalents(args) -> int:
    base = os.path.join(HERE, "tasks")
    summary = []
    for tid in sorted(os.listdir(base)):
        td = os.path.join(base, tid)
        if not os.path.isdir(td):
            continue
        try:
            task = load_task(tid)
        except Exception as e:
            summary.append({"id": tid, "ok": False, "note": f"load: {e}"})
            continue
        if not task["config"].get("python_equivalent"):
            continue
        out = run_python_equivalent(task)
        summary.append({
            "id": tid,
            "ok": out.get("ok", False),
            "stage": out.get("stage"),
            "exit_code": out.get("exit_code"),
            "stdout": out.get("stdout", ""),
            "stderr": out.get("stderr", ""),
            "elapsed_ms": out.get("elapsed_ms"),
            "failure_messages": out.get("failure_messages", []),
        })
    print(json.dumps(summary, indent=2))
    n_ok = sum(1 for s in summary if s.get("ok"))
    print(f"# {n_ok}/{len(summary)} python equivalents pass", file=sys.stderr)
    return 0 if n_ok == len(summary) else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="aether-bench")
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("list-tasks", help="list available tasks")
    sp = sub.add_parser("show-prompt", help="print a task's prompt")
    sp.add_argument("task_id")
    sp = sub.add_parser("run-task", help="grade a candidate solution")
    sp.add_argument("task_id")
    sp.add_argument("--candidate", required=True)
    sp = sub.add_parser("run-python", help="run and grade a task's Python equivalent")
    sp.add_argument("task_id")
    sp = sub.add_parser("run-reference",
                        help="run reference.aeth for every task; sanity check")
    sp = sub.add_parser("run-python-equivalents",
                        help="run configured Python equivalents for every task")
    args = p.parse_args(argv)
    if args.cmd == "list-tasks":      return cmd_list_tasks(args)
    if args.cmd == "show-prompt":     return cmd_show_prompt(args)
    if args.cmd == "run-task":        return cmd_run_task(args)
    if args.cmd == "run-python":      return cmd_run_python(args)
    if args.cmd == "run-reference":   return cmd_run_reference(args)
    if args.cmd == "run-python-equivalents": return cmd_run_python_equivalents(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
