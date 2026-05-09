from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_json(source: str, command: str = "run"):
    path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".aeth", delete=False, encoding="utf-8") as f:
            f.write(source)
            path = f.name
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "transpiler.aether.cli", "--json", command, path],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0, proc
        return json.loads(proc.stderr)["diagnostic"]
    finally:
        if path and os.path.exists(path):
            os.unlink(path)


def _assert_rich_diagnostic(diag: dict) -> None:
    for key in ("code", "category", "message", "line", "column", "source_snippet", "hint"):
        assert key in diag, diag
    assert diag["line"] > 0, diag
    assert diag["column"] > 0, diag
    assert diag["source_snippet"], diag


def test_requires_violation_names_function_contract_and_actual_value():
    diag = _run_json(
        """
function positiveOnly(x: Int) returns Int
  requires x > 0
  effects pure
do
  return x
end

function main() returns Unit
  effects log
do
  print(intToString(positiveOnly(0)))
end
"""
    )
    _assert_rich_diagnostic(diag)
    assert diag["code"] == "E0301", diag
    assert diag["category"] == "contract", diag
    assert diag["function"] == "positiveOnly", diag
    assert diag["contract_kind"] == "requires", diag
    assert diag["actual_value"]["x"] == "0", diag
    assert "requires x > 0" in diag["source_snippet"], diag
    assert diag["callsite_line"] == 12, diag
    assert "positiveOnly(0)" in diag["callsite_source_snippet"], diag


def test_ensures_violation_names_function_and_result_value():
    diag = _run_json(
        """
function liar() returns Int
  ensures positive?(result)
  effects pure
do
  return 0
end

function positive?(x: Int) returns Bool
  effects pure
do
  return x > 0
end

function main() returns Unit
  effects log
do
  print(intToString(liar()))
end
"""
    )
    _assert_rich_diagnostic(diag)
    assert diag["code"] == "E0301", diag
    assert diag["category"] == "contract", diag
    assert diag["function"] == "liar", diag
    assert diag["contract_kind"] == "ensures", diag
    assert diag["actual_value"]["result"] == "0", diag
    assert "ensures positive?(result)" in diag["source_snippet"], diag
    assert diag["callsite_line"] == 18, diag
    assert "liar()" in diag["callsite_source_snippet"], diag


def test_refinement_violation_names_function_argument_and_actual_value():
    diag = _run_json(
        """
type PositiveInt = Int where self > 0

function show(n: PositiveInt) returns String
  effects pure
do
  return intToString(n)
end

function main() returns Unit
  effects log
do
  print(show(0))
end
"""
    )
    _assert_rich_diagnostic(diag)
    assert diag["code"] == "E0302", diag
    assert diag["category"] == "refinement", diag
    assert diag["function"] == "show", diag
    assert diag["argument"] == "n", diag
    assert diag["actual_value"] == "0", diag
    assert diag["type_name"] == "PositiveInt", diag
    assert diag["callsite_line"] == 13, diag
    assert "show(0)" in diag["callsite_source_snippet"], diag


def test_type_json_diagnostic_has_expected_actual_and_source_span():
    diag = _run_json(
        """
function bad() returns Int
  effects pure
do
  return "oops"
end
""",
        command="check",
    )
    _assert_rich_diagnostic(diag)
    assert diag["code"] == "TYPE_RETURN_MISMATCH", diag
    assert diag["expected"] == "Int", diag
    assert diag["actual"] == "String", diag


if __name__ == "__main__":
    test_requires_violation_names_function_contract_and_actual_value()
    test_ensures_violation_names_function_and_result_value()
    test_refinement_violation_names_function_argument_and_actual_value()
    test_type_json_diagnostic_has_expected_actual_and_source_span()
    print("CONTRACT DIAGNOSTIC TESTS PASS")
