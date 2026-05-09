from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_cli(source: str, command: str = "check"):
    path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".aeth", delete=False, encoding="utf-8") as f:
            f.write(source)
            path = f.name
        return subprocess.run(
            [sys.executable, "-B", "-m", "transpiler.aether.cli", "--json", command, path],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
    finally:
        if path and os.path.exists(path):
            os.unlink(path)


def _diag(source: str, command: str = "check") -> dict:
    proc = _run_cli(source, command)
    assert proc.returncode != 0, proc
    return json.loads(proc.stderr)["diagnostic"]


def test_static_out_of_bounds_positive_index():
    diag = _diag(
        """
function main() returns Unit
  effects pure
do
  let xs = [1, 2, 3]
  let value: Int = xs[3]
end
"""
    )
    assert diag["code"] == "INDEX_OUT_OF_BOUNDS_STATIC", diag
    assert diag["valid_range"] == "0..2", diag
    assert diag["actual_index"] == 3, diag
    assert diag["line"] == 6, diag
    assert diag["source_snippet"].strip() == "let value: Int = xs[3]", diag


def test_negative_index_is_unsupported():
    diag = _diag(
        """
function main() returns Unit
  effects pure
do
  let xs = [1, 2, 3]
  let value: Int = xs[-1]
end
"""
    )
    assert diag["code"] == "INDEX_NEGATIVE_UNSUPPORTED", diag
    assert diag["actual_index"] == -1, diag


def test_non_integer_index_is_rejected():
    diag = _diag(
        """
function main() returns Unit
  effects pure
do
  let xs = [1, 2, 3]
  let value: Int = xs["0"]
end
"""
    )
    assert diag["code"] == "INDEX_TYPE_INVALID", diag
    assert diag["expected"] == "Int", diag
    assert diag["actual"] == "String", diag


def test_cli_exit_codes_for_valid_and_invalid_programs():
    valid = _run_cli(
        """
function main() returns Unit
  effects pure
do
  let xs = [1, 2, 3]
  let value: Int = xs[2]
end
"""
    )
    assert valid.returncode == 0, valid.stderr
    invalid = _run_cli(
        """
function main() returns Unit
  effects pure
do
  let xs = [1, 2, 3]
  let value: Int = xs[4]
end
"""
    )
    assert invalid.returncode != 0, invalid
    assert json.loads(invalid.stderr)["diagnostic"]["code"] == "INDEX_OUT_OF_BOUNDS_STATIC"


def test_dynamic_out_of_bounds_uses_structured_runtime_diagnostic():
    proc = _run_cli(
        """
function at(xs: List<Int>, index: Int) returns Int
  effects pure
do
  return xs[index]
end

function main() returns Unit
  effects log
do
  print(intToString(at([1, 2], 3)))
end
""",
        command="run",
    )
    assert proc.returncode != 0, proc
    diag = json.loads(proc.stderr)["diagnostic"]
    assert diag["code"] == "INDEX_OUT_OF_BOUNDS_RUNTIME", diag
    assert diag["valid_range"] == "0..1", diag
    assert diag["actual_index"] == 3, diag
    assert "Traceback" not in proc.stderr, proc.stderr


if __name__ == "__main__":
    test_static_out_of_bounds_positive_index()
    test_negative_index_is_unsupported()
    test_non_integer_index_is_rejected()
    test_cli_exit_codes_for_valid_and_invalid_programs()
    test_dynamic_out_of_bounds_uses_structured_runtime_diagnostic()
    print("STATIC INDEX DIAGNOSTIC TESTS PASS")
