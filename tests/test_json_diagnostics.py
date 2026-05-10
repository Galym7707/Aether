from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_cli(source: str, command: str):
    path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".aeth", delete=False, encoding="utf-8"
        ) as f:
            f.write(source)
            path = f.name
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "transpiler.aether.cli",
                "--json",
                command,
                path,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0, proc
        payload = json.loads(proc.stderr)
        diag = payload["diagnostic"]
        for key in (
            "code",
            "category",
            "severity",
            "message",
            "line",
            "column",
            "position",
            "source_snippet",
            "suggestion",
        ):
            assert key in diag, diag
        assert isinstance(diag["line"], int), diag
        assert isinstance(diag["column"], int), diag
        return proc, diag
    finally:
        if path and os.path.exists(path):
            os.unlink(path)


def test_syntax_error_json_diagnostic():
    _, diag = _run_cli(
        """
fn bad(x: Int) -> Int
  effects pure
do
  return x
end
""",
        "check",
    )
    assert diag["code"] == "E0001", diag
    assert diag["category"] == "parse", diag
    assert "function" in diag["suggestion"], diag


def test_type_error_json_diagnostic():
    _, diag = _run_cli(
        """
function bad() returns Int
  effects pure
do
  return "oops"
end
""",
        "check",
    )
    assert diag["code"] == "TYPE_RETURN_MISMATCH", diag
    assert diag["category"] == "type", diag
    assert "expected Int" in diag["message"], diag
    assert diag["expected"] == "Int", diag
    assert diag["actual"] == "String", diag


def test_contract_violation_json_diagnostic():
    _, diag = _run_cli(
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
""",
        "run",
    )
    assert diag["code"] == "E0301", diag
    assert diag["category"] == "contract", diag
    assert diag["line"] > 0, diag
    assert diag["source_snippet"], diag


def test_refinement_violation_json_diagnostic():
    _, diag = _run_cli(
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
""",
        "run",
    )
    assert diag["code"] == "E0302", diag
    assert diag["category"] == "refinement", diag
    assert diag["line"] > 0, diag
    assert diag["source_snippet"], diag


def test_effect_violation_json_diagnostic():
    _, diag = _run_cli(
        """
function helper() returns Unit
  effects pure
do
  print("bad")
end
""",
        "check",
    )
    assert diag["code"] == "EFFECT_NOT_COVERED", diag
    assert diag["category"] == "effect", diag
    assert diag["source_snippet"], diag


if __name__ == "__main__":
    test_syntax_error_json_diagnostic()
    test_type_error_json_diagnostic()
    test_contract_violation_json_diagnostic()
    test_refinement_violation_json_diagnostic()
    test_effect_violation_json_diagnostic()
    print("JSON DIAGNOSTIC TESTS PASS")
