"""Static effect-subset checker.

This pass walks every FunctionDecl and checks direct calls to known local or
stdlib functions. For each call, the callee's declared effects must be covered
by the caller's declared effects. The pass is intentionally conservative:
unknown callees, higher-order function parameters, and dynamic field calls are
left to runtime behavior or future type analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..diagnostics import Diagnostic, Position


EffectPath = Tuple[str, ...]


@dataclass(frozen=True)
class EffectSpec:
    path: EffectPath
    arg: Optional[str] = None
    has_arg: bool = False


EffectSet = Tuple[EffectSpec, ...]


def _spec(path: Iterable[str], arg: Optional[str] = None) -> EffectSpec:
    return EffectSpec(tuple(path), arg, arg is not None)


_PURE: EffectSet = ()


_STDLIB_EFFECTS: Dict[str, EffectSet] = {
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
    "print": (_spec(("log",)),),
    "readLine": (_spec(("log",)),),
    "readFile": (_spec(("fs", "read")),),
    "writeFile": (_spec(("fs", "write")),),
    # Time / Hash / Math.
    "now": (_spec(("time", "now")),),
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


def _literal_string_arg(expr: Optional[Dict[str, Any]]) -> Optional[str]:
    if expr and expr.get("kind") == "StringLit":
        return expr["value"]
    return None


def _effect_specs(effects: Iterable[Dict[str, Any]]) -> EffectSet:
    specs: List[EffectSpec] = []
    for effect in effects:
        path = tuple(effect.get("path") or ())
        if not path or path == ("pure",):
            continue
        arg_expr = effect.get("arg")
        specs.append(
            EffectSpec(path, _literal_string_arg(arg_expr), arg_expr is not None)
        )
    return tuple(specs)


def _effect_name(effect: EffectSpec) -> str:
    name = ".".join(effect.path)
    if effect.has_arg:
        if effect.arg is None:
            return f"{name}(?)"
        return f"{name}({effect.arg!r})"
    return name


def _has_glob(pattern: str) -> bool:
    return any(ch in pattern for ch in "*?[")


def _trailing_star_prefix(pattern: str) -> Optional[str]:
    if not pattern.endswith("*"):
        return None
    prefix = pattern[:-1]
    if _has_glob(prefix):
        return None
    return prefix


def _glob_covers(declared_pattern: str, required_pattern: str) -> bool:
    """True when every required URL is covered by the declared URL glob.

    General glob-subset solving is intentionally out of scope. This accepts
    exact equality, concrete required strings matched by the caller glob, and
    the common trailing-star subset case used by `net.fetch(".../*")`.
    """
    if declared_pattern == required_pattern:
        return True
    if not _has_glob(required_pattern):
        return fnmatchcase(required_pattern, declared_pattern)
    declared_prefix = _trailing_star_prefix(declared_pattern)
    required_prefix = _trailing_star_prefix(required_pattern)
    if declared_prefix is None or required_prefix is None:
        return False
    return required_prefix.startswith(declared_prefix)


def _covers(declared: EffectSpec, required: EffectSpec) -> bool:
    """True when a caller declaration covers a callee effect.

    This mirrors the current runtime prefix rule: declaring `fs` covers
    `fs.read`, while declaring `fs.read` does not cover a callee that declares
    broader `fs`. For equal paths, an unargumented caller effect such as
    `net.fetch` covers an argumented callee effect like
    `net.fetch("https://api.x/*")`; a narrower caller glob does not cover a
    broader callee declaration.
    """
    if len(declared.path) > len(required.path):
        return False
    if declared.path != required.path[: len(declared.path)]:
        return False
    if len(declared.path) < len(required.path):
        return True
    if not declared.has_arg:
        return True
    if not required.has_arg:
        return False
    if declared.arg is None or required.arg is None:
        return False
    return _glob_covers(declared.arg, required.arg)


def _effect_allowed(required: EffectSpec, caller_effects: EffectSet) -> bool:
    return any(_covers(declared, required) for declared in caller_effects)


def _local_effect_table(ast: Dict[str, Any]) -> Dict[str, EffectSet]:
    table: Dict[str, EffectSet] = {}
    for decl in ast.get("decls", []):
        if decl.get("kind") == "FunctionDecl":
            table[decl["name"]] = _effect_specs(decl.get("effects", []))
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
        caller_effects = _effect_specs(fn.get("effects", []))
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
                                    _effect_name(effect) for effect in caller_effects
                                ],
                                "required_effect": _effect_name(required),
                            },
                        )
                    )
    return diags


def _format_effect_set(effects: EffectSet) -> str:
    if not effects:
        return "'pure'"
    return ", ".join(repr(_effect_name(effect)) for effect in effects)
