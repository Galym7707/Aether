"""Static effect-subset checker.

This pass walks every FunctionDecl and checks direct calls to known local or
stdlib functions. For each call, the callee's declared effects must be covered
by the caller's declared effects. It also handles the implemented higher-order
Option/Result helpers when their callback argument resolves to a known function.
Unknown callees, function parameters, and dynamic field calls are intentionally
left to runtime behavior or future type analysis.
"""

from __future__ import annotations

import ast as py_ast
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
    "safeAt": _PURE,
    "updateAt": _PURE,
    "safeSlice": _PURE,
    "inBounds": _PURE,
    "validSliceBounds": _PURE,
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
    "random": (_spec(("random",)),),
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
    "isOk": _PURE,
    "isErr": _PURE,
    "unwrapOr": _PURE,
    "unwrapOrResult": _PURE,
    "isSome?": _PURE,
    "isNone?": _PURE,
    "isSome": _PURE,
    "isNone": _PURE,
    "unwrapOrElse": _PURE,
    "mapOption": _PURE,
    "andThenOption": _PURE,
    "expectSome": _PURE,
    "mapResult": _PURE,
    "mapErr": _PURE,
    "andThenResult": _PURE,
    "expectOk": _PURE,
}


_HIGHER_ORDER_CALLBACK_ARG: Dict[str, int] = {
    "mapOption": 1,
    "andThenOption": 1,
    "mapResult": 1,
    "mapErr": 1,
    "andThenResult": 1,
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
        return f"{name}({_quote_effect_arg(effect.arg)})"
    return name


def _quote_effect_arg(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _effect_from_source(source: str) -> EffectSpec:
    text = source.strip()
    if "(" not in text:
        path = tuple(part for part in text.split(".") if part)
        return EffectSpec(path)
    path_text, raw_arg = text.split("(", 1)
    path = tuple(part for part in path_text.split(".") if part)
    raw_arg = raw_arg.rsplit(")", 1)[0].strip()
    try:
        parsed = py_ast.literal_eval(raw_arg)
    except (SyntaxError, ValueError):
        parsed = None
    if isinstance(parsed, str):
        return EffectSpec(path, parsed, True)
    return EffectSpec(path, None, True)


def effect_sources(effects: Iterable[Dict[str, Any]]) -> Tuple[str, ...]:
    """Return canonical source-like effect names from parsed effect AST nodes."""
    return tuple(_effect_name(effect) for effect in _effect_specs(effects))


def effect_row_covers(declared: Iterable[str], required: Iterable[str]) -> bool:
    """Return True when every required effect is covered by the declaration row."""
    declared_specs = tuple(_effect_from_source(effect) for effect in declared)
    for required_effect in required:
        required_spec = _effect_from_source(required_effect)
        if not any(_covers(declared_spec, required_spec) for declared_spec in declared_specs):
            return False
    return True


def first_uncovered_effect(declared: Iterable[str], required: Iterable[str]) -> Optional[str]:
    declared_specs = tuple(_effect_from_source(effect) for effect in declared)
    for required_effect in required:
        required_spec = _effect_from_source(required_effect)
        if not any(_covers(declared_spec, required_spec) for declared_spec in declared_specs):
            return required_effect
    return None


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

    Effect rows are intentionally precise: `log`, `fs.read`, and `fs.write`
    cover only themselves. `net.fetch` is the one supported row with URL
    arguments; unargumented `net.fetch` covers all URL fetches, while
    argumented rows use exact or trailing-star glob coverage.
    """
    if declared.path != required.path:
        return False
    if not declared.has_arg:
        if required.has_arg:
            return declared.path == ("net", "fetch")
        return True
    if not required.has_arg:
        return False
    if declared.arg is None or required.arg is None:
        return False
    if declared.path != ("net", "fetch"):
        return declared.arg == required.arg
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


def _function_param_effect_table(fn: Dict[str, Any]) -> Dict[str, EffectSet]:
    table: Dict[str, EffectSet] = {}
    for param in fn.get("params", []):
        ty = param.get("type") or {}
        if ty.get("kind") == "FunctionType":
            table[param.get("name", "")] = _effect_specs(ty.get("effects", []))
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


def _pos(node: Dict[str, Any]) -> Position:
    raw = node.get("pos") or {"line": 0, "column": 0}
    return Position(raw.get("line", 0), raw.get("column", 0))


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
    """Return static effect diagnostics for direct and known callback calls."""
    local_effects = _local_effect_table(ast)
    known_effects = dict(_STDLIB_EFFECTS)
    known_effects.update(local_effects)

    diags: List[Diagnostic] = []
    for fn in ast.get("decls", []):
        if fn.get("kind") != "FunctionDecl":
            continue
        caller = fn["name"]
        caller_effects = _effect_specs(fn.get("effects", []))
        param_effects = _function_param_effect_table(fn)

        for root_expr in _function_expressions(fn):
            for expr in _walk_expr(root_expr):
                if expr.get("kind") != "Call":
                    continue
                callee = _resolve_callee_name(expr["func"])
                if callee is None:
                    continue
                if callee in known_effects:
                    required_effects = known_effects[callee]
                    for required in required_effects:
                        if _effect_allowed(required, caller_effects):
                            continue
                        required_name = _effect_name(required)
                        diags.append(
                            Diagnostic(
                                code="EFFECT_NOT_COVERED",
                                category="effect",
                                severity="error",
                                message=(
                                    f"function {caller!r} declares effects "
                                    f"{_format_effect_set(caller_effects)} but calls "
                                    f"{callee!r}, which requires effect "
                                    f"{required_name!r}"
                                ),
                                position=_pos(expr),
                                suggestion=(
                                    f"add `effects {required_name}` to the enclosing "
                                    "function, or call a function whose effects are "
                                    "covered by the current effect row"
                                ),
                                confidence=1.0,
                                extra={
                                    "caller": caller,
                                    "callee": callee,
                                    "caller_effects": [
                                        _effect_name(effect) for effect in caller_effects
                                    ],
                                    "required_effect": required_name,
                                    "legacy_code": "E0801",
                                },
                            )
                        )
                elif callee in param_effects:
                    for escaped in param_effects[callee]:
                        if _effect_allowed(escaped, caller_effects):
                            continue
                        escaped_name = _effect_name(escaped)
                        diags.append(
                            Diagnostic(
                                code="HIGHER_ORDER_EFFECT_ESCAPE",
                                category="effect",
                                severity="error",
                                message=(
                                    f"function-typed parameter {callee!r} requires "
                                    f"effect {escaped_name!r}, but enclosing function "
                                    f"{caller!r} declares effects "
                                    f"{_format_effect_set(caller_effects)}"
                                ),
                                position=_pos(expr),
                                suggestion=(
                                    f"add `effects {escaped_name}` to the enclosing "
                                    "function, or call a function whose effects are "
                                    "covered by the current effect row"
                                ),
                                confidence=1.0,
                                extra={
                                    "caller": caller,
                                    "helper": callee,
                                    "callback": callee,
                                    "escaped_effect": escaped_name,
                                    "caller_effects": [
                                        _effect_name(effect) for effect in caller_effects
                                    ],
                                    "expected_function_type_effects": [
                                        _effect_name(effect) for effect in param_effects[callee]
                                    ],
                                },
                            )
                        )
                    continue
                else:
                    continue
                callback_index = _HIGHER_ORDER_CALLBACK_ARG.get(callee)
                if callback_index is None:
                    continue
                args = expr.get("args", [])
                if callback_index >= len(args):
                    continue
                callback_name = _resolve_callee_name(args[callback_index])
                if callback_name is None or callback_name not in known_effects:
                    continue
                for escaped in known_effects[callback_name]:
                    if _effect_allowed(escaped, caller_effects):
                        continue
                    escaped_name = _effect_name(escaped)
                    diags.append(
                        Diagnostic(
                            code="HIGHER_ORDER_EFFECT_ESCAPE",
                            category="effect",
                            severity="error",
                            message=(
                                f"callback {callback_name!r} passed to {callee!r} "
                                f"requires effect {escaped_name!r}, but enclosing "
                                f"function {caller!r} declares effects "
                                f"{_format_effect_set(caller_effects)}"
                            ),
                            position=_pos(expr),
                            suggestion=(
                                f"add `effects {escaped_name}` to the enclosing "
                                "function, or call a function whose effects are "
                                "covered by the current effect row"
                            ),
                            confidence=1.0,
                            extra={
                                "caller": caller,
                                "helper": callee,
                                "callback": callback_name,
                                "escaped_effect": escaped_name,
                                "caller_effects": [
                                    _effect_name(effect) for effect in caller_effects
                                ],
                                "actual_callback_effects": [
                                    _effect_name(effect) for effect in known_effects[callback_name]
                                ],
                            },
                        )
                    )
    return diags


def _format_effect_set(effects: EffectSet) -> str:
    if not effects:
        return "'pure'"
    return ", ".join(repr(_effect_name(effect)) for effect in effects)
