from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from transpiler.aether.agent_sdk import run_source
from transpiler.aether.prelint import lint_common_ai_syntax


def test_index_read_append_and_rebuild_update():
    source = """
function updateAt(xs: List<Int>, index: Int, value: Int) returns List<Int>
  requires index >= 0 and index < length(xs)
  ensures length(result) == length(xs)
  effects pure
do
  var out: List<Int> = []
  var i: Int = 0
  while i < length(xs) do
    if i == index then
      out = append(out, value)
    else
      out = append(out, xs[i])
    end
    i = i + 1
  end
  return out
end

function main() returns Unit
  effects log
do
  let xs: List<Int> = append(append([], 10), 20)
  let ys: List<Int> = updateAt(xs, 1, 99)
  print(intToString(xs[0]))
  print(intToString(ys[1]))
end
"""
    result = run_source(source, "<list-test>")
    assert result.ok is True, result.to_dict()
    assert result.stdout == "10\n99\n", result.to_dict()


def test_list_item_assignment_is_rejected_by_prelint():
    diags = lint_common_ai_syntax(
        """
function bad(xs: List<Int>) returns List<Int>
  effects pure
do
  xs[0] = 99
  return xs
end
"""
    )
    assert diags, "item assignment should be rejected"
    assert diags[0].code == "E0006", diags[0].to_dict()
    assert "append" in (diags[0].suggestion or ""), diags[0].to_dict()


if __name__ == "__main__":
    test_index_read_append_and_rebuild_update()
    test_list_item_assignment_is_rejected_by_prelint()
    print("LIST OPERATION TESTS PASS")
