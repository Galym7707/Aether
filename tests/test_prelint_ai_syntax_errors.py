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
    assert _first_code("xs[1:3]") == "E0010"
    assert _first_code("xs.get(1)") == "E0011"


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


def test_list_repair_hints_point_to_standard_helpers():
    item_assignment = lint_common_ai_syntax("result[i] = value")[0]
    assert item_assignment.code == "E0006", item_assignment.to_dict()
    assert "updateAt" in (item_assignment.suggestion or ""), item_assignment.to_dict()
    assert "Result" in (item_assignment.suggestion or ""), item_assignment.to_dict()

    slicing = lint_common_ai_syntax("let ys = xs[start:end]")[0]
    assert slicing.code == "E0010", slicing.to_dict()
    assert "safeSlice" in (slicing.suggestion or ""), slicing.to_dict()

    get_call = lint_common_ai_syntax("let x = xs.get(i)")[0]
    assert get_call.code == "E0011", get_call.to_dict()
    assert "safeAt" in (get_call.suggestion or ""), get_call.to_dict()

    append_call = lint_common_ai_syntax("xs.append(x)")[0]
    assert append_call.code == "E0009", append_call.to_dict()
    assert "append(xs, x)" in (append_call.suggestion or ""), append_call.to_dict()
    assert "updateAt" in (append_call.suggestion or ""), append_call.to_dict()


if __name__ == "__main__":
    test_common_ai_syntax_errors_have_specific_codes()
    test_prelint_does_not_flag_supported_index_equality_or_map_literal()
    test_list_repair_hints_point_to_standard_helpers()
    print("PRELINT TESTS PASS")
