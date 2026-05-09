from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _diag(source: str) -> dict:
    path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".aeth", delete=False, encoding="utf-8") as f:
            f.write(source)
            path = f.name
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "transpiler.aether.cli", "--json", "check", path],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0, proc
        payload = json.loads(proc.stderr)
        assert payload["errors"], payload
        return payload["errors"][0]
    finally:
        if path and os.path.exists(path):
            os.unlink(path)


def test_common_ai_wrong_syntax_has_repair_hints():
    cases = [
        ("fn f(x: Int) -> Int\n  effects pure\ndo\n  return x\nend\n", "E0001", "function"),
        ("function f(x: Int) -> Int\n  effects pure\ndo\n  return x\nend\n", "E0002", "returns"),
        ("function f(xs: List[Int]) returns Int\n  effects pure\ndo\n  return 0\nend\n", "E0003", "List<Int>"),
        ("function f(xs: List<Int>) returns Int\n  effects pure\ndo\n  return xs.len()\nend\n", "E0004", "length(value)"),
        ("function f() returns Int\n  effects pure\ndo\n  let g = (x) => x\n  return 0\nend\n", "E0005", "helper"),
        ("function f(xs: List<Int>) returns List<Int>\n  effects pure\ndo\n  xs[0] = 1\n  return xs\nend\n", "E0006", "append"),
        ("function f(x: Int) returns Int { return x }\n", "E0007", "do"),
        ("function f() returns Unit\n  effects pure\ndo\n  let xs: List<Int> = [1]\n  xs.append(2)\nend\n", "E0009", "append(xs, value)"),
        (
            "function identity<T>(x: T) returns T\n  effects pure\ndo\n  return x\nend\nfunction main() returns Unit\n  effects pure\ndo\n  let x: Int = identity<Int>(5)\nend\n",
            "E0008",
            "identity(5)",
        ),
    ]
    for source, code, hint_fragment in cases:
        diag = _diag(source)
        assert diag["code"] == code, diag
        assert hint_fragment in diag["hint"], diag
        assert diag["line"] > 0, diag
        assert diag["source_snippet"], diag


def test_type_error_diagnostic_is_suitable_for_repair_loop():
    diag = _diag(
        """
function main() returns Unit
  effects pure
do
  let xs: List<Int> = [1, "bad"]
end
"""
    )
    assert diag["code"] == "TYPE_LIST_ELEMENT_MISMATCH", diag
    assert diag["expected"] == "Int", diag
    assert diag["actual"] == "String", diag
    assert "Use only Int values" in diag["hint"], diag
    assert diag["source_snippet"].strip() == 'let xs: List<Int> = [1, "bad"]', diag


if __name__ == "__main__":
    test_common_ai_wrong_syntax_has_repair_hints()
    test_type_error_diagnostic_is_suitable_for_repair_loop()
    print("AI REPAIR DIAGNOSTIC TESTS PASS")
