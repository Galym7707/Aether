from __future__ import annotations

import os
import sys
from textwrap import dedent

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from transpiler.aether.agent_sdk import check_source, run_source


def _run(source: str):
    result = run_source(dedent(source).strip() + "\n", "<option-result-helper-test>")
    assert result.ok is True, result.to_dict()
    return result


def _bad_check(source: str):
    result = check_source(dedent(source).strip() + "\n", "<option-result-helper-test>")
    assert result.ok is False, result.to_dict()
    return result


def _bad_run(source: str):
    result = run_source(dedent(source).strip() + "\n", "<option-result-helper-test>")
    assert result.ok is False, result.to_dict()
    return result


def test_option_predicates_and_unwrap_or():
    result = _run(
        """
        function main() returns Unit
          effects log
        do
          if isSome(Some(1)) then
            print("some")
          end
          if isNone(None()) then
            print("none")
          end
          print(intToString(unwrapOr(Some(1), 0)))
          print(intToString(unwrapOr(None(), 0)))
        end
        """
    )
    assert result.stdout == "some\nnone\n1\n0\n", result.to_dict()


def test_map_option_and_and_then_option():
    result = _run(
        """
        function double(x: Int) returns Int
          effects pure
        do
          return x * 2
        end

        function safeHalf(x: Int) returns Option<Int>
          effects pure
        do
          if x % 2 == 0 then
            return Some(x / 2)
          end
          return None()
        end

        function describe(opt: Option<Int>) returns String
          effects pure
        do
          match opt do
            case Some(value) do
              return intToString(value)
            end
            case None() do
              return "none"
            end
          end
        end

        function main() returns Unit
          effects log
        do
          print(describe(mapOption(Some(2), double)))
          print(describe(mapOption(None(), double)))
          print(describe(andThenOption(Some(2), safeHalf)))
        end
        """
    )
    assert result.stdout == "4\nnone\n1\n", result.to_dict()


def test_expect_some_none_gives_structured_diagnostic():
    result = _bad_run(
        """
        function main() returns Unit
          effects log
        do
          print(intToString(expectSome(None(), "missing option")))
        end
        """
    )
    diag = result.diagnostic or {}
    assert diag.get("code") == "EXPECT_SOME_FAILED", result.to_dict()
    assert diag.get("category") == "runtime", result.to_dict()
    assert diag.get("line", 0) > 0, diag
    assert diag.get("source_snippet"), diag


def test_result_predicates_and_unwrap_or_result():
    result = _run(
        """
        function main() returns Unit
          effects log
        do
          if isOk(Ok(1)) then
            print("ok")
          end
          if isErr(Err("bad")) then
            print("err")
          end
          print(intToString(unwrapOrResult(Ok(1), 0)))
          print(intToString(unwrapOrResult(Err("bad"), 0)))
        end
        """
    )
    assert result.stdout == "ok\nerr\n1\n0\n", result.to_dict()


def test_map_result_map_err_and_and_then_result():
    result = _run(
        """
        function double(x: Int) returns Int
          effects pure
        do
          return x * 2
        end

        function prefix(s: String) returns String
          effects pure
        do
          return join(["err=", s], "")
        end

        function safeHalf(x: Int) returns Result<Int, String>
          effects pure
        do
          if x % 2 == 0 then
            return Ok(x / 2)
          end
          return Err("odd")
        end

        function describe(res: Result<Int, String>) returns String
          effects pure
        do
          match res do
            case Ok(value) do
              return intToString(value)
            end
            case Err(message) do
              return message
            end
          end
        end

        function main() returns Unit
          effects log
        do
          print(describe(mapResult(Ok(2), double)))
          print(describe(mapErr(Err("bad"), prefix)))
          print(describe(andThenResult(Ok(2), safeHalf)))
        end
        """
    )
    assert result.stdout == "4\nerr=bad\n1\n", result.to_dict()


def test_expect_ok_err_gives_structured_diagnostic():
    result = _bad_run(
        """
        function main() returns Unit
          effects log
        do
          print(intToString(expectOk(Err("bad"), "missing ok")))
        end
        """
    )
    diag = result.diagnostic or {}
    assert diag.get("code") == "EXPECT_OK_FAILED", result.to_dict()
    assert diag.get("category") == "runtime", result.to_dict()
    assert diag.get("line", 0) > 0, diag
    assert diag.get("source_snippet"), diag


def test_option_helper_type_diagnostics():
    diag = _bad_check(
        """
        function main() returns Unit
          effects pure
        do
          let value: Int = unwrapOr(Some(1), "bad")
        end
        """
    ).diagnostic
    assert diag["code"] == "OPTION_HELPER_TYPE_MISMATCH", diag
    assert diag["expected"] == "Int", diag
    assert diag["actual"] == "String", diag


def test_option_mapper_function_type_diagnostic():
    diag = _bad_check(
        """
        function stringLength(s: String) returns Int
          effects pure
        do
          return length(s)
        end

        function main() returns Unit
          effects pure
        do
          let value: Option<Int> = mapOption(Some(1), stringLength)
        end
        """
    ).diagnostic
    assert diag["code"] == "OPTION_HELPER_FUNCTION_TYPE", diag
    assert diag["expected"] == "Int", diag
    assert diag["actual"] == "String", diag


def test_result_helper_type_diagnostics():
    diag = _bad_check(
        """
        function main() returns Unit
          effects pure
        do
          let value: Int = unwrapOrResult(Ok(1), "bad")
        end
        """
    ).diagnostic
    assert diag["code"] == "RESULT_HELPER_TYPE_MISMATCH", diag
    assert diag["expected"] == "Int", diag
    assert diag["actual"] == "String", diag


def test_result_mapper_function_type_diagnostics():
    map_result_diag = _bad_check(
        """
        function stringLength(s: String) returns Int
          effects pure
        do
          return length(s)
        end

        function main() returns Unit
          effects pure
        do
          let value: Result<Int, String> = mapResult(Ok(1), stringLength)
        end
        """
    ).diagnostic
    assert map_result_diag["code"] == "RESULT_HELPER_FUNCTION_TYPE", map_result_diag
    assert map_result_diag["expected"] == "Int", map_result_diag
    assert map_result_diag["actual"] == "String", map_result_diag

    map_err_diag = _bad_check(
        """
        function takesInt(x: Int) returns String
          effects pure
        do
          return intToString(x)
        end

        function main() returns Unit
          effects pure
        do
          let value: Result<Int, String> = mapErr(Err("bad"), takesInt)
        end
        """
    ).diagnostic
    assert map_err_diag["code"] == "RESULT_HELPER_FUNCTION_TYPE", map_err_diag
    assert map_err_diag["expected"] == "String", map_err_diag
    assert map_err_diag["actual"] == "Int", map_err_diag


if __name__ == "__main__":
    test_option_predicates_and_unwrap_or()
    test_map_option_and_and_then_option()
    test_expect_some_none_gives_structured_diagnostic()
    test_result_predicates_and_unwrap_or_result()
    test_map_result_map_err_and_and_then_result()
    test_expect_ok_err_gives_structured_diagnostic()
    test_option_helper_type_diagnostics()
    test_option_mapper_function_type_diagnostic()
    test_result_helper_type_diagnostics()
    test_result_mapper_function_type_diagnostics()
    print("OPTION RESULT HELPER TESTS PASS")
