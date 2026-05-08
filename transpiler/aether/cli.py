"""Aether CLI — single entry point for the v0.1 toolchain.

Subcommands:
    aether parse  <file>           Lex + parse, print canonical AST as JSON
    aether emit   <file>           Emit Python source for the program
    aether check  <file>           Parse + emit (without running) — exit 0 if OK
    aether run    <file>           Parse, emit, exec; mirrors stdout/stderr
    aether test   <dir>            Run a reference-program directory: expects
                                   `program.aeth` and `expected_stdout.txt`

Global flag: --json — emit machine-readable error output. The CLI prints a
single JSON object on stderr and exits non-zero on failure.
"""

from __future__ import annotations
import argparse
import io
import json
import os
import sys
from contextlib import redirect_stdout
from typing import Any, Dict

from .diagnostics import AetherError, Diagnostic
from .lexer import tokenize
from .parser import parse
from .emitter import emit
from .passes.capability import check_capabilities
from .passes.effects import check_effects
from .runtime import build_namespace, set_effect_strict


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _emit_error(diag: Diagnostic, as_json: bool):
    if as_json:
        json.dump({"ok": False, "diagnostic": diag.to_dict()}, sys.stderr)
        sys.stderr.write("\n")
    else:
        sys.stderr.write(
            f"[{diag.code}] {diag.severity} ({diag.category}) "
            f"at line {diag.position.line}, col {diag.position.column}: "
            f"{diag.message}\n"
        )
        if diag.suggestion:
            sys.stderr.write(f"  hint: {diag.suggestion}\n")


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ----------------------------------------------------------------------
# Subcommands
# ----------------------------------------------------------------------

def cmd_parse(args) -> int:
    src = _read(args.file)
    ast = parse(src, args.file)
    print(json.dumps(ast, indent=2, default=str, ensure_ascii=False))
    return 0


def cmd_emit(args) -> int:
    src = _read(args.file)
    ast = parse(src, args.file)
    py = emit(ast)
    print(py)
    return 0


def _run_capability_check(ast, as_json) -> int:
    """Returns 0 if all capabilities OK, 2 otherwise (writes diagnostics)."""
    diags = check_capabilities(ast)
    if not diags:
        return 0
    for d in diags:
        _emit_error(d, as_json)
    return 2


def _run_effect_check(ast, as_json) -> int:
    """Returns 0 if all effect subsets OK, 2 otherwise."""
    diags = check_effects(ast)
    if not diags:
        return 0
    for d in diags:
        _emit_error(d, as_json)
    return 2


def cmd_check(args) -> int:
    src = _read(args.file)
    ast = parse(src, args.file)
    rc = _run_effect_check(ast, args.json)
    if rc != 0:
        return rc
    py = emit(ast)
    # Compile but don't execute.
    compile(py, args.file + ".py", "exec")
    if getattr(args, "capability_strict", False):
        rc = _run_capability_check(ast, args.json)
        if rc != 0:
            return rc
    if args.json:
        json.dump({"ok": True, "decls": len(ast["decls"])}, sys.stdout)
        sys.stdout.write("\n")
    else:
        print(f"OK: {args.file} ({len(ast['decls'])} decls)")
    return 0


def cmd_run(args) -> int:
    if args.effect_strict:
        set_effect_strict(True)
    src = _read(args.file)
    ast = parse(src, args.file)
    rc = _run_effect_check(ast, args.json)
    if rc != 0:
        return rc
    if getattr(args, "capability_strict", False):
        rc = _run_capability_check(ast, args.json)
        if rc != 0:
            return rc
    py = emit(ast)
    code = compile(py, args.file + ".py", "exec")
    g = build_namespace()
    g["__name__"] = "__main__"
    g["__file__"] = args.file + ".py"
    exec(code, g)
    return 0


def cmd_test(args) -> int:
    """Run a directory containing program.aeth + expected_stdout.txt.

    Exits 0 on match, 1 on mismatch, 2 on compile/runtime error.
    """
    pdir = args.dir
    src_path = os.path.join(pdir, "program.aeth")
    exp_path = os.path.join(pdir, "expected_stdout.txt")
    if not os.path.isfile(src_path):
        print(f"missing program.aeth in {pdir}", file=sys.stderr)
        return 2
    src = _read(src_path)
    expected = _read(exp_path) if os.path.isfile(exp_path) else ""
    try:
        ast = parse(src, src_path)
        rc = _run_effect_check(ast, args.json)
        if rc != 0:
            return rc
        py = emit(ast)
        code = compile(py, src_path + ".py", "exec")
        g = build_namespace()
        g["__name__"] = "__main__"
        buf = io.StringIO()
        with redirect_stdout(buf):
            exec(code, g)
        actual = buf.getvalue()
    except AetherError as e:
        _emit_error(e.diag, args.json)
        return 2
    except Exception as e:  # pragma: no cover
        sys.stderr.write(f"runtime error: {e}\n")
        return 2
    ok = actual == expected
    if args.json:
        json.dump({"ok": ok, "expected": expected, "actual": actual}, sys.stdout)
        sys.stdout.write("\n")
    elif ok:
        print(f"PASS  {pdir}")
    else:
        print(f"FAIL  {pdir}")
        print("--- expected ---")
        print(expected, end="")
        print("--- actual ---")
        print(actual, end="")
        print("--- end ---")
    return 0 if ok else 1


# ----------------------------------------------------------------------
# argparse wiring
# ----------------------------------------------------------------------

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="aether", description="Aether v0.1 toolchain")
    p.add_argument("--json", action="store_true",
                   help="emit machine-readable JSON output for diagnostics")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("parse", help="parse a file and print its AST")
    sp.add_argument("file")

    sp = sub.add_parser("emit", help="emit Python source for a file")
    sp.add_argument("file")

    sp = sub.add_parser("check", help="parse + emit (no execution)")
    sp.add_argument("file")
    sp.add_argument("--capability-strict", action="store_true",
                    help="enforce that every effect's required capability is "
                         "declared by some module in the program")

    sp = sub.add_parser("run", help="parse + emit + execute")
    sp.add_argument("file")
    sp.add_argument("--effect-strict", action="store_true",
                    help="enforce that observed effects are subset of declared")
    sp.add_argument("--capability-strict", action="store_true",
                    help="enforce that every effect's required capability is "
                         "declared by some module in the program")

    sp = sub.add_parser("test", help="run a reference program directory")
    sp.add_argument("dir")

    args = p.parse_args(argv)
    try:
        if args.cmd == "parse":   return cmd_parse(args)
        if args.cmd == "emit":    return cmd_emit(args)
        if args.cmd == "check":   return cmd_check(args)
        if args.cmd == "run":     return cmd_run(args)
        if args.cmd == "test":    return cmd_test(args)
    except AetherError as e:
        _emit_error(e.diag, args.json)
        return 2
    except FileNotFoundError as e:
        sys.stderr.write(f"file not found: {e}\n")
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
