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
    assert proc.returncode != 0, proc.stdout + proc.stderr
    return json.loads(proc.stderr.splitlines()[0])["diagnostic"]


def test_loop_invariant_and_variant_pass():
    out = _run_ok(
        """
function main() returns Unit
  effects log
do
  var i: Int = 3
  while i > 0
  invariant i >= 0
  variant i
  do
    i = i - 1
  end
  print(intToString(i))
end
"""
    )
    assert out == "0\n"


def test_range_quantifier_invariant_passes():
    out = _run_ok(
        """
function main() returns Unit
  effects log
do
  let xs: List<Int> = [1, 2, 3]
  var i: Int = 0
  while i < 1
  invariant forall j in 0..length(xs) - 1: xs[j] <= xs[j + 1]
  variant 1 - i
  do
    i = i + 1
  end
  print("ok")
end
"""
    )
    assert out == "ok\n"


def test_ast_preserves_loop_annotations():
    proc = _run_cli(
        """
function main() returns Unit
  effects pure
do
  var i: Int = 1
  while i > 0
  invariant i >= 0
  variant i
  do
    i = i - 1
  end
end
""",
        "ast",
    )
    assert proc.returncode == 0, proc.stderr
    ast = json.loads(proc.stdout)
    loop = ast["decls"][0]["body"][1]
    assert loop["kind"] == "While"
    assert loop["invariants"][0]["kind"] == "BinOp"
    assert loop["variant"]["kind"] == "Ident"


def test_invariant_runtime_diagnostic_for_dynamic_case():
    diag = _diag(
        """
function badInvariant(n: Int) returns Int
  effects pure
do
  var i: Int = n
  while i < 1
  invariant i > 0
  variant 1 - i
  do
    i = i + 1
  end
  return i
end

function main() returns Unit
  effects pure
do
  let value: Int = badInvariant(0)
end
""",
        "run",
    )
    assert diag["code"] == "LOOP_INVARIANT_FAILED", diag
    assert diag["contract_kind"] == "loop invariant", diag


def test_variant_static_diagnostic():
    diag = _diag(
        """
function main() returns Unit
  effects pure
do
  var i: Int = 0
  while i < 2
  invariant i >= 0
  variant 10 - i
  do
    i = i - 1
  end
end
"""
    )
    assert diag["code"] == "LOOP_VARIANT_NOT_DECREASING_STATIC", diag


def test_variant_runtime_diagnostic_for_unsupported_smt_case():
    diag = _diag(
        """
function delta() returns Int
  effects pure
do
  return -1
end

function main() returns Unit
  effects pure
do
  var i: Int = 0
  while i < 1
  invariant i >= -10
  variant 10 - i
  do
    i = i + delta()
  end
end
""",
        "run",
    )
    assert diag["code"] == "LOOP_VARIANT_NOT_DECREASING", diag


def test_record_update_expression_returns_new_record():
    out = _run_ok(
        """
record Point do
  x: Int
  y: Int
end

function main() returns Unit
  effects log
do
  let p: Point = Point(1, 2)
  let q: Point = p { x = 5 }
  print(intToString(p.x))
  print(intToString(q.x))
  print(intToString(q.y))
end
"""
    )
    assert out == "1\n5\n2\n"


def test_record_update_field_type_diagnostic():
    diag = _diag(
        """
record Point do
  x: Int
end

function main() returns Unit
  effects pure
do
  let p: Point = Point(1)
  let q: Point = p { x = "bad" }
end
"""
    )
    assert diag["code"] == "RECORD_UPDATE_FIELD_TYPE", diag
    assert diag["expected"] == "Int", diag
    assert diag["actual"] == "String", diag


if __name__ == "__main__":
    test_loop_invariant_and_variant_pass()
    test_range_quantifier_invariant_passes()
    test_ast_preserves_loop_annotations()
    test_invariant_runtime_diagnostic_for_dynamic_case()
    test_variant_static_diagnostic()
    test_variant_runtime_diagnostic_for_unsupported_smt_case()
    test_record_update_expression_returns_new_record()
    test_record_update_field_type_diagnostic()
    print("LOOP INVARIANT AND RECORD UPDATE TESTS PASS")
