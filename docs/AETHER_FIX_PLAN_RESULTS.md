# Aether Fix Plan Results

## 1. Executive Summary

This pass made Aether easier for external AI models to read, imitate, check,
and repair. It added AI-facing language documentation, canonical examples,
prompt packs, feature/list documentation, local packaging, CI, JSON diagnostic
coverage, AI syntax prelint, conservative type diagnostics, and a benchmark
plan. Aether remains a research prototype and is not production-ready.

The follow-up language-completion pass added structural generic/list type
checking for the supported subset, direct static index diagnostics for obvious
known-length cases, clearer runtime index errors, richer contract/refinement
diagnostics, additional tests, and eight new contract-wedge benchmark tasks.

## 2. Files Changed

- `.github/workflows/ci.yml`
- `README.md`
- `SPEC_ISSUES.md`
- `bench/AI_GENERATION_BENCHMARK_PLAN.md`
- `bench/tasks/t11_contract_nonzero_division/*`
- `bench/tasks/t12_contract_percentage_range/*`
- `bench/tasks/t13_contract_safe_index_access/*`
- `bench/tasks/t14_contract_positive_matrix_dimensions/*`
- `bench/tasks/t15_contract_probability_value/*`
- `bench/tasks/t16_contract_bounded_loop_count/*`
- `bench/tasks/t17_contract_normalized_vector_denominator/*`
- `bench/tasks/t18_contract_valid_age_score/*`
- `docs/AETHER_FIX_PLAN_RESULTS.md`
- `docs/AETHER_LANGUAGE_GUIDE.md`
- `docs/FEATURE_MATRIX.md`
- `docs/LISTS.md`
- `examples/01_safe_divide.aeth`
- `examples/02_non_empty_average.aeth`
- `examples/03_sorted_binary_search.aeth`
- `examples/04_bounded_index_update.aeth`
- `examples/05_safe_normalize_weights.aeth`
- `examples/README.md`
- `examples/negative/01_empty_average_contract.aeth`
- `examples/negative/06_effect_violation_demo.aeth`
- `grammar/effects.md`
- `grammar/grammar.ebnf`
- `grammar/types.md`
- `prompt/AETHER_SYNTAX_CHEATSHEET.md`
- `prompt/CLAUDE_AETHER_PROMPT.md`
- `prompt/GEMINI_AETHER_PROMPT.md`
- `prompt/GPT_AETHER_PROMPT.md`
- `pyproject.toml`
- `scripts/run_all.py`
- `tests/test_json_diagnostics.py`
- `tests/test_generic_typechecking.py`
- `tests/test_static_index_diagnostics.py`
- `tests/test_contract_diagnostics.py`
- `tests/test_ai_repair_diagnostics.py`
- `tests/test_list_operations.py`
- `tests/test_prelint_ai_syntax_errors.py`
- `transpiler/__init__.py`
- `transpiler/aether/agent_sdk.py`
- `transpiler/aether/cli.py`
- `transpiler/aether/diagnostics.py`
- `transpiler/aether/emitter.py`
- `transpiler/aether/passes/types.py`
- `transpiler/aether/prelint.py`
- `transpiler/aether/runtime.py`

## 3. Documentation Improvements

`README.md` now starts with a one-sentence pitch, honest prototype status,
a 30-second Python-versus-Aether diagnostic demo, Windows/macOS/Linux
quickstart commands, AI-writing guidance, implemented features, known gaps, and
development commands.

`docs/AETHER_LANGUAGE_GUIDE.md` documents valid current syntax for humans and
AI models, includes a do/do-not table, supported and unsupported syntax, five
canonical code patterns, an effect violation example, and a copyable AI prompt.

`docs/LISTS.md` documents list creation, indexing, `length`, `append`,
functional update patterns, unsupported item assignment, and AI mistakes.

`docs/FEATURE_MATRIX.md` classifies implemented, partial, not implemented, and
planned features against local implementation evidence.

The new prompt files teach Gemini, Claude, and GPT the current syntax traps:
`function`, `returns`, `List<Int>`, `length(xs)`, `do/end`, helper predicates,
contracts, and explicit effects.

## 4. Language / Compiler Improvements

Diagnostics now serialize top-level `line`, `column`, and `source_snippet`
fields when source context is available. Existing nested `position` remains.

