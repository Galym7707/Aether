# Aether Option / Result Ergonomics Report

## 1. Executive Summary

This pass added explicit `Option` and `Result` helper functions, type-checker
knowledge for those helpers, static `match` exhaustiveness diagnostics for
known sum types, and structured runtime fallback diagnostics for non-exhaustive
matches that still reach execution.

Aether remains a research / early compiler prototype, not production-ready.
The changes are intended to make generated Aether code easier for external AI
models to write and easier to repair from structured diagnostics.

## 2. Files Changed

- `README.md`
- `bench/CONTRACT_TASKS.md`
- `bench/tasks/t21_option_unwrap_helper/README.md`
- `bench/tasks/t21_option_unwrap_helper/grader.json`
- `bench/tasks/t21_option_unwrap_helper/prompt.md`
- `bench/tasks/t21_option_unwrap_helper/python_equivalent.py`
- `bench/tasks/t21_option_unwrap_helper/reference.aeth`
- `bench/tasks/t22_result_error_handling/README.md`
- `bench/tasks/t22_result_error_handling/grader.json`
- `bench/tasks/t22_result_error_handling/prompt.md`
- `bench/tasks/t22_result_error_handling/python_equivalent.py`
- `bench/tasks/t22_result_error_handling/reference.aeth`
- `docs/AETHER_FIX_PLAN_RESULTS.md`
- `docs/AETHER_LANGUAGE_GUIDE.md`
- `docs/AETHER_OPTION_RESULT_ERGONOMICS_REPORT.md`
- `docs/FEATURE_MATRIX.md`
- `docs/LISTS.md`
- `examples/09_option_helpers.aeth`
- `examples/10_result_helpers.aeth`
- `examples/11_exhaustive_match.aeth`
- `examples/README.md`
- `examples/negative/04_match_missing_option_case.aeth`
- `examples/negative/05_match_missing_result_case.aeth`
- `examples/negative/06_match_missing_union_case.aeth`
- `examples/negative/07_bad_option_helper_type.aeth`
- `examples/negative/08_bad_result_helper_type.aeth`
- `grammar/stdlib.md`
- `grammar/types.md`
- `prompt/AETHER_SYNTAX_CHEATSHEET.md`
- `prompt/CLAUDE_AETHER_PROMPT.md`
- `prompt/GEMINI_AETHER_PROMPT.md`
- `prompt/GPT_AETHER_PROMPT.md`
- `prompt/system_prompt.md`
- `scripts/run_all.py`
- `tests/test_match_exhaustiveness.py`
- `tests/test_option_result_helpers.py`
- `tests/test_prelint_ai_syntax_errors.py`
- `transpiler/aether/emitter.py`
- `transpiler/aether/passes/effects.py`
- `transpiler/aether/passes/types.py`
- `transpiler/aether/prelint.py`
- `transpiler/aether/runtime.py`

## 3. Option Helpers Added

Runtime helpers were added using the existing tuple-backed `Some` / `None`
representation:

- `isSome(opt) -> Bool`
- `isNone(opt) -> Bool`
- `unwrapOr(opt, default) -> T`
- `mapOption(opt, f) -> Option<U>`
- `andThenOption(opt, f) -> Option<U>`
- `expectSome(opt, message) -> T`

`expectSome(None(), message)` raises a structured diagnostic with code
`EXPECT_SOME_FAILED` instead of a raw Python traceback.

## 4. Result Helpers Added

Runtime helpers were added using the existing tuple-backed `Ok` / `Err`
representation:

- `isOk(result) -> Bool`
- `isErr(result) -> Bool`
- `unwrapOrResult(result, default) -> T`
- `mapResult(result, f) -> Result<U, E>`
- `mapErr(result, f) -> Result<T, F>`
- `andThenResult(result, f) -> Result<U, E>`
- `expectOk(result, message) -> T`

`expectOk(Err(...), message)` raises a structured diagnostic with code
`EXPECT_OK_FAILED`.

## 5. Type-Checking Behavior

The type checker now recognizes the helper flows above. It checks fallback
values and mapper function signatures where the prototype has enough static
information.

Stable diagnostic codes added:

- `OPTION_HELPER_TYPE_MISMATCH`
- `RESULT_HELPER_TYPE_MISMATCH`
- `OPTION_HELPER_FUNCTION_TYPE`
- `RESULT_HELPER_FUNCTION_TYPE`

Known limitation: higher-order helper effects are still treated as pure helper
calls by the current effect pass; mapper effect composition is not fully
modeled yet.

## 6. Match Exhaustiveness Diagnostics

Static exhaustiveness checking now runs when the scrutinee type is known:

- `Option<T>` must cover `Some` and `None`, unless `_` is present.
- `Result<T, E>` must cover `Ok` and `Err`, unless `_` is present.
- User-defined unions must cover all declared cases, unless `_` is present.

Missing cases produce `MATCH_NON_EXHAUSTIVE` with
`extra.missing_cases` in JSON diagnostics.

## 7. Runtime Fallback Behavior

Generated Python now calls `_aether_match_failed(...)` for otherwise
non-exhaustive match fallbacks. Runtime diagnostics use code
`MATCH_NON_EXHAUSTIVE_RUNTIME` and include the actual runtime case when it can
be identified.

