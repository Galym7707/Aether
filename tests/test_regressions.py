"""Regression tests for the three post-audit fixes.

S-001 — ensures clauses fire at runtime.
S-011 — `x!=3` (no spaces) tokenizes correctly.
S-012 — harness enforces timeout_ms.
"""

from __future__ import annotations
import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "transpiler"))
sys.path.insert(0, ROOT)

from aether.lexer import tokenize
from aether.parser import parse
from aether.emitter import emit
from aether.runtime import build_namespace
from aether.diagnostics import AetherError
from bench.harness import compile_and_run, grade_task, run_python_equivalent


def test_S011_lexer_tight_neq():
    """`x!=3` must lex as ident, !=, int — not as ident-with-bang then = then int."""
    toks = tokenize("x!=3")
    kinds_values = [(t.kind, t.value) for t in toks if t.kind != "eof"]
    assert kinds_values == [("ident", "x"), ("sym", "!="), ("int", 3)], kinds_values
    # And predicate idents still work
    toks = tokenize("isVowel? c")
    vals = [t.value for t in toks if t.kind != "eof"]
    assert vals == ["isVowel?", "c"], vals
    # Effectful idents still work
    toks = tokenize("readFile! path")
    vals = [t.value for t in toks if t.kind != "eof"]
    assert vals == ["readFile!", "path"], vals
    # And ident! followed by = still lexes correctly: writeFile != 5
    toks = tokenize("writeFile!=5")
    vals = [(t.kind, t.value) for t in toks if t.kind != "eof"]
    assert vals == [("ident", "writeFile"), ("sym", "!="), ("int", 5)], vals
    print("S-011: lexer handles x!=3 correctly")


def _run(src):
    """Compile + exec a program, return its captured stdout or raise."""
    import io
    from contextlib import redirect_stdout
    ast = parse(src, "<test>")
    py = emit(ast)
    code = compile(py, "<test>", "exec")
    g = build_namespace()
    g["__name__"] = "__main__"
    buf = io.StringIO()
    with redirect_stdout(buf):
        exec(code, g)
    return buf.getvalue()


def test_S001_ensures_violation_raises():
    """A function that violates its ensures clause must raise [E0301]."""
    bad = """
function double(x: Int) returns Int
  ensures result == x * 2
  effects pure
do
  return x + x + 1
end

function main() returns Unit
  effects log
do
  print(intToString(double(5)))
end
"""
    raised = False
    try:
        _run(bad)
    except AetherError as e:
        raised = True
        assert e.diag.code == "E0301", e.diag.code
        assert "ensures" in e.diag.message, e.diag.message
        assert "double" in e.diag.message, e.diag.message
    assert raised, "ensures violation did not raise"
    print("S-001: ensures violation correctly raises E0301")


def test_S001_ensures_honored_passes():
    """A function that honors its ensures clause must run to completion."""
    good = """
function double(x: Int) returns Int
  ensures result == x * 2
  effects pure
do
  return x + x
end

function main() returns Unit
  effects log
do
  print(intToString(double(5)))
end
"""
    out = _run(good)
    assert out == "10\n", repr(out)
    print("S-001: honored ensures lets program complete")


def test_S012_timeout_fires():
    """compile_and_run must enforce timeout_ms via SIGALRM."""
    if not hasattr(__import__("signal"), "SIGALRM"):
        print("S-012: SKIPPED (no SIGALRM on this platform)")
        return
    looper = """
function main() returns Unit
  effects log
do
  var i: Int = 0
  while i >= 0 do
    i = i + 1
  end
end
"""
    t0 = time.time()
    out = compile_and_run(looper, "<looper>", timeout_ms=300)
    elapsed = (time.time() - t0) * 1000
    assert out["ok"] is False, out
    assert out["stage"] == "exec", out
    assert out["diagnostic"]["category"] == "timeout", out
    assert out["diagnostic"]["code"] == "E0601", out
    # Timeout should fire close to 300ms (allow generous slack)
    assert 250 <= elapsed <= 1500, f"timeout fired at {elapsed:.0f}ms"
    print(f"S-012: timeout fired at {elapsed:.0f}ms with structured diagnostic")


