# Aether Effect-Aware Helpers Report

## 1. Summary

This pass added static effect-aware checking for named callbacks passed to the
implemented higher-order `Option` and `Result` helpers:

- `mapOption`
- `andThenOption`
- `mapResult`
- `mapErr`
- `andThenResult`

If a named callback declares an effect that the enclosing function does not
declare, Aether now emits a structured static diagnostic instead of treating
the helper call as pure. Aether remains a research / early compiler prototype,
not production-ready.

## 2. Files Changed

- `README.md`
- `bench/CONTRACT_TASKS.md`
- `bench/tasks/t23_map_option_effect_escape/README.md`
- `bench/tasks/t23_map_option_effect_escape/grader.json`
- `bench/tasks/t23_map_option_effect_escape/prompt.md`
- `bench/tasks/t23_map_option_effect_escape/python_equivalent.py`
- `bench/tasks/t23_map_option_effect_escape/reference.aeth`
- `bench/tasks/t24_map_result_effect_escape/README.md`
- `bench/tasks/t24_map_result_effect_escape/grader.json`
- `bench/tasks/t24_map_result_effect_escape/prompt.md`
- `bench/tasks/t24_map_result_effect_escape/python_equivalent.py`
- `bench/tasks/t24_map_result_effect_escape/reference.aeth`
- `bench/tasks/t25_map_err_effect_escape/README.md`
- `bench/tasks/t25_map_err_effect_escape/grader.json`
- `bench/tasks/t25_map_err_effect_escape/prompt.md`
- `bench/tasks/t25_map_err_effect_escape/python_equivalent.py`
- `bench/tasks/t25_map_err_effect_escape/reference.aeth`
- `docs/AETHER_EFFECT_AWARE_HELPERS_REPORT.md`
- `docs/AETHER_FIX_PLAN_RESULTS.md`
- `docs/AETHER_LANGUAGE_GUIDE.md`
- `docs/AETHER_OPTION_RESULT_ERGONOMICS_REPORT.md`
- `docs/FEATURE_MATRIX.md`
- `examples/12_pure_option_result_chaining.aeth`
- `examples/13_effect_aware_helpers.aeth`
- `examples/README.md`
- `examples/negative/09_effect_escape_map_option.aeth`
- `examples/negative/10_effect_escape_map_result.aeth`
- `grammar/effects.md`
- `grammar/stdlib.md`
- `prompt/AETHER_SYNTAX_CHEATSHEET.md`
- `prompt/CLAUDE_AETHER_PROMPT.md`
- `prompt/GEMINI_AETHER_PROMPT.md`
- `prompt/GPT_AETHER_PROMPT.md`
- `prompt/system_prompt.md`
- `scripts/run_all.py`
- `tests/test_higher_order_effects.py`
- `transpiler/aether/passes/effects.py`

## 3. New Diagnostics

Added diagnostic code:

- `HIGHER_ORDER_EFFECT_ESCAPE`

The diagnostic is emitted when:

1. A call uses `mapOption`, `andThenOption`, `mapResult`, `mapErr`, or
   `andThenResult`.
2. The callback argument resolves to a known named function.
3. That callback declares one or more effects.
4. The enclosing function does not declare a covering effect.

The diagnostic includes line, column, source snippet, helper name, callback
name, escaped effect, caller effects, and a repair hint.

Example repair hint:

```text
add effect 'log' to 'main', pass a pure callback to 'mapOption',
or move the effectful work outside the helper
```

## 4. Implementation Notes

The implementation is intentionally small and conservative. It lives in
`transpiler/aether/passes/effects.py`, next to the existing direct-call effect
checker. The pass now has a table of supported higher-order helper callback
positions and resolves the callback only when it is a known named callee.

No runtime representation changes were needed. Existing helper runtime behavior
and type checking remain intact.

## 5. New Tests and Examples

Added `tests/test_higher_order_effects.py` covering:

- pure callback through `mapOption`;
- effectful callback through `mapOption` allowed when enclosing function
  declares `effects log`;
- `HIGHER_ORDER_EFFECT_ESCAPE` for `mapOption`;
- `HIGHER_ORDER_EFFECT_ESCAPE` for `andThenOption`;
- `HIGHER_ORDER_EFFECT_ESCAPE` for `mapResult`;
- `HIGHER_ORDER_EFFECT_ESCAPE` for `mapErr`;
- `HIGHER_ORDER_EFFECT_ESCAPE` for `andThenResult`;
- all supported helper callbacks accepted when the enclosing function declares
  the needed effect.

Added examples:

- `examples/12_pure_option_result_chaining.aeth`
- `examples/13_effect_aware_helpers.aeth`
- `examples/negative/09_effect_escape_map_option.aeth`
- `examples/negative/10_effect_escape_map_result.aeth`

## 6. Benchmark Tasks

Added benchmark tasks:

