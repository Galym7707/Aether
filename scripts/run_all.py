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
PYTHON = sys.executable


def main() -> int:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    results = {
        "reference_programs": [],
        "benchmark_tasks": [],
        "python_equivalents": [],
        "regression_tests": None,
        "additional_tests": [],
    }

    refdir = os.path.join(ROOT, "reference")
    for d in sorted(os.listdir(refdir)):
        td = os.path.join(refdir, d)
        if not os.path.isdir(td):
            continue
        cmd = [PYTHON, "-B", "-m", "transpiler.aether.cli", "test", td]
        r = subprocess.run(cmd, cwd=ROOT, env=env,
                           capture_output=True, text=True)
        results["reference_programs"].append(
            {"id": d, "ok": r.returncode == 0,
             "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}
        )

    cmd = [PYTHON, "-B", "-m", "bench.harness", "run-reference"]
    r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    try:
        results["benchmark_tasks"] = json.loads(r.stdout)
    except Exception:
        results["benchmark_tasks"] = [
            {"ok": False, "raw": r.stdout, "err": r.stderr}
        ]

    cmd = [PYTHON, "-B", "-m", "bench.harness", "run-python-equivalents"]
    r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    try:
        results["python_equivalents"] = json.loads(r.stdout)
    except Exception:
        results["python_equivalents"] = [
            {"ok": False, "raw": r.stdout, "err": r.stderr}
        ]

    reg = os.path.join(ROOT, "tests", "test_regressions.py")
    if os.path.isfile(reg):
        cmd = [PYTHON, "-B", reg]
        r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
        results["regression_tests"] = {
            "ok": r.returncode == 0,
            "stdout": r.stdout.strip(),
            "stderr": r.stderr.strip(),
        }

    for rel in (
        os.path.join("tests", "test_json_diagnostics.py"),
        os.path.join("tests", "test_prelint_ai_syntax_errors.py"),
        os.path.join("tests", "test_list_operations.py"),
        os.path.join("tests", "test_generic_typechecking.py"),
        os.path.join("tests", "test_explicit_generic_calls.py"),
        os.path.join("tests", "test_quantifiers_and_aggregates.py"),
        os.path.join("tests", "test_static_index_diagnostics.py"),
        os.path.join("tests", "test_contract_diagnostics.py"),
        os.path.join("tests", "test_ai_repair_diagnostics.py"),
        os.path.join("tests", "test_safe_list_helpers.py"),
        os.path.join("tests", "test_option_result_helpers.py"),
        os.path.join("tests", "test_match_exhaustiveness.py"),
        os.path.join("tests", "test_higher_order_effects.py"),
        os.path.join("tests", "test_function_type_effects.py"),
        os.path.join("tests", "test_effect_row_precision.py"),
        os.path.join("tests", "test_deterministic_runtime.py"),
        os.path.join("tests", "test_loop_invariants_and_records.py"),
        os.path.join("tests", "test_continue_loop_invariants.py"),
        os.path.join("tests", "test_record_literals.py"),
    ):
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            continue
        cmd = [PYTHON, "-B", path]
        r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
        results["additional_tests"].append({
            "id": rel,
            "ok": r.returncode == 0,
            "stdout": r.stdout.strip(),
            "stderr": r.stderr.strip(),
        })

    fuzz = os.path.join(ROOT, "scripts", "fuzz_parser.py")
    if os.path.isfile(fuzz):
        cmd = [PYTHON, "-B", fuzz, "--rounds", "200", "--mode", "all"]
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
    n_py_ok = sum(1 for r in results["python_equivalents"] if r.get("ok"))
    n_py = len(results["python_equivalents"])
    reg_ok = bool(results["regression_tests"] and results["regression_tests"]["ok"])
    add_ok = all(r.get("ok") for r in results["additional_tests"])
    fuzz_ok = bool(results.get("parser_fuzz") and results["parser_fuzz"]["ok"])
    print(f"# reference:    {n_ref_ok}/{n_ref}", file=sys.stderr)
    print(f"# bench:        {n_bench_ok}/{n_bench}", file=sys.stderr)
    print(f"# python eq:    {n_py_ok}/{n_py}", file=sys.stderr)
    print(f"# regression:   {'PASS' if reg_ok else 'FAIL'}", file=sys.stderr)
    print(f"# additional:   {'PASS' if add_ok else 'FAIL'} ({len(results['additional_tests'])} scripts)", file=sys.stderr)
    print(f"# fuzz:         {'PASS' if fuzz_ok else 'FAIL'} (200 rounds x 3 modes)", file=sys.stderr)
    everything = (
        (n_ref_ok == n_ref)
        and (n_bench_ok == n_bench)
        and (n_py_ok == n_py)
        and reg_ok
        and add_ok
        and fuzz_ok
    )
    return 0 if everything else 1


if __name__ == "__main__":
    raise SystemExit(main())
