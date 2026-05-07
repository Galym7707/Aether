"""Grade Phase 1.4 Python candidate solutions for a given model.

Walks runs/phase1/python_validation/<model>/<task_id>/candidate.py for each
active validation task, runs the candidate, saves grade.json, and writes
runs/phase1/python_validation/<model>/_summary.json.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PYTHON = sys.executable


def run_python(path: str, stdin_text: str, timeout_ms: int) -> Dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    t0 = time.time()
    try:
        proc = subprocess.run(
            [PYTHON, "-B", path],
            cwd=os.path.dirname(path),
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=timeout_ms / 1000.0 if timeout_ms > 0 else None,
            env=env,
        )
        return {
            "stage": "exec",
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
            "elapsed_ms": int((time.time() - t0) * 1000),
        }
    except subprocess.TimeoutExpired as e:
        return {
            "stage": "timeout",
            "stdout": e.stdout or "",
            "stderr": e.stderr or "",
            "exit_code": 124,
            "elapsed_ms": int((time.time() - t0) * 1000),
        }


def grade_candidate(task_id: str, cfg: Dict[str, Any], cand_path: str) -> Dict[str, Any]:
    if not os.path.isfile(cand_path):
        return {
            "task": task_id,
            "ok": False,
            "reason": "no_candidate",
            "stage": None,
            "expected": cfg.get("expected_stdout", ""),
            "actual": None,
        }

    out = run_python(
        cand_path,
        stdin_text=cfg.get("stdin", "") or "",
        timeout_ms=int(cfg.get("timeout_ms", 5000)),
    )
    expected_stdout = cfg.get("expected_stdout", "")
    expected_exit_code = int(cfg.get("expected_exit_code", 0))
    expected_stderr = cfg.get("expected_stderr", "")
    ok = (
        out["exit_code"] == expected_exit_code
        and out["stdout"] == expected_stdout
        and out["stderr"] == expected_stderr
    )
    failures = []
    if out["exit_code"] != expected_exit_code:
        failures.append(
            f"exit_code mismatch: expected {expected_exit_code}, got {out['exit_code']}"
        )
    if out["stdout"] != expected_stdout:
        failures.append(
            f"stdout mismatch: expected {expected_stdout!r}, got {out['stdout']!r}"
        )
    if out["stderr"] != expected_stderr:
        failures.append(
            f"stderr mismatch: expected {expected_stderr!r}, got {out['stderr']!r}"
        )
    if out["exit_code"] == 124:
        failures.append(f"process timed out after timeout_ms={cfg.get('timeout_ms', 5000)}")

    return {
        "task": task_id,
        "ok": bool(ok),
        "stage": out["stage"],
        "elapsed_ms": out["elapsed_ms"],
        "expected": expected_stdout,
        "actual": out["stdout"],
        "stderr": out["stderr"],
        "exit_code": out["exit_code"],
        "failure_messages": failures,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--candidate-name", default="candidate.py")
    args = p.parse_args()

    val_dir = os.path.join(ROOT, "validation", "tasks")
    out_dir = os.path.join(ROOT, "runs", "phase1", "python_validation", args.model)
    os.makedirs(out_dir, exist_ok=True)

    summary = []
    for tid in sorted(os.listdir(val_dir)):
        td = os.path.join(val_dir, tid)
        cfg_path = os.path.join(td, "grader.json")
        py_prompt = os.path.join(td, "python_prompt.md")
        if not (os.path.isfile(cfg_path) and os.path.isfile(py_prompt)):
            continue
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        if cfg.get("deprecated"):
            continue
        cand_dir = os.path.join(out_dir, tid)
        cand_path = os.path.join(cand_dir, args.candidate_name)
        grade_path = os.path.join(cand_dir, "grade.json")
        record = grade_candidate(tid, cfg, cand_path)
        os.makedirs(cand_dir, exist_ok=True)
        with open(grade_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
        summary.append({
            "task": tid,
            "ok": record["ok"],
            "stage": record.get("stage"),
            "elapsed_ms": record.get("elapsed_ms"),
            "reason": record.get("reason"),
        })

    summary_path = os.path.join(out_dir, "_summary.json")
    n_ok = sum(1 for s in summary if s["ok"])
    n = len(summary)
    pct = (100.0 * n_ok / n) if n else 0.0
    summary_doc = {
        "model": args.model,
        "language": "python",
        "ok": n_ok,
        "total": n,
        "first_attempt_pct": round(pct, 1),
        "results": summary,
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_doc, f, indent=2)

    print(json.dumps(summary_doc, indent=2))
    return 0 if n_ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
