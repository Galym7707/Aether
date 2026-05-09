# Aether Feature Matrix

This matrix is based on the local repository implementation audited on
2026-05-09. Evidence files include `transpiler/aether/parser.py`,
`transpiler/aether/emitter.py`, `transpiler/aether/runtime.py`,
`transpiler/aether/passes/*.py`, `tests/test_regressions.py`, and the new
diagnostic/list tests.

| Feature | Status | Supported Syntax | Test Coverage | Notes |
|---|---|---|---|---|
| function declarations | Implemented | `function f(x: Int) returns Int ... effects pure do ... end` | reference corpus, regression tests | `effects` is required. |
| requires | Implemented | `requires x > 0` | regression tests, bench contract tasks | Runtime checked; some arithmetic clauses checked by SMT. |
| ensures | Implemented | `ensures result > 0` | regression tests | Runtime checked at return sites; some arithmetic clauses checked by SMT. |
| effects | Implemented | `effects pure`, `effects log`, `effects fs.read` | regression tests | Static direct-call checker runs by default. Runtime strict mode is optional. |
| `List<Int>` | Implemented | `List<Int>` | examples, list tests, corpus | Use angle brackets, not square brackets. |
| list literals | Implemented | `[]`, `[1, 2, 3]`, `[[1], [2]]` | examples, corpus, `tests/test_generic_typechecking.py` | Non-empty lists infer one element type. Empty lists require a contextual type or annotation. Mixed lists are rejected. |
| indexing | Implemented | `xs[0]` | examples, corpus, `tests/test_static_index_diagnostics.py` | Non-Int, negative, obvious known-length out-of-bounds indexes produce structured diagnostics. Dynamic out-of-bounds indexes use runtime diagnostic `INDEX_OUT_OF_BOUNDS_RUNTIME`. |
| list mutation | Not implemented | None | prelint tests | `xs[i] = value` is rejected by prelint as `E0006`. |
| append/update helpers | Partially implemented | `append(xs, x)` | list tests, examples, generic tests | `append` is stdlib and checks element type. `updateAt` is a user helper, not stdlib. Method-style `xs.append(x)` is unsupported. |
| records | Implemented | `record Point do ... end`, `Point(1, 2)`, `p.x` | validation corpus | Records emit positional constructors and dictionary-backed field access. |
| record literals | Not implemented | None | SPEC_ISSUES S-006 | `Point { x = 1, y = 2 }` is misleading in old grammar docs and should not be generated. |
| unions | Implemented | `union Shape do case Square(side: Int) end` | validation corpus | Constructors can be qualified, e.g. `Shape.Square(4)`. |
| generics | Implemented for supported subset | `function id<T>(x: T) returns T`, `List<T>`, `Map<K,V>`, `Option<T>`, `Result<T,E>` | `tests/test_generic_typechecking.py`, corpus | The checker validates supported user generic function calls and container element flows. Explicit generic call syntax such as `id<Int>(5)` is unsupported. This is not a complete type-inference/proof system. |
| refinement types | Implemented at runtime boundaries | `type PositiveInt = Int where self > 0` | regression tests, examples | Checked for parameters when entering functions. |
| runtime contract checks | Implemented | `requires`, `ensures`, refinement parameter types | regression tests, bench tasks, `tests/test_contract_diagnostics.py` | Diagnostics include function name, contract kind, actual argument/result snapshot, line, column, source snippet, hint, and direct local call-site metadata when available. |
| static contract checks | Partially implemented | arithmetic `requires`/`ensures` fragment | regression tests | SMT pass only handles numeric arithmetic and boolean connectives. |
| SMT checks | Partially implemented | no special syntax | regression tests | Requires `z3-solver`; unsupported clauses fall back to runtime. |
| effect checking | Implemented with limits | direct calls to known functions | regression tests | Higher-order and dynamic calls are conservatively left unchecked. |
| capability checking | Partially implemented | `module App requires capability log ... end` plus `--capability-strict` | regression tests | Opt-in CLI pass. Not enforced by default. |
| deterministic runtime | Not implemented | None | SPEC_ISSUES S-009 | Time/random are not seedable for deterministic replay. |
| JSON diagnostics | Implemented | `aether --json check file.aeth` | `tests/test_json_diagnostics.py`, diagnostic tests | Diagnostics include code, category, severity, message, line, column, position, source snippet when available, suggestion/hint, plus `expected`/`actual` and bounds fields where relevant. |
| AST output | Implemented | `aether ast file.aeth`, `aether parse file.aeth` | manual CLI verification planned | `ast` is an alias for `parse`. |
| AI Agent SDK | Implemented | Python API in `transpiler.aether.agent_sdk` | regression tests | Exposes parse/check/run/grade APIs. |
| general static type checker | Partially implemented | no special syntax | generic, index, JSON diagnostic tests | Covers supported generic containers, user generic function calls, primitive mismatches, return/binding/argument mismatches, and obvious index bounds. It is still conservative and not a complete verifier. |
