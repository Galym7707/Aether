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


def _check_ok(source: str) -> None:
    proc = _run_cli(source)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["ok"] is True


def test_valid_list_int_passes():
    _check_ok(
        """
function main() returns Unit
  effects pure
do
  let xs: List<Int> = [1, 2, 3]
  let first: Int = xs[0]
end
"""
    )


def test_invalid_mixed_list_int_fails_with_expected_actual():
    diag = _diag(
        """
function main() returns Unit
  effects pure
do
  let xs: List<Int> = [1, 2, "bad"]
end
"""
    )
    assert diag["code"] == "TYPE_LIST_ELEMENT_MISMATCH", diag
    assert diag["expected"] == "Int", diag
    assert diag["actual"] == "String", diag
    assert diag["line"] == 5, diag
    assert diag["source_snippet"].strip() == 'let xs: List<Int> = [1, 2, "bad"]', diag


def test_empty_list_without_annotation_fails_clearly():
    diag = _diag(
        """
function main() returns Unit
  effects pure
do
  let xs = []
end
"""
    )
    assert diag["code"] == "TYPE_EMPTY_LIST_NEEDS_ANNOTATION", diag
    assert diag["expected"] == "List<T>", diag
    assert diag["actual"] == "List<?>", diag


def test_nested_list_generic_type_passes_and_mismatch_fails():
    _check_ok(
        """
function main() returns Unit
  effects pure
do
  let xs: List<List<Int>> = [[1], [2, 3]]
end
"""
    )
    diag = _diag(
        """
function main() returns Unit
  effects pure
do
  let xs: List<List<Int>> = [[1], ["bad"]]
end
"""
    )
    assert diag["code"] == "TYPE_LIST_ELEMENT_MISMATCH", diag
    assert diag["expected"] == "Int", diag
    assert diag["actual"] == "String", diag


def test_wrong_append_type_fails():
    diag = _diag(
        """
function main() returns Unit
  effects pure
do
  let xs: List<Int> = [1, 2]
  let ys: List<Int> = append(xs, "bad")
end
"""
    )
    assert diag["code"] == "TYPE_LIST_APPEND_MISMATCH", diag
    assert diag["expected"] == "Int", diag
    assert diag["actual"] == "String", diag


def test_method_append_push_are_unsupported_syntax():
    diag = _diag(
        """
function main() returns Unit
  effects pure
do
  let xs: List<Int> = [1]
  xs.append(2)
end
"""
    )
    assert diag["code"] == "E0009", diag
    assert "append(xs, value)" in diag["hint"], diag


def test_generic_identity_inference_and_mismatch():
    _check_ok(
        """
function identity<T>(x: T) returns T
  effects pure
do
  return x
end

function main() returns Unit
  effects pure
do
  let value: Int = identity(5)
end
"""
    )
    diag = _diag(
        """
function identity<T>(x: T) returns T
  effects pure
do
  return x
end

function main() returns Unit
  effects pure
do
  let value: Int = identity("bad")
end
"""
    )
    assert diag["code"] == "TYPE_BINDING_MISMATCH", diag
    assert diag["expected"] == "Int", diag
    assert diag["actual"] == "String", diag


def test_generic_function_arguments_must_agree():
    diag = _diag(
        """
function choose<T>(a: T, b: T) returns T
  effects pure
do
  return a
end

function main() returns Unit
  effects pure
do
  let value: Int = choose(1, "bad")
end
"""
    )
    assert diag["code"] == "TYPE_ARGUMENT_MISMATCH", diag
    assert diag["expected"] == "Int", diag
    assert diag["actual"] == "String", diag


def test_explicit_generic_call_syntax_is_rejected():
    diag = _diag(
        """
function identity<T>(x: T) returns T
  effects pure
do
  return x
end

function main() returns Unit
  effects pure
do
  let value: Int = identity<Int>(5)
end
"""
    )
    assert diag["code"] == "E0008", diag


if __name__ == "__main__":
    test_valid_list_int_passes()
    test_invalid_mixed_list_int_fails_with_expected_actual()
    test_empty_list_without_annotation_fails_clearly()
    test_nested_list_generic_type_passes_and_mismatch_fails()
    test_wrong_append_type_fails()
    test_method_append_push_are_unsupported_syntax()
    test_generic_identity_inference_and_mismatch()
    test_generic_function_arguments_must_agree()
    test_explicit_generic_call_syntax_is_rejected()
    print("GENERIC TYPECHECKING TESTS PASS")
