"""Run Python reference solutions for every active validation task.

Skips tasks whose grader.json has "deprecated": true.
"""

from __future__ import annotations

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
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
            "elapsed_ms": int((time.time() - t0) * 1000),
        }
    except subprocess.TimeoutExpired as e:
        return {
            "stdout": e.stdout or "",
            "stderr": e.stderr or "",
            "exit_code": 124,
            "elapsed_ms": int((time.time() - t0) * 1000),
        }


def main() -> int:
    base = os.path.join(HERE, "tasks")
    summary = []
    skipped = 0
    for tid in sorted(os.listdir(base)):
        td = os.path.join(base, tid)
        ref = os.path.join(td, "python_reference.py")
        cfg_path = os.path.join(td, "grader.json")
        prompt_path = os.path.join(td, "python_prompt.md")
        if not (os.path.isfile(ref) and os.path.isfile(cfg_path)):
            continue
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        if cfg.get("deprecated"):
            skipped += 1
            continue
        out = run_python(
            ref,
            stdin_text=cfg.get("stdin", "") or "",
            timeout_ms=int(cfg.get("timeout_ms", 5000)),
        )
        ok = (
            out["exit_code"] == int(cfg.get("expected_exit_code", 0))
            and out["stdout"] == cfg.get("expected_stdout", "")
            and out["stderr"] == cfg.get("expected_stderr", "")
        )
        summary.append({
            "id": tid,
            "ok": bool(ok),
            "has_python_prompt": os.path.isfile(prompt_path),
            "exit_code": out["exit_code"],
            "elapsed_ms": out["elapsed_ms"],
            "expected": cfg.get("expected_stdout", "") if not ok else None,
            "actual": out["stdout"] if not ok else None,
            "stderr": out["stderr"] if not ok else None,
        })
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    n_ok = sum(1 for s in summary if s["ok"])
    print(f"# {n_ok}/{len(summary)} python validation references pass "
          f"({skipped} deprecated task(s) skipped)", file=sys.stderr)
    return 0 if n_ok == len(summary) else 1


if __name__ == "__main__":
    raise SystemExit(main())
