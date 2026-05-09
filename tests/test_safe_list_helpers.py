from __future__ import annotations

import json
import os
import subprocess
import sys
from textwrap import dedent

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from transpiler.aether.agent_sdk import check_source, run_source


def _run(source: str):
    result = run_source(dedent(source).strip() + "\n", "<safe-list-helper-test>")
    assert result.ok is True, result.to_dict()
    return result


def _bad_check(source: str):
    result = check_source(dedent(source).strip() + "\n", "<safe-list-helper-test>")
    assert result.ok is False, result.to_dict()
    return result


def _assert_structured_type_diag(result, code: str):
    diag = result.diagnostic or {}
    assert diag.get("code") == code, result.to_dict()
    assert diag.get("line", 0) > 0, diag
    assert diag.get("column", 0) > 0, diag
    assert diag.get("source_snippet"), diag
    assert diag.get("expected"), diag
    assert diag.get("actual"), diag
    return diag


def test_safe_at_valid_index_returns_some():
    result = _run(
        """
        function main() returns Unit
          effects log
        do
          match safeAt([10, 20], 1) do
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
    assert result.stdout == "20\n", result.to_dict()


def test_safe_at_invalid_index_returns_none():
    result = _run(
        """
        function main() returns Unit
          effects log
        do
          match safeAt([10, 20], 5) do
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
    assert result.stdout == "none\n", result.to_dict()


def test_update_at_valid_index_returns_ok_with_changed_list():
    result = _run(
        """
        function main() returns Unit
          effects log
        do
          match updateAt([1, 2, 3], 1, 99) do
            case Ok(updated) do
              print(intToString(length(updated)))
              print(intToString(updated[1]))
            end
            case Err(message) do
              print(message)
            end
          end
        end
        """
    )
    assert result.stdout == "3\n99\n", result.to_dict()


def test_update_at_invalid_index_returns_err():
    result = _run(
        """
        function main() returns Unit
          effects log
        do
          match updateAt([1, 2, 3], 9, 99) do
            case Ok(updated) do
              print(intToString(updated[0]))
            end
            case Err(message) do
              print(message)
            end
          end
        end
        """
    )
    assert result.stdout == "index out of bounds\n", result.to_dict()


def test_update_at_does_not_mutate_original_list():
    result = _run(
        """
        function main() returns Unit
          effects log
        do
          let xs: List<Int> = [1, 2, 3]
          match updateAt(xs, 1, 99) do
            case Ok(updated) do
              print(intToString(xs[1]))
              print(intToString(updated[1]))
            end
            case Err(message) do
              print(message)
            end
          end
        end
        """
    )
    assert result.stdout == "2\n99\n", result.to_dict()


def test_safe_slice_valid_bounds_returns_ok_with_slice():
    result = _run(
        """
        function main() returns Unit
          effects log
        do
          match safeSlice([1, 2, 3, 4], 1, 3) do
            case Ok(part) do
              print(intToString(length(part)))
              print(intToString(part[0]))
              print(intToString(part[1]))
            end
            case Err(message) do
              print(message)
            end
          end
        end
        """
    )
    assert result.stdout == "2\n2\n3\n", result.to_dict()


def test_safe_slice_invalid_start_returns_err():
    result = _run(
        """
        function main() returns Unit
          effects log
        do
          match safeSlice([1, 2, 3], -1, 2) do
            case Ok(part) do
              print(intToString(length(part)))
            end
            case Err(message) do
              print(message)
            end
          end
        end
        """
    )
    assert result.stdout == "slice bounds out of range\n", result.to_dict()


def test_safe_slice_start_greater_than_end_returns_err():
    result = _run(
        """
        function main() returns Unit
          effects log
        do
          match safeSlice([1, 2, 3], 2, 1) do
            case Ok(part) do
              print(intToString(length(part)))
            end
            case Err(message) do
              print(message)
            end
          end
        end
        """
    )
    assert result.stdout == "slice bounds out of range\n", result.to_dict()


def test_safe_slice_end_greater_than_length_returns_err():
    result = _run(
        """
        function main() returns Unit
          effects log
        do
          match safeSlice([1, 2, 3], 1, 9) do
            case Ok(part) do
              print(intToString(length(part)))
            end
            case Err(message) do
              print(message)
            end
          end
        end
        """
    )
    assert result.stdout == "slice bounds out of range\n", result.to_dict()


def test_typechecker_rejects_bad_index_type_for_safe_at():
    result = _bad_check(
        """
        function main() returns Unit
          effects log
        do
          let value: Option<Int> = safeAt([1, 2], "0")
          print("unreachable")
        end
        """
    )
    diag = _assert_structured_type_diag(result, "LIST_HELPER_INDEX_TYPE")
    assert diag["expected"] == "Int", diag
    assert diag["actual"] == "String", diag


def test_typechecker_rejects_bad_value_type_for_update_at():
    result = _bad_check(
        """
        function main() returns Unit
          effects log
        do
          let value: Result<List<Int>, String> = updateAt([1, 2], 0, "bad")
          print("unreachable")
        end
        """
    )
    diag = _assert_structured_type_diag(result, "LIST_HELPER_VALUE_TYPE")
    assert diag["expected"] == "Int", diag
    assert diag["actual"] == "String", diag


def test_typechecker_rejects_bad_bound_types_for_safe_slice():
    first = _bad_check(
        """
        function main() returns Unit
          effects log
        do
          let value: Result<List<Int>, String> = safeSlice([1, 2], "0", 1)
          print("unreachable")
        end
        """
    )
    _assert_structured_type_diag(first, "LIST_HELPER_BOUND_TYPE")

    second = _bad_check(
        """
        function main() returns Unit
          effects log
        do
          let value: Result<List<Int>, String> = safeSlice([1, 2], 0, "1")
          print("unreachable")
        end
        """
    )
    _assert_structured_type_diag(second, "LIST_HELPER_BOUND_TYPE")


def test_typechecker_rejects_bad_bounds_for_predicates():
    first = _bad_check(
        """
        function main() returns Unit
          effects log
        do
          let ok: Bool = inBounds([1, 2], "0")
          print("unreachable")
        end
        """
    )
    _assert_structured_type_diag(first, "LIST_HELPER_INDEX_TYPE")

    second = _bad_check(
        """
        function main() returns Unit
          effects log
        do
          let ok: Bool = validSliceBounds([1, 2], 0, "1")
          print("unreachable")
        end
        """
    )
    _assert_structured_type_diag(second, "LIST_HELPER_BOUND_TYPE")


def test_examples_06_08_pass_check_and_run():
    expected = {
        "06_safe_at.aeth": "20\nnone\n",
        "07_update_at.aeth": "99\nindex out of bounds\n",
        "08_safe_slice.aeth": "2:20,30\nslice bounds out of range\n",
    }
    for name, stdout in expected.items():
        path = os.path.join(ROOT, "examples", name)
        check = subprocess.run(
            [sys.executable, "-B", "-m", "transpiler.aether.cli", "check", path],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        assert check.returncode == 0, check.stderr or check.stdout
        run = subprocess.run(
            [sys.executable, "-B", "-m", "transpiler.aether.cli", "run", path],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        assert run.returncode == 0, run.stderr or run.stdout
        assert run.stdout == stdout, run.stdout


def test_negative_examples_fail_with_structured_diagnostics():
    expected = {
        "02_bad_update_at_type.aeth": "LIST_HELPER_VALUE_TYPE",
        "03_bad_safe_slice_bounds_type.aeth": "LIST_HELPER_BOUND_TYPE",
    }
    for name, code in expected.items():
        path = os.path.join(ROOT, "examples", "negative", name)
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "transpiler.aether.cli", "check", "--json", path],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        assert proc.returncode != 0, proc.stdout
        payload = json.loads(proc.stdout or proc.stderr)
        diag = payload["errors"][0]
        assert diag["code"] == code, payload
        assert diag["line"] > 0, payload
        assert diag["column"] > 0, payload
        assert diag["source_snippet"], payload


if __name__ == "__main__":
    test_safe_at_valid_index_returns_some()
    test_safe_at_invalid_index_returns_none()
    test_update_at_valid_index_returns_ok_with_changed_list()
    test_update_at_invalid_index_returns_err()
    test_update_at_does_not_mutate_original_list()
    test_safe_slice_valid_bounds_returns_ok_with_slice()
    test_safe_slice_invalid_start_returns_err()
    test_safe_slice_start_greater_than_end_returns_err()
    test_safe_slice_end_greater_than_length_returns_err()
    test_typechecker_rejects_bad_index_type_for_safe_at()
    test_typechecker_rejects_bad_value_type_for_update_at()
    test_typechecker_rejects_bad_bound_types_for_safe_slice()
    test_typechecker_rejects_bad_bounds_for_predicates()
    test_examples_06_08_pass_check_and_run()
    test_negative_examples_fail_with_structured_diagnostics()
    print("SAFE LIST HELPER TESTS PASS")