Runtime `requires`, `ensures`, and refinement diagnostics now receive enclosing
function or return positions from the emitter instead of always reporting
line 0, column 0. This is approximate, not exact call-site positioning.

`transpiler/aether/prelint.py` adds pre-parse diagnostics for common AI syntax
errors: `fn`, `->`, `List[Int]`, `.len()`, JavaScript lambdas, list item
assignment, and brace control blocks.

`transpiler/aether/passes/types.py` now performs structural checks for the
implemented subset: `List<T>` element types, nested lists, contextual empty
lists, `append`, selected `Map<K,V>`/`Option<T>`/`Result<T,E>` helper flows,
user generic function argument/return relationships, and primitive
binding/return/argument mismatches. It remains conservative and is not a full
program verifier.

List behavior is documented and tested. `append` remains the supported build
pattern and checks element types; direct `xs[i] = value` and method-style
`xs.append(x)` are rejected by prelint. Obvious static out-of-bounds indexes
produce `INDEX_OUT_OF_BOUNDS_STATIC`; dynamic checked indexes produce runtime
diagnostics instead of Python tracebacks.

Contract and refinement diagnostics now include function name, contract kind or
argument name, an actual argument/result snapshot when available, and source
context. Direct local Aether function calls also thread call-site metadata into
failed contract/refinement diagnostics.

Grammar/spec docs were aligned with implementation by marking record literals
and set literals as not implemented, correcting assignment syntax, and removing
misleading type/effect claims.

## 5. Packaging / CI Improvements

`pyproject.toml` supports local editable install:

```text
pip install -e .
```

It exposes:

```text
aether = transpiler.aether.cli:main
```

The CLI now supports:

```text
aether ast file.aeth
aether check file.aeth
aether run file.aeth
```

`.github/workflows/ci.yml` runs on push and pull request using Python 3.11.
It installs `.[dev]`, runs the local gate, validation scripts, standalone
tests, pytest, example checks, and parser fuzzing.

## 6. AI Generation Readiness

External models now have a short language guide, examples to copy, prompt
files per model family, a syntax cheatsheet, and prelint diagnostics for the
exact wrong forms observed from AI generation.

The examples folder gives positive runnable programs for safe divide,
non-empty average, sorted binary search, bounded index update, and safe weight
normalization. Negative examples demonstrate refinement and effect diagnostics.

The AI benchmark plan defines ten tasks, scoring metrics, command templates,
and a result table without claiming unrun benchmark results.

## 7. Verification Commands

