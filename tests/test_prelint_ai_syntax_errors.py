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
    assert _first_code("opt.unwrap()") == "E0012"
    assert _first_code("result.unwrap()") == "E0013"
    assert _first_code("result.is_ok()") == "E0014"
    assert _first_code("option.is_some()") == "E0015"
    assert _first_code("match opt { case Some(v) { v } }") == "E0016"


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


def test_option_result_repair_hints_point_to_standard_helpers():
    opt_unwrap = lint_common_ai_syntax("opt.unwrap()")[0]
    assert opt_unwrap.code == "E0012", opt_unwrap.to_dict()
    assert "expectSome" in (opt_unwrap.suggestion or ""), opt_unwrap.to_dict()
    assert "unwrapOr" in (opt_unwrap.suggestion or ""), opt_unwrap.to_dict()

    result_unwrap = lint_common_ai_syntax("result.unwrap()")[0]
    assert result_unwrap.code == "E0013", result_unwrap.to_dict()
    assert "expectOk" in (result_unwrap.suggestion or ""), result_unwrap.to_dict()
    assert "unwrapOrResult" in (result_unwrap.suggestion or ""), result_unwrap.to_dict()

    result_is_ok = lint_common_ai_syntax("result.is_ok()")[0]
    assert result_is_ok.code == "E0014", result_is_ok.to_dict()
    assert "isOk(result)" in (result_is_ok.suggestion or ""), result_is_ok.to_dict()

    option_is_some = lint_common_ai_syntax("option.is_some()")[0]
    assert option_is_some.code == "E0015", option_is_some.to_dict()
    assert "isSome(option)" in (option_is_some.suggestion or ""), option_is_some.to_dict()

    match_braces = lint_common_ai_syntax("match opt { case Some(v) { v } }")[0]
    assert match_braces.code == "E0016", match_braces.to_dict()
    assert "match expr do" in (match_braces.suggestion or ""), match_braces.to_dict()


if __name__ == "__main__":
    test_common_ai_syntax_errors_have_specific_codes()
    test_prelint_does_not_flag_supported_index_equality_or_map_literal()
    test_list_repair_hints_point_to_standard_helpers()
    test_option_result_repair_hints_point_to_standard_helpers()
    print("PRELINT TESTS PASS")
