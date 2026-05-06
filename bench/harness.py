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
import sys
import time
from contextlib import redirect_stdout
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
            "actual": "",
            "stderr": f"internal error (emitter produced bad python): {e}\n",
            "exit_code": 1,
            "elapsed_ms": elapsed(),
        }

    g = build_namespace()
    g["__name__"] = "__main__"
    g["__file__"] = filename + ".py"
    buf = io.StringIO()
    saved_stdin = sys.stdin
    sys.stdin = io.StringIO(stdin_text)

    have_alarm = hasattr(signal, "SIGALRM")
    prev_handler = None
    if have_alarm and timeout_ms and timeout_ms > 0:
        prev_handler = signal.signal(signal.SIGALRM, _alarm_handler)
        signal.setitimer(signal.ITIMER_REAL, timeout_ms / 1000.0)
    try:
        try:
            with redirect_stdout(buf):
                exec(code, g)
        except _CandidateTimeout:
            timeout_diag = {
                "code": "E0601", "category": "timeout", "severity": "error",
                "message": f"candidate exceeded timeout_ms={timeout_ms}",
                "suggestion": "check for infinite loops or runaway recursion",
                "position": {"line": 0, "column": 0},
            }
            return {
                "stage": "exec", "ok": False,
                "diagnostic": timeout_diag,
                "actual": buf.getvalue(),
                "stderr": _format_diag_as_stderr(timeout_diag),
                "exit_code": 124,
                "elapsed_ms": elapsed(),
            }
        except AetherError as e:
            return {
                "stage": "exec", "ok": False,
                "diagnostic": e.diag.to_dict(),
                "actual": buf.getvalue(),
                "stderr": _format_diag_as_stderr(e.diag),
                "exit_code": 2,
                "elapsed_ms": elapsed(),
            }
        except Exception as e:
            return {
                "stage": "exec", "ok": False,
                "diagnostic": {
                    "message": f"{type(e).__name__}: {e}",
                    "category": "runtime", "code": "E9003",
                },
                "actual": buf.getvalue(),
                "stderr": f"runtime error: {type(e).__name__}: {e}\n",
                "exit_code": 1,
                "elapsed_ms": elapsed(),
            }
    finally:
        if have_alarm and timeout_ms and timeout_ms > 0:
            signal.setitimer(signal.ITIMER_REAL, 0)
            if prev_handler is not None:
                signal.signal(signal.SIGALRM, prev_handler)
        sys.stdin = saved_stdin

    return {
        "stage": "exec", "ok": True,
        "actual": buf.getvalue(),
        "stderr": "",
        "exit_code": 0,
        "elapsed_ms": elapsed(),
    }


# ----------------------------------------------------------------------
# Task loading + grading
# ----------------------------------------------------------------------

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

    actual_stdout = result.get("actual", "")
    actual_stderr = result.get("stderr", "")
    actual_exit_code = result.get("exit_code", 0 if result.get("ok") else 1)

    stdout_ok = (actual_stdout == expected_stdout)
    exit_ok = (expected_exit_code is None) or (actual_exit_code == expected_exit_code)
    stderr_ok = True
    if expected_stderr_pattern:
        stderr_ok = bool(re.search(expected_stderr_pattern, actual_stderr))

    wedge_mode = (expected_exit_code is not None) or (expected_stderr_pattern is not None)
    if wedge_mode:
        match = stdout_ok and exit_ok and stderr_ok
    else:
        match = stdout_ok

    out["expected"] = expected_stdout
    out["match"] = match
    out["ok"] = match
    out["wedge_mode"] = wedge_mode
    out["checks"] = {
        "stdout_ok": stdout_ok,
        "exit_code_ok": exit_ok,
        "stderr_pattern_ok": stderr_ok,
        "expected_exit_code": expected_exit_code,
        "expected_stderr_pattern": expected_stderr_pattern,
        "actual_exit_code": actual_exit_code,
    }
    return out


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
                        "wedge": (cfg.get("expected_exit_code") is not None)
                                 or (cfg.get("expected_stderr_pattern") is not None)})
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
                        "wedge_mode": out.get("wedge_mode", False),
                        "elapsed_ms": out.get("elapsed_ms")})
    print(json.dumps(summary, indent=2))
    n_ok = sum(1 for s in summary if s.get("ok"))
    print(f"# {n_ok}/{len(summary)} reference solutions pass", file=sys.stderr)
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
    sp = sub.add_parser("run-reference",
                        help="run reference.aeth for every task; sanity check")
    args = p.parse_args(argv)
    if args.cmd == "list-tasks":      return cmd_list_tasks(args)
    if args.cmd == "show-prompt":     return cmd_show_prompt(args)
    if args.cmd == "run-task":        return cmd_run_task(args)
    if args.cmd == "run-reference":   return cmd_run_reference(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
