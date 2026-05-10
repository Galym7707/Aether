# Aether Effect Row Precision Report

## 1. Summary

This pass implemented precise checking for supported argumented effects,
focused on `net.fetch("...")` rows. Aether still remains a research prototype,
but direct calls, function-typed callbacks, and named callbacks passed to the
implemented Option/Result helpers now use the same effect-row coverage rules.

## 2. Files Changed

- `transpiler/aether/passes/effects.py`
- `transpiler/aether/passes/types.py`
- `transpiler/aether/runtime.py`
- `tests/test_effect_row_precision.py`
- existing effect/type diagnostic tests
- `examples/15_effect_row_precision_direct.aeth`
- `examples/16_effect_row_precision_function_type.aeth`
- `examples/17_effect_row_precision_option_result.aeth`
- `examples/negative/12_effect_row_direct_mismatch.aeth`
- `examples/negative/13_function_type_effect_mismatch.aeth`
- `examples/negative/14_helper_effect_row_escape.aeth`
- `bench/tasks/t26_effect_row_direct_mismatch/`
- `bench/tasks/t27_effect_row_callback_mismatch/`
- README, grammar docs, language guide, feature matrix, prompts, benchmark docs

## 3. Effect Coverage Rules

- `pure` is bottom and is represented as no effects.
- `log` covers only `log`.
- `fs.read` covers only `fs.read`.
- `fs.write` covers only `fs.write`.
- `net.fetch` covers every argumented `net.fetch("...")`.
- `net.fetch("*")` covers every argumented fetch.
- `net.fetch("https://api.example.com/*")` covers matching URL prefixes.
- Concrete URL rows cover only the exact same URL.
- A narrower caller row does not cover a broader callee row.

## 4. Diagnostics

- Direct-call effect mismatch: `EFFECT_NOT_COVERED`.
- Function type callback mismatch: `FUNCTION_TYPE_EFFECT_MISMATCH`.
- Option/Result helper callback escape: `HIGHER_ORDER_EFFECT_ESCAPE`.

Diagnostics include the caller, callee or callback/helper name, required or
escaped effect, declared caller effects where applicable, source position,
source snippet, and a repair hint.

## 5. Examples and Benchmarks

Positive examples:

- `examples/15_effect_row_precision_direct.aeth`
- `examples/16_effect_row_precision_function_type.aeth`
- `examples/17_effect_row_precision_option_result.aeth`

Negative examples:

- `examples/negative/12_effect_row_direct_mismatch.aeth`
- `examples/negative/13_function_type_effect_mismatch.aeth`
- `examples/negative/14_helper_effect_row_escape.aeth`

Benchmark tasks:

- `bench/tasks/t26_effect_row_direct_mismatch/`
- `bench/tasks/t27_effect_row_callback_mismatch/`

## 6. Verification Results

| Command | Result | Summary |
|---|---|---|
| `python -B tests\test_effect_row_precision.py` | pass | `EFFECT ROW PRECISION TESTS PASS` |
| `python -B tests\test_higher_order_effects.py` | pass | `HIGHER ORDER EFFECT TESTS PASS` |
| `python -B tests\test_function_type_effects.py` | pass | `FUNCTION TYPE EFFECT TESTS PASS` |
| `python -B tests\test_regressions.py` | pass | `ALL REGRESSION TESTS PASS`; canonical AST round-trip covered `50` corpus programs |
| `python -m pytest -q` | pass | `112 passed in 9.00s` |
| `python -B scripts\run_all.py` | pass | reference `10/10`, bench `25/25`, Python equivalents `22/22`, regression PASS, additional PASS, fuzz PASS |
| `python -B validation\run_validation.py` | pass | `10/10 validation references pass` |
| `python -B validation\run_python_validation.py` | pass | `10/10 python validation references pass` |
| `python -m bench.harness run-reference` | pass | `25/25 reference solutions pass` |
| `python -m bench.harness run-python-equivalents` | pass | `22/22 python equivalents pass` |
| `python -B -m transpiler.aether.cli check examples\15_effect_row_precision_direct.aeth` | pass | `OK` |
| `python -B -m transpiler.aether.cli check examples\16_effect_row_precision_function_type.aeth` | pass | `OK` |
| `python -B -m transpiler.aether.cli check examples\17_effect_row_precision_option_result.aeth` | pass | `OK` |
| `python -B -m transpiler.aether.cli --json check examples\negative\12_effect_row_direct_mismatch.aeth` | expected failure | `EFFECT_NOT_COVERED` |
| `python -B -m transpiler.aether.cli --json check examples\negative\13_function_type_effect_mismatch.aeth` | expected failure | `FUNCTION_TYPE_EFFECT_MISMATCH` |
| `python -B -m transpiler.aether.cli --json check examples\negative\14_helper_effect_row_escape.aeth` | expected failure | `HIGHER_ORDER_EFFECT_ESCAPE` |

## 7. Remaining Limitations

- Effect-row precision is implemented for the supported string-literal
  `net.fetch("...")` cases, not a general symbolic effect algebra.
- Unknown or dynamic callback values remain conservatively limited.
- Lambda syntax is still unsupported.
- Runtime source spans remain best effort for some dynamic failures.
- Aether is not production-ready.

## 8. Recommended Next Task

Add richer effect metadata for future standard-library operations such as
`db.read(...)`, `db.write(...)`, and file paths, using the same small,
testable row-coverage model.
