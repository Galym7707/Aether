from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_cli(source: str, command: str = "run") -> subprocess.CompletedProcess[str]:
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


def _run_ok(source: str) -> str:
    proc = _run_cli(source, "run")
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def _diag(source: str, command: str = "check") -> dict:
    proc = _run_cli(source, command)
    assert proc.returncode != 0, proc
    return json.loads(proc.stderr.splitlines()[0])["diagnostic"]


def test_forall_literal_list_true():
    out = _run_ok(
        """
function main() returns Unit
  effects log
do
  if forall x in [1, 2, 3]: x > 0 then
    print("true")
  else
    print("false")
  end
end
"""
    )
    assert out == "true\n"


def test_exists_literal_list_true():
    out = _run_ok(
        """
function main() returns Unit
  effects log
do
  if exists x in [1, 2, 3]: x > 2 then
    print("true")
  else
    print("false")
  end
end
"""
    )
    assert out == "true\n"


def test_sum_min_max_literals():
    out = _run_ok(
        """
function main() returns Unit
  effects log
do
  print(intToString(sum([1, 2, 3])))
  print(intToString(min([5, 3, 7])))
  print(intToString(max([5, 3, 7])))
end
"""
    )
    assert out == "6\n3\n7\n"


def test_sorted_literals():
    out = _run_ok(
        """
function main() returns Unit
  effects log
do
  if sorted([1, 2, 3]) then
    print("sorted")
  end
  if not sorted([3, 2, 1]) then
    print("unsorted")
  end
end
"""
    )
    assert out == "sorted\nunsorted\n"


def test_permutation_literals():
    out = _run_ok(
        """
function main() returns Unit
  effects log
do
  if permutation([1, 2, 3], [3, 2, 1]) then
    print("perm")
  end
  if not permutation([1, 2], [1, 1]) then
    print("not")
  end
end
"""
    )
    assert out == "perm\nnot\n"


def test_ast_preserves_quantifier_node():
    proc = _run_cli(
        """
function main() returns Unit
  effects pure
do
  let ok: Bool = forall x in [1, 2, 3]: x > 0
end
""",
        "ast",
    )
    assert proc.returncode == 0, proc.stderr
    ast = json.loads(proc.stdout)
    value = ast["decls"][0]["body"][0]["value"]
    assert value["kind"] == "Quantifier"
    assert value["op"] == "forall"
    assert value["var"] == "x"


def test_empty_min_static_diagnostic():
    diag = _diag(
        """
function main() returns Unit
  effects pure
do
  let value: Int = min([])
end
"""
    )
    assert diag["code"] == "AGGREGATE_EMPTY_LIST", diag


def test_empty_max_runtime_diagnostic_for_dynamic_list():
    diag = _diag(
        """
function largest(xs: List<Int>) returns Int
  effects pure
do
  return max(xs)
end

function main() returns Unit
  effects pure
do
  let value: Int = largest([])
end
""",
        "run",
    )
    assert diag["code"] == "AGGREGATE_EMPTY_LIST_RUNTIME", diag


def test_sum_wrong_element_type_diagnostic():
    diag = _diag(
        """
function main() returns Unit
  effects pure
do
  let value: Int = sum(["a"])
end
"""
    )
    assert diag["code"] == "AGGREGATE_ELEMENT_TYPE", diag
    assert diag["expected"] == "Int", diag
    assert diag["actual"] == "String", diag


def test_quantifier_predicate_type_diagnostic():
    diag = _diag(
        """
function main() returns Unit
  effects pure
do
  let ok: Bool = forall x in [1, 2, 3]: x + 1
end
"""
    )
    assert diag["code"] == "QUANTIFIER_PREDICATE_TYPE", diag


if __name__ == "__main__":
    test_forall_literal_list_true()
    test_exists_literal_list_true()
    test_sum_min_max_literals()
    test_sorted_literals()
    test_permutation_literals()
    test_ast_preserves_quantifier_node()
    test_empty_min_static_diagnostic()
    test_empty_max_runtime_diagnostic_for_dynamic_list()
    test_sum_wrong_element_type_diagnostic()
    test_quantifier_predicate_type_diagnostic()
    print("QUANTIFIER AND AGGREGATE TESTS PASS")
