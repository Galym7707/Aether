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
import json
import os
import sys
from typing import Any, Dict

# transpiler must be importable
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "transpiler"))

from aether.agent_sdk import (                              # noqa: E402
    format_diagnostic_stderr,
    grade_candidate_file,
    run_python_equivalent_file,
    run_source,
)


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

def _format_diag_as_stderr(diag) -> str:
    """Backward-compatible wrapper for the SDK diagnostic formatter."""
    return format_diagnostic_stderr(diag)


def compile_and_run(src: str, filename: str, stdin_text: str = "",
                    timeout_ms: int = 5000) -> Dict[str, Any]:
    """Run an Aether candidate via the stable agent SDK."""
    return run_source(
        src,
        filename,
        stdin_text=stdin_text,
        timeout_ms=timeout_ms,
    ).to_dict()


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
    return grade_candidate_file(task["id"], task["config"], candidate_path)


def run_python_equivalent(task: Dict[str, Any]) -> Dict[str, Any]:
    return run_python_equivalent_file(task["id"], task["dir"], task["config"])


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
