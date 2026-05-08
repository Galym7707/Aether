"""Scoped SMT contract checker.

This pass intentionally implements only a small arithmetic fragment:
requires/ensures clauses made from Int/Float arithmetic, comparisons, and
boolean connectives. Clauses with function calls, strings, collections,
conditionals, field/index access, or other unsupported syntax are left to the
existing runtime contract checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..diagnostics import Diagnostic, Position
from ..printer import strip_positions


class _UnsupportedSMT(Exception):
    pass


@dataclass
class _SmtValue:
    expr: Any
    ty: str


@dataclass
class _ReturnContext:
    env: Dict[str, _SmtValue]
    position: Position


def _load_z3():
    try:
        import z3  # type: ignore
    except ImportError:
        return None
    return z3


def check_smt_contracts(ast: Dict[str, Any]) -> List[Diagnostic]:
    """Return E0901/E0902 diagnostics for the supported arithmetic fragment.

    E0901 is an error for a statically unsatisfiable contract clause. E0902 is
    informational for a statically valid clause; it is surfaced by direct pass
    callers and kept non-fatal by the CLI/harness integration.
    """
    z3 = _load_z3()
    if z3 is None:
        return []

    aliases = _numeric_type_aliases(ast)
    diags: List[Diagnostic] = []

    for fn in ast.get("decls", []):
        if fn.get("kind") != "FunctionDecl":
            continue
        fn_name = fn["name"]
        fn_pos = _pos(fn)
        param_env = _param_env(fn, aliases, z3)

        for clause in fn.get("requires", []):
            status = _classify_clause(clause, param_env, z3)
            if status:
                diags.append(
                    _diag(status, "requires", fn_name, clause, fn_pos)
                )

        returns = _return_contexts(fn.get("body", []), param_env, aliases, z3)
        for clause in fn.get("ensures", []):
            clause_statuses: List[Tuple[str, Position]] = []
            for ret in returns:
                status = _classify_clause(clause, ret.env, z3)
                if status:
                    clause_statuses.append((status, ret.position))
            for idx, (status, pos) in enumerate(clause_statuses):
                if status == "disproved":
                    diags.append(
                        _diag(
                            status,
                            "ensures",
                            fn_name,
                            clause,
                            pos,
                            {"return_index": idx},
                        )
                    )
            if (
                clause_statuses
                and all(status == "proved" for status, _ in clause_statuses)
                and len(clause_statuses) == len(returns)
            ):
                diags.append(_diag("proved", "ensures", fn_name, clause, fn_pos))

    return diags


def _numeric_type_aliases(ast: Dict[str, Any]) -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    for decl in ast.get("decls", []):
        if decl.get("kind") != "TypeDecl":
            continue
        base = decl.get("base") or {}
        if base.get("kind") == "TypeName" and base.get("name") in {"Int", "Float"}:
            aliases[decl["name"]] = base["name"]
    return aliases


def _resolve_type(ty: Optional[Dict[str, Any]], aliases: Dict[str, str]) -> Optional[str]:
    if not ty or ty.get("kind") != "TypeName":
        return None
    name = ty.get("name")
    if name in {"Int", "Float"}:
        return name
    return aliases.get(name)


def _param_env(fn: Dict[str, Any], aliases: Dict[str, str], z3) -> Dict[str, _SmtValue]:
    env: Dict[str, _SmtValue] = {}
    for param in fn.get("params", []):
        ty = _resolve_type(param.get("type"), aliases)
        if ty == "Int":
            env[param["name"]] = _SmtValue(z3.Int(param["name"]), "Int")
        elif ty == "Float":
            env[param["name"]] = _SmtValue(z3.Real(param["name"]), "Float")
    return env


def _return_contexts(
    stmts: List[Dict[str, Any]],
    env: Dict[str, _SmtValue],
    aliases: Dict[str, str],
    z3,
) -> List[_ReturnContext]:
    out: List[_ReturnContext] = []
    current = dict(env)
    for stmt in stmts:
        kind = stmt.get("kind")
        if kind == "Let":
            _bind_let(stmt, current, aliases, z3)
        elif kind in {"Var", "Assign"}:
            current.pop(stmt.get("name") or stmt.get("target"), None)
        elif kind == "Return":
            ret_env = dict(current)
            value = stmt.get("value")
            if value is not None:
                try:
                    ret_env["result"] = _numeric_expr(value, current, z3)
                except _UnsupportedSMT:
                    pass
            out.append(_ReturnContext(ret_env, _pos(stmt)))
        elif kind == "If":
            out.extend(_return_contexts(stmt.get("then", []), dict(current), aliases, z3))
            for branch in stmt.get("elifs", []):
                out.extend(
                    _return_contexts(branch.get("body", []), dict(current), aliases, z3)
                )
            if stmt.get("else") is not None:
                out.extend(
                    _return_contexts(stmt.get("else", []), dict(current), aliases, z3)
                )
        elif kind in {"While", "For"}:
            out.extend(_return_contexts(stmt.get("body", []), dict(current), aliases, z3))
        elif kind == "Match":
            for arm in stmt.get("arms", []):
                out.extend(
                    _return_contexts(arm.get("body", []), dict(current), aliases, z3)
                )
    return out


def _bind_let(
    stmt: Dict[str, Any],
    env: Dict[str, _SmtValue],
    aliases: Dict[str, str],
    z3,
) -> None:
    name = stmt["name"]
    declared = _resolve_type(stmt.get("type"), aliases)
    try:
        value = _numeric_expr(stmt["value"], env, z3)
    except _UnsupportedSMT:
        env.pop(name, None)
        return
    if declared is not None and declared != value.ty:
        if declared == "Float" and value.ty == "Int":
            value = _SmtValue(z3.ToReal(value.expr), "Float")
        else:
            env.pop(name, None)
            return
    env[name] = value


def _classify_clause(
    clause: Dict[str, Any],
    env: Dict[str, _SmtValue],
    z3,
) -> Optional[str]:
    try:
        formula = _bool_expr(clause, env, z3)
    except _UnsupportedSMT:
        return None

    s = z3.Solver()
    s.add(formula)
    sat_result = s.check()
    if sat_result == z3.unsat:
        return "disproved"
    if sat_result == z3.unknown:
        return None

    s = z3.Solver()
    s.add(z3.Not(formula))
    neg_result = s.check()
    if neg_result == z3.unsat:
        return "proved"
    return None


def _bool_expr(e: Dict[str, Any], env: Dict[str, _SmtValue], z3):
    kind = e.get("kind")
    if kind == "BoolLit":
        return z3.BoolVal(e["value"])
    if kind == "UnaryOp" and e.get("op") == "not":
        return z3.Not(_bool_expr(e["value"], env, z3))
    if kind == "BinOp":
        op = e["op"]
        if op == "and":
            return z3.And(_bool_expr(e["left"], env, z3), _bool_expr(e["right"], env, z3))
        if op == "or":
            return z3.Or(_bool_expr(e["left"], env, z3), _bool_expr(e["right"], env, z3))
        if op == "implies":
            return z3.Implies(
                _bool_expr(e["left"], env, z3),
                _bool_expr(e["right"], env, z3),
            )
        if op in {"==", "!=", "<", "<=", ">", ">="}:
            left = _numeric_expr(e["left"], env, z3)
            right = _numeric_expr(e["right"], env, z3)
            left, right = _coerce_pair(left, right, z3)
            if op == "==":
                return left.expr == right.expr
            if op == "!=":
                return left.expr != right.expr
            if op == "<":
                return left.expr < right.expr
            if op == "<=":
                return left.expr <= right.expr
            if op == ">":
                return left.expr > right.expr
            if op == ">=":
                return left.expr >= right.expr
    raise _UnsupportedSMT()


def _numeric_expr(e: Dict[str, Any], env: Dict[str, _SmtValue], z3) -> _SmtValue:
    kind = e.get("kind")
    if kind == "IntLit":
        return _SmtValue(z3.IntVal(e["value"]), "Int")
    if kind == "FloatLit":
        return _SmtValue(z3.RealVal(str(e["value"])), "Float")
    if kind == "Ident":
        name = e["name"]
        if name not in env:
            raise _UnsupportedSMT()
        return env[name]
    if kind == "UnaryOp" and e.get("op") == "neg":
        value = _numeric_expr(e["value"], env, z3)
        return _SmtValue(-value.expr, value.ty)
    if kind == "Old":
        return _numeric_expr(e["value"], env, z3)
    if kind == "BinOp":
        op = e["op"]
        if op not in {"+", "-", "*", "/", "%"}:
            raise _UnsupportedSMT()
        left = _numeric_expr(e["left"], env, z3)
        right = _numeric_expr(e["right"], env, z3)
        left, right = _coerce_pair(left, right, z3)
        if op == "+":
            return _SmtValue(left.expr + right.expr, left.ty)
        if op == "-":
            return _SmtValue(left.expr - right.expr, left.ty)
        if op == "*":
            return _SmtValue(left.expr * right.expr, left.ty)
        if op == "/":
            return _SmtValue(left.expr / right.expr, left.ty)
        if op == "%" and left.ty == "Int" and right.ty == "Int":
            return _SmtValue(left.expr % right.expr, "Int")
    raise _UnsupportedSMT()


def _coerce_pair(left: _SmtValue, right: _SmtValue, z3) -> Tuple[_SmtValue, _SmtValue]:
    if left.ty == right.ty:
        return left, right
    if left.ty == "Int" and right.ty == "Float":
        return _SmtValue(z3.ToReal(left.expr), "Float"), right
    if left.ty == "Float" and right.ty == "Int":
        return left, _SmtValue(z3.ToReal(right.expr), "Float")
    raise _UnsupportedSMT()


def _diag(
    status: str,
    clause_kind: str,
    fn_name: str,
    clause: Dict[str, Any],
    pos: Position,
    extra: Optional[Dict[str, Any]] = None,
) -> Diagnostic:
    code = "E0901" if status == "disproved" else "E0902"
    severity = "error" if status == "disproved" else "info"
    action = "disproved" if status == "disproved" else "proved"
    suggestion = (
        "fix the contract or implementation; this clause is impossible in "
        "the supported arithmetic SMT fragment"
        if status == "disproved"
        else "v0.4 may elide this runtime contract check"
    )
    data = {
        "function": fn_name,
        "clause_kind": clause_kind,
        "clause": strip_positions(clause),
        "smt_fragment": "arithmetic-int-float",
    }
    if extra:
        data.update(extra)
    return Diagnostic(
        code=code,
        category="contract",
        severity=severity,
        message=f"SMT {action} {clause_kind} clause in {fn_name}",
        position=pos,
        suggestion=suggestion,
        confidence=1.0,
        extra=data,
    )


def _pos(node: Dict[str, Any]) -> Position:
    raw = node.get("pos") or {"line": 0, "column": 0}
    return Position(raw.get("line", 0), raw.get("column", 0))
