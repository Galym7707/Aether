from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


COMMON_DEFS = """
function id<T>(x: T) returns T
  effects pure
do
  return x
end

function choose<T>(a: T, b: T) returns T
  effects pure
do
  return a
end

function singleton<T>(x: T) returns List<T>
  effects pure
do
  return [x]
end

function wrapOption<T>(x: T) returns Option<T>
  effects pure
do
  return Some(x)
end

function makeResult<T, E>(x: T) returns Result<T, E>
  effects pure
do
  return Ok(x)
end

function nonGeneric(x: Int) returns Int
  effects pure
do
  return x
end
"""


def _run_cli(source: str, command: str = "check") -> subprocess.CompletedProcess[str]:
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


def _check_ok(source: str) -> None:
    proc = _run_cli(source)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["ok"] is True


def _diag(source: str, command: str = "check") -> dict:
    proc = _run_cli(source, command)
    assert proc.returncode != 0, proc
    return json.loads(proc.stderr.splitlines()[0])["diagnostic"]


def test_explicit_id_int_passes():
    _check_ok(COMMON_DEFS + """
function main() returns Unit
  effects pure
do
  let a: Int = id<Int>(5)
end
""")


def test_explicit_id_string_passes():
    _check_ok(COMMON_DEFS + """
function main() returns Unit
  effects pure
do
  let a: String = id<String>("x")
end
""")


def test_explicit_choose_int_passes():
    _check_ok(COMMON_DEFS + """
function main() returns Unit
  effects pure
do
  let a: Int = choose<Int>(1, 2)
end
""")


def test_explicit_singleton_list_passes():
    _check_ok(COMMON_DEFS + """
function main() returns Unit
  effects pure
do
  let xs: List<Int> = singleton<Int>(5)
end
""")


def test_explicit_wrap_option_passes():
    _check_ok(COMMON_DEFS + """
function main() returns Unit
  effects pure
do
  let x: Option<Int> = wrapOption<Int>(5)
end
""")


def test_explicit_make_result_passes():
    _check_ok(COMMON_DEFS + """
function main() returns Unit
  effects pure
do
  let x: Result<Int, String> = makeResult<Int, String>(5)
end
""")


def test_nested_type_argument_passes():
    _check_ok(COMMON_DEFS + """
function main() returns Unit
  effects pure
do
  let xs: List<Int> = id<List<Int>>([1, 2])
end
""")


def test_deeply_nested_type_argument_passes():
    _check_ok(COMMON_DEFS + """
function main() returns Unit
  effects pure
do
  let x: Result<List<Int>, String> = id<Result<List<Int>, String>>(Ok([1, 2]))
end
""")


def test_inferred_calls_still_pass():
    _check_ok(COMMON_DEFS + """
function main() returns Unit
  effects pure
do
  let a: Int = id(5)
  let b: String = choose("x", "y")
  let xs: List<Int> = singleton(1)
end
""")


def test_ast_json_preserves_type_arguments():
    proc = _run_cli(COMMON_DEFS + """
function main() returns Unit
  effects pure
do
  let a: Int = id<Int>(5)
end
""", "ast")
    assert proc.returncode == 0, proc.stderr
    ast = json.loads(proc.stdout)
    let_stmt = ast["decls"][-1]["body"][0]
    assert let_stmt["value"]["kind"] == "Call"
    assert let_stmt["value"]["type_args"] == [{"kind": "TypeName", "name": "Int"}]


def test_non_generic_explicit_call_fails():
    diag = _diag(COMMON_DEFS + """
function main() returns Unit
  effects pure
do
  let a: Int = nonGeneric<Int>(5)
end
""")
    assert diag["code"] == "GENERIC_CALL_ON_NON_GENERIC", diag


def test_explicit_type_arg_arity_fails():
    diag = _diag(COMMON_DEFS + """
function main() returns Unit
  effects pure
do
  let a: Int = id<Int, String>(5)
end
""")
    assert diag["code"] == "GENERIC_TYPE_ARG_ARITY", diag


def test_explicit_type_arg_argument_mismatch_fails():
    diag = _diag(COMMON_DEFS + """
function main() returns Unit
  effects pure
do
  let a: Int = id<Int>("bad")
end
""")
    assert diag["code"] == "GENERIC_TYPE_ARG_MISMATCH", diag
    assert diag["expected"] == "Int", diag
    assert diag["actual"] == "String", diag


def test_explicit_type_arg_return_mismatch_fails():
    diag = _diag(COMMON_DEFS + """
function main() returns Unit
  effects pure
do
  let a: String = id<Int>(5)
end
""")
    assert diag["code"] in {"GENERIC_RETURN_TYPE_MISMATCH", "TYPE_BINDING_MISMATCH"}, diag


def test_square_bracket_generic_call_has_repair_hint():
    diag = _diag(COMMON_DEFS + """
function main() returns Unit
  effects pure
do
  let a: Int = id[Integer](5)
end
""")
    assert diag["code"] == "E0008", diag
    assert "Use f<Int>(x)" in diag["hint"], diag


def test_malformed_explicit_generic_call_has_structured_parse_diagnostic():
    diag = _diag(COMMON_DEFS + """
function main() returns Unit
  effects pure
do
  let a: Int = id<Int(5)
end
""")
    assert diag["code"] == "E0201", diag
    assert "Use f<Int>(x)" in diag["hint"], diag


if __name__ == "__main__":
    test_explicit_id_int_passes()
    test_explicit_id_string_passes()
    test_explicit_choose_int_passes()
    test_explicit_singleton_list_passes()
    test_explicit_wrap_option_passes()
    test_explicit_make_result_passes()
    test_nested_type_argument_passes()
    test_deeply_nested_type_argument_passes()
    test_inferred_calls_still_pass()
    test_ast_json_preserves_type_arguments()
    test_non_generic_explicit_call_fails()
    test_explicit_type_arg_arity_fails()
    test_explicit_type_arg_argument_mismatch_fails()
    test_explicit_type_arg_return_mismatch_fails()
    test_square_bracket_generic_call_has_repair_hint()
    test_malformed_explicit_generic_call_has_structured_parse_diagnostic()
    print("EXPLICIT GENERIC CALL TESTS PASS")
