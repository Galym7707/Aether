"""Structural type diagnostics for the implemented Aether subset.

This pass is intentionally pragmatic rather than complete: it checks the type
relationships that the current parser, emitter, runtime, and standard helpers
actually support. It tracks generic ``List<T>`` element types, selected
``Map<K,V>``/``Option<T>``/``Result<T,E>`` flows, user generic functions, and
simple compile-time index bounds for list literals and append-built lists.
Unknown values remain unknown so prototype-only features keep running.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from ..diagnostics import Diagnostic, Position


@dataclass(frozen=True)
class AType:
    name: str
    args: Tuple["AType", ...] = ()

    def __str__(self) -> str:
        if not self.args:
            return self.name
        return f"{self.name}<" + ", ".join(str(arg) for arg in self.args) + ">"

    @property
    def unknown(self) -> bool:
        return self.name == "?"


@dataclass
class ValueInfo:
    ty: AType
    list_len: Optional[int] = None
    const_int: Optional[int] = None


UNKNOWN = AType("?")
UNIT = AType("Unit")
BOOL = AType("Bool")
INT = AType("Int")
FLOAT = AType("Float")
STRING = AType("String")


def check_types(ast: Dict[str, Any]) -> List[Diagnostic]:
    """Return static type diagnostics for the implemented language subset."""
    checker = _TypeChecker(ast)
    return checker.check()


class _TypeChecker:
    def __init__(self, ast: Dict[str, Any]):
        self.ast = ast
        self.diags: List[Diagnostic] = []
        self.aliases: Dict[str, AType] = {}
        self.refinements: Dict[str, AType] = {}
        self.functions: Dict[str, Dict[str, Any]] = {}
        self.records: Dict[str, Dict[str, AType]] = {}
        self.unions: Dict[str, List[str]] = {}
        self.union_cases: Dict[str, AType] = {}
        self.global_env: Dict[str, ValueInfo] = {}
        self._collect_symbols()

    def check(self) -> List[Diagnostic]:
        for decl in self.ast.get("decls", []):
            if decl.get("kind") == "ConstDecl":
                self._check_const(decl)

        for decl in self.ast.get("decls", []):
            if decl.get("kind") == "FunctionDecl":
                self._check_function(decl)
        return self.diags

    # ------------------------------------------------------------------
    # Symbol collection
    # ------------------------------------------------------------------

    def _collect_symbols(self) -> None:
        for decl in self.ast.get("decls", []):
            kind = decl.get("kind")
            if kind == "TypeDecl":
                base = self._type_from_ast(decl.get("base"))
                self.aliases[decl["name"]] = base
                if decl.get("refinement") is not None:
                    self.refinements[decl["name"]] = base
            elif kind == "RecordDecl":
                fields = {
                    field["name"]: self._type_from_ast(field.get("type"))
                    for field in decl.get("fields", [])
                }
                self.records[decl["name"]] = fields
                self.functions[decl["name"]] = {
                    "kind": "RecordConstructor",
                    "name": decl["name"],
                    "generics": [],
                    "params": decl.get("fields", []),
                    "return_type": {"kind": "TypeName", "name": decl["name"]},
                }
            elif kind == "UnionDecl":
                union_ty = AType(decl["name"])
                self.unions[decl["name"]] = [case["name"] for case in decl.get("cases", [])]
                for case in decl.get("cases", []):
                    self.union_cases[case["name"]] = union_ty
                    self.functions[case["name"]] = {
                        "kind": "UnionConstructor",
                        "name": case["name"],
                        "generics": [],
                        "params": case.get("params", []),
                        "return_type": {"kind": "TypeName", "name": decl["name"]},
                    }
            elif kind == "FunctionDecl":
                self.functions[decl["name"]] = decl

        # Built-in constructors are available even without explicit union decls.
        self.union_cases.setdefault("Some", AType("Option", (UNKNOWN,)))
        self.union_cases.setdefault("None", AType("Option", (UNKNOWN,)))
        self.union_cases.setdefault("Ok", AType("Result", (UNKNOWN, UNKNOWN)))
        self.union_cases.setdefault("Err", AType("Result", (UNKNOWN, UNKNOWN)))

    # ------------------------------------------------------------------
    # Declarations and statements
    # ------------------------------------------------------------------

    def _check_const(self, decl: Dict[str, Any]) -> None:
        expected = self._type_from_ast(decl.get("type"))
        actual = self._infer_expr(decl.get("value"), self.global_env, expected)
        self._diag_if_incompatible(
            "TYPE_BINDING_MISMATCH",
            expected,
            actual.ty,
            self._expr_pos(decl.get("value")) or self._pos(decl),
            f"constant {decl.get('name')!r}",
            "change the value or update the declared constant type",
        )
        self.global_env[decl["name"]] = ValueInfo(expected, actual.list_len, actual.const_int)

    def _check_function(self, decl: Dict[str, Any]) -> None:
        env = dict(self.global_env)
        generic_vars = set(decl.get("generics", []))
        for param in decl.get("params", []):
            env[param["name"]] = ValueInfo(self._type_from_ast(param.get("type"), generic_vars))
        expected_return = self._type_from_ast(decl.get("return_type"), generic_vars)
        for stmt in decl.get("body", []):
            self._check_stmt(stmt, env, expected_return, generic_vars)

    def _check_stmt(
        self,
        stmt: Dict[str, Any],
        env: Dict[str, ValueInfo],
        expected_return: AType,
        generic_vars: set[str],
    ) -> None:
        kind = stmt.get("kind")
        if kind in {"Let", "Var"}:
            declared = self._type_from_ast(stmt.get("type"), generic_vars)
            expected = None if declared.unknown else declared
            actual = self._infer_expr(stmt.get("value"), env, expected, generic_vars)
            if not declared.unknown:
                self._diag_if_incompatible(
                    "TYPE_BINDING_MISMATCH",
                    declared,
                    actual.ty,
                    self._expr_pos(stmt.get("value")) or self._pos(stmt),
                    f"binding {stmt.get('name')!r}",
                    "change the value or update the declared type",
                )
                env[stmt["name"]] = ValueInfo(declared, actual.list_len, actual.const_int)
            else:
                env[stmt["name"]] = actual
        elif kind == "Assign":
            actual = self._infer_expr(
                stmt.get("value"),
                env,
                env.get(stmt.get("target", ""), ValueInfo(UNKNOWN)).ty,
                generic_vars,
            )
            expected = env.get(stmt.get("target", ""), ValueInfo(UNKNOWN)).ty
            self._diag_if_incompatible(
                "TYPE_ASSIGNMENT_MISMATCH",
                expected,
                actual.ty,
                self._expr_pos(stmt.get("value")) or self._pos(stmt),
                f"assignment to {stmt.get('target')!r}",
                "assign a value with the variable's declared type",
            )
            if stmt.get("target") in env:
                env[stmt["target"]] = ValueInfo(expected, actual.list_len, actual.const_int)
        elif kind == "Return":
            if stmt.get("value") is None:
                actual = ValueInfo(UNIT)
            else:
                actual = self._infer_expr(stmt.get("value"), env, expected_return, generic_vars)
            self._diag_if_incompatible(
                "TYPE_RETURN_MISMATCH",
                expected_return,
                actual.ty,
                self._expr_pos(stmt.get("value")) or self._pos(stmt),
                "return value",
                "return a value matching the function's declared return type",
            )
        elif kind == "If":
            cond = self._infer_expr(stmt.get("cond"), env, BOOL, generic_vars)
            self._diag_if_incompatible(
                "TYPE_CONDITION_MISMATCH",
                BOOL,
                cond.ty,
                self._expr_pos(stmt.get("cond")) or self._pos(stmt),
                "if condition",
                "conditions must have type Bool",
            )
            for nested in stmt.get("then", []):
                self._check_stmt(nested, dict(env), expected_return, generic_vars)
            for branch in stmt.get("elifs", []):
                branch_cond = self._infer_expr(branch.get("cond"), env, BOOL, generic_vars)
                self._diag_if_incompatible(
                    "TYPE_CONDITION_MISMATCH",
                    BOOL,
                    branch_cond.ty,
                    self._expr_pos(branch.get("cond")) or self._pos(stmt),
                    "elif condition",
                    "conditions must have type Bool",
                )
                for nested in branch.get("body", []):
                    self._check_stmt(nested, dict(env), expected_return, generic_vars)
            if stmt.get("else") is not None:
                for nested in stmt.get("else", []):
                    self._check_stmt(nested, dict(env), expected_return, generic_vars)
        elif kind == "While":
            cond = self._infer_expr(stmt.get("cond"), env, BOOL, generic_vars)
            self._diag_if_incompatible(
                "TYPE_CONDITION_MISMATCH",
                BOOL,
                cond.ty,
                self._expr_pos(stmt.get("cond")) or self._pos(stmt),
                "while condition",
                "conditions must have type Bool",
            )
            nested_env = dict(env)
            for nested in stmt.get("body", []):
                self._check_stmt(nested, nested_env, expected_return, generic_vars)
        elif kind == "For":
            iter_info = self._infer_expr(stmt.get("iter"), env, None, generic_vars)
            nested_env = dict(env)
            nested_env[stmt.get("var", "")] = ValueInfo(self._list_elem_type(iter_info.ty))
            for nested in stmt.get("body", []):
                self._check_stmt(nested, nested_env, expected_return, generic_vars)
        elif kind == "Match":
            scrutinee = self._infer_expr(stmt.get("scrutinee"), env, None, generic_vars)
            self._check_match_exhaustiveness(stmt, scrutinee.ty)
            for arm in stmt.get("arms", []):
                for nested in arm.get("body", []):
                    self._check_stmt(nested, dict(env), expected_return, generic_vars)
        elif kind == "ExprStmt":
            self._infer_expr(stmt.get("expr"), env, None, generic_vars)

    # ------------------------------------------------------------------
    # Expression inference
    # ------------------------------------------------------------------

    def _infer_expr(
        self,
        expr: Optional[Dict[str, Any]],
        env: Dict[str, ValueInfo],
        expected: Optional[AType] = None,
        generic_vars: Optional[set[str]] = None,
    ) -> ValueInfo:
        generic_vars = generic_vars or set()
        if not expr:
            return ValueInfo(UNKNOWN)
        kind = expr.get("kind")
        if kind == "IntLit":
            return ValueInfo(INT, const_int=int(expr.get("value", 0)))
        if kind == "FloatLit":
            return ValueInfo(FLOAT)
        if kind == "StringLit":
            return ValueInfo(STRING)
        if kind == "BoolLit":
            return ValueInfo(BOOL)
        if kind == "NullLit":
            return ValueInfo(UNIT)
        if kind == "Ident":
            return env.get(expr.get("name"), ValueInfo(UNKNOWN))
        if kind == "ListLit":
            return self._infer_list_literal(expr, env, expected, generic_vars)
        if kind == "MapLit":
            return self._infer_map_literal(expr, env, expected, generic_vars)
        if kind == "Index":
            return self._infer_index(expr, env, generic_vars)
        if kind == "Field":
            value = self._infer_expr(expr.get("value"), env, None, generic_vars)
            record_fields = self.records.get(self._dealias(value.ty).name)
            if record_fields and expr.get("name") in record_fields:
                return ValueInfo(record_fields[expr["name"]])
            return ValueInfo(UNKNOWN)
        if kind == "UnaryOp":
            value = self._infer_expr(expr.get("value"), env, expected, generic_vars)
            if expr.get("op") == "neg" and value.const_int is not None:
                return ValueInfo(value.ty, const_int=-value.const_int)
            if expr.get("op") == "not":
                self._diag_if_incompatible(
                    "TYPE_UNARY_MISMATCH",
                    BOOL,
                    value.ty,
                    self._expr_pos(expr.get("value")) or self._pos(expr),
                    "not operand",
                    "`not` requires a Bool operand",
                )
                return ValueInfo(BOOL)
            return value
        if kind == "BinOp":
            return self._infer_binop(expr, env, generic_vars)
        if kind == "Call":
            return self._infer_call(expr, env, expected, generic_vars)
        if kind == "IfExpr":
            cond = self._infer_expr(expr.get("cond"), env, BOOL, generic_vars)
            self._diag_if_incompatible(
                "TYPE_CONDITION_MISMATCH",
                BOOL,
                cond.ty,
                self._expr_pos(expr.get("cond")) or self._pos(expr),
                "if expression condition",
                "conditions must have type Bool",
            )
            then_info = self._infer_expr(expr.get("then"), env, expected, generic_vars)
            else_info = self._infer_expr(expr.get("else"), env, expected, generic_vars)
            if self._compatible(then_info.ty, else_info.ty):
                return then_info
            self._type_diag(
                "TYPE_BRANCH_MISMATCH",
                then_info.ty,
                else_info.ty,
                self._expr_pos(expr.get("else")) or self._pos(expr),
                "if expression branches have different types",
                "make both branches return the same type",
                {"context": "if expression branches"},
            )
            return ValueInfo(UNKNOWN)
        if kind == "MatchExpr":
            scrutinee = self._infer_expr(expr.get("scrutinee"), env, None, generic_vars)
            self._check_match_exhaustiveness(expr, scrutinee.ty)
            arm_types: List[AType] = []
            for arm in expr.get("arms", []):
                arm_types.append(self._infer_expr(arm.get("value"), dict(env), expected, generic_vars).ty)
            if not arm_types:
                return ValueInfo(UNKNOWN)
            first = arm_types[0]
            return ValueInfo(first if all(self._compatible(first, ty) for ty in arm_types[1:]) else UNKNOWN)
        if kind == "Old":
            return self._infer_expr(expr.get("value"), env, expected, generic_vars)
        return ValueInfo(UNKNOWN)

    def _infer_list_literal(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        expected: Optional[AType],
        generic_vars: set[str],
    ) -> ValueInfo:
        elems = expr.get("elems", [])
        expected_elem = self._list_elem_type(expected) if expected is not None else UNKNOWN
        if not elems:
            if expected is None or not self._is_list_like(expected):
                self._simple_diag(
                    "TYPE_EMPTY_LIST_NEEDS_ANNOTATION",
                    "Cannot infer the element type of an empty list.",
                    self._pos(expr),
                    "write a type annotation such as `let xs: List<Int> = []`",
                    {"expected": "List<T>", "actual": "List<?>"},
                )
                return ValueInfo(AType("List", (UNKNOWN,)), list_len=0)
            return ValueInfo(self._list_type_with_elem(expected, expected_elem), list_len=0)

        if not expected_elem.unknown:
            for elem in elems:
                info = self._infer_expr(elem, env, expected_elem, generic_vars)
                if not self._compatible(expected_elem, info.ty):
                    self._type_diag(
                        "TYPE_LIST_ELEMENT_MISMATCH",
                        expected_elem,
                        info.ty,
                        self._pos(elem),
                        f"List element has type {info.ty} but expected {expected_elem}.",
                        f"Use only {expected_elem} values in {self._list_type_with_elem(expected, expected_elem)}, or change the list type.",
                        {"context": "list element"},
                    )
            return ValueInfo(self._list_type_with_elem(expected, expected_elem), list_len=len(elems))

        first = self._infer_expr(elems[0], env, None, generic_vars)
        elem_ty = first.ty
        for elem in elems[1:]:
            info = self._infer_expr(elem, env, elem_ty, generic_vars)
            if not self._compatible(elem_ty, info.ty):
                self._type_diag(
                    "TYPE_LIST_ELEMENT_MISMATCH",
                    elem_ty,
                    info.ty,
                    self._pos(elem),
                    f"List element has type {info.ty} but expected {elem_ty}.",
                    "Use one element type per list literal.",
                    {"context": "list element"},
                )
        return ValueInfo(AType("List", (elem_ty,)), list_len=len(elems))

    def _infer_map_literal(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        expected: Optional[AType],
        generic_vars: set[str],
    ) -> ValueInfo:
        entries = expr.get("entries", [])
        expected_map = self._dealias(expected) if expected is not None else UNKNOWN
        key_expected = expected_map.args[0] if expected_map.name == "Map" and len(expected_map.args) == 2 else UNKNOWN
        value_expected = expected_map.args[1] if expected_map.name == "Map" and len(expected_map.args) == 2 else UNKNOWN
        if not entries:
            if expected_map.name == "Map":
                return ValueInfo(expected_map)
            return ValueInfo(AType("Map", (UNKNOWN, UNKNOWN)))

        first_key = key_expected
        first_value = value_expected
        if first_key.unknown:
            first_key = self._infer_expr(entries[0]["key"], env, None, generic_vars).ty
        if first_value.unknown:
            first_value = self._infer_expr(entries[0]["value"], env, None, generic_vars).ty

        for entry in entries:
            key_info = self._infer_expr(entry["key"], env, first_key, generic_vars)
            value_info = self._infer_expr(entry["value"], env, first_value, generic_vars)
            self._diag_if_incompatible(
                "TYPE_MAP_KEY_MISMATCH",
                first_key,
                key_info.ty,
                self._pos(entry["key"]),
                "map key",
                "use a consistent key type in a map literal",
            )
            self._diag_if_incompatible(
                "TYPE_MAP_VALUE_MISMATCH",
                first_value,
                value_info.ty,
                self._pos(entry["value"]),
                "map value",
                "use a consistent value type in a map literal",
            )
        return ValueInfo(AType("Map", (first_key, first_value)))

    def _infer_index(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        generic_vars: set[str],
    ) -> ValueInfo:
        coll_info = self._infer_expr(expr.get("value"), env, None, generic_vars)
        index_info = self._infer_expr(expr.get("index"), env, INT, generic_vars)
        if not self._compatible(INT, index_info.ty):
            self._type_diag(
                "INDEX_TYPE_INVALID",
                INT,
                index_info.ty,
                self._pos(expr.get("index") or expr),
                "Index expression must have type Int.",
                "use an Int index expression",
                {"context": "index"},
            )
        if index_info.const_int is not None:
            actual_index = index_info.const_int
            if actual_index < 0:
                self._simple_diag(
                    "INDEX_NEGATIVE_UNSUPPORTED",
                    f"Aether does not support negative indexing; got index {actual_index}.",
                    self._pos(expr.get("index") or expr),
                    "check `index >= 0` before indexing",
                    {"actual_index": actual_index, "expected": "index >= 0", "actual": str(actual_index)},
                )
            elif coll_info.list_len is not None and actual_index >= coll_info.list_len:
                valid_range = "empty" if coll_info.list_len == 0 else f"0..{coll_info.list_len - 1}"
                self._simple_diag(
                    "INDEX_OUT_OF_BOUNDS_STATIC",
                    f"Index {actual_index} is out of bounds for a list of length {coll_info.list_len}.",
                    self._pos(expr.get("index") or expr),
                    "ensure the index is less than length(xs) before indexing",
                    {
                        "valid_range": valid_range,
                        "actual_index": actual_index,
                        "expected": valid_range,
                        "actual": str(actual_index),
                    },
                )
        return ValueInfo(self._index_result_type(coll_info.ty))

    def _infer_binop(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        generic_vars: set[str],
    ) -> ValueInfo:
        op = expr.get("op")
        expected_operand = BOOL if op in {"and", "or", "implies"} else None
        left = self._infer_expr(expr.get("left"), env, expected_operand, generic_vars)
        right = self._infer_expr(expr.get("right"), env, expected_operand, generic_vars)
        if op in {"==", "!=", "<", "<=", ">", ">=", "and", "or", "implies", "is", "in"}:
            return ValueInfo(BOOL)
        if op in {"+", "-", "*", "/", "%"}:
            if left.const_int is not None and right.const_int is not None:
                const = self._eval_int_binop(op, left.const_int, right.const_int)
            else:
                const = None
            if FLOAT in {self._dealias(left.ty), self._dealias(right.ty)}:
                return ValueInfo(FLOAT, const_int=const)
            if self._compatible(INT, left.ty) and self._compatible(INT, right.ty):
                return ValueInfo(INT, const_int=const)
        return ValueInfo(UNKNOWN)

    def _infer_call(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        expected: Optional[AType],
        generic_vars: set[str],
    ) -> ValueInfo:
        name = self._callee_name(expr.get("func") or {})
        args = expr.get("args", [])
        if name == "append":
            return self._infer_append(expr, env, generic_vars)
        if name == "prepend":
            return self._infer_prepend(expr, env, generic_vars)
        if name == "concat":
            return self._infer_concat(expr, env, generic_vars)
        if name in {"length", "size"}:
            self._infer_args(args, env, [UNKNOWN], generic_vars)
            return ValueInfo(INT)
        if name == "get":
            return self._infer_get(expr, env, generic_vars)
        if name in {"safeAt", "updateAt", "safeSlice", "inBounds", "validSliceBounds"} and name in self.functions:
            return self._infer_user_call(name, expr, env, generic_vars)
        if name == "safeAt":
            return self._infer_safe_at(expr, env, expected, generic_vars)
        if name == "updateAt":
            return self._infer_update_at(expr, env, expected, generic_vars)
        if name == "safeSlice":
            return self._infer_safe_slice(expr, env, expected, generic_vars)
        if name == "inBounds":
            return self._infer_in_bounds(expr, env, generic_vars)
        if name == "validSliceBounds":
            return self._infer_valid_slice_bounds(expr, env, generic_vars)
        if name == "set":
            return self._infer_set(expr, env, generic_vars)
        if name in {"isSome", "isSome?", "isNone", "isNone?"}:
            return self._infer_option_predicate(expr, env, generic_vars)
        if name in {"isOk", "isOk?", "isErr", "isErr?"}:
            return self._infer_result_predicate(expr, env, generic_vars)
        if name == "unwrapOr":
            return self._infer_unwrap_or(expr, env, expected, generic_vars)
        if name == "unwrapOrElse":
            return self._infer_unwrap_or_else(expr, env, expected, generic_vars)
        if name == "unwrapOrResult":
            return self._infer_unwrap_or_result(expr, env, expected, generic_vars)
        if name == "mapOption":
            return self._infer_map_option(expr, env, expected, generic_vars)
        if name == "andThenOption":
            return self._infer_and_then_option(expr, env, expected, generic_vars)
        if name == "expectSome":
            return self._infer_expect_some(expr, env, expected, generic_vars)
        if name == "mapResult":
            return self._infer_map_result(expr, env, expected, generic_vars)
        if name == "mapErr":
            return self._infer_map_err(expr, env, expected, generic_vars)
        if name == "andThenResult":
            return self._infer_and_then_result(expr, env, expected, generic_vars)
        if name == "expectOk":
            return self._infer_expect_ok(expr, env, expected, generic_vars)
        if name in {"Some", "None", "Ok", "Err"}:
            return self._infer_builtin_constructor(name, args, env, expected, generic_vars)
        if name in {"intToString"}:
            self._infer_args(args, env, [INT], generic_vars)
            return ValueInfo(STRING)
        if name in {"parseInt"}:
            self._infer_args(args, env, [STRING], generic_vars)
            return ValueInfo(AType("Result", (INT, STRING)))
        if name in {"parseFloat"}:
            self._infer_args(args, env, [STRING], generic_vars)
            return ValueInfo(AType("Result", (FLOAT, STRING)))
        if name == "print":
            self._infer_args(args, env, [UNKNOWN], generic_vars)
            return ValueInfo(UNIT)
        if name in {"empty?", "contains?", "startsWith?", "endsWith?", "has?"}:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(BOOL)
        if name in {"abs", "min", "max", "floor", "ceil"}:
            self._infer_args(args, env, [INT] * len(args), generic_vars)
            return ValueInfo(INT)
        if name in {"sqrt", "pow"}:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(FLOAT)
        if name in {"slice"}:
            self._infer_args(args, env, [STRING, INT, INT], generic_vars)
            return ValueInfo(STRING)
        if name in {"split"}:
            self._infer_args(args, env, [STRING, STRING], generic_vars)
            return ValueInfo(AType("List", (STRING,)))
        if name in {"join"}:
            self._infer_args(args, env, [AType("List", (STRING,)), STRING], generic_vars)
            return ValueInfo(STRING)
        if name in {"trim", "toLower", "toUpper"}:
            self._infer_args(args, env, [STRING], generic_vars)
            return ValueInfo(STRING)
        if name in {"replace"}:
            self._infer_args(args, env, [STRING, STRING, STRING], generic_vars)
            return ValueInfo(STRING)
        if name in {"range"}:
            self._infer_args(args, env, [INT, INT], generic_vars)
            return ValueInfo(AType("List", (INT,)))
        if name in {"head", "tail", "reverse"}:
            return self._infer_list_builtin(name, expr, env, generic_vars)
        if name in {"keys", "values"}:
            return self._infer_map_keys_values(name, expr, env, generic_vars)
        if name in self.functions:
            return self._infer_user_call(name, expr, env, generic_vars)

        self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
        return ValueInfo(UNKNOWN)

    # ------------------------------------------------------------------
    # Built-in calls
    # ------------------------------------------------------------------

    def _infer_args(
        self,
        args: Sequence[Dict[str, Any]],
        env: Dict[str, ValueInfo],
        expected: Sequence[AType],
        generic_vars: set[str],
    ) -> List[ValueInfo]:
        infos: List[ValueInfo] = []
        for i, arg in enumerate(args):
            exp = expected[i] if i < len(expected) else UNKNOWN
            exp_arg = None if exp.unknown else exp
            info = self._infer_expr(arg, env, exp_arg, generic_vars)
            if i < len(expected):
                self._diag_if_incompatible(
                    "TYPE_ARGUMENT_MISMATCH",
                    exp,
                    info.ty,
                    self._pos(arg),
                    f"argument {i + 1}",
                    "pass an argument with the expected type",
                )
            infos.append(info)
        return infos

    def _infer_append(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 2:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(AType("List", (UNKNOWN,)))
        first_arg = args[0]
        if first_arg.get("kind") == "ListLit" and not first_arg.get("elems"):
            value_info = self._infer_expr(args[1], env, None, generic_vars)
            list_expected = AType("List", (value_info.ty,)) if not value_info.ty.unknown else None
            list_info = self._infer_expr(first_arg, env, list_expected, generic_vars)
        else:
            list_info = self._infer_expr(first_arg, env, None, generic_vars)
            elem_hint = self._list_elem_type(list_info.ty)
            value_info = self._infer_expr(
                args[1],
                env,
                None if elem_hint.unknown else elem_hint,
                generic_vars,
            )
        elem_ty = self._list_elem_type(list_info.ty)
        if elem_ty.unknown and not value_info.ty.unknown:
            elem_ty = value_info.ty
        if not self._compatible(elem_ty, value_info.ty):
            self._type_diag(
                "TYPE_LIST_APPEND_MISMATCH",
                elem_ty,
                value_info.ty,
                self._pos(args[1]),
                f"append value has type {value_info.ty} but list elements are {elem_ty}.",
                "append a value with the list element type",
                {"context": "append value"},
            )
        length = list_info.list_len + 1 if list_info.list_len is not None else None
        return ValueInfo(AType("List", (elem_ty,)), list_len=length)

    def _infer_prepend(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 2:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(AType("List", (UNKNOWN,)))
        second_arg = args[1]
        if second_arg.get("kind") == "ListLit" and not second_arg.get("elems"):
            value_info = self._infer_expr(args[0], env, None, generic_vars)
            list_info = self._infer_expr(second_arg, env, AType("List", (value_info.ty,)), generic_vars)
        else:
            list_info = self._infer_expr(second_arg, env, None, generic_vars)
            elem_hint = self._list_elem_type(list_info.ty)
            value_info = self._infer_expr(
                args[0],
                env,
                None if elem_hint.unknown else elem_hint,
                generic_vars,
            )
        elem_ty = self._list_elem_type(list_info.ty)
        if elem_ty.unknown and not value_info.ty.unknown:
            elem_ty = value_info.ty
        self._diag_if_incompatible(
            "TYPE_LIST_APPEND_MISMATCH",
            elem_ty,
            value_info.ty,
            self._pos(args[0]),
            "prepend value",
            "prepend a value with the list element type",
        )
        length = list_info.list_len + 1 if list_info.list_len is not None else None
        return ValueInfo(AType("List", (elem_ty,)), list_len=length)

    def _infer_concat(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 2:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(AType("List", (UNKNOWN,)))
        left = self._infer_expr(args[0], env, None, generic_vars)
        elem_ty = self._list_elem_type(left.ty)
        right = self._infer_expr(args[1], env, AType("List", (elem_ty,)), generic_vars)
        right_elem = self._list_elem_type(right.ty)
        self._diag_if_incompatible(
            "TYPE_LIST_ELEMENT_MISMATCH",
            elem_ty,
            right_elem,
            self._pos(args[1]),
            "concat list element",
            "concat lists with the same element type",
        )
        length = None
        if left.list_len is not None and right.list_len is not None:
            length = left.list_len + right.list_len
        return ValueInfo(AType("List", (elem_ty if not elem_ty.unknown else right_elem,)), list_len=length)

    def _infer_get(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 2:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(AType("Option", (UNKNOWN,)))
        coll = self._infer_expr(args[0], env, None, generic_vars)
        coll_ty = self._dealias(coll.ty)
        if coll_ty.name == "Map" and len(coll_ty.args) == 2:
            key_ty, value_ty = coll_ty.args
            key = self._infer_expr(args[1], env, key_ty, generic_vars)
            self._diag_if_incompatible(
                "TYPE_ARGUMENT_MISMATCH",
                key_ty,
                key.ty,
                self._pos(args[1]),
                "map key",
                "use a key with the map key type",
            )
            return ValueInfo(AType("Option", (value_ty,)))
        if coll_ty.name == "List" and len(coll_ty.args) == 1:
            index = self._infer_expr(args[1], env, INT, generic_vars)
            self._diag_if_incompatible(
                "INDEX_TYPE_INVALID",
                INT,
                index.ty,
                self._pos(args[1]),
                "list index",
                "use an Int index expression",
            )
            return ValueInfo(AType("Option", (coll_ty.args[0],)))
        self._infer_expr(args[1], env, None, generic_vars)
        return ValueInfo(AType("Option", (UNKNOWN,)))

    def _infer_safe_at(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        expected: Optional[AType],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 2:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(AType("Option", (UNKNOWN,)))
        expected_norm = self._dealias(expected) if expected is not None else UNKNOWN
        expected_elem = expected_norm.args[0] if expected_norm.name == "Option" and expected_norm.args else UNKNOWN
        list_expected = None if expected_elem.unknown else AType("List", (expected_elem,))
        list_info = self._infer_expr(args[0], env, list_expected, generic_vars)
        elem_ty = self._list_elem_type(list_info.ty)
        if elem_ty.unknown and not expected_elem.unknown:
            elem_ty = expected_elem
        index = self._infer_expr(args[1], env, INT, generic_vars)
        self._list_helper_diag_if_incompatible(
            "LIST_HELPER_INDEX_TYPE",
            INT,
            index.ty,
            self._pos(args[1]),
            "safeAt index",
            "safeAt expects an Int index",
        )
        return ValueInfo(AType("Option", (elem_ty,)))

    def _infer_update_at(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        expected: Optional[AType],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 3:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(AType("Result", (AType("List", (UNKNOWN,)), STRING)))
        expected_list = self._expected_result_list(expected)
        first_arg = args[0]
        if first_arg.get("kind") == "ListLit" and not first_arg.get("elems"):
            value_hint = self._infer_expr(args[2], env, None, generic_vars).ty
            if expected_list is None and not value_hint.unknown:
                expected_list = AType("List", (value_hint,))
            list_info = self._infer_expr(first_arg, env, expected_list, generic_vars)
            value_info = self._infer_expr(args[2], env, self._list_elem_type(list_info.ty), generic_vars)
        else:
            list_info = self._infer_expr(first_arg, env, expected_list, generic_vars)
            elem_ty = self._list_elem_type(list_info.ty)
            value_info = self._infer_expr(
                args[2],
                env,
                None if elem_ty.unknown else elem_ty,
                generic_vars,
            )
        elem_ty = self._list_elem_type(list_info.ty)
        if elem_ty.unknown and not value_info.ty.unknown:
            elem_ty = value_info.ty
        index = self._infer_expr(args[1], env, INT, generic_vars)
        self._list_helper_diag_if_incompatible(
            "LIST_HELPER_INDEX_TYPE",
            INT,
            index.ty,
            self._pos(args[1]),
            "updateAt index",
            "updateAt expects an Int index",
        )
        self._list_helper_diag_if_incompatible(
            "LIST_HELPER_VALUE_TYPE",
            elem_ty,
            value_info.ty,
            self._pos(args[2]),
            "updateAt value",
            "updateAt replacement value must match the list element type",
        )
        return ValueInfo(AType("Result", (AType("List", (elem_ty,)), STRING)))

    def _infer_safe_slice(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        expected: Optional[AType],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 3:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(AType("Result", (AType("List", (UNKNOWN,)), STRING)))
        expected_list = self._expected_result_list(expected)
        list_info = self._infer_expr(args[0], env, expected_list, generic_vars)
        elem_ty = self._list_elem_type(list_info.ty)
        for idx, label in ((1, "start"), (2, "end")):
            bound = self._infer_expr(args[idx], env, INT, generic_vars)
            self._list_helper_diag_if_incompatible(
                "LIST_HELPER_BOUND_TYPE",
                INT,
                bound.ty,
                self._pos(args[idx]),
                f"safeSlice {label} bound",
                "safeSlice expects Int start and end bounds",
            )
        return ValueInfo(AType("Result", (AType("List", (elem_ty,)), STRING)))

    def _infer_in_bounds(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 2:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(BOOL)
        self._infer_expr(args[0], env, None, generic_vars)
        index = self._infer_expr(args[1], env, INT, generic_vars)
        self._list_helper_diag_if_incompatible(
            "LIST_HELPER_INDEX_TYPE",
            INT,
            index.ty,
            self._pos(args[1]),
            "inBounds index",
            "inBounds expects an Int index",
        )
        return ValueInfo(BOOL)

    def _infer_valid_slice_bounds(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 3:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(BOOL)
        self._infer_expr(args[0], env, None, generic_vars)
        for idx, label in ((1, "start"), (2, "end")):
            bound = self._infer_expr(args[idx], env, INT, generic_vars)
            self._list_helper_diag_if_incompatible(
                "LIST_HELPER_BOUND_TYPE",
                INT,
                bound.ty,
                self._pos(args[idx]),
                f"validSliceBounds {label} bound",
                "validSliceBounds expects Int start and end bounds",
            )
        return ValueInfo(BOOL)

    def _infer_set(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 3:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(AType("Map", (UNKNOWN, UNKNOWN)))
        coll = self._infer_expr(args[0], env, None, generic_vars)
        coll_ty = self._dealias(coll.ty)
        if coll_ty.name == "Map" and len(coll_ty.args) == 2:
            key_ty, value_ty = coll_ty.args
            key = self._infer_expr(args[1], env, key_ty, generic_vars)
            value = self._infer_expr(args[2], env, value_ty, generic_vars)
            self._diag_if_incompatible(
                "TYPE_ARGUMENT_MISMATCH",
                key_ty,
                key.ty,
                self._pos(args[1]),
                "map key",
                "use a key with the map key type",
            )
            self._diag_if_incompatible(
                "TYPE_ARGUMENT_MISMATCH",
                value_ty,
                value.ty,
                self._pos(args[2]),
                "map value",
                "use a value with the map value type",
            )
            return ValueInfo(coll_ty)
        self._infer_expr(args[1], env, None, generic_vars)
        self._infer_expr(args[2], env, None, generic_vars)
        return ValueInfo(coll_ty if coll_ty.name == "Map" else AType("Map", (UNKNOWN, UNKNOWN)))

    def _infer_unwrap_or_else(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        expected: Optional[AType],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 2:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(UNKNOWN)
        opt = self._infer_expr(args[0], env, None, generic_vars)
        opt_ty = self._dealias(opt.ty)
        value_ty = opt_ty.args[0] if opt_ty.name == "Option" and opt_ty.args else (expected or UNKNOWN)
        default = self._infer_expr(args[1], env, value_ty if not value_ty.unknown else expected, generic_vars)
        self._diag_if_incompatible(
            "TYPE_ARGUMENT_MISMATCH",
            value_ty,
            default.ty,
            self._pos(args[1]),
            "unwrapOrElse default",
            "default value must match the Option payload type",
        )
        return ValueInfo(value_ty if not value_ty.unknown else default.ty, default.list_len, default.const_int)

    def _infer_option_predicate(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 1:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(BOOL)
        opt = self._infer_expr(args[0], env, None, generic_vars)
        opt_ty = self._dealias(opt.ty)
        if not opt_ty.unknown and opt_ty.name != "Option":
            self._type_diag(
                "OPTION_HELPER_TYPE_MISMATCH",
                AType("Option", (UNKNOWN,)),
                opt.ty,
                self._pos(args[0]),
                f"Option helper expects Option<T>, got {opt.ty}",
                "pass an Option value such as Some(x) or None()",
                {"context": self._callee_name(expr.get("func") or {}) or "Option helper"},
            )
        return ValueInfo(BOOL)

    def _infer_result_predicate(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 1:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(BOOL)
        result = self._infer_expr(args[0], env, None, generic_vars)
        result_ty = self._dealias(result.ty)
        if not result_ty.unknown and result_ty.name != "Result":
            self._type_diag(
                "RESULT_HELPER_TYPE_MISMATCH",
                AType("Result", (UNKNOWN, UNKNOWN)),
                result.ty,
                self._pos(args[0]),
                f"Result helper expects Result<T, E>, got {result.ty}",
                "pass a Result value such as Ok(x) or Err(e)",
                {"context": self._callee_name(expr.get("func") or {}) or "Result helper"},
            )
        return ValueInfo(BOOL)

    def _infer_unwrap_or(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        expected: Optional[AType],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 2:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(expected or UNKNOWN)
        expected_opt = AType("Option", (expected,)) if expected is not None and not expected.unknown else None
        value = self._infer_expr(args[0], env, expected_opt, generic_vars)
        value_ty = self._dealias(value.ty)
        if value_ty.name == "Result" and len(value_ty.args) == 2:
            ok_ty = value_ty.args[0]
            default = self._infer_expr(args[1], env, ok_ty if not ok_ty.unknown else expected, generic_vars)
            if ok_ty.unknown:
                ok_ty = default.ty
            self._helper_diag_if_incompatible(
                "RESULT_HELPER_TYPE_MISMATCH",
                ok_ty,
                default.ty,
                self._pos(args[1]),
                "unwrapOr default",
                "default value must match the Result Ok type",
            )
            return ValueInfo(ok_ty if not ok_ty.unknown else default.ty, default.list_len, default.const_int)
        payload_ty = value_ty.args[0] if value_ty.name == "Option" and value_ty.args else (expected or UNKNOWN)
        default = self._infer_expr(args[1], env, payload_ty if not payload_ty.unknown else expected, generic_vars)
        if payload_ty.unknown:
            payload_ty = default.ty
        self._helper_diag_if_incompatible(
            "OPTION_HELPER_TYPE_MISMATCH",
            payload_ty,
            default.ty,
            self._pos(args[1]),
            "unwrapOr default",
            "default value must match the Option payload type",
        )
        return ValueInfo(payload_ty if not payload_ty.unknown else default.ty, default.list_len, default.const_int)

    def _infer_unwrap_or_result(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        expected: Optional[AType],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 2:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(expected or UNKNOWN)
        expected_result = AType("Result", (expected, UNKNOWN)) if expected is not None and not expected.unknown else None
        result = self._infer_expr(args[0], env, expected_result, generic_vars)
        result_ty = self._dealias(result.ty)
        ok_ty = result_ty.args[0] if result_ty.name == "Result" and len(result_ty.args) == 2 else (expected or UNKNOWN)
        default = self._infer_expr(args[1], env, ok_ty if not ok_ty.unknown else expected, generic_vars)
        if ok_ty.unknown:
            ok_ty = default.ty
        self._helper_diag_if_incompatible(
            "RESULT_HELPER_TYPE_MISMATCH",
            ok_ty,
            default.ty,
            self._pos(args[1]),
            "unwrapOrResult default",
            "default value must match the Result Ok type",
        )
        return ValueInfo(ok_ty if not ok_ty.unknown else default.ty, default.list_len, default.const_int)

    def _infer_expect_some(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        expected: Optional[AType],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 2:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(expected or UNKNOWN)
        expected_opt = AType("Option", (expected,)) if expected is not None and not expected.unknown else None
        opt = self._infer_expr(args[0], env, expected_opt, generic_vars)
        self._infer_expr(args[1], env, STRING, generic_vars)
        opt_ty = self._dealias(opt.ty)
        payload_ty = opt_ty.args[0] if opt_ty.name == "Option" and opt_ty.args else (expected or UNKNOWN)
        return ValueInfo(payload_ty)

    def _infer_expect_ok(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        expected: Optional[AType],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 2:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(expected or UNKNOWN)
        expected_result = AType("Result", (expected, UNKNOWN)) if expected is not None and not expected.unknown else None
        result = self._infer_expr(args[0], env, expected_result, generic_vars)
        self._infer_expr(args[1], env, STRING, generic_vars)
        result_ty = self._dealias(result.ty)
        ok_ty = result_ty.args[0] if result_ty.name == "Result" and len(result_ty.args) == 2 else (expected or UNKNOWN)
        return ValueInfo(ok_ty)

    def _infer_map_option(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        expected: Optional[AType],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 2:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(AType("Option", (UNKNOWN,)))
        expected_norm = self._dealias(expected) if expected is not None else UNKNOWN
        expected_payload = expected_norm.args[0] if expected_norm.name == "Option" and expected_norm.args else UNKNOWN
        opt = self._infer_expr(args[0], env, None, generic_vars)
        opt_ty = self._dealias(opt.ty)
        payload_ty = opt_ty.args[0] if opt_ty.name == "Option" and opt_ty.args else UNKNOWN
        fn_ty = self._function_type_from_expr(args[1], env, generic_vars)
        params, ret = self._function_parts(fn_ty)
        if params:
            if payload_ty.unknown:
                payload_ty = params[0]
            self._helper_diag_if_incompatible(
                "OPTION_HELPER_FUNCTION_TYPE",
                payload_ty,
                params[0],
                self._pos(args[1]),
                "mapOption mapper argument",
                "mapper must accept the Option payload type",
            )
        out_ty = ret if ret is not None else expected_payload
        return ValueInfo(AType("Option", (out_ty if out_ty is not None else UNKNOWN,)))

    def _infer_and_then_option(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        expected: Optional[AType],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 2:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(AType("Option", (UNKNOWN,)))
        opt = self._infer_expr(args[0], env, None, generic_vars)
        opt_ty = self._dealias(opt.ty)
        payload_ty = opt_ty.args[0] if opt_ty.name == "Option" and opt_ty.args else UNKNOWN
        fn_ty = self._function_type_from_expr(args[1], env, generic_vars)
        params, ret = self._function_parts(fn_ty)
        if params:
            if payload_ty.unknown:
                payload_ty = params[0]
            self._helper_diag_if_incompatible(
                "OPTION_HELPER_FUNCTION_TYPE",
                payload_ty,
                params[0],
                self._pos(args[1]),
                "andThenOption mapper argument",
                "mapper must accept the Option payload type",
            )
        ret_norm = self._dealias(ret) if ret is not None else UNKNOWN
        if not ret_norm.unknown and ret_norm.name != "Option":
            self._type_diag(
                "OPTION_HELPER_FUNCTION_TYPE",
                AType("Option", (UNKNOWN,)),
                ret_norm,
                self._pos(args[1]),
                f"andThenOption mapper must return Option<U>, got {ret_norm}",
                "return Some(value) or None() from the mapper",
                {"context": "andThenOption mapper return"},
            )
        out_ty = ret_norm.args[0] if ret_norm.name == "Option" and ret_norm.args else UNKNOWN
        return ValueInfo(AType("Option", (out_ty,)))

    def _infer_map_result(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        expected: Optional[AType],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 2:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(AType("Result", (UNKNOWN, UNKNOWN)))
        result = self._infer_expr(args[0], env, None, generic_vars)
        ok_ty, err_ty = self._result_type_args(result.ty)
        fn_ty = self._function_type_from_expr(args[1], env, generic_vars)
        params, ret = self._function_parts(fn_ty)
        if params:
            if ok_ty.unknown:
                ok_ty = params[0]
            self._helper_diag_if_incompatible(
                "RESULT_HELPER_FUNCTION_TYPE",
                ok_ty,
                params[0],
                self._pos(args[1]),
                "mapResult mapper argument",
                "mapper must accept the Result Ok type",
            )
        return ValueInfo(AType("Result", (ret if ret is not None else UNKNOWN, err_ty)))

    def _infer_map_err(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        expected: Optional[AType],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 2:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(AType("Result", (UNKNOWN, UNKNOWN)))
        result = self._infer_expr(args[0], env, None, generic_vars)
        ok_ty, err_ty = self._result_type_args(result.ty)
        fn_ty = self._function_type_from_expr(args[1], env, generic_vars)
        params, ret = self._function_parts(fn_ty)
        if params:
            if err_ty.unknown:
                err_ty = params[0]
            self._helper_diag_if_incompatible(
                "RESULT_HELPER_FUNCTION_TYPE",
                err_ty,
                params[0],
                self._pos(args[1]),
                "mapErr mapper argument",
                "mapper must accept the Result Err type",
            )
        return ValueInfo(AType("Result", (ok_ty, ret if ret is not None else UNKNOWN)))

    def _infer_and_then_result(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        expected: Optional[AType],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if len(args) != 2:
            self._infer_args(args, env, [UNKNOWN] * len(args), generic_vars)
            return ValueInfo(AType("Result", (UNKNOWN, UNKNOWN)))
        result = self._infer_expr(args[0], env, None, generic_vars)
        ok_ty, err_ty = self._result_type_args(result.ty)
        fn_ty = self._function_type_from_expr(args[1], env, generic_vars)
        params, ret = self._function_parts(fn_ty)
        if params:
            if ok_ty.unknown:
                ok_ty = params[0]
            self._helper_diag_if_incompatible(
                "RESULT_HELPER_FUNCTION_TYPE",
                ok_ty,
                params[0],
                self._pos(args[1]),
                "andThenResult mapper argument",
                "mapper must accept the Result Ok type",
            )
        ret_norm = self._dealias(ret) if ret is not None else UNKNOWN
        if not ret_norm.unknown and ret_norm.name != "Result":
            self._type_diag(
                "RESULT_HELPER_FUNCTION_TYPE",
                AType("Result", (UNKNOWN, err_ty)),
                ret_norm,
                self._pos(args[1]),
                f"andThenResult mapper must return Result<U, E>, got {ret_norm}",
                "return Ok(value) or Err(error) from the mapper",
                {"context": "andThenResult mapper return"},
            )
        if ret_norm.name == "Result" and len(ret_norm.args) == 2:
            self._helper_diag_if_incompatible(
                "RESULT_HELPER_FUNCTION_TYPE",
                err_ty,
                ret_norm.args[1],
                self._pos(args[1]),
                "andThenResult error type",
                "mapper Err type must match the input Result Err type",
            )
            return ValueInfo(ret_norm)
        return ValueInfo(AType("Result", (UNKNOWN, err_ty)))

    def _infer_builtin_constructor(
        self,
        name: str,
        args: Sequence[Dict[str, Any]],
        env: Dict[str, ValueInfo],
        expected: Optional[AType],
        generic_vars: set[str],
    ) -> ValueInfo:
        expected_norm = self._dealias(expected) if expected is not None else UNKNOWN
        if name == "Some":
            payload_expected = expected_norm.args[0] if expected_norm.name == "Option" and expected_norm.args else UNKNOWN
            payload = self._infer_expr(args[0], env, None if payload_expected.unknown else payload_expected, generic_vars) if args else ValueInfo(UNKNOWN)
            return ValueInfo(AType("Option", (payload.ty,)))
        if name == "None":
            payload = expected_norm.args[0] if expected_norm.name == "Option" and expected_norm.args else UNKNOWN
            return ValueInfo(AType("Option", (payload,)))
        if name == "Ok":
            ok_expected = expected_norm.args[0] if expected_norm.name == "Result" and len(expected_norm.args) == 2 else UNKNOWN
            err_expected = expected_norm.args[1] if expected_norm.name == "Result" and len(expected_norm.args) == 2 else UNKNOWN
            payload = self._infer_expr(args[0], env, None if ok_expected.unknown else ok_expected, generic_vars) if args else ValueInfo(UNKNOWN)
            return ValueInfo(AType("Result", (payload.ty, err_expected)))
        if name == "Err":
            ok_expected = expected_norm.args[0] if expected_norm.name == "Result" and len(expected_norm.args) == 2 else UNKNOWN
            err_expected = expected_norm.args[1] if expected_norm.name == "Result" and len(expected_norm.args) == 2 else UNKNOWN
            payload = self._infer_expr(args[0], env, None if err_expected.unknown else err_expected, generic_vars) if args else ValueInfo(UNKNOWN)
            return ValueInfo(AType("Result", (ok_expected, payload.ty)))
        return ValueInfo(UNKNOWN)

    def _infer_list_builtin(
        self,
        name: str,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        if not args:
            return ValueInfo(UNKNOWN)
        list_info = self._infer_expr(args[0], env, None, generic_vars)
        elem_ty = self._list_elem_type(list_info.ty)
        if name == "head":
            return ValueInfo(AType("Option", (elem_ty,)))
        if name == "tail":
            length = list_info.list_len - 1 if list_info.list_len and list_info.list_len > 0 else None
            return ValueInfo(AType("List", (elem_ty,)), list_len=length)
        if name == "reverse":
            return ValueInfo(AType("List", (elem_ty,)), list_len=list_info.list_len)
        return ValueInfo(UNKNOWN)

    def _infer_map_keys_values(
        self,
        name: str,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        generic_vars: set[str],
    ) -> ValueInfo:
        args = expr.get("args", [])
        info = self._infer_expr(args[0], env, None, generic_vars) if args else ValueInfo(UNKNOWN)
        ty = self._dealias(info.ty)
        if ty.name == "Map" and len(ty.args) == 2:
            return ValueInfo(AType("List", (ty.args[0] if name == "keys" else ty.args[1],)))
        return ValueInfo(AType("List", (UNKNOWN,)))

    def _infer_user_call(
        self,
        name: str,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        generic_vars: set[str],
    ) -> ValueInfo:
        fn = self.functions[name]
        fn_generics = set(fn.get("generics", []))
        subst: Dict[str, AType] = {}
        args = expr.get("args", [])
        params = fn.get("params", [])
        for idx, arg in enumerate(args):
            if idx >= len(params):
                self._infer_expr(arg, env, None, generic_vars)
                continue
            param_ty = self._type_from_ast(params[idx].get("type"), fn_generics)
            contextual = self._substitute(param_ty, subst)
            arg_expected = None if self._contains_unresolved_typevar(contextual, fn_generics) else contextual
            actual = self._infer_expr(arg, env, arg_expected, generic_vars)
            ok = self._unify(param_ty, actual.ty, subst, fn_generics)
            expected_ty = self._substitute(param_ty, subst)
            if not ok:
                self._type_diag(
                    "TYPE_ARGUMENT_MISMATCH",
                    expected_ty,
                    actual.ty,
                    self._pos(arg),
                    f"Argument {idx + 1} passed to {name} has type {actual.ty} but expected {expected_ty}.",
                    "pass an argument matching the function parameter type",
                    {"function": name, "argument": params[idx].get("name", str(idx + 1))},
                )
        ret = self._substitute(self._type_from_ast(fn.get("return_type"), fn_generics), subst)
        return ValueInfo(ret)

    # ------------------------------------------------------------------
    # Type helpers
    # ------------------------------------------------------------------

    def _type_from_ast(
        self,
        ty: Optional[Dict[str, Any]],
        generic_vars: Optional[set[str]] = None,
    ) -> AType:
        del generic_vars
        if not ty:
            return UNKNOWN
        kind = ty.get("kind")
        if kind == "TypeName":
            return AType(ty.get("name", "?"))
        if kind == "GenericType":
            return AType(
                ty.get("name", "?"),
                tuple(self._type_from_ast(arg) for arg in ty.get("args", [])),
            )
        if kind == "FunctionType":
            params = tuple(self._type_from_ast(arg) for arg in ty.get("params", []))
            ret = self._type_from_ast(ty.get("returns"))
            return AType("function", params + (ret,))
        return UNKNOWN

    def _compatible(self, expected: AType, actual: AType) -> bool:
        if expected.unknown or actual.unknown:
            return True
        exp = self._dealias(expected)
        act = self._dealias(actual)
        if exp.unknown or act.unknown:
            return True
        if exp.name != act.name:
            return False
        if len(exp.args) != len(act.args):
            return False
        return all(self._compatible(e, a) for e, a in zip(exp.args, act.args))

    def _unify(
        self,
        expected: AType,
        actual: AType,
        subst: Dict[str, AType],
        typevars: set[str],
    ) -> bool:
        if expected.name in typevars and not expected.args:
            if actual.unknown:
                return True
            if expected.name in subst:
                return self._compatible(subst[expected.name], actual)
            subst[expected.name] = actual
            return True
        if expected.unknown or actual.unknown:
            return True
        exp = self._dealias(expected)
        act = self._dealias(actual)
        if exp.name != act.name or len(exp.args) != len(act.args):
            return False
        return all(self._unify(e, a, subst, typevars) for e, a in zip(exp.args, act.args))

    def _substitute(self, ty: AType, subst: Mapping[str, AType]) -> AType:
        if ty.name in subst and not ty.args:
            return subst[ty.name]
        if not ty.args:
            return ty
        return AType(ty.name, tuple(self._substitute(arg, subst) for arg in ty.args))

    def _contains_unresolved_typevar(self, ty: AType, typevars: set[str]) -> bool:
        if ty.name in typevars and not ty.args:
            return True
        return any(self._contains_unresolved_typevar(arg, typevars) for arg in ty.args)

    def _dealias(self, ty: Optional[AType]) -> AType:
        if ty is None:
            return UNKNOWN
        if ty.name in self.aliases and not ty.args:
            return self._dealias(self.aliases[ty.name])
        if not ty.args:
            return ty
        return AType(ty.name, tuple(self._dealias(arg) for arg in ty.args))

    def _list_elem_type(self, ty: Optional[AType]) -> AType:
        ty = self._dealias(ty)
        if ty.name == "List" and len(ty.args) == 1:
            return ty.args[0]
        return UNKNOWN

    def _list_type_with_elem(self, expected: Optional[AType], elem: AType) -> AType:
        del expected
        return AType("List", (elem,))

    def _is_list_like(self, ty: Optional[AType]) -> bool:
        return self._dealias(ty).name == "List"

    def _index_result_type(self, ty: AType) -> AType:
        ty = self._dealias(ty)
        if ty.name == "List" and ty.args:
            return ty.args[0]
        if ty.name == "String":
            return STRING
        if ty.name in {"Tuple", "Result", "Option"} and ty.args:
            return UNKNOWN
        return UNKNOWN

    def _callee_name(self, callee: Dict[str, Any]) -> Optional[str]:
        if callee.get("kind") == "Ident":
            return callee.get("name")
        if callee.get("kind") == "Field":
            return callee.get("name")
        return None

    def _eval_int_binop(self, op: str, left: int, right: int) -> Optional[int]:
        try:
            if op == "+":
                return left + right
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if op == "/" and right != 0:
                return left // right
            if op == "%" and right != 0:
                return left % right
        except Exception:
            return None
        return None

    def _expected_result_list(self, expected: Optional[AType]) -> Optional[AType]:
        expected_norm = self._dealias(expected) if expected is not None else UNKNOWN
        if expected_norm.name != "Result" or len(expected_norm.args) != 2:
            return None
        ok_ty = self._dealias(expected_norm.args[0])
        if ok_ty.name == "List" and len(ok_ty.args) == 1:
            return ok_ty
        return None

    def _result_type_args(self, ty: AType) -> Tuple[AType, AType]:
        ty_norm = self._dealias(ty)
        if ty_norm.name == "Result" and len(ty_norm.args) == 2:
            return ty_norm.args[0], ty_norm.args[1]
        return UNKNOWN, UNKNOWN

    def _function_type_from_expr(
        self,
        expr: Dict[str, Any],
        env: Dict[str, ValueInfo],
        generic_vars: set[str],
    ) -> AType:
        if expr.get("kind") == "Ident":
            name = expr.get("name")
            if name in self.functions:
                fn = self.functions[name]
                fn_generics = set(fn.get("generics", []))
                params = tuple(
                    self._type_from_ast(param.get("type"), fn_generics)
                    for param in fn.get("params", [])
                )
                ret = self._type_from_ast(fn.get("return_type"), fn_generics)
                return AType("function", params + (ret,))
        return self._infer_expr(expr, env, None, generic_vars).ty

    def _function_parts(self, ty: AType) -> Tuple[Tuple[AType, ...], Optional[AType]]:
        ty_norm = self._dealias(ty)
        if ty_norm.name == "function" and ty_norm.args:
            return ty_norm.args[:-1], ty_norm.args[-1]
        return (), None

    def _check_match_exhaustiveness(self, node: Dict[str, Any], scrutinee_ty: AType) -> None:
        required = self._required_match_cases(scrutinee_ty)
        if not required:
            return
        covered = self._covered_match_cases(node.get("arms", []))
        if covered is None:
            return
        missing = [case for case in required if case not in covered]
        if not missing:
            return
        hint = "Add cases for: " + ", ".join(missing) + " or use `_`."
        self.diags.append(Diagnostic(
            code="MATCH_NON_EXHAUSTIVE",
            category="type",
            severity="error",
            message="match is not exhaustive; missing cases: " + ", ".join(missing),
            position=self._pos(node),
            suggestion=hint,
            confidence=0.95,
            extra={
                "missing_cases": missing,
                "expected": ", ".join(required),
                "actual": ", ".join(sorted(covered)),
            },
        ))

    def _required_match_cases(self, ty: AType) -> List[str]:
        ty_norm = self._dealias(ty)
        if ty_norm.name == "Option":
            return ["Some", "None"]
        if ty_norm.name == "Result":
            return ["Ok", "Err"]
        return list(self.unions.get(ty_norm.name, []))

    def _covered_match_cases(self, arms: Sequence[Dict[str, Any]]) -> Optional[set[str]]:
        covered: set[str] = set()
        for arm in arms:
            pat = arm.get("pattern") or {}
            if self._pattern_is_catch_all(pat):
                return None
            case = self._constructor_case_name(pat)
            if case is not None:
                covered.add(case)
        return covered

    def _pattern_is_catch_all(self, pat: Dict[str, Any]) -> bool:
        kind = pat.get("kind")
        if kind in {"WildcardPat", "BindPat"}:
            return True
        if kind == "AsPat":
            return self._pattern_is_catch_all(pat.get("pattern") or {})
        return False

    def _constructor_case_name(self, pat: Dict[str, Any]) -> Optional[str]:
        if pat.get("kind") == "ConstructorPat":
            path = pat.get("path") or []
            return path[-1] if path else None
        if pat.get("kind") == "AsPat":
            return self._constructor_case_name(pat.get("pattern") or {})
        return None

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def _diag_if_incompatible(
        self,
        code: str,
        expected: AType,
        actual: AType,
        pos: Position,
        context: str,
        hint: str,
    ) -> None:
        if self._compatible(expected, actual):
            return
        self._type_diag(
            code,
            expected,
            actual,
            pos,
            f"type mismatch for {context}: expected {expected}, got {actual}",
            hint,
            {"context": context},
        )

    def _list_helper_diag_if_incompatible(
        self,
        code: str,
        expected: AType,
        actual: AType,
        pos: Position,
        context: str,
        hint: str,
    ) -> None:
        if self._compatible(expected, actual):
            return
        self._type_diag(
            code,
            expected,
            actual,
            pos,
            f"type mismatch for {context}: expected {expected}, got {actual}",
            hint,
            {"context": context},
        )

    def _helper_diag_if_incompatible(
        self,
        code: str,
        expected: AType,
        actual: AType,
        pos: Position,
        context: str,
        hint: str,
    ) -> None:
        if self._compatible(expected, actual):
            return
        self._type_diag(
            code,
            expected,
            actual,
            pos,
            f"type mismatch for {context}: expected {expected}, got {actual}",
            hint,
            {"context": context},
        )

    def _type_diag(
        self,
        code: str,
        expected: AType,
        actual: AType,
        pos: Position,
        message: str,
        hint: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = {"expected": str(expected), "actual": str(actual)}
        if extra:
            payload.update(extra)
        self.diags.append(
            Diagnostic(
                code=code,
                category="type",
                severity="error",
                message=message,
                position=pos,
                suggestion=hint,
                confidence=0.95,
                extra=payload,
            )
        )

    def _simple_diag(
        self,
        code: str,
        message: str,
        pos: Position,
        hint: str,
        extra: Optional[Dict[str, Any]] = None,
        category: str = "type",
    ) -> None:
        self.diags.append(
            Diagnostic(
                code=code,
                category=category,
                severity="error",
                message=message,
                position=pos,
                suggestion=hint,
                confidence=0.95,
                extra=extra or {},
            )
        )

    def _pos(self, node: Optional[Dict[str, Any]]) -> Position:
        if not node:
            return Position(0, 0)
        raw = node.get("pos") or {"line": 0, "column": 0}
        return Position(int(raw.get("line", 0)), int(raw.get("column", 0)))

    def _expr_pos(self, expr: Optional[Dict[str, Any]]) -> Optional[Position]:
        if not expr:
            return None
        return self._pos(expr)