| Command | Result | Important output summary |
|---|---|---|
| `python -B scripts\run_all.py` | pass | reference `10/10`, bench `25/25`, python equivalents `22/22`, regression PASS, additional PASS, fuzz PASS |
| `python -B validation\run_validation.py` | pass | active validation references `10/10`, 5 deprecated skipped |
| `python -B validation\run_python_validation.py` | pass | python validation references `10/10` |
| `python -B tests\test_regressions.py` | pass | `ALL REGRESSION TESTS PASS`; `S-012` skipped because Windows lacks `SIGALRM` |
| `python -B tests\test_json_diagnostics.py` | pass | `JSON DIAGNOSTIC TESTS PASS` |
| `python -B tests\test_prelint_ai_syntax_errors.py` | pass | `PRELINT TESTS PASS` |
| `python -B tests\test_list_operations.py` | pass | `LIST OPERATION TESTS PASS` |
| `python -B tests\test_generic_typechecking.py` | pass | `GENERIC TYPECHECKING TESTS PASS` |
| `python -B tests\test_static_index_diagnostics.py` | pass | `STATIC INDEX DIAGNOSTIC TESTS PASS` |
| `python -B tests\test_contract_diagnostics.py` | pass | `CONTRACT DIAGNOSTIC TESTS PASS` |
| `python -B tests\test_ai_repair_diagnostics.py` | pass | `AI REPAIR DIAGNOSTIC TESTS PASS` |
| `python -B tests\test_safe_list_helpers.py` | pass | `SAFE LIST HELPER TESTS PASS` |
| `python -B tests\test_option_result_helpers.py` | pass | `OPTION RESULT HELPER TESTS PASS` |
| `python -B tests\test_match_exhaustiveness.py` | pass | `MATCH EXHAUSTIVENESS TESTS PASS` |
| `python -B tests\test_higher_order_effects.py` | pass | `HIGHER ORDER EFFECT TESTS PASS` |
| `python -B tests\test_function_type_effects.py` | pass | `FUNCTION TYPE EFFECT TESTS PASS` |
| `python -B -m transpiler.aether.cli check examples\01_safe_divide.aeth` | pass | `OK: examples\01_safe_divide.aeth (2 decls)` |
| `python -B -m transpiler.aether.cli run examples\01_safe_divide.aeth` | pass | printed `5` |
| `python -B -m transpiler.aether.cli ast examples\01_safe_divide.aeth` | pass | printed AST JSON with 2 declarations |
| `python -B -m transpiler.aether.cli check examples/01_safe_divide.aeth` | pass | forward-slash path accepted on Windows |
| `python -B -m transpiler.aether.cli run examples/01_safe_divide.aeth` | pass | printed `5` |
| `pip install -e .` | pass | built and installed editable `aether-lang-prototype==0.1.0` |
| `pip install -e ".[dev]"` | pass | editable install plus existing `pytest>=8` |
| `aether check examples\01_safe_divide.aeth` | pass | `OK: examples\01_safe_divide.aeth (2 decls)` |
| `aether run examples\01_safe_divide.aeth` | pass | printed `5` |
| `aether ast examples\01_safe_divide.aeth` | pass | printed AST JSON with 2 declarations |
| `aether --json check examples\negative\06_effect_violation_demo.aeth` | expected failure | produced JSON diagnostic `EFFECT_NOT_COVERED`, category `effect`, source snippet present |
| `pytest -q` | pass | `115 passed in 6.14s` |
| `python -B scripts\fuzz_parser.py --rounds 200 --mode all` | pass | 0 violations, 0 emit violations, 0 roundtrip errors |
| `git diff --check` | pass | exit 0; only line-ending warnings from Git on Windows |
| `python3 -B scripts/run_all.py` | not run | `python3` command is not installed on this Windows host |
| `python3 -B -m transpiler.aether.cli check examples/01_safe_divide.aeth` | not run | `python3` command is not installed on this Windows host |
| `python3 -B -m transpiler.aether.cli run examples/01_safe_divide.aeth` | not run | `python3` command is not installed on this Windows host |

## Safe List Helpers Pass

Implemented standard safe list helpers in the runtime and typechecker:
`safeAt(List<T>, Int) -> Option<T>`, `updateAt(List<T>, Int, T) ->
Result<List<T>, String>`, `safeSlice(List<T>, Int, Int) ->
Result<List<T>, String>`, `inBounds(List<T>, Int) -> Bool`, and
`validSliceBounds(List<T>, Int, Int) -> Bool`.

The checker now validates helper argument relationships with stable diagnostic
codes `LIST_HELPER_INDEX_TYPE`, `LIST_HELPER_VALUE_TYPE`, and
`LIST_HELPER_BOUND_TYPE`. Prelint now gives direct repair hints for
`xs[i] = value`, `xs[start:end]`, `xs.get(i)`, and `xs.append(x)`.

Added examples `examples/06_safe_at.aeth`, `examples/07_update_at.aeth`, and
`examples/08_safe_slice.aeth`, plus negative examples for wrong helper value
and bound types. Added `tests/test_safe_list_helpers.py` and benchmark tasks
`bench/tasks/t19_safe_list_update_helper/` and
`bench/tasks/t20_safe_slice_helper/`.

## Option / Result Ergonomics Pass

Implemented explicit `Option` helpers (`isSome`, `isNone`, `unwrapOr`,
`mapOption`, `andThenOption`, `expectSome`) and `Result` helpers (`isOk`,
`isErr`, `unwrapOrResult`, `mapResult`, `mapErr`, `andThenResult`, `expectOk`)
using the existing tuple-backed `Some`/`None` and `Ok`/`Err` representation.

The typechecker now validates helper flows with stable diagnostics such as
`OPTION_HELPER_TYPE_MISMATCH`, `RESULT_HELPER_TYPE_MISMATCH`,
`OPTION_HELPER_FUNCTION_TYPE`, and `RESULT_HELPER_FUNCTION_TYPE`.

