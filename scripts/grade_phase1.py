"""Grade Phase 1.1 candidate solutions for a given model.

Walks runs/phase1/validation/<model>/<task_id>/candidate.aeth for each
validation task, runs the harness (compile_and_run), saves grade.json,
and writes runs/phase1/validation/<model>/_summary.json plus an
appended row to runs/phase1/validation_summary.md.
"""

from __future__ import annotations
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "transpiler"))

from bench.harness import compile_and_run  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    args = p.parse_args()
    model = args.model
    val_dir = os.path.join(ROOT, "validation", "tasks")
    out_dir = os.path.join(ROOT, "runs", "phase1", "validation", model)
    os.makedirs(out_dir, exist_ok=True)

    summary = []
    for tid in sorted(os.listdir(val_dir)):
        td = os.path.join(val_dir, tid)
        cfg_path = os.path.join(td, "grader.json")
        if not os.path.isfile(cfg_path):
            continue
        with open(cfg_path) as f:
            cfg = json.load(f)
        if cfg.get("deprecated"):
            continue
        cand_dir = os.path.join(out_dir, tid)
        cand_path = os.path.join(cand_dir, "candidate.aeth")
        grade_path = os.path.join(cand_dir, "grade.json")
        if not os.path.isfile(cand_path):
            summary.append({"task": tid, "ok": False,
                            "reason": "no_candidate", "stage": None})
            continue
        with open(cand_path) as f:
            src = f.read()
        out = compile_and_run(
            src, cand_path,
            stdin_text=cfg.get("stdin", "") or "",
            timeout_ms=int(cfg.get("timeout_ms", 5000)),
        )
        ok = out.get("ok") and out.get("actual") == cfg.get("expected_stdout", "")
        record = {
            "task": tid,
            "ok": bool(ok),
            "stage": out.get("stage"),
            "elapsed_ms": out.get("elapsed_ms"),
            "diagnostic": out.get("diagnostic"),
            "expected": cfg.get("expected_stdout", ""),
            "actual": out.get("actual"),
        }
        os.makedirs(cand_dir, exist_ok=True)
        with open(grade_path, "w") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
        summary.append({k: record[k] for k in ("task", "ok", "stage", "elapsed_ms")})

    summary_path = os.path.join(out_dir, "_summary.json")
    with open(summary_path, "w") as f:
        json.dump({"model": model, "results": summary}, f, indent=2)

    n_ok = sum(1 for s in summary if s["ok"])
    n = len(summary)
    pct = (100.0 * n_ok / n) if n else 0.0
    print(json.dumps({"model": model, "ok": n_ok, "total": n,
                      "first_attempt_pct": round(pct, 1)},
                     indent=2))
    return 0 if n_ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
