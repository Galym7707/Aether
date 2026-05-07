"""Run Phase 1.4 Python prompt validation through Claude Code CLI.

This script is intentionally narrow:

* system prompt: prompt/python_system_prompt.md
* task prompts: validation/tasks/<task_id>/python_prompt.md
* output: runs/phase1/python_validation/<model>/<task_id>/
* tools disabled for model calls

It saves raw model output and then invokes scripts/grade_phase1_python.py.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Iterable


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PYTHON = sys.executable


def active_tasks() -> list[str]:
    base = os.path.join(ROOT, "validation", "tasks")
    out = []
    for tid in sorted(os.listdir(base)):
        td = os.path.join(base, tid)
        cfg_path = os.path.join(td, "grader.json")
        py_prompt_path = os.path.join(td, "python_prompt.md")
        if not (os.path.isfile(cfg_path) and os.path.isfile(py_prompt_path)):
            continue
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        if not cfg.get("deprecated"):
            out.append(tid)
    return out


def parse_task_filter(value: str | None) -> set[str] | None:
    if not value:
        return None
    return {part.strip() for part in value.split(",") if part.strip()}


def strip_markdown_fences(text: str) -> str:
    stripped = text.strip()
    match = re.fullmatch(r"```(?:python|py)?\s*(.*?)\s*```", stripped, re.DOTALL)
    if match:
        return match.group(1).strip() + "\n"
    return text if text.endswith("\n") else text + "\n"


def extract_result(stdout: str) -> tuple[str, object]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return stdout, None
    if isinstance(payload, dict):
        result = payload.get("result")
        if isinstance(result, str):
            return result, payload
        message = payload.get("message")
        if isinstance(message, str):
            return message, payload
    return stdout, payload


def run_one(model: str, task_id: str, system_prompt: str, timeout_s: int,
            max_budget_usd: str | None, force: bool) -> dict:
    td = os.path.join(ROOT, "validation", "tasks", task_id)
    out_dir = os.path.join(ROOT, "runs", "phase1", "python_validation", model, task_id)
    os.makedirs(out_dir, exist_ok=True)

    candidate_path = os.path.join(out_dir, "candidate.py")
    if os.path.isfile(candidate_path) and not force:
        return {"task": task_id, "status": "skipped_existing", "ok": True}

    with open(os.path.join(td, "python_prompt.md"), encoding="utf-8") as f:
        task_prompt = f.read()

    prompt_sent = (
        "# SYSTEM\n\n"
        + system_prompt
        + "\n\n# USER\n\n"
        + task_prompt
    )
    with open(os.path.join(out_dir, "prompt_sent.txt"), "w", encoding="utf-8") as f:
        f.write(prompt_sent)

    cmd = [
        "claude",
        "--print",
        "--model", model,
        "--system-prompt", system_prompt,
        "--tools", "",
        "--output-format", "json",
        "--no-session-persistence",
    ]
    if max_budget_usd:
        cmd.extend(["--max-budget-usd", max_budget_usd])
    cmd.append(task_prompt)

    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )

    with open(os.path.join(out_dir, "raw_stdout.json"), "w", encoding="utf-8") as f:
        f.write(proc.stdout)
    with open(os.path.join(out_dir, "raw_stderr.txt"), "w", encoding="utf-8") as f:
        f.write(proc.stderr)

    result_text, payload = extract_result(proc.stdout)
    if payload is not None:
        with open(os.path.join(out_dir, "raw_payload.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    if proc.returncode != 0 or (isinstance(payload, dict) and payload.get("is_error")):
        return {
            "task": task_id,
            "status": "model_call_failed",
            "ok": False,
            "exit_code": proc.returncode,
            "stderr": proc.stderr[-1000:],
            "result": result_text[-1000:],
        }

    candidate = strip_markdown_fences(result_text)
    with open(candidate_path, "w", encoding="utf-8") as f:
        f.write(candidate)
    return {"task": task_id, "status": "generated", "ok": True}


def run_grade(model: str) -> dict:
    cmd = [PYTHON, "-B", os.path.join(ROOT, "scripts", "grade_phase1_python.py"),
           "--model", model]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"raw_stdout": proc.stdout, "raw_stderr": proc.stderr}
    payload["grade_exit_code"] = proc.returncode
    return payload


def select_tasks(all_tasks: Iterable[str], requested: set[str] | None,
                 limit: int | None) -> list[str]:
    tasks = [tid for tid in all_tasks if requested is None or tid in requested]
    if limit is not None:
        tasks = tasks[:limit]
    return tasks


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True,
                   help="Claude model name, e.g. claude-sonnet-4-6")
    p.add_argument("--tasks", help="comma-separated task ids; default all active")
    p.add_argument("--limit", type=int, help="run only first N selected tasks")
    p.add_argument("--timeout-s", type=int, default=180)
    p.add_argument("--max-budget-usd", default=None)
    p.add_argument("--force", action="store_true")
    p.add_argument("--no-grade", action="store_true")
    args = p.parse_args()

    system_path = os.path.join(ROOT, "prompt", "python_system_prompt.md")
    with open(system_path, encoding="utf-8") as f:
        system_prompt = f.read()

    requested = parse_task_filter(args.tasks)
    tasks = select_tasks(active_tasks(), requested, args.limit)
    if requested is not None:
        missing = sorted(requested - set(tasks))
        if missing:
            print(json.dumps({"ok": False, "missing_tasks": missing}, indent=2))
            return 1

    results = []
    for task_id in tasks:
        try:
            results.append(run_one(
                args.model,
                task_id,
                system_prompt,
                args.timeout_s,
                args.max_budget_usd,
                args.force,
            ))
        except subprocess.TimeoutExpired:
            results.append({"task": task_id, "status": "timeout", "ok": False})

    out = {"model": args.model, "results": results}
    if not args.no_grade:
        out["grade"] = run_grade(args.model)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    model_ok = all(r.get("ok") for r in results)
    grade_ok = args.no_grade or out.get("grade", {}).get("grade_exit_code") == 0
    return 0 if model_ok and grade_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
