"""Run reference solutions for every validation task.

Skips tasks whose grader.json has "deprecated": true.
"""

from __future__ import annotations
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "transpiler"))

from bench.harness import compile_and_run  # noqa: E402


def main() -> int:
    base = os.path.join(HERE, "tasks")
    summary = []
    skipped = 0
    for tid in sorted(os.listdir(base)):
        td = os.path.join(base, tid)
        ref = os.path.join(td, "reference.aeth")
        cfg_path = os.path.join(td, "grader.json")
        if not (os.path.isfile(ref) and os.path.isfile(cfg_path)):
            continue
        with open(cfg_path) as f:
            cfg = json.load(f)
        if cfg.get("deprecated"):
            skipped += 1
            continue
        with open(ref) as f:
            src = f.read()
        out = compile_and_run(
            src, ref,
            stdin_text=cfg.get("stdin", "") or "",
            timeout_ms=int(cfg.get("timeout_ms", 5000)),
        )
        ok = out.get("ok") and out.get("actual") == cfg.get("expected_stdout", "")
        summary.append({
            "id": tid,
            "ok": bool(ok),
            "stage": out.get("stage"),
            "elapsed_ms": out.get("elapsed_ms"),
            "diagnostic": None if ok else out.get("diagnostic"),
            "expected": cfg.get("expected_stdout", "") if not ok else None,
            "actual": out.get("actual") if not ok else None,
        })
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    n_ok = sum(1 for s in summary if s["ok"])
    print(f"# {n_ok}/{len(summary)} validation references pass "
          f"({skipped} deprecated task(s) skipped)", file=sys.stderr)
    return 0 if n_ok == len(summary) else 1


if __name__ == "__main__":
    raise SystemExit(main())
