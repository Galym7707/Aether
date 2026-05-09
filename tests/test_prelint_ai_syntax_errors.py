from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from transpiler.aether.prelint import lint_common_ai_syntax


def _first_code(source: str) -> str:
    diags = lint_common_ai_syntax(source)
    assert diags, source
    return diags[0].code


def test_common_ai_syntax_errors_have_specific_codes():
    assert _first_code("fn f(x: Int) returns Int do return x end") == "E0001"
    assert _first_code("function f(x: Int) -> Int do return x end") == "E0002"
    assert _first_code("function f(xs: List[Int]) returns Int effects pure do return 0 end") == "E0003"
    assert _first_code("let n: Int = xs.len()") == "E0004"
    assert _first_code("let f = (x) => x + 1") == "E0005"
    assert _first_code("result[i] = value") == "E0006"
    assert _first_code("if x > 0 { return x }") == "E0007"
    assert _first_code("let x = identity<Int>(5)") == "E0008"
    assert _first_code("xs.append(1)") == "E0009"


def test_prelint_does_not_flag_supported_index_equality_or_map_literal():
    src = """
function ok(xs: List<Int>) returns Int
  effects pure
do
  if xs[0] == 1 then
    let m: Map<String, Int> = {"a": 1}
    return get(m, "a")[1]
  end
  return 0
end
"""
    assert lint_common_ai_syntax(src) == []


if __name__ == "__main__":
    test_common_ai_syntax_errors_have_specific_codes()
    test_prelint_does_not_flag_supported_index_equality_or_map_literal()
    print("PRELINT TESTS PASS")