def test_S002_refinement_violation_raises():
    """A value that fails its refinement predicate must raise [E0302]."""
    bad = """
type PositiveInt = Int where self > 0

function show(n: PositiveInt) returns String
  effects pure
do
  return intToString(n)
end

function main() returns Unit
  effects log
do
  print(show(0))
end
"""
    raised = False
    try:
        _run(bad)
    except AetherError as e:
        raised = True
        assert e.diag.code == "E0302", e.diag.code
        assert "PositiveInt" in e.diag.message, e.diag.message
    assert raised, "refinement violation did not raise"
    print("S-002: refinement boundary check fires with E0302")


def test_S002_refinement_passes_on_valid():
    """A value that satisfies the refinement must pass through cleanly."""
    good = """
type PositiveInt = Int where self > 0

function show(n: PositiveInt) returns String
  effects pure
do
  return intToString(n)
end

function main() returns Unit
  effects log
do
  print(show(42))
  print(show(1))
end
"""
    out = _run(good)
    assert out == "42\n1\n", repr(out)
    print("S-002: honored refinement lets program complete")


def test_harness_wedge_checks_diagnostic_code():
    """Wedge grading must check exit code, stderr regex, and diagnostic code."""
    src = """
function positiveOnly(x: Int) returns Int
  requires x > 0
  effects pure
do
  return x
end

function main() returns Unit
  effects log
do
  print(intToString(positiveOnly(0)))
end
"""
    path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".aeth", delete=False, encoding="utf-8"
        ) as f:
            f.write(src)
            path = f.name
        task = {
            "id": "harness_contract_wedge",
            "config": {
                "expected_stdout": "",
                "expected_exit_code": 2,
                "expected_stderr_pattern": "(?i)requires.*positiveOnly",
                "expected_diagnostic_code": "E0301",
                "expected_diagnostic_category": "contract",
                "timeout_ms": 5000,
            },
        }
        out = grade_task(task, path)
        assert out["ok"] is True, out
        assert out["checks"]["diagnostic_code_ok"] is True, out
        assert out["checks"]["diagnostic_category_ok"] is True, out
    finally:
        if path and os.path.exists(path):
            os.unlink(path)


def test_harness_python_equivalent_metadata():
    """Python equivalent metadata must be executable and gradeable by harness."""
    with tempfile.TemporaryDirectory() as td:
        py_path = os.path.join(td, "equivalent.py")
        with open(py_path, "w", encoding="utf-8") as f:
            f.write("print('wrong-but-silent')\n")
        task = {
            "id": "python_equivalent_metadata",
            "dir": td,
            "config": {
                "python_equivalent": "equivalent.py",
                "python_expected_exit_code": 0,
                "python_expected_stdout": "wrong-but-silent\n",
                "python_expected_stderr": "",
                "python_forbidden_stderr_pattern": "(?i)(contract|requires|refinement)",
                "timeout_ms": 5000,
            },
        }
        out = run_python_equivalent(task)
        assert out["ok"] is True, out
        assert out["exit_code"] == 0, out
        assert out["stderr"] == "", out


def test_capability_strict_blocks_undeclared():
    """--capability-strict must reject programs whose declared effects exceed
    the capabilities declared by any module."""
    from aether.passes.capability import check_capabilities
    from aether.parser import parse as _parse
    src = """
function main() returns Unit
  effects log
do
  print("hello")
end
"""
    ast = _parse(src, "<cap>")
    diags = check_capabilities(ast)
    assert len(diags) == 1, diags
    assert diags[0].code == "E0701"
    assert diags[0].extra["required_capability"] == "log"
    print("capability gating: undeclared 'log' capability flagged with E0701")


def test_capability_strict_admits_declared():
    """A program whose module declares the capability passes the static check."""
    from aether.passes.capability import check_capabilities
    from aether.parser import parse as _parse
    src = """
module App
  requires capability log
  exports main
end

function main() returns Unit
  effects log
do
  print("hello")
end
"""
    ast = _parse(src, "<cap>")
    diags = check_capabilities(ast)
    assert diags == [], diags
    print("capability gating: declared capability admits the function")


if __name__ == "__main__":
    test_S011_lexer_tight_neq()
    test_S001_ensures_violation_raises()
    test_S001_ensures_honored_passes()
    test_S012_timeout_fires()
    test_S002_refinement_violation_raises()
    test_S002_refinement_passes_on_valid()
    test_harness_wedge_checks_diagnostic_code()
    test_harness_python_equivalent_metadata()
    test_capability_strict_blocks_undeclared()
    test_capability_strict_admits_declared()
    print("ALL REGRESSION TESTS PASS")