- `bench/tasks/t23_map_option_effect_escape/`
- `bench/tasks/t24_map_result_effect_escape/`
- `bench/tasks/t25_map_err_effect_escape/`

The Python equivalents execute callback side effects and exit normally:

- `t23`: prints `audit:1`
- `t24`: prints `audit:2`
- `t25`: prints `audit:bad`

The Aether references are wedge tasks that fail statically with
`HIGHER_ORDER_EFFECT_ESCAPE`.

## 7. Documentation Updates

Updated documentation and prompts to explain:

- named callbacks passed to supported Option/Result helpers propagate effects;
- pure callbacks remain valid in `effects pure` functions;
- effectful callbacks require the enclosing function to declare the escaped
  effect;
- `HIGHER_ORDER_EFFECT_ESCAPE` means the enclosing function has an incomplete
  `effects` clause;
- fixes are to add the effect, pass a pure callback, or move effectful work
  outside the helper.

## 8. Commands Run and Results

| Command | Result | Summary |
|---|---|---|
| `python -B tests\test_higher_order_effects.py` | pass | `HIGHER ORDER EFFECT TESTS PASS` |
| `python -m pytest -q` | pass | `90 passed in 29.09s` |
| `python -B scripts\run_all.py` | pass | reference `10/10`, bench `23/23`, python equivalents `20/20`, regression PASS, additional PASS, fuzz PASS |
| `python -B validation\run_validation.py` | pass | `10/10 validation references pass` |
| `python -B validation\run_python_validation.py` | pass | `10/10 python validation references pass` |
| `python -B tests\test_regressions.py` | pass | `ALL REGRESSION TESTS PASS`; `S-012` skipped because this Windows host lacks `SIGALRM` |
| `python -B tests\test_option_result_helpers.py` | pass | `OPTION RESULT HELPER TESTS PASS` |
| `python -B tests\test_match_exhaustiveness.py` | pass | `MATCH EXHAUSTIVENESS TESTS PASS` |
| `python -m bench.harness run-reference` | pass | `23/23 reference solutions pass` |
| `python -m bench.harness run-python-equivalents` | pass | `20/20 python equivalents pass` |
| `python -m bench.harness run-task t23_map_option_effect_escape --candidate bench\tasks\t23_map_option_effect_escape\reference.aeth` | pass | produced `HIGHER_ORDER_EFFECT_ESCAPE` as expected |
| `python -m bench.harness run-task t24_map_result_effect_escape --candidate bench\tasks\t24_map_result_effect_escape\reference.aeth` | pass | produced `HIGHER_ORDER_EFFECT_ESCAPE` as expected |
| `python -m bench.harness run-task t25_map_err_effect_escape --candidate bench\tasks\t25_map_err_effect_escape\reference.aeth` | pass | produced `HIGHER_ORDER_EFFECT_ESCAPE` as expected |
| `python -B -m transpiler.aether.cli check examples\12_pure_option_result_chaining.aeth` | pass | `OK: examples\12_pure_option_result_chaining.aeth (5 decls)` |
| `python -B -m transpiler.aether.cli run examples\12_pure_option_result_chaining.aeth` | pass | printed `8`, `10` |
| `python -B -m transpiler.aether.cli check examples\13_effect_aware_helpers.aeth` | pass | `OK: examples\13_effect_aware_helpers.aeth (5 decls)` |
| `python -B -m transpiler.aether.cli run examples\13_effect_aware_helpers.aeth` | pass | printed `7`, `9`, `14`, `9` |
| `python -B -m transpiler.aether.cli --json check examples\negative\09_effect_escape_map_option.aeth` | expected failure | JSON diagnostic `HIGHER_ORDER_EFFECT_ESCAPE`, category `effect` |
| `python -B -m transpiler.aether.cli --json check examples\negative\10_effect_escape_map_result.aeth` | expected failure | JSON diagnostic `HIGHER_ORDER_EFFECT_ESCAPE`, category `effect` |
| `git diff --check` | pass | exit code `0`; Git printed CRLF conversion warnings on this Windows host |
| `python3 --version` | environment limitation | `python3` is not installed on this Windows host |

## 9. Remaining Limitations

- Aether is still a research / early compiler prototype.
- The checker handles named callbacks whose function declarations are known.
- Anonymous callback syntax is still unsupported by the parser, so there is no
  lambda effect inference yet.
- Dynamic function-valued parameters remain conservatively unchecked.
- Function types do not yet carry explicit effect rows.
- Runtime source spans remain best effort for some non-contract failures.

## 10. Recommended Next Tasks

1. Add effect annotations to function types if Aether adds first-class function
   values or lambda syntax.
2. Extend effect propagation to future generic collection helpers such as
   `map`, `filter`, and `foldLeft`.
3. Improve runtime call-site span threading for remaining dynamic failures.
4. Add more AI generation benchmarks using saved model outputs from
   Gemini/Claude/GPT.
