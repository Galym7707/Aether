from __future__ import annotations

import os
import sys
from textwrap import dedent

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from transpiler.aether.agent_sdk import check_source, run_source
from transpiler.aether.parser import parse


def _check_ok(source: str):
    result = check_source(dedent(source).strip() + "\n", "<function-type-effect-test>")
    assert result.ok is True, result.to_dict()
    return result


def _bad_check(source: str):
    result = check_source(dedent(source).strip() + "\n", "<function-type-effect-test>")
    assert result.ok is False, result.to_dict()
    return result


def _run_ok(source: str):
    result = run_source(dedent(source).strip() + "\n", "<function-type-effect-test>")
    assert result.ok is True, result.to_dict()
    return result


def test_parser_records_function_type_effects():
    ast = parse(
        dedent(
            """
            type Mapper = function(Int) returns Int effects log
            """
        ).strip()
        + "\n"
    )
    ty = ast["decls"][0]["base"]
    assert ty["kind"] == "FunctionType", ty
    assert ty["effects"] == [{"path": ["log"], "arg": None}], ty


def test_parser_defaults_function_type_effects_to_pure():
    ast = parse(
        dedent(
            """
            type Mapper = function(Int) returns Int
            """
        ).strip()
        + "\n"
    )
    ty = ast["decls"][0]["base"]
    assert ty["effects"] == [{"path": ["pure"], "arg": None}], ty


def test_parser_records_nested_function_type_effects():
    ast = parse(
        dedent(
            """
            type Factory = function(Int) returns function(Int) returns Bool effects log effects pure
            """
        ).strip()
        + "\n"
    )
    outer = ast["decls"][0]["base"]
    inner = outer["returns"]
    assert outer["effects"] == [{"path": ["pure"], "arg": None}], outer
    assert inner["effects"] == [{"path": ["log"], "arg": None}], inner


def test_pure_function_typed_callback_passes():
    _check_ok(
        """
        function apply(f: function(Int) returns Int, x: Int) returns Int
          effects pure
        do
          return f(x)
        end

        function increment(x: Int) returns Int
          effects pure
        do
          return x + 1
        end

        function main() returns Unit
          effects pure
        do
          let value: Int = apply(increment, 1)
        end
        """
    )


def test_effectful_function_typed_callback_allowed_when_declared():
    result = _run_ok(
        """
        function apply(f: function(Int) returns Int effects log, x: Int) returns Int
          effects log
        do
          return f(x)
        end

        function audit(x: Int) returns Int
          effects log
        do
          print(intToString(x))
          return x + 1
        end

        function main() returns Unit
          effects log
        do
          print(intToString(apply(audit, 2)))
        end
        """
    )
    assert result.stdout == "2\n3\n", result.to_dict()


def test_function_typed_parameter_effect_escape_is_rejected():
    result = _bad_check(
        """
        function apply(f: function(Int) returns Int effects log, x: Int) returns Int
          effects pure
        do
          return f(x)
        end
        """
    )
    diag = result.diagnostic or {}
    assert diag.get("code") == "HIGHER_ORDER_EFFECT_ESCAPE", result.to_dict()
    assert diag.get("category") == "effect", diag
    assert diag.get("line", 0) > 0, diag
    assert diag.get("source_snippet") == "  return f(x)", diag
    extra = diag.get("extra") or {}
    assert extra.get("helper") == "f", diag
    assert extra.get("escaped_effect") == "log", diag


def test_passing_effectful_function_to_default_pure_function_type_is_rejected():
    result = _bad_check(
        """
        function apply(f: function(Int) returns Int, x: Int) returns Int
          effects pure
        do
          return f(x)
        end

        function audit(x: Int) returns Int
          effects log
        do
          print(intToString(x))
          return x
        end

        function main() returns Unit
          effects log
        do
          let value: Int = apply(audit, 2)
        end
        """
    )
    diag = result.diagnostic or {}
    assert diag.get("code") == "FUNCTION_TYPE_EFFECT_MISMATCH", result.to_dict()
    assert diag.get("expected") == "function(Int) returns Int", diag
    assert diag.get("actual") == "function(Int) returns Int effects log", diag


def test_incorrect_callback_effect_annotation_still_triggers_direct_effect_diagnostic():
    result = _bad_check(
        """
        function badAudit(x: Int) returns Int
          effects pure
        do
          print(intToString(x))
          return x
        end
        """
    )
    diag = result.diagnostic or {}
    assert diag.get("code") == "EFFECT_NOT_COVERED", result.to_dict()
    assert diag.get("category") == "effect", diag


if __name__ == "__main__":
    test_parser_records_function_type_effects()
    test_parser_defaults_function_type_effects_to_pure()
    test_parser_records_nested_function_type_effects()
    test_pure_function_typed_callback_passes()
    test_effectful_function_typed_callback_allowed_when_declared()
    test_function_typed_parameter_effect_escape_is_rejected()
    test_passing_effectful_function_to_default_pure_function_type_is_rejected()
    test_incorrect_callback_effect_annotation_still_triggers_direct_effect_diagnostic()
    print("FUNCTION TYPE EFFECT TESTS PASS")
