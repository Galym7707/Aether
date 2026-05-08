"""Canonical Aether source printer.

The parser stores source positions in ``pos`` fields. Those positions are
layout metadata, so round-trip equality for the canonical printer is checked
after stripping ``pos`` from both ASTs.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


def print_ast(ast: Dict[str, Any]) -> str:
    """Return canonical Aether source for a parsed Program AST."""
    if ast.get("kind") != "Program":
        raise ValueError(f"expected Program AST, got {ast.get('kind')!r}")
    decls = [_decl(d) for d in ast.get("decls", [])]
    return "\n\n".join(decls).rstrip() + "\n"


def strip_positions(value: Any) -> Any:
    """Return a copy of an AST-like value without source-position metadata."""
    if isinstance(value, dict):
        return {
            k: strip_positions(v)
            for k, v in value.items()
            if k != "pos"
        }
    if isinstance(value, list):
        return [strip_positions(v) for v in value]
    return value


def ast_round_trips(original: Dict[str, Any], reparsed: Dict[str, Any]) -> bool:
    return strip_positions(original) == strip_positions(reparsed)


def _ind(lines: Iterable[str]) -> str:
    return "\n".join(("  " + line) if line else line for line in lines)


def _decl(d: Dict[str, Any]) -> str:
    kind = d["kind"]
    if kind == "ModuleDecl":
        lines = [f"module {d['name']}"]
        for cap in d.get("capabilities", []):
            lines.append(f"  requires capability {cap}")
        if d.get("exports"):
            lines.append("  exports " + ", ".join(d["exports"]))
        lines.append("end")
        return "\n".join(lines)
    if kind == "ImportDecl":
        src = "import " + ".".join(d["path"])
        if d.get("alias"):
            src += f" as {d['alias']}"
        return src
    if kind == "TypeDecl":
        src = f"type {d['name']} = {_type(d['base'])}"
        if d.get("refinement") is not None:
            src += f" where {_expr(d['refinement'])}"
        return src
    if kind == "RecordDecl":
        lines = [f"record {d['name']} do"]
        for field in d.get("fields", []):
            lines.append(f"  {field['name']}: {_type(field['type'])}")
        lines.append("end")
        return "\n".join(lines)
    if kind == "UnionDecl":
        lines = [f"union {d['name']} do"]
        for case in d.get("cases", []):
            params = case.get("params", [])
            if params:
                rendered = ", ".join(_param(p) for p in params)
                lines.append(f"  case {case['name']}({rendered})")
            else:
                lines.append(f"  case {case['name']}")
        lines.append("end")
        return "\n".join(lines)
    if kind == "ConstDecl":
        return f"const {d['name']}: {_type(d['type'])} = {_expr(d['value'])}"
    if kind == "FunctionDecl":
        return _function(d)
    raise NotImplementedError(f"top-level decl kind: {kind}")


def _function(d: Dict[str, Any]) -> str:
    generics = ""
    if d.get("generics"):
        generics = "<" + ", ".join(d["generics"]) + ">"
    params = ", ".join(_param(p) for p in d.get("params", []))
    lines = [
        f"function {d['name']}{generics}({params}) returns {_type(d['return_type'])}"
    ]
    for clause in d.get("requires", []):
        lines.append(f"  requires {_expr(clause)}")
    for clause in d.get("ensures", []):
        lines.append(f"  ensures {_expr(clause)}")
    lines.append("  effects " + ", ".join(_effect(e) for e in d.get("effects", [])))
    lines.append("do")
    body = d.get("body", [])
    if body:
        lines.append(_ind(_stmt(s) for s in body))
    lines.append("end")
    return "\n".join(lines)


def _param(p: Dict[str, Any]) -> str:
    return f"{p['name']}: {_type(p['type'])}"


def _type(t: Dict[str, Any]) -> str:
    kind = t["kind"]
    if kind == "TypeName":
        return t["name"]
    if kind == "GenericType":
        return f"{t['name']}<" + ", ".join(_type(a) for a in t.get("args", [])) + ">"
    if kind == "FunctionType":
        params = ", ".join(_type(p) for p in t.get("params", []))
        return f"function({params}) returns {_type(t['returns'])}"
    raise NotImplementedError(f"type kind: {kind}")


def _effect(e: Dict[str, Any]) -> str:
    path = e.get("path") or []
    if path == ["pure"]:
        return "pure"
    src = ".".join(path)
    if e.get("arg") is not None:
        src += f"({_expr(e['arg'])})"
    return src


def _stmt(s: Dict[str, Any]) -> str:
    kind = s["kind"]
    if kind in {"Let", "Var"}:
        src = kind.lower() + f" {s['name']}"
        if s.get("type") is not None:
            src += f": {_type(s['type'])}"
        return src + f" = {_expr(s['value'])}"
    if kind == "Assign":
        return f"{s['target']} = {_expr(s['value'])}"
    if kind == "ExprStmt":
        return _expr(s["expr"])
    if kind == "Return":
        if s.get("value") is None:
            return "return"
        return f"return {_expr(s['value'])}"
    if kind == "Break":
        return "break"
    if kind == "Continue":
        return "continue"
    if kind == "If":
        return _if_stmt(s)
    if kind == "While":
        lines = [f"while {_expr(s['cond'])} do"]
        body = s.get("body", [])
        if body:
            lines.append(_ind(_stmt(x) for x in body))
        lines.append("end")
        return "\n".join(lines)
    if kind == "For":
        lines = [f"for {s['var']} in {_expr(s['iter'])} do"]
        body = s.get("body", [])
        if body:
            lines.append(_ind(_stmt(x) for x in body))
        lines.append("end")
        return "\n".join(lines)
    if kind == "Match":
        return _match_stmt(s)
    raise NotImplementedError(f"stmt kind: {kind}")


def _if_stmt(s: Dict[str, Any]) -> str:
    lines = [f"if {_expr(s['cond'])} then"]
    if s.get("then"):
        lines.append(_ind(_stmt(x) for x in s["then"]))
    for branch in s.get("elifs", []):
        lines.append(f"elif {_expr(branch['cond'])} then")
        if branch.get("body"):
            lines.append(_ind(_stmt(x) for x in branch["body"]))
    if s.get("else") is not None:
        lines.append("else")
        if s["else"]:
            lines.append(_ind(_stmt(x) for x in s["else"]))
    lines.append("end")
    return "\n".join(lines)


def _match_stmt(s: Dict[str, Any]) -> str:
    lines = [f"match {_expr(s['scrutinee'])} do"]
    for arm in s.get("arms", []):
        lines.append(f"  case {_pattern(arm['pattern'])} do")
        body = arm.get("body", [])
        if body:
            lines.append(_ind(_ind(_stmt(x) for x in body).splitlines()))
        lines.append("  end")
    lines.append("end")
    return "\n".join(lines)


_BIN_PREC = {
    "or": 1,
    "and": 2,
    "implies": 3,
    "==": 4,
    "!=": 4,
    "<": 5,
    "<=": 5,
    ">": 5,
    ">=": 5,
    "is": 5,
    "in": 5,
    "+": 6,
    "-": 6,
    "*": 7,
    "/": 7,
    "%": 7,
}
_UNARY_PREC = 8


def _expr(
    e: Dict[str, Any],
    parent_prec: int = 0,
    side: str = "",
    parent_op: str = "",
) -> str:
    kind = e["kind"]
    if kind == "IntLit":
        return str(e["value"])
    if kind == "FloatLit":
        return repr(e["value"])
    if kind == "StringLit":
        return _string(e["value"])
    if kind == "BoolLit":
        return "true" if e["value"] else "false"
    if kind == "NullLit":
        return "null"
    if kind == "Ident":
        return e["name"]
    if kind == "BinOp":
        op = e["op"]
        prec = _BIN_PREC[op]
        src = (
            f"{_expr(e['left'], prec, 'left', op)} "
            f"{op} "
            f"{_expr(e['right'], prec, 'right', op)}"
        )
        if _needs_bin_parens(prec, op, parent_prec, side, parent_op):
            return f"({src})"
        return src
    if kind == "UnaryOp":
        value = e["value"]
        if e["op"] == "neg":
            inner = _expr(value, _UNARY_PREC)
            if value.get("kind") in {"BinOp", "IfExpr", "MatchExpr"}:
                inner = f"({inner})"
            src = f"-{inner}"
        else:
            inner = _expr(value, _UNARY_PREC)
            if value.get("kind") in {"BinOp", "IfExpr", "MatchExpr"}:
                inner = f"({inner})"
            src = f"{e['op']} {inner}"
        if _UNARY_PREC < parent_prec:
            return f"({src})"
        return src
    if kind == "Call":
        return f"{_postfix_base(e['func'])}(" + ", ".join(
            _expr(a) for a in e.get("args", [])
        ) + ")"
    if kind == "Field":
        return f"{_postfix_base(e['value'])}.{e['name']}"
    if kind == "Index":
        return f"{_postfix_base(e['value'])}[{_expr(e['index'])}]"
    if kind == "ListLit":
        return "[" + ", ".join(_expr(x) for x in e.get("elems", [])) + "]"
    if kind == "MapLit":
        items = [
            f"{_expr(entry['key'])}: {_expr(entry['value'])}"
            for entry in e.get("entries", [])
        ]
        return "{" + ", ".join(items) + "}"
    if kind == "IfExpr":
        return _if_expr(e)
    if kind == "MatchExpr":
        return _match_expr(e)
    if kind == "Old":
        return f"old({_expr(e['value'])})"
    raise NotImplementedError(f"expr kind: {kind}")


def _needs_bin_parens(
    prec: int,
    op: str,
    parent_prec: int,
    side: str,
    parent_op: str,
) -> bool:
    if parent_prec == 0:
        return False
    if prec < parent_prec:
        return True
    if prec > parent_prec:
        return False
    if parent_op == "implies":
        return side == "left"
    if op == "implies":
        return side == "left"
    return side == "right"


def _postfix_base(e: Dict[str, Any]) -> str:
    src = _expr(e)
    if e.get("kind") in {"BinOp", "UnaryOp", "IfExpr", "MatchExpr"}:
        return f"({src})"
    return src


def _if_expr(e: Dict[str, Any]) -> str:
    parts = [f"if {_expr(e['cond'])} then {_expr(e['then'])}"]
    for branch in e.get("elifs", []):
        parts.append(f"elif {_expr(branch['cond'])} then {_expr(branch['value'])}")
    parts.append(f"else {_expr(e['else'])} end")
    return " ".join(parts)


def _match_expr(e: Dict[str, Any]) -> str:
    parts = [f"match {_expr(e['scrutinee'])} do"]
    for arm in e.get("arms", []):
        parts.append(f"case {_pattern(arm['pattern'])} do {_expr(arm['value'])} end")
    parts.append("end")
    return " ".join(parts)


def _pattern(p: Dict[str, Any]) -> str:
    kind = p["kind"]
    if kind == "WildcardPat":
        return "_"
    if kind == "BindPat":
        return p["name"]
    if kind == "LiteralPat":
        lit_kind = p.get("lit_kind")
        if lit_kind == "string":
            return _string(p["value"])
        if lit_kind == "kw":
            return str(p["value"])
        return str(p["value"])
    if kind == "ConstructorPat":
        return ".".join(p["path"]) + "(" + ", ".join(
            _pattern(a) for a in p.get("args", [])
        ) + ")"
    if kind == "AsPat":
        return f"{_pattern(p['pattern'])} as {p['name']}"
    raise NotImplementedError(f"pattern kind: {kind}")


def _string(value: str) -> str:
    out: List[str] = ['"']
    for ch in value:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\0":
            out.append("\\0")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)
