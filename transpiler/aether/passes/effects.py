"""Static effect-subset checker.

This pass walks every FunctionDecl and checks direct calls to known local or
stdlib functions. For each call, the callee's declared effects must be covered
by the caller's declared effects. The pass is intentionally conservative:
unknown callees, higher-order function parameters, and dynamic field calls are
left to runtime behavior or future type analysis.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..diagnostics import Diagnostic, Position


EffectPath = Tuple[str, ...]


_PURE: Tuple[EffectPath, ...] = ()


_STDLIB_EFFECTS: Dict[str, Tuple[EffectPath, ...]] = {
    # Built-in union constructors.
    "Some": _PURE,
    "None": _PURE,
    "Ok": _PURE,
    "Err": _PURE,
    # List.
    "length": _PURE,
    "empty?": _PURE,
    "head": _PURE,
    "tail": _PURE,
    "append": _PURE,
    "prepend": _PURE,
    "concat": _PURE,
    "get": _PURE,
    "map": _PURE,
    "filter": _PURE,
    "foldLeft": _PURE,
    "reverse": _PURE,
    "range": _PURE,
    # Map.
    "size": _PURE,
    "set": _PURE,
    "remove": _PURE,
    "has?": _PURE,
    "keys": _PURE,
    "values": _PURE,
    # Set.
    "add": _PURE,
    "contains?": _PURE,
    # String.
    "slice": _PURE,
    "split": _PURE,
    "join": _PURE,
    "trim": _PURE,
    "toLower": _PURE,
    "toUpper": _PURE,
    "replace": _PURE,
    "startsWith?": _PURE,
    "endsWith?": _PURE,
    "parseInt": _PURE,
    "parseFloat": _PURE,
    "intToString": _PURE,
    # IO.
    "print": (("log",),),
    "readLine": (("log",),),
    "readFile": (("fs", "read"),),
    "writeFile": (("fs", "write"),),
    # Time / Hash / Math.
    "now": (("time", "now"),),
    "sha256": _PURE,
    "sha1": _PURE,
    "md5": _PURE,
    "abs": _PURE,
    "min": _PURE,
    "max": _PURE,
    "floor": _PURE,
    "ceil": _PURE,
    "pow": _PURE,
    "sqrt": _PURE,
    # Result / Option helpers.
    "isOk?": _PURE,
    "isErr?": _PURE,
    "unwrapOr": _PURE,
    "isSome?": _PURE,
    "isNone?": _PURE,
    "unwrapOrElse": _PURE,
}


def _effect_paths(effects: Iterable[Dict[str, Any]]) -> Tuple[EffectPath, ...]:
    paths: List[EffectPath] = []
    for effect in effects:
        path = tuple(effect.get("path") or ())
        if not path or path == ("pure",):
            continue
        paths.append(path)
    return tuple(paths)


def _effect_name(path: EffectPath) -> str:
    return ".".join(path)


def _covers(declared: EffectPath, required: EffectPath) -> bool:
    """True when a caller declaration covers a callee effect.

    This mirrors the current runtime prefix rule: declaring `fs` covers
    `fs.read`, while declaring `fs.read` does not cover a callee that declares
    broader `fs`.
    """
    if len(declared) > len(required):
        return False
    return declared == required[: len(declared)]


def _effect_allowed(required: EffectPath, caller_effects: Tuple[EffectPath, ...]) -> bool:
    return any(_covers(declared, required) for declared in caller_effects)


def _local_effect_table(ast: Dict[str, Any]) -> Dict[str, Tuple[EffectPath, ...]]:
    table: Dict[str, Tuple[EffectPath, ...]] = {}
    for decl in ast.get("decls", []):
        if decl.get("kind") == "FunctionDecl":
            table[decl["name"]] = _effect_paths(decl.get("effects", []))
        elif decl.get("kind") == "RecordDecl":
            table[decl["name"]] = _PURE
        elif decl.get("kind") == "UnionDecl":
            for case in decl.get("cases", []):
                table[case["name"]] = _PURE
    return table


def _resolve_callee_name(callee: Dict[str, Any]) -> Optional[str]:
    if callee.get("kind") == "Ident":
        return callee["name"]
    if callee.get("kind") == "Field":
        # Qualified union constructors such as `Climate.Cold(...)` are pure.
        inner = callee.get("value") or {}
        if inner.get("kind") == "Ident":
            return callee.get("name")
    return None


def _expr_children(expr: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    kind = expr.get("kind")
    if kind == "Call":
        yield expr["func"]
        yield from expr.get("args", [])
    elif kind == "BinOp":
        yield expr["left"]
        yield expr["right"]
    elif kind == "UnaryOp":
        yield expr["value"]
    elif kind == "Field":
        yield expr["value"]
    elif kind == "Index":
        yield expr["value"]
        yield expr["index"]
    elif kind == "ListLit":
        yield from expr.get("elems", [])
    elif kind == "MapLit":
        for entry in expr.get("entries", []):
            yield entry["key"]
            yield entry["value"]
    elif kind == "IfExpr":
        yield expr["cond"]
        yield expr["then"]
        for branch in expr.get("elifs", []):
            yield branch["cond"]
            yield branch["value"]
        yield expr["else"]
    elif kind == "MatchExpr":
        yield expr["scrutinee"]
        for arm in expr.get("arms", []):
            yield arm["value"]
    elif kind == "Old":
        yield expr["value"]


def _walk_expr(expr: Optional[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    if not expr:
        return
    yield expr
    for child in _expr_children(expr):
        yield from _walk_expr(child)


def _stmt_exprs(stmt: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    kind = stmt.get("kind")
    if kind in {"Let", "Var", "Assign"}:
        yield stmt["value"]
    elif kind == "ExprStmt":
        yield stmt["expr"]
    elif kind == "Return" and stmt.get("value") is not None:
        yield stmt["value"]
    elif kind == "If":
        yield stmt["cond"]
        for nested in stmt.get("then", []):
            yield from _stmt_exprs(nested)
        for branch in stmt.get("elifs", []):
            yield branch["cond"]
            for nested in branch.get("body", []):
                yield from _stmt_exprs(nested)
        if stmt.get("else") is not None:
            for nested in stmt.get("else", []):
                yield from _stmt_exprs(nested)
    elif kind == "While":
        yield stmt["cond"]
        for nested in stmt.get("body", []):
            yield from _stmt_exprs(nested)
    elif kind == "For":
        yield stmt["iter"]
        for nested in stmt.get("body", []):
            yield from _stmt_exprs(nested)
    elif kind == "Match":
        yield stmt["scrutinee"]
        for arm in stmt.get("arms", []):
            for nested in arm.get("body", []):
                yield from _stmt_exprs(nested)


def _function_expressions(fn: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for clause in fn.get("requires", []):
        yield clause
    for clause in fn.get("ensures", []):
        yield clause
    for stmt in fn.get("body", []):
        yield from _stmt_exprs(stmt)


def check_effects(ast: Dict[str, Any]) -> List[Diagnostic]:
    """Return E0801 diagnostics for static effect-subset violations."""
    local_effects = _local_effect_table(ast)
    known_effects = dict(_STDLIB_EFFECTS)
    known_effects.update(local_effects)

    diags: List[Diagnostic] = []
    for fn in ast.get("decls", []):
        if fn.get("kind") != "FunctionDecl":
            continue
        caller = fn["name"]
        caller_effects = _effect_paths(fn.get("effects", []))
        pos = fn.get("pos") or {"line": 0, "column": 0}

        for root_expr in _function_expressions(fn):
            for expr in _walk_expr(root_expr):
                if expr.get("kind") != "Call":
                    continue
                callee = _resolve_callee_name(expr["func"])
                if callee is None or callee not in known_effects:
                    continue
                required_effects = known_effects[callee]
                for required in required_effects:
                    if _effect_allowed(required, caller_effects):
                        continue
                    diags.append(
                        Diagnostic(
                            code="E0801",
                            category="effect",
                            severity="error",
                            message=(
                                f"function {caller!r} declares effects "
                                f"{_format_effect_set(caller_effects)} but calls "
                                f"{callee!r}, which requires effect "
                                f"{_effect_name(required)!r}"
                            ),
                            position=Position(pos.get("line", 0), pos.get("column", 0)),
                            suggestion=(
                                f"add effect {_effect_name(required)!r} to "
                                f"{caller!r}, or call only functions covered by "
                                "the declared effects"
                            ),
                            confidence=1.0,
                            extra={
                                "caller": caller,
                                "callee": callee,
                                "caller_effects": [
                                    _effect_name(path) for path in caller_effects
                                ],
                                "required_effect": _effect_name(required),
                            },
                        )
                    )
    return diags


def _format_effect_set(effects: Tuple[EffectPath, ...]) -> str:
    if not effects:
        return "'pure'"
    return ", ".join(repr(_effect_name(effect)) for effect in effects)
