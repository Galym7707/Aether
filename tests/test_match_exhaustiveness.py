from __future__ import annotations

import json
import os
import subprocess
import sys
from textwrap import dedent

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from transpiler.aether.agent_sdk import check_source, run_source


def _check_ok(source: str):
    result = check_source(dedent(source).strip() + "\n", "<match-exhaustiveness-test>")
    assert result.ok is True, result.to_dict()
    return result


def _bad_check(source: str, missing: str):
    result = check_source(dedent(source).strip() + "\n", "<match-exhaustiveness-test>")
    assert result.ok is False, result.to_dict()
    diag = result.diagnostic or {}
    assert diag.get("code") == "MATCH_NON_EXHAUSTIVE", result.to_dict()
    assert missing in diag.get("extra", {}).get("missing_cases", []), diag
    assert diag.get("line", 0) > 0, diag
    assert diag.get("column", 0) > 0, diag
    assert diag.get("source_snippet"), diag
    return result


def test_exhaustive_option_match_passes():
    _check_ok(
        """
        function main() returns Unit
          effects log
        do
          match Some(1) do
            case Some(value) do
              print(intToString(value))
            end
            case None() do
              print("none")
            end
          end
        end
        """
    )


def test_missing_none_fails():
    _bad_check(
        """
        function main() returns Unit
          effects log
        do
          match Some(1) do
            case Some(value) do
              print(intToString(value))
            end
          end
        end
        """,
        "None",
    )


def test_missing_some_fails():
    _bad_check(
        """
        function main() returns Unit
          effects log
        do
          match None() do
            case None() do
              print("none")
            end
          end
        end
        """,
        "Some",
    )


def test_wildcard_passes():
    _check_ok(
        """
        function main() returns Unit
          effects log
        do
          match Some(1) do
            case Some(value) do
              print(intToString(value))
            end
            case _ do
              print("fallback")
            end
          end
        end
        """
    )


def test_exhaustive_result_match_passes_and_missing_err_fails():
    _check_ok(
        """
        function main() returns Unit
          effects log
        do
          match Ok(1) do
            case Ok(value) do
              print(intToString(value))
            end
            case Err(message) do
              print(message)
            end
          end
        end
        """
    )
    _bad_check(
        """
        function main() returns Unit
          effects log
        do
          match Ok(1) do
            case Ok(value) do
              print(intToString(value))
            end
          end
        end
        """,
        "Err",
    )


def test_custom_union_exhaustive_and_missing_case():
    _check_ok(
        """
        union Color do
          case Red
          case Green
          case Blue
        end

        function describe(color: Color) returns String
          effects pure
        do
          match color do
            case Red() do
              return "red"
            end
            case Green() do
              return "green"
            end
            case Blue() do
              return "blue"
            end
          end
        end
        """
    )
    _bad_check(
        """
        union Color do
          case Red
          case Green
          case Blue
        end

        function describe(color: Color) returns String
          effects pure
        do
          match color do
            case Red() do
              return "red"
            end
            case Green() do
              return "green"
            end
          end
        end
        """,
        "Blue",
    )


def test_missing_cases_appear_in_json_diagnostic_extra():
    path = os.path.join(ROOT, "examples", "negative", "04_match_missing_option_case.aeth")
    proc = subprocess.run(
        [sys.executable, "-B", "-m", "transpiler.aether.cli", "check", "--json", path],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode != 0, proc.stdout
    payload = json.loads(proc.stdout or proc.stderr)
    diag = payload["errors"][0]
    assert diag["code"] == "MATCH_NON_EXHAUSTIVE", payload
    assert diag["extra"]["missing_cases"] == ["None"], payload


def test_runtime_fallback_uses_structured_diagnostic_for_unknown_match():
    result = run_source(
        dedent(
            """
            function main() returns Unit
              effects log
            do
              let value = null
              match value do
                case Some(v) do
                  print(intToString(v))
                end
              end
            end
            """
        ).strip()
        + "\n",
        "<match-runtime-fallback-test>",
    )
    assert result.ok is False, result.to_dict()
    diag = result.diagnostic or {}
    assert diag.get("code") == "MATCH_NON_EXHAUSTIVE_RUNTIME", result.to_dict()
    assert diag.get("category") == "runtime", result.to_dict()
    assert diag.get("line", 0) > 0, diag
    assert diag.get("source_snippet"), diag


if __name__ == "__main__":
    test_exhaustive_option_match_passes()
    test_missing_none_fails()
    test_missing_some_fails()
    test_wildcard_passes()
    test_exhaustive_result_match_passes_and_missing_err_fails()
    test_custom_union_exhaustive_and_missing_case()
    test_missing_cases_appear_in_json_diagnostic_extra()
    test_runtime_fallback_uses_structured_diagnostic_for_unknown_match()
    print("MATCH EXHAUSTIVENESS TESTS PASS")