Known limitation: source positions are best effort and depend on the AST node
position available to the emitter.

## 8. Examples Added

- `examples/09_option_helpers.aeth`
- `examples/10_result_helpers.aeth`
- `examples/11_exhaustive_match.aeth`
- `examples/negative/04_match_missing_option_case.aeth`
- `examples/negative/05_match_missing_result_case.aeth`
- `examples/negative/06_match_missing_union_case.aeth`
- `examples/negative/07_bad_option_helper_type.aeth`
- `examples/negative/08_bad_result_helper_type.aeth`

Positive examples pass `check` and `run`. Negative examples fail with
structured diagnostics.

## 9. Benchmark Tasks Added

- `bench/tasks/t21_option_unwrap_helper/`
- `bench/tasks/t22_result_error_handling/`

These tasks show Aether programs making missing values and update failures
explicit with `Option` / `Result`, while the Python equivalents silently return
fallback or misleading output.

## 10. Documentation Updates

Documentation now tells AI models to:

- prefer exhaustive `match` for `Option` and `Result`;
- use `unwrapOr` / `unwrapOrResult` only when a fallback is semantically
  correct;
- use `expectSome` / `expectOk` only when failure should become a structured
  runtime diagnostic;
- avoid method-style forms such as `opt.unwrap()`, `result.unwrap()`,
  `result.is_ok()`, and `option.is_some()`.

## 11. Verification Commands and Results

| Command | Result | Summary |
|---|---|---|
| `python -B scripts\run_all.py` | pass | reference `10/10`, bench `20/20`, python equivalents `17/17`, regression PASS, additional PASS, fuzz PASS |
| `python -B validation\run_validation.py` | pass | `10/10 validation references pass` |
| `python -B validation\run_python_validation.py` | pass | `10/10 python validation references pass` |
| `python -B tests\test_regressions.py` | pass | `ALL REGRESSION TESTS PASS` |
| `python -B tests\test_option_result_helpers.py` | pass | `OPTION RESULT HELPER TESTS PASS` |
| `python -B tests\test_match_exhaustiveness.py` | pass | `MATCH EXHAUSTIVENESS TESTS PASS` |
| `python -B tests\test_prelint_ai_syntax_errors.py` | pass | `PRELINT TESTS PASS` |
| `python -m pytest -q` | pass | `82 passed in 8.84s` |
| `python -B -m transpiler.aether.cli check examples\09_option_helpers.aeth` | pass | `OK: examples\09_option_helpers.aeth (3 decls)` |
| `python -B -m transpiler.aether.cli run examples\09_option_helpers.aeth` | pass | printed `some`, `20`, `-1`, `20` |
| `python -B -m transpiler.aether.cli check examples\10_result_helpers.aeth` | pass | `OK: examples\10_result_helpers.aeth (3 decls)` |
| `python -B -m transpiler.aether.cli run examples\10_result_helpers.aeth` | pass | printed `ok`, `99`, `4`, `bad update` |
| `python -B -m transpiler.aether.cli check examples\11_exhaustive_match.aeth` | pass | `OK: examples\11_exhaustive_match.aeth (3 decls)` |
| `python -B -m transpiler.aether.cli run examples\11_exhaustive_match.aeth` | pass | printed `1`, `-1` |
| `python -m bench.harness run-reference` | pass | `20/20 reference solutions pass` |
| `python -m bench.harness run-python-equivalents` | pass | `17/17 python equivalents pass` |
| `pip install -e .` | pass | editable `aether-lang-prototype==0.1.0` installed |
| `pip install -e ".[dev]"` | pass | editable install with existing `pytest>=8` |
| `aether check examples\09_option_helpers.aeth` | pass | `OK: examples\09_option_helpers.aeth (3 decls)` |
| `aether run examples\09_option_helpers.aeth` | pass | printed `some`, `20`, `-1`, `20` |
| `aether check examples\10_result_helpers.aeth` | pass | `OK: examples\10_result_helpers.aeth (3 decls)` |
| `aether run examples\10_result_helpers.aeth` | pass | printed `ok`, `99`, `4`, `bad update` |
| `aether ast examples\11_exhaustive_match.aeth` | pass | printed AST JSON |
| `git diff --check` | pass | exit 0; Git printed CRLF conversion warnings on this Windows host |
| `python3 --version` | environment limitation | command failed because `python3` is not installed on this Windows host |

## 12. Remaining Limitations

- Aether remains a research prototype and early compiler prototype.
- Match exhaustiveness is checked only when the scrutinee type is statically
  known.
- Higher-order helper type checking is pragmatic, not a complete Hindley-Milner
  style inference system.
- Mapper effect propagation for `mapOption`, `mapResult`, and related helpers
  is not fully modeled.
- Runtime diagnostic source spans are best effort.
- Static verification remains limited; many contracts/refinements are still
  runtime checks.

## 13. Recommended Next Task

Implement effect-aware higher-order helper checking, so functions passed to
`mapOption`, `mapResult`, `andThenOption`, and `andThenResult` contribute their
effects to the caller instead of being treated as pure helper calls.