Static match exhaustiveness checking now covers known `Option<T>`,
`Result<T,E>`, and user-defined union scrutinees. Missing cases produce
`MATCH_NON_EXHAUSTIVE` with `extra.missing_cases`; runtime fallback uses
`MATCH_NON_EXHAUSTIVE_RUNTIME` instead of a raw Python `RuntimeError`.

Added examples `examples/09_option_helpers.aeth`,
`examples/10_result_helpers.aeth`, and `examples/11_exhaustive_match.aeth`,
negative examples `04` through `08`, tests for helpers and match
exhaustiveness, and benchmark tasks `t21_option_unwrap_helper` and
`t22_result_error_handling`.

## Effect-Aware Helper Pass

Implemented static effect propagation for named callbacks passed to
`mapOption`, `andThenOption`, `mapResult`, `mapErr`, and `andThenResult`.
If a callback declares an effect not covered by the enclosing function, the
checker emits `HIGHER_ORDER_EFFECT_ESCAPE` at the helper call with the helper
name, callback name, escaped effect, source snippet, and repair hint.

Added positive examples `examples/12_pure_option_result_chaining.aeth` and
`examples/13_effect_aware_helpers.aeth`, negative examples
`examples/negative/09_effect_escape_map_option.aeth` and
`examples/negative/10_effect_escape_map_result.aeth`, and
`tests/test_higher_order_effects.py`.

Added benchmark wedge tasks `t23_map_option_effect_escape`,
`t24_map_result_effect_escape`, and `t25_map_err_effect_escape`, showing Python
executing callback side effects while Aether rejects missing effect
declarations.

## Function Type Effects Pass

Implemented effect annotations on function types. The parser now accepts
`function(Int) returns Int effects log`, and omitted function type effects
default to pure. Nested function types can carry their own effects, for example
`function(Int) returns function(Int) returns Bool effects log effects pure`.

The typechecker now preserves function type effects and can typecheck calls
through function-typed parameters. Passing an effectful named function where a
pure function type is expected is rejected. The effect checker now emits
`HIGHER_ORDER_EFFECT_ESCAPE` when a function-typed parameter such as
`f: function(Int) returns Int effects log` is called from an enclosing function
that does not declare a covering effect.

Added `examples/14_function_type_effects.aeth`,
`examples/negative/11_function_type_effect_escape.aeth`, and
`tests/test_function_type_effects.py`. Added
`docs/AETHER_FUNCTION_TYPE_EFFECTS_REPORT.md` for the full implementation and
verification report.

## Effect Row Precision Pass

Implemented precise coverage for supported argumented effects. `pure` remains
bottom, `log`, `fs.read`, and `fs.write` cover only themselves, and
`net.fetch("...")` rows use exact or trailing-star URL coverage. For example,
`net.fetch("https://api.example.com/*")` covers
`net.fetch("https://api.example.com/users")` but not
`net.fetch("https://billing.example.com/*")` or broader `net.fetch`.

Direct-call mismatches now report `EFFECT_NOT_COVERED` with the caller, callee,
required effect, declared caller row, source snippet, and repair hint. Function
type callback mismatches report `FUNCTION_TYPE_EFFECT_MISMATCH`; named
Option/Result helper callback escapes continue to report
`HIGHER_ORDER_EFFECT_ESCAPE` using the same precise coverage rules.

Added examples `examples/15_effect_row_precision_direct.aeth`,
`examples/16_effect_row_precision_function_type.aeth`, and
`examples/17_effect_row_precision_option_result.aeth`, negative examples
`12` through `14`, tests in `tests/test_effect_row_precision.py`, benchmark
tasks `t26_effect_row_direct_mismatch` and
`t27_effect_row_callback_mismatch`, and
`docs/AETHER_EFFECT_ROW_PRECISION_REPORT.md`.

## Deterministic Runtime Pass

Implemented deterministic runtime hooks for `random()`, `time.now()`, and
`now()`. The CLI now supports `aether run --deterministic`, `--seed`, and
`--fixed-time`. `random()` uses a seeded pseudo-random generator; `time.now()`
and `now()` return a fixed `Instant` in deterministic mode.

