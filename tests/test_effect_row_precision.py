from __future__ import annotations

import os
import sys
from textwrap import dedent

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from transpiler.aether.agent_sdk import check_source


def _check_ok(source: str):
    result = check_source(dedent(source).strip() + "\n", "<effect-row-precision-test>")
    assert result.ok is True, result.to_dict()
    return result


def _bad_check(source: str):
    result = check_source(dedent(source).strip() + "\n", "<effect-row-precision-test>")
    assert result.ok is False, result.to_dict()
    return result


def _first_diag(source: str):
    result = _bad_check(source)
    return result.diagnostic or {}


def test_net_fetch_covers_concrete_url():
    _check_ok(
        """
        function fetchUser(id: Int) returns String
          effects net.fetch("https://api.example.com/users")
        do
          return "user"
        end

        function main() returns Unit
          effects net.fetch
        do
          let value: String = fetchUser(1)
        end
        """
    )


def test_net_fetch_star_covers_concrete_url():
    _check_ok(
        """
        function fetchUser(id: Int) returns String
          effects net.fetch("https://api.example.com/users")
        do
          return "user"
        end

        function main() returns Unit
          effects net.fetch("*")
        do
          let value: String = fetchUser(1)
        end
        """
    )


def test_net_fetch_url_prefix_covers_matching_url():
    _check_ok(
        """
        function fetchUser(id: Int) returns String
          effects net.fetch("https://api.example.com/users")
        do
          return "user"
        end

        function main() returns Unit
          effects net.fetch("https://api.example.com/*")
        do
          let value: String = fetchUser(1)
        end
        """
    )


def test_net_fetch_url_prefix_rejects_billing_url():
    diag = _first_diag(
        """
        function fetchBilling(id: Int) returns String
          effects net.fetch("https://billing.example.com/*")
        do
          return "billing"
        end

        function main() returns Unit
          effects net.fetch("https://api.example.com/*")
        do
          let value: String = fetchBilling(1)
        end
        """
    )
    assert diag.get("code") == "EFFECT_NOT_COVERED", diag
    assert diag.get("source_snippet") == "  let value: String = fetchBilling(1)", diag
    extra = diag.get("extra") or {}
    assert extra.get("required_effect") == 'net.fetch("https://billing.example.com/*")', diag
    assert 'effects net.fetch("https://billing.example.com/*")' in (diag.get("hint") or ""), diag


def test_concrete_url_rejects_different_concrete_url():
    diag = _first_diag(
        """
        function fetchBilling(id: Int) returns String
          effects net.fetch("https://billing.example.com/users")
        do
          return "billing"
        end

        function main() returns Unit
          effects net.fetch("https://api.example.com/users")
        do
          let value: String = fetchBilling(1)
        end
        """
    )
    assert diag.get("code") == "EFFECT_NOT_COVERED", diag
    assert (diag.get("extra") or {}).get("required_effect") == 'net.fetch("https://billing.example.com/users")', diag


def test_broader_callee_effect_is_not_covered_by_narrower_caller_effect():
    diag = _first_diag(
        """
        function fetchAnything(id: Int) returns String
          effects net.fetch
        do
          return "value"
        end

        function main() returns Unit
          effects net.fetch("https://api.example.com/*")
        do
          let value: String = fetchAnything(1)
        end
        """
    )
    assert diag.get("code") == "EFFECT_NOT_COVERED", diag
    assert (diag.get("extra") or {}).get("required_effect") == "net.fetch", diag


def test_function_type_effect_accepts_compatible_named_function():
    _check_ok(
        """
        function fetchUser(id: Int) returns String
          effects net.fetch("https://api.example.com/users/*")
        do
          return "user"
        end

        function useFetcher(f: function(Int) returns String effects net.fetch("https://api.example.com/*"), id: Int) returns String
          effects net.fetch("https://api.example.com/*")
        do
          return f(id)
        end

        function main() returns Unit
          effects net.fetch("https://api.example.com/*")
        do
          let value: String = useFetcher(fetchUser, 1)
        end
        """
    )


