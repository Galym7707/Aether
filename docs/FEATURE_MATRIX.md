# Aether Feature Matrix

This matrix is based on the local repository implementation audited and updated
through 2026-05-10. Evidence files include `transpiler/aether/parser.py`,
`transpiler/aether/emitter.py`, `transpiler/aether/runtime.py`,
`transpiler/aether/passes/*.py`, `tests/test_regressions.py`, and the new
diagnostic/list tests.

| Feature | Status | Supported Syntax | Test Coverage | Notes |
|---|---|---|---|---|
| function declarations | Implemented | `function f(x: Int) returns Int ... effects pure do ... end` | reference corpus, regression tests | `effects` is required. |
| requires | Implemented | `requires x > 0` | regression tests, bench contract tasks | Runtime checked; some arithmetic clauses checked by SMT. |
| ensures | Implemented | `ensures result > 0` | regression tests | Runtime checked at return sites; some arithmetic clauses checked by SMT. |
| effects | Implemented | `effects pure`, `effects log`, `effects fs.read` | regression tests, `tests/test_higher_order_effects.py` | Static direct-call checker runs by default. Named callbacks passed to implemented Option/Result helpers are checked for escaping effects. Runtime strict mode is optional. |
| function type effects | Implemented for supported subset | `function(Int) returns Int effects log` | `tests/test_function_type_effects.py`, examples | Function type effects are optional and default to pure. Calls through function-typed parameters require the enclosing function to declare covering effects. |
| `List<Int>` | Implemented | `List<Int>` | examples, list tests, corpus | Use angle brackets, not square brackets. |
| list literals | Implemented | `[]`, `[1, 2, 3]`, `[[1], [2]]` | examples, corpus, `tests/test_generic_typechecking.py` | Non-empty lists infer one element type. Empty lists require a contextual type or annotation. Mixed lists are rejected. |
| indexing | Implemented | `xs[0]` | examples, corpus, `tests/test_static_index_diagnostics.py` | Non-Int, negative, obvious known-length out-of-bounds indexes produce structured diagnostics. Dynamic out-of-bounds indexes use runtime diagnostic `INDEX_OUT_OF_BOUNDS_RUNTIME`. |
| list mutation | Not implemented | None | prelint tests | `xs[i] = value` is rejected by prelint as `E0006`. |
| append/update helpers | Implemented for supported list subset | `append(xs, x)`, `safeAt(xs, i)`, `updateAt(xs, i, value)`, `safeSlice(xs, start, end)`, `inBounds(xs, i)`, `validSliceBounds(xs, start, end)` | `tests/test_safe_list_helpers.py`, list tests, examples, generic tests | Helpers are stdlib runtime functions with generic typechecker rules. `updateAt` returns `Result<List<T>, String>` and does not mutate the original list. Method-style `xs.append(x)` is unsupported. |
| direct list item assignment | Not implemented | None | prelint tests | `xs[i] = value` is rejected by prelint as `E0006`; use `updateAt(xs, i, value)` and handle `Result`. |
| Option helpers | Implemented for supported subset | `isSome(opt)`, `isNone(opt)`, `unwrapOr(opt, default)`, `mapOption(opt, f)`, `andThenOption(opt, f)`, `expectSome(opt, message)` | `tests/test_option_result_helpers.py`, examples | Uses existing `Some`/`None` tuple representation. `expectSome` raises structured diagnostic `EXPECT_SOME_FAILED` on `None`. |
| Result helpers | Implemented for supported subset | `isOk(res)`, `isErr(res)`, `unwrapOrResult(res, default)`, `mapResult(res, f)`, `mapErr(res, f)`, `andThenResult(res, f)`, `expectOk(res, message)` | `tests/test_option_result_helpers.py`, examples | Uses existing `Ok`/`Err` tuple representation. `expectOk` raises structured diagnostic `EXPECT_OK_FAILED` on `Err`. |
| higher-order helper effect checking | Implemented for named callbacks | `mapOption(Some(1), helper)`, `mapResult(Ok(1), helper)` | `tests/test_higher_order_effects.py`, examples, bench tasks t23-t25 | If the named callback declares an effect not covered by the enclosing function, the checker emits `HIGHER_ORDER_EFFECT_ESCAPE`. Anonymous/dynamic callbacks are not supported by the current parser/checker. |
| match exhaustiveness diagnostics | Implemented for known sum types | `match value do case Some(x) do ... end case None() do ... end end` | `tests/test_match_exhaustiveness.py`, examples | Checks known `Option`, `Result`, and user union scrutinee types. Unknown scrutinee types are not guessed; runtime fallback emits `MATCH_NON_EXHAUSTIVE_RUNTIME`. |
| records | Implemented | `record Point do ... end`, `Point(1, 2)`, `p.x` | validation corpus | Records emit positional constructors and dictionary-backed field access. |
| record literals | Not implemented | None | SPEC_ISSUES S-006 | `Point { x = 1, y = 2 }` is misleading in old grammar docs and should not be generated. |
| unions | Implemented | `union Shape do case Square(side: Int) end` | validation corpus | Constructors can be qualified, e.g. `Shape.Square(4)`. |
| generics | Implemented for supported subset | `function id<T>(x: T) returns T`, `List<T>`, `Map<K,V>`, `Option<T>`, `Result<T,E>` | `tests/test_generic_typechecking.py`, corpus | The checker validates supported user generic function calls and container element flows. Explicit generic call syntax such as `id<Int>(5)` is unsupported. This is not a complete type-inference/proof system. |
| refinement types | Implemented at runtime boundaries | `type PositiveInt = Int where self > 0` | regression tests, examples | Checked for parameters when entering functions. |
| runtime contract checks | Implemented | `requires`, `ensures`, refinement parameter types | regression tests, bench tasks, `tests/test_contract_diagnostics.py` | Diagnostics include function name, contract kind, actual argument/result snapshot, line, column, source snippet, hint, and direct local call-site metadata when available. |
| static contract checks | Partially implemented | arithmetic `requires`/`ensures` fragment | regression tests | SMT pass only handles numeric arithmetic and boolean connectives. |
| SMT checks | Partially implemented | no special syntax | regression tests | Requires `z3-solver`; unsupported clauses fall back to runtime. |
| effect checking | Implemented with limits | direct calls to known functions; named callbacks for selected helpers; annotated function-typed parameters | regression tests, `tests/test_higher_order_effects.py`, `tests/test_function_type_effects.py` | Dynamic function values without function type effect metadata are conservatively limited. |
| capability checking | Partially implemented | `module App requires capability log ... end` plus `--capability-strict` | regression tests | Opt-in CLI pass. Not enforced by default. |
| deterministic runtime | Not implemented | None | SPEC_ISSUES S-009 | Time/random are not seedable for deterministic replay. |
| JSON diagnostics | Implemented | `aether --json check file.aeth` | `tests/test_json_diagnostics.py`, diagnostic tests | Diagnostics include code, category, severity, message, line, column, position, source snippet when available, suggestion/hint, plus `expected`/`actual` and bounds fields where relevant. |
| AST output | Implemented | `aether ast file.aeth`, `aether parse file.aeth` | manual CLI verification planned | `ast` is an alias for `parse`. |
| AI Agent SDK | Implemented | Python API in `transpiler.aether.agent_sdk` | regression tests | Exposes parse/check/run/grade APIs. |
| general static type checker | Partially implemented | no special syntax | generic, index, JSON diagnostic tests | Covers supported generic containers, user generic function calls, primitive mismatches, return/binding/argument mismatches, and obvious index bounds. It is still conservative and not a complete verifier. |