Added `examples/18_deterministic_random.aeth`,
`examples/19_deterministic_time.aeth`, and
`tests/test_deterministic_runtime.py`. Updated README, language guide,
feature matrix, stdlib/effect docs, and example index.

## Explicit Generic Calls Pass

Added parser, AST, printer, and type-checker support for explicit generic calls:
`id<Int>(5)`, `makeResult<Int, String>(5)`, and nested forms such as
`id<List<Int>>([1, 2])`. Ordinary inferred calls such as `id(5)` remain
supported.

The checker reports stable diagnostics for explicit generic misuse:
`GENERIC_CALL_ON_NON_GENERIC`, `GENERIC_TYPE_ARG_ARITY`,
`GENERIC_TYPE_ARG_MISMATCH`, and `GENERIC_RETURN_TYPE_MISMATCH`. Prelint now
keeps `f<Int>(x)` valid while rejecting common wrong forms such as
`f[Integer](x)` and `f::<Int>(x)` with repair hints.

Added `tests/test_explicit_generic_calls.py`, examples 20-21, negative examples
15-17, benchmark tasks t28-t29, and
`docs/AETHER_EXPLICIT_GENERIC_CALLS_REPORT.md`.

## Quantifiers And Aggregates Pass

Added list quantifier expressions and aggregate helpers for collection
contracts: `forall x in xs: predicate`, `exists x in xs: predicate`,
`sum(xs)`, `min(xs)`, `max(xs)`, `sorted(xs)`, and
`permutation(xs, ys)`.

The parser now emits `Quantifier` AST nodes, the emitter lowers them to Python
`all`/`any` loops, and the type checker validates list element types, predicate
types, non-empty aggregate requirements, and same-element-type permutation
arguments. Runtime aggregate failures use structured diagnostics.

Added `tests/test_quantifiers_and_aggregates.py`, examples 22-23, benchmark
tasks t30-t31, and `docs/AETHER_QUANTIFIERS_REPORT.md`.

## Loop Invariants And Record Updates Pass

Added annotated `while` loops with `invariant` and `variant` clauses, half-open
range expressions such as `0..length(xs) - 1`, and record copy-update syntax
such as `account { balance = newBalance }`.

The parser now stores loop annotations, `RangeExpr`, and `RecordUpdate` nodes.
The type checker validates invariant `Bool` expressions, `Int` variants, range
bounds, and record update fields. The SMT pass proves simple arithmetic variant
decreases when possible and emits `LOOP_VARIANT_NOT_DECREASING_STATIC` when it
can disprove a decrease. Dynamic cases use runtime fallback diagnostics:
`LOOP_INVARIANT_FAILED` and `LOOP_VARIANT_NOT_DECREASING`.

Added `tests/test_loop_invariants_and_records.py`, examples 24-25, and
`docs/AETHER_LOOP_INVARIANTS_REPORT.md`.

## 8. Remaining Limitations

Aether is still not production-ready.

Generic/list type checking is implemented for supported constructs, including
explicit generic calls such as `identity<Int>(5)`. Aether still does not have
complete type inference, value-dependent typing, or full proof of generic
program consistency.

Static verification is limited. The SMT pass handles only a small arithmetic
fragment; most contracts/refinements remain runtime checks.

Diagnostics are better but not complete. Runtime contract/refinement
diagnostics include call-site metadata for direct local Aether function calls,
and named Option/Result helper callback effect diagnostics point at the helper
call. Dynamic higher-order calls and some non-contract runtime failures still
lack exact caller spans.

The deterministic runtime is implemented for the supported `random()`,
`time.now()`, and `now()` hooks. It is a reproducibility aid, not a complete
deterministic scheduler or sandbox.

The capability system is partial. `--capability-strict` is useful for static
effect/capability consistency, but it is not a production sandbox.

Record literals, direct list item assignment, value-level `as` casts, and set
literals are not implemented.

## 9. Next Steps

1. Stronger static verification beyond the current SMT arithmetic fragment.
2. More complete type inference and generic checking for future language
   constructs.
3. Richer standard library beyond the current safe list helper subset.
4. More AI generation benchmarks with saved model outputs.
5. Package release workflow after the prototype stabilizes.
6. Documentation site generated from `docs/`, `grammar/`, and `examples/`.