def test_function_type_effect_rejects_incompatible_named_function():
    diag = _first_diag(
        """
        function fetchBilling(id: Int) returns String
          effects net.fetch("https://billing.example.com/*")
        do
          return "billing"
        end

        function useFetcher(f: function(Int) returns String effects net.fetch("https://api.example.com/*"), id: Int) returns String
          effects net.fetch("https://api.example.com/*")
        do
          return f(id)
        end

        function main() returns Unit
          effects net.fetch("https://api.example.com/*")
        do
          let value: String = useFetcher(fetchBilling, 1)
        end
        """
    )
    assert diag.get("code") == "FUNCTION_TYPE_EFFECT_MISMATCH", diag
    extra = diag.get("extra") or {}
    assert extra.get("expected_function_type_effects") == ['net.fetch("https://api.example.com/*")'], diag
    assert extra.get("actual_callback_effects") == ['net.fetch("https://billing.example.com/*")'], diag
    assert extra.get("required_effect") == 'net.fetch("https://billing.example.com/*")', diag


def test_omitted_function_type_effects_default_to_pure():
    diag = _first_diag(
        """
        function audit(x: Int) returns Int
          effects log
        do
          print(intToString(x))
          return x
        end

        function apply(f: function(Int) returns Int, x: Int) returns Int
          effects pure
        do
          return f(x)
        end

        function main() returns Unit
          effects log
        do
          let value: Int = apply(audit, 1)
        end
        """
    )
    assert diag.get("code") == "FUNCTION_TYPE_EFFECT_MISMATCH", diag
    assert diag.get("expected") == "function(Int) returns Int", diag
    assert diag.get("actual") == "function(Int) returns Int effects log", diag


def test_passing_effectful_function_to_pure_function_type_fails():
    test_omitted_function_type_effects_default_to_pure()


def test_map_option_compatible_precise_effect_passes():
    _check_ok(
        """
        function fetchInt(x: Int) returns Int
          effects net.fetch("https://api.example.com/users/*")
        do
          return x
        end

        function main() returns Unit
          effects net.fetch("https://api.example.com/*")
        do
          let value: Option<Int> = mapOption(Some(1), fetchInt)
        end
        """
    )


def test_map_option_incompatible_precise_effect_fails():
    diag = _first_diag(
        """
        function fetchBilling(x: Int) returns Int
          effects net.fetch("https://billing.example.com/*")
        do
          return x
        end

        function main() returns Unit
          effects net.fetch("https://api.example.com/*")
        do
          let value: Option<Int> = mapOption(Some(1), fetchBilling)
        end
        """
    )
    assert diag.get("code") == "HIGHER_ORDER_EFFECT_ESCAPE", diag
    extra = diag.get("extra") or {}
    assert extra.get("helper") == "mapOption", diag
    assert extra.get("escaped_effect") == 'net.fetch("https://billing.example.com/*")', diag


def test_map_result_compatible_precise_effect_passes():
    _check_ok(
        """
        function fetchInt(x: Int) returns Int
          effects net.fetch("https://api.example.com/users/*")
        do
          return x
        end

        function main() returns Unit
          effects net.fetch("https://api.example.com/*")
        do
          let value: Result<Int, String> = mapResult(Ok(1), fetchInt)
        end
        """
    )


def test_map_err_incompatible_precise_effect_fails():
    diag = _first_diag(
        """
        function fetchBilling(message: String) returns String
          effects net.fetch("https://billing.example.com/*")
        do
          return message
        end

        function main() returns Unit
          effects net.fetch("https://api.example.com/*")
        do
          let value: Result<Int, String> = mapErr(Err("bad"), fetchBilling)
        end
        """
    )
    assert diag.get("code") == "HIGHER_ORDER_EFFECT_ESCAPE", diag
    extra = diag.get("extra") or {}
    assert extra.get("helper") == "mapErr", diag
    assert extra.get("escaped_effect") == 'net.fetch("https://billing.example.com/*")', diag
    assert extra.get("actual_callback_effects") == ['net.fetch("https://billing.example.com/*")'], diag


if __name__ == "__main__":
    test_net_fetch_covers_concrete_url()
    test_net_fetch_star_covers_concrete_url()
    test_net_fetch_url_prefix_covers_matching_url()
    test_net_fetch_url_prefix_rejects_billing_url()
    test_concrete_url_rejects_different_concrete_url()
    test_broader_callee_effect_is_not_covered_by_narrower_caller_effect()
    test_function_type_effect_accepts_compatible_named_function()
    test_function_type_effect_rejects_incompatible_named_function()
    test_omitted_function_type_effects_default_to_pure()
    test_passing_effectful_function_to_pure_function_type_fails()
    test_map_option_compatible_precise_effect_passes()
    test_map_option_incompatible_precise_effect_fails()
    test_map_result_compatible_precise_effect_passes()
    test_map_err_incompatible_precise_effect_fails()
    print("EFFECT ROW PRECISION TESTS PASS")
