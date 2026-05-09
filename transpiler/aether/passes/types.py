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
            self._infer_expr(stmt.get("scrutinee"), env, None, generic_vars)
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
            self._infer_expr(expr.get("scrutinee"), env, None, generic_vars)
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
        if name == "set":
            return self._infer_set(expr, env, generic_vars)
        if name == "unwrapOrElse":
            return self._infer_unwrap_or_else(expr, env, expected, generic_vars)
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
        if name in {"empty?", "contains?", "startsWith?", "endsWith?", "isOk?", "isErr?", "isSome?", "isNone?", "has?"}:
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
