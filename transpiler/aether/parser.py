"""Aether parser. Hand-written recursive descent + Pratt loop for expressions.

Produces a canonical AST as nested Python dicts. The dict shape is documented
in transpiler/aether/ast_schema.json.

The parser tries to recover at statement boundaries when a syntax error is hit;
v0.1 just stops on first error to keep behavior predictable.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any, Callable

from .lexer import Token, tokenize
from .diagnostics import AetherError, Diagnostic, Position


def parse(source: str, filename: str = "<input>") -> Dict[str, Any]:
    tokens = tokenize(source, filename)
    p = Parser(tokens)
    return p.parse_program()


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.i = 0

    # --- token helpers --------------------------------------------------

    def peek(self, offset: int = 0) -> Token:
        j = self.i + offset
        if j >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[j]

    def at_kw(self, *keywords: str, offset: int = 0) -> bool:
        t = self.peek(offset)
        return t.kind == "kw" and t.value in keywords

    def at_sym(self, *symbols: str, offset: int = 0) -> bool:
        t = self.peek(offset)
        return t.kind == "sym" and t.value in symbols

    def advance(self) -> Token:
        t = self.tokens[self.i]
        self.i += 1
        return t

    def expect_kw(self, kw: str) -> Token:
        t = self.peek()
        if t.kind != "kw" or t.value != kw:
            raise self.err(f"expected keyword '{kw}', got {self._show(t)}", t.pos,
                           suggestion=f"insert '{kw}' here")
        return self.advance()

    def expect_sym(self, sym: str) -> Token:
        t = self.peek()
        if t.kind != "sym" or t.value != sym:
            raise self.err(f"expected '{sym}', got {self._show(t)}", t.pos,
                           suggestion=f"insert '{sym}' here")
        return self.advance()

    def expect_ident(self) -> Token:
        t = self.peek()
        if t.kind != "ident":
            raise self.err(f"expected identifier, got {self._show(t)}", t.pos)
        return self.advance()

    def _show(self, t: Token) -> str:
        if t.kind == "eof":
            return "<eof>"
        return f"{t.kind}({t.value!r})"

    def err(self, msg: str, pos: Position, suggestion: Optional[str] = None) -> AetherError:
        return AetherError(Diagnostic(
            code="E0201", category="parse", severity="error",
            message=msg, position=pos, suggestion=suggestion, confidence=0.8,
        ))

    def with_pos(self, node: Dict[str, Any], pos: Position) -> Dict[str, Any]:
        node.setdefault("pos", pos.to_dict())
        return node

    def expr_pos(self, expr: Dict[str, Any]) -> Position:
        raw = expr.get("pos") or {"line": 0, "column": 0}
        return Position(raw.get("line", 0), raw.get("column", 0))

    # --- program --------------------------------------------------------

    def parse_program(self) -> Dict[str, Any]:
        decls = []
        while self.peek().kind != "eof":
            decls.append(self.parse_top_decl())
        return {"kind": "Program", "decls": decls}

    def parse_top_decl(self) -> Dict[str, Any]:
        t = self.peek()
        if t.kind == "kw":
            if t.value == "function":
                return self.parse_function_decl()
            if t.value == "type":
                return self.parse_type_decl()
            if t.value == "record":
                return self.parse_record_decl()
            if t.value == "union":
                return self.parse_union_decl()
            if t.value == "const":
                return self.parse_const_decl()
            if t.value == "module":
                return self.parse_module_decl()
            if t.value == "import":
                return self.parse_import_decl()
        raise self.err(f"expected top-level declaration, got {self._show(t)}", t.pos,
                       suggestion="top-level must start with one of: module, import, function, type, record, union, const")

    # --- module / import -----------------------------------------------

    def parse_module_decl(self) -> Dict[str, Any]:
        kw = self.expect_kw("module")
        name = self.expect_ident().value
        capabilities = []
        exports = []
        while not self.at_kw("end"):
            if self.at_kw("requires"):
                self.advance()
                self.expect_kw("capability")
                cap = self.expect_ident().value
                capabilities.append(cap)
            elif self.at_kw("exports"):
                self.advance()
                exports.append(self.expect_ident().value)
                while self.at_sym(","):
                    self.advance()
                    exports.append(self.expect_ident().value)
            else:
                t = self.peek()
                raise self.err(f"unexpected token in module body: {self._show(t)}", t.pos)
        self.expect_kw("end")
        return {"kind": "ModuleDecl", "name": name,
                "capabilities": capabilities, "exports": exports,
                "pos": kw.pos.to_dict()}

    def parse_import_decl(self) -> Dict[str, Any]:
        kw = self.expect_kw("import")
        path = [self.expect_ident().value]
        while self.at_sym("."):
            self.advance()
            path.append(self.expect_ident().value)
        alias = None
        if self.at_kw("as"):
            self.advance()
            alias = self.expect_ident().value
        return {"kind": "ImportDecl", "path": path, "alias": alias,
                "pos": kw.pos.to_dict()}

    # --- type / record / union / const ----------------------------------

    def parse_type_decl(self) -> Dict[str, Any]:
        kw = self.expect_kw("type")
        name = self.expect_ident().value
        self.expect_sym("=")
        base = self.parse_type_expr()
        refinement = None
        if self.at_kw("where"):
            self.advance()
            refinement = self.parse_expr()
        return {"kind": "TypeDecl", "name": name, "base": base,
                "refinement": refinement, "pos": kw.pos.to_dict()}

    def parse_record_decl(self) -> Dict[str, Any]:
        kw = self.expect_kw("record")
        name = self.expect_ident().value
        self.expect_kw("do")
        fields = []
        while not self.at_kw("end"):
            fname = self.expect_ident().value
            self.expect_sym(":")
            ftype = self.parse_type_expr()
            fields.append({"name": fname, "type": ftype})
        self.expect_kw("end")
        return {"kind": "RecordDecl", "name": name, "fields": fields,
                "pos": kw.pos.to_dict()}

    def parse_union_decl(self) -> Dict[str, Any]:
        kw = self.expect_kw("union")
        name = self.expect_ident().value
        self.expect_kw("do")
        cases = []
        while self.at_kw("case"):
            self.advance()
            cname = self.expect_ident().value
            cparams = []
            if self.at_sym("("):
                self.advance()
                if not self.at_sym(")"):
                    cparams.append(self._parse_param())
                    while self.at_sym(","):
                        self.advance()
                        cparams.append(self._parse_param())
                self.expect_sym(")")
            cases.append({"name": cname, "params": cparams})
        self.expect_kw("end")
        return {"kind": "UnionDecl", "name": name, "cases": cases,
                "pos": kw.pos.to_dict()}

    def parse_const_decl(self) -> Dict[str, Any]:
        kw = self.expect_kw("const")
        name = self.expect_ident().value
        self.expect_sym(":")
        ty = self.parse_type_expr()
        self.expect_sym("=")
        value = self.parse_expr()
        return {"kind": "ConstDecl", "name": name, "type": ty, "value": value,
                "pos": kw.pos.to_dict()}

    # --- function ------------------------------------------------------

    def parse_function_decl(self) -> Dict[str, Any]:
        kw = self.expect_kw("function")
        name = self.expect_ident().value
        generics: List[str] = []
        # generic params: "<" IDENT { "," IDENT } ">" — only in this position
        if self.at_sym("<"):
            self.advance()
            generics.append(self.expect_ident().value)
            while self.at_sym(","):
                self.advance()
                generics.append(self.expect_ident().value)
            self.expect_sym(">")
        self.expect_sym("(")
        params: List[Dict[str, Any]] = []
        if not self.at_sym(")"):
            params.append(self._parse_param())
            while self.at_sym(","):
                self.advance()
                params.append(self._parse_param())
        self.expect_sym(")")
        self.expect_kw("returns")
        ret_type = self.parse_type_expr(stop_before_decl_effect=True)
        requires_clauses: List[Dict[str, Any]] = []
        ensures_clauses: List[Dict[str, Any]] = []
        effects: List[Dict[str, Any]] = []
        # Contract clauses + effects can interleave
        while self.at_kw("requires") or self.at_kw("ensures") or self.at_kw("effects"):
            if self.at_kw("requires"):
                self.advance()
                requires_clauses.append(self.parse_expr())
            elif self.at_kw("ensures"):
                self.advance()
                ensures_clauses.append(self.parse_expr())
            elif self.at_kw("effects"):
                self.advance()
                effects = self.parse_effect_list()
        if not effects:
            raise self.err(
                f"function {name!r} must declare 'effects' (use 'effects pure' for no effects)",
                kw.pos, suggestion="add 'effects pure' before 'do'",
            )
        self.expect_kw("do")
        body = self.parse_block(end_kws=("end",))
        self.expect_kw("end")
        return {
            "kind": "FunctionDecl",
            "name": name,
            "generics": generics,
            "params": params,
            "return_type": ret_type,
            "requires": requires_clauses,
            "ensures": ensures_clauses,
            "effects": effects,
            "body": body,
            "pos": kw.pos.to_dict(),
        }

    def _parse_param(self) -> Dict[str, Any]:
        n = self.expect_ident().value
        self.expect_sym(":")
        ty = self.parse_type_expr()
        return {"name": n, "type": ty}

    def parse_effect_list(self, *, type_context: bool = False) -> List[Dict[str, Any]]:
        out = [self.parse_effect()]
        while self.at_sym(","):
            if type_context and self._comma_ends_type_effect_list():
                break
            self.advance()
            out.append(self.parse_effect())
        return out

    def _comma_ends_type_effect_list(self) -> bool:
        nxt = self.peek(1)
        after = self.peek(2)
        if nxt.kind == "ident" and after.kind == "sym" and after.value == ":":
            return True
        if nxt.kind == "ident" and not (after.kind == "sym" and after.value in {".", "("}):
            return True
        if nxt.kind == "kw" and nxt.value == "function":
            return True
        return False

    def parse_effect(self) -> Dict[str, Any]:
        if self.at_kw("pure"):
            self.advance()
            return {"path": ["pure"], "arg": None}
        # dotted_ident
        path = [self.expect_ident().value]
        while self.at_sym("."):
            self.advance()
            path.append(self.expect_ident().value)
        arg = None
        if self.at_sym("("):
            self.advance()
            arg = self.parse_expr()
            self.expect_sym(")")
        return {"path": path, "arg": arg}

    # --- type expressions ----------------------------------------------

    def parse_type_expr(self, *, stop_before_decl_effect: bool = False) -> Dict[str, Any]:
        # function ( T1, T2, ... ) returns T
        if self.at_kw("function"):
            self.advance()
            self.expect_sym("(")
            params: List[Dict[str, Any]] = []
            if not self.at_sym(")"):
                params.append(self.parse_type_expr())
                while self.at_sym(","):
                    self.advance()
                    params.append(self.parse_type_expr())
            self.expect_sym(")")
            self.expect_kw("returns")
            ret = self.parse_type_expr(stop_before_decl_effect=stop_before_decl_effect)
            effects = [{"path": ["pure"], "arg": None}]
            if self.at_kw("effects") and not (
                stop_before_decl_effect and self._effect_clause_belongs_to_decl()
            ):
                self.advance()
                effects = self.parse_effect_list(type_context=True)
            return {"kind": "FunctionType", "params": params, "returns": ret, "effects": effects}
        # IDENT [<...>]
        name = self.expect_ident().value
        args: List[Dict[str, Any]] = []
        if self.at_sym("<"):
            # commit: type generic
            self.advance()
            args.append(self.parse_type_expr())
            while self.at_sym(","):
                self.advance()
                args.append(self.parse_type_expr())
            self.expect_sym(">")
            return {"kind": "GenericType", "name": name, "args": args}
        return {"kind": "TypeName", "name": name}

    def _effect_clause_belongs_to_decl(self) -> bool:
        """True when the current `effects` token is the enclosing function clause.

        Function declarations and function types both use `effects` after a
        return type. In a declaration such as
        `function make() returns function(Int) returns Int effects pure do`,
        the single `effects pure` is the declaration clause and the function
        type defaults to pure. To annotate the returned function type itself,
        write two clauses: `... returns Int effects log effects pure do`.
        """
        depth = 0
        idx = self.i + 1
        while True:
            tok = self.peek(idx - self.i)
            if tok.kind == "eof":
                return False
            if tok.kind == "sym":
                if tok.value in {"(", "[", "<"}:
                    depth += 1
                elif tok.value in {")", "]", ">"}:
                    if depth == 0:
                        return False
                    depth -= 1
                elif depth == 0 and tok.value in {",", "="}:
                    return False
            elif depth == 0 and tok.kind == "kw":
                if tok.value in {"do", "requires", "ensures"}:
                    return True
                if tok.value == "effects":
                    return False
            idx += 1

    # --- block / statements --------------------------------------------

    def parse_block(self, end_kws: tuple) -> List[Dict[str, Any]]:
        stmts: List[Dict[str, Any]] = []
        while not (self.peek().kind == "kw" and self.peek().value in end_kws):
            if self.peek().kind == "eof":
                t = self.peek()
                raise self.err(f"unexpected end of file inside block; expected one of {end_kws}", t.pos)
            stmts.append(self.parse_stmt())
        return stmts

    def parse_stmt(self) -> Dict[str, Any]:
        t = self.peek()
        if t.kind == "kw":
            v = t.value
            if v == "let":
                return self._let_or_var("let")
            if v == "var":
                return self._let_or_var("var")
            if v == "if":
                return self.parse_if_stmt()
            if v == "while":
                return self.parse_while_stmt()
            if v == "for":
                return self.parse_for_stmt()
            if v == "match":
                return self.parse_match_stmt()
            if v == "return":
                return self.parse_return_stmt()
            if v == "break":
                self.advance()
                return {"kind": "Break"}
            if v == "continue":
                self.advance()
                return {"kind": "Continue"}
        # assign vs expr_stmt: lookahead for IDENT '='
        if t.kind == "ident" and self.peek(1).kind == "sym" and self.peek(1).value == "=":
            name = self.advance().value
            self.advance()  # =
            value = self.parse_expr()
            return {"kind": "Assign", "target": name, "value": value, "pos": t.pos.to_dict()}
        # otherwise, expression statement
        e = self.parse_expr()
        return {"kind": "ExprStmt", "expr": e}

    def _let_or_var(self, which: str) -> Dict[str, Any]:
        kw = self.advance()
        name = self.expect_ident().value
        ty = None
        if self.at_sym(":"):
            self.advance()
            ty = self.parse_type_expr()
        self.expect_sym("=")
        value = self.parse_expr()
        return {"kind": "Let" if which == "let" else "Var",
                "name": name, "type": ty, "value": value,
                "pos": kw.pos.to_dict()}

    def parse_if_stmt(self) -> Dict[str, Any]:
        kw = self.expect_kw("if")
        cond = self.parse_expr()
        self.expect_kw("then")
        then_block = self.parse_block(end_kws=("elif", "else", "end"))
        elifs: List[Dict[str, Any]] = []
        else_block: Optional[List[Dict[str, Any]]] = None
        while self.at_kw("elif"):
            self.advance()
            c = self.parse_expr()
            self.expect_kw("then")
            b = self.parse_block(end_kws=("elif", "else", "end"))
            elifs.append({"cond": c, "body": b})
        if self.at_kw("else"):
            self.advance()
            else_block = self.parse_block(end_kws=("end",))
        self.expect_kw("end")
        return {"kind": "If", "cond": cond, "then": then_block,
                "elifs": elifs, "else": else_block,
                "pos": kw.pos.to_dict()}

    def parse_while_stmt(self) -> Dict[str, Any]:
        kw = self.expect_kw("while")
        cond = self.parse_expr()
        self.expect_kw("do")
        body = self.parse_block(end_kws=("end",))
        self.expect_kw("end")
        return {"kind": "While", "cond": cond, "body": body,
                "pos": kw.pos.to_dict()}

    def parse_for_stmt(self) -> Dict[str, Any]:
        kw = self.expect_kw("for")
        var = self.expect_ident().value
        self.expect_kw("in")
        iterable = self.parse_expr()
        self.expect_kw("do")
        body = self.parse_block(end_kws=("end",))
        self.expect_kw("end")
        return {"kind": "For", "var": var, "iter": iterable, "body": body,
                "pos": kw.pos.to_dict()}

    def parse_match_stmt(self) -> Dict[str, Any]:
        kw = self.expect_kw("match")
        scrutinee = self.parse_expr()
        self.expect_kw("do")
        arms: List[Dict[str, Any]] = []
        while self.at_kw("case"):
            self.advance()
            pat = self.parse_pattern()
            self.expect_kw("do")
            body = self.parse_block(end_kws=("end",))
            self.expect_kw("end")
            arms.append({"pattern": pat, "body": body})
        self.expect_kw("end")
        return {"kind": "Match", "scrutinee": scrutinee, "arms": arms,
                "pos": kw.pos.to_dict()}

    def parse_return_stmt(self) -> Dict[str, Any]:
        kw = self.expect_kw("return")
        value = None
        # heuristic: a return can be followed by EOF, end, else, elif, case, or another stmt keyword
        t = self.peek()
        terminators_kw = {"end", "else", "elif", "case"}
        if not (t.kind == "kw" and t.value in terminators_kw) and t.kind != "eof":
            # if next token is one of the statement-starters, no expression follows
            if not (t.kind == "kw" and t.value in {"let", "var", "if", "while", "for", "match", "return", "break", "continue"}):
                value = self.parse_expr()
        return {"kind": "Return", "value": value, "pos": kw.pos.to_dict()}

    # --- patterns ------------------------------------------------------

    def parse_pattern(self) -> Dict[str, Any]:
        t = self.peek()
        # wildcard
        if t.kind == "ident" and t.value == "_":
            self.advance()
            return {"kind": "WildcardPat"}
        # literal patterns
        if t.kind in ("int", "float", "string"):
            self.advance()
            return {"kind": "LiteralPat", "value": t.value, "lit_kind": t.kind}
        if t.kind == "kw" and t.value in ("true", "false", "null"):
            self.advance()
            return {"kind": "LiteralPat", "value": t.value, "lit_kind": "kw"}
        # IDENT — either constructor pattern or binding
        if t.kind == "ident":
            self.advance()
            name = t.value
            # qualified constructor: IDENT { "." IDENT }
            path = [name]
            while self.at_sym("."):
                self.advance()
                path.append(self.expect_ident().value)
            if self.at_sym("("):
                self.advance()
                args: List[Dict[str, Any]] = []
                if not self.at_sym(")"):
                    args.append(self.parse_pattern())
                    while self.at_sym(","):
                        self.advance()
                        args.append(self.parse_pattern())
                self.expect_sym(")")
                pat: Dict[str, Any] = {"kind": "ConstructorPat", "path": path, "args": args}
            else:
                if len(path) > 1:
                    raise self.err("qualified name without (...) is not a valid pattern", t.pos)
                pat = {"kind": "BindPat", "name": name}
            if self.at_kw("as"):
                self.advance()
                alias = self.expect_ident().value
                pat = {"kind": "AsPat", "pattern": pat, "name": alias}
            return pat
        raise self.err(f"expected pattern, got {self._show(t)}", t.pos)

    # --- expressions ----------------------------------------------------
    # implemented with explicit precedence climbing per the EBNF order

    def parse_expr(self) -> Dict[str, Any]:
        return self._parse_or()

    def _binop_loop(self, sub: Callable[[], Dict[str, Any]], ops: tuple) -> Dict[str, Any]:
        left = sub()
        while True:
            t = self.peek()
            matched = None
            if t.kind == "sym" and t.value in ops:
                matched = t.value
            elif t.kind == "kw" and t.value in ops:
                matched = t.value
            if matched is None:
                return left
            self.advance()
            right = sub()
            left = self.with_pos(
                {"kind": "BinOp", "op": matched, "left": left, "right": right},
                self.expr_pos(left),
            )

    def _parse_or(self) -> Dict[str, Any]:
        return self._binop_loop(self._parse_and, ("or",))

    def _parse_and(self) -> Dict[str, Any]:
        return self._binop_loop(self._parse_implies, ("and",))

    def _parse_implies(self) -> Dict[str, Any]:
        # right-assoc
        left = self._parse_not()
        if self.at_kw("implies"):
            self.advance()
            right = self._parse_implies()
            return self.with_pos(
                {"kind": "BinOp", "op": "implies", "left": left, "right": right},
                self.expr_pos(left),
            )
        return left

    def _parse_not(self) -> Dict[str, Any]:
        if self.at_kw("not"):
            kw = self.advance()
            v = self._parse_not()
            return self.with_pos({"kind": "UnaryOp", "op": "not", "value": v}, kw.pos)
        return self._parse_eq()

    def _parse_eq(self) -> Dict[str, Any]:
        return self._binop_loop(self._parse_rel, ("==", "!="))

    def _parse_rel(self) -> Dict[str, Any]:
        return self._binop_loop(self._parse_add, ("<", "<=", ">", ">=", "is", "in"))

    def _parse_add(self) -> Dict[str, Any]:
        return self._binop_loop(self._parse_mul, ("+", "-"))

    def _parse_mul(self) -> Dict[str, Any]:
        return self._binop_loop(self._parse_unary, ("*", "/", "%"))

    def _parse_unary(self) -> Dict[str, Any]:
        if self.at_sym("-"):
            sym = self.advance()
            v = self._parse_postfix()
            return self.with_pos({"kind": "UnaryOp", "op": "neg", "value": v}, sym.pos)
        return self._parse_postfix()

    def _parse_postfix(self) -> Dict[str, Any]:
        e = self._parse_primary()
        while True:
            type_args = self._try_parse_call_type_args(e)
            if type_args is not None:
                call_pos = self.expr_pos(e)
                self.expect_sym("(")
                args: List[Dict[str, Any]] = []
                if not self.at_sym(")"):
                    args.append(self.parse_expr())
                    while self.at_sym(","):
                        self.advance()
                        args.append(self.parse_expr())
                self.expect_sym(")")
                e = self.with_pos(
                    {"kind": "Call", "func": e, "args": args, "type_args": type_args},
                    call_pos,
                )
            elif self.at_sym("("):
                call_pos = self.expr_pos(e)
                self.advance()
                args: List[Dict[str, Any]] = []
                if not self.at_sym(")"):
                    args.append(self.parse_expr())
                    while self.at_sym(","):
                        self.advance()
                        args.append(self.parse_expr())
                self.expect_sym(")")
                e = self.with_pos({"kind": "Call", "func": e, "args": args}, call_pos)
            elif self.at_sym("."):
                field_pos = self.expr_pos(e)
                self.advance()
                fname = self.expect_ident().value
                e = self.with_pos({"kind": "Field", "value": e, "name": fname}, field_pos)
            elif self.at_sym("["):
                bracket = self.advance()
                idx = self.parse_expr()
                self.expect_sym("]")
                e = self.with_pos(
                    {"kind": "Index", "value": e, "index": idx},
                    bracket.pos,
                )
            else:
                return e

    def _try_parse_call_type_args(self, callee: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        if not self.at_sym("<"):
            return None
        if not self._call_type_args_are_adjacent(callee):
            return None
        if not self._starts_type_arg_like():
            return None

        save = self.i
        try:
            self.advance()
            args: List[Dict[str, Any]] = [self.parse_type_expr()]
            while self.at_sym(","):
                self.advance()
                args.append(self.parse_type_expr())
            self.expect_sym(">")
            if self.at_sym("("):
                return args
        except AetherError as exc:
            self.i = save
            if self._tokens_suggest_generic_call(save):
                raise self.err(
                    "malformed explicit generic call; use f<Int>(x), f<Int, String>(x), or f<List<Int>>(xs)",
                    exc.diag.position,
                    suggestion="Use f<Int>(x), not f[Integer](x) or f::<Int>(x).",
                )
            return None

        self.i = save
        return None

    def _call_type_args_are_adjacent(self, callee: Dict[str, Any]) -> bool:
        if callee.get("kind") != "Ident":
            return False
        raw = callee.get("pos") or {}
        line = raw.get("line", 0)
        column = raw.get("column", 0)
        name = callee.get("name", "")
        lt = self.peek()
        return lt.pos.line == line and lt.pos.column == column + len(name)

    def _starts_type_arg_like(self) -> bool:
        if not self.at_sym("<"):
            return False
        t = self.peek(1)
        if t.kind == "kw" and t.value == "function":
            return True
        if t.kind != "ident":
            return False
        text = str(t.value)
        return bool(text) and text[0].isupper()

    def _tokens_suggest_generic_call(self, start: int) -> bool:
        depth = 0
        idx = start
        start_line = self.peek().pos.line
        while True:
            tok = self.peek(idx - self.i)
            if tok.kind == "eof" or tok.pos.line != start_line:
                return False
            if tok.kind == "sym":
                if tok.value == "<":
                    depth += 1
                elif tok.value == ">":
                    depth -= 1
                    if depth == 0 and self.peek(idx - self.i + 1).kind == "sym" and self.peek(idx - self.i + 1).value == "(":
                        return True
                elif tok.value == "(":
                    return depth > 0
            idx += 1

    def _parse_primary(self) -> Dict[str, Any]:
        t = self.peek()
        # literals
        if t.kind == "int":
            self.advance()
            return self.with_pos({"kind": "IntLit", "value": t.value}, t.pos)
        if t.kind == "float":
            self.advance()
            return self.with_pos({"kind": "FloatLit", "value": t.value}, t.pos)
        if t.kind == "string":
            self.advance()
            return self.with_pos({"kind": "StringLit", "value": t.value}, t.pos)
        if t.kind == "kw" and t.value in ("true", "false"):
            self.advance()
            return self.with_pos({"kind": "BoolLit", "value": t.value == "true"}, t.pos)
        if t.kind == "kw" and t.value == "null":
            self.advance()
            return self.with_pos({"kind": "NullLit"}, t.pos)
        # special function-like keywords
        if t.kind == "kw" and t.value == "old":
            kw = self.advance()
            self.expect_sym("(")
            v = self.parse_expr()
            self.expect_sym(")")
            return self.with_pos({"kind": "Old", "value": v}, kw.pos)
        if t.kind == "kw" and t.value in ("self", "result"):
            self.advance()
            return self.with_pos({"kind": "Ident", "name": t.value}, t.pos)
        # parenthesised
        if t.kind == "sym" and t.value == "(":
            self.advance()
            e = self.parse_expr()
            self.expect_sym(")")
            return e
        # if-expression
        if t.kind == "kw" and t.value == "if":
            return self._parse_if_expr()
        # match-expression
        if t.kind == "kw" and t.value == "match":
            return self._parse_match_expr()
        # list literal
        if t.kind == "sym" and t.value == "[":
            start = self.advance()
            elems: List[Dict[str, Any]] = []
            if not self.at_sym("]"):
                elems.append(self.parse_expr())
                while self.at_sym(","):
                    self.advance()
                    elems.append(self.parse_expr())
            self.expect_sym("]")
            return self.with_pos({"kind": "ListLit", "elems": elems}, start.pos)
        # map literal
        if t.kind == "sym" and t.value == "{":
            start = self.advance()
            entries: List[Dict[str, Any]] = []
            if not self.at_sym("}"):
                k = self.parse_expr()
                self.expect_sym(":")
                v = self.parse_expr()
                entries.append({"key": k, "value": v})
                while self.at_sym(","):
                    self.advance()
                    k = self.parse_expr()
                    self.expect_sym(":")
                    v = self.parse_expr()
                    entries.append({"key": k, "value": v})
            self.expect_sym("}")
            return self.with_pos({"kind": "MapLit", "entries": entries}, start.pos)
        # identifier
        if t.kind == "ident":
            self.advance()
            return self.with_pos({"kind": "Ident", "name": t.value}, t.pos)
        raise self.err(f"expected expression, got {self._show(t)}", t.pos)

    def _parse_if_expr(self) -> Dict[str, Any]:
        kw = self.expect_kw("if")
        cond = self.parse_expr()
        self.expect_kw("then")
        then_e = self.parse_expr()
        elifs: List[Dict[str, Any]] = []
        while self.at_kw("elif"):
            self.advance()
            c = self.parse_expr()
            self.expect_kw("then")
            elifs.append({"cond": c, "value": self.parse_expr()})
        self.expect_kw("else")
        else_e = self.parse_expr()
        self.expect_kw("end")
        return self.with_pos(
            {"kind": "IfExpr", "cond": cond, "then": then_e,
             "elifs": elifs, "else": else_e},
            kw.pos,
        )

    def _parse_match_expr(self) -> Dict[str, Any]:
        kw = self.expect_kw("match")
        scr = self.parse_expr()
        self.expect_kw("do")
        arms: List[Dict[str, Any]] = []
        while self.at_kw("case"):
            self.advance()
            pat = self.parse_pattern()
            self.expect_kw("do")
            value = self.parse_expr()
            self.expect_kw("end")
            arms.append({"pattern": pat, "value": value})
        self.expect_kw("end")
        return self.with_pos({"kind": "MatchExpr", "scrutinee": scr, "arms": arms}, kw.pos)
