from __future__ import annotations

import os
import sys
from textwrap import dedent

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from transpiler.aether.agent_sdk import check_source, run_source


def _check_ok(source: str):
    result = check_source(dedent(source).strip() + "\n", "<higher-order-effect-test>")
    assert result.ok is True, result.to_dict()
    return result


def _run_ok(source: str):
    result = run_source(dedent(source).strip() + "\n", "<higher-order-effect-test>")
    assert result.ok is True, result.to_dict()
    return result


def _bad_check(source: str):
    result = check_source(dedent(source).strip() + "\n", "<higher-order-effect-test>")
    assert result.ok is False, result.to_dict()
    return result


def _assert_effect_escape(source: str, helper: str):
    result = _bad_check(source)
    diag = result.diagnostic or {}
    assert diag.get("code") == "HIGHER_ORDER_EFFECT_ESCAPE", result.to_dict()
    assert diag.get("category") == "effect", diag
    assert diag.get("line", 0) > 0, diag
    assert diag.get("column", 0) > 0, diag
    assert diag.get("source_snippet"), diag
    extra = diag.get("extra") or {}
    assert extra.get("helper") == helper, diag
    assert extra.get("escaped_effect") == "log", diag
    assert "add effect 'log'" in (diag.get("hint") or ""), diag
    return diag


def test_pure_callback_through_map_option_passes():
    _check_ok(
        """
        function double(x: Int) returns Int
          effects pure
        do
          return x * 2
        end

        function main() returns Unit
          effects pure
        do
          let value: Option<Int> = mapOption(Some(1), double)
        end
        """
    )


def test_effectful_callback_through_map_option_allowed_when_declared():
    result = _run_ok(
        """
        function logValue(x: Int) returns Int
          effects log
        do
          print(intToString(x))
          return x
        end

        function main() returns Unit
          effects log
        do
          let value: Option<Int> = mapOption(Some(3), logValue)
        end
        """
    )
    assert result.stdout == "3\n", result.to_dict()


def test_map_option_effect_escape_rejected_in_pure_context():
    _assert_effect_escape(
        """
        function logValue(x: Int) returns Int
          effects log
        do
          print(intToString(x))
          return x
        end

        function main() returns Unit
          effects pure
        do
          let value: Option<Int> = mapOption(Some(3), logValue)
        end
        """,
        "mapOption",
    )


def test_and_then_option_effect_escape_rejected_in_pure_context():
    _assert_effect_escape(
        """
        function logOption(x: Int) returns Option<Int>
          effects log
        do
          print(intToString(x))
          return Some(x)
        end

        function main() returns Unit
          effects pure
        do
          let value: Option<Int> = andThenOption(Some(3), logOption)
        end
        """,
        "andThenOption",
    )


def test_map_result_effect_escape_rejected_in_pure_context():
    _assert_effect_escape(
        """
        function logValue(x: Int) returns Int
          effects log
        do
          print(intToString(x))
          return x
        end

        function main() returns Unit
          effects pure
        do
          let value: Result<Int, String> = mapResult(Ok(3), logValue)
        end
        """,
        "mapResult",
    )


def test_map_err_effect_escape_rejected_in_pure_context():
    _assert_effect_escape(
        """
        function logError(message: String) returns String
          effects log
        do
          print(message)
          return message
        end

        function main() returns Unit
          effects pure
        do
          let value: Result<Int, String> = mapErr(Err("bad"), logError)
        end
        """,
        "mapErr",
    )


def test_and_then_result_effect_escape_rejected_in_pure_context():
    _assert_effect_escape(
        """
        function logResult(x: Int) returns Result<Int, String>
          effects log
        do
          print(intToString(x))
          return Ok(x)
        end

        function main() returns Unit
          effects pure
        do
          let value: Result<Int, String> = andThenResult(Ok(3), logResult)
        end
        """,
        "andThenResult",
    )


def test_effectful_callbacks_are_allowed_when_enclosing_function_declares_effect():
    result = _run_ok(
        """
        function logValue(x: Int) returns Int
          effects log
        do
          print(intToString(x))
          return x + 1
        end

        function logResult(x: Int) returns Result<Int, String>
          effects log
        do
          print(intToString(x))
          return Ok(x + 1)
        end

        function logOption(x: Int) returns Option<Int>
          effects log
        do
          print(intToString(x))
          return Some(x + 1)
        end

        function logError(message: String) returns String
          effects log
        do
          print(message)
          return join(["handled:", message], "")
        end

        function main() returns Unit
          effects log
        do
          let first: Option<Int> = mapOption(Some(1), logValue)
          let second: Option<Int> = andThenOption(Some(2), logOption)
          let third: Result<Int, String> = mapResult(Ok(3), logValue)
          let fourth: Result<Int, String> = mapErr(Err("bad"), logError)
          let fifth: Result<Int, String> = andThenResult(Ok(4), logResult)
        end
        """
    )
    assert result.stdout == "1\n2\n3\nbad\n4\n", result.to_dict()


if __name__ == "__main__":
    test_pure_callback_through_map_option_passes()
    test_effectful_callback_through_map_option_allowed_when_declared()
    test_map_option_effect_escape_rejected_in_pure_context()
    test_and_then_option_effect_escape_rejected_in_pure_context()
    test_map_result_effect_escape_rejected_in_pure_context()
    test_map_err_effect_escape_rejected_in_pure_context()
    test_and_then_result_effect_escape_rejected_in_pure_context()
    test_effectful_callbacks_are_allowed_when_enclosing_function_declares_effect()
    print("HIGHER ORDER EFFECT TESTS PASS")
