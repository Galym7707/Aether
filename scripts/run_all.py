"""Run every reference program, every benchmark reference solution, and
the regression test suite.

Exit 0 if everything passes, 1 otherwise.
"""

from __future__ import annotations
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    results = {"reference_programs": [], "benchmark_tasks": [], "regression_tests": None}

    refdir = os.path.join(ROOT, "reference")
    for d in sorted(os.listdir(refdir)):
        td = os.path.join(refdir, d)
        if not os.path.isdir(td):
            continue
        cmd = ["python3", "-B", "-m", "transpiler.aether.cli", "test", td]
        r = subprocess.run(cmd, cwd=ROOT, env=env,
                           capture_output=True, text=True)
        results["reference_programs"].append(
            {"id": d, "ok": r.returncode == 0,
             "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}
        )

    cmd = ["python3", "-B", "-m", "bench.harness", "run-reference"]
    r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    try:
        results["benchmark_tasks"] = json.loads(r.stdout)
    except Exception:
        results["benchmark_tasks"] = [
            {"ok": False, "raw": r.stdout, "err": r.stderr}
        ]

    reg = os.path.join(ROOT, "tests", "test_regressions.py")
    if os.path.isfile(reg):
        cmd = ["python3", "-B", reg]
        r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
        results["regression_tests"] = {
            "ok": r.returncode == 0,
            "stdout": r.stdout.strip(),
            "stderr": r.stderr.strip(),
        }

    fuzz = os.path.join(ROOT, "scripts", "fuzz_parser.py")
    if os.path.isfile(fuzz):
        cmd = ["python3", "-B", fuzz, "--rounds", "200", "--mode", "all"]
        r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
        results["parser_fuzz"] = {
            "ok": r.returncode == 0,
            "stdout_tail": r.stdout.strip().splitlines()[-12:] if r.stdout else [],
            "stderr": r.stderr.strip()[:400],
        }

    print(json.dumps(results, indent=2))
    n_ref_ok = sum(1 for r in results["reference_programs"] if r.get("ok"))
    n_ref = len(results["reference_programs"])
    n_bench_ok = sum(1 for r in results["benchmark_tasks"] if r.get("ok"))
    n_bench = len(results["benchmark_tasks"])
    reg_ok = bool(results["regression_tests"] and results["regression_tests"]["ok"])
    fuzz_ok = bool(results.get("parser_fuzz") and results["parser_fuzz"]["ok"])
    print(f"# reference:    {n_ref_ok}/{n_ref}", file=sys.stderr)
    print(f"# bench:        {n_bench_ok}/{n_bench}", file=sys.stderr)
    print(f"# regression:   {'PASS' if reg_ok else 'FAIL'}", file=sys.stderr)
    print(f"# fuzz:         {'PASS' if fuzz_ok else 'FAIL'} (200 rounds x 3 modes)", file=sys.stderr)
    everything = (n_ref_ok == n_ref) and (n_bench_ok == n_bench) and reg_ok and fuzz_ok
    return 0 if everything else 1


if __name__ == "__main__":
    raise SystemExit(main())
