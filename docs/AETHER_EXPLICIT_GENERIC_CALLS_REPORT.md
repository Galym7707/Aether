# Aether Explicit Generic Calls Report

## Summary

Implemented explicit generic call syntax for the supported generic-function
subset. Aether now accepts calls such as `id<Int>(5)`,
`makeResult<Int, String>(5)`, and `id<List<Int>>([1, 2])`. Existing inferred
generic calls such as `id(5)` still work.

## Files Changed

- `transpiler/aether/parser.py`
- `transpiler/aether/passes/types.py`
- `transpiler/aether/printer.py`
- `transpiler/aether/prelint.py`
- `tests/test_explicit_generic_calls.py`
- `tests/test_generic_typechecking.py`
- `tests/test_prelint_ai_syntax_errors.py`
- `tests/test_ai_repair_diagnostics.py`
- `examples/20_explicit_generic_id.aeth`
- `examples/21_explicit_generic_collections.aeth`
- `examples/negative/15_generic_call_on_non_generic.aeth`
- `examples/negative/16_generic_type_arg_mismatch.aeth`
- `examples/negative/17_generic_type_arg_arity.aeth`
- `bench/tasks/t28_explicit_generic_collection/*`
- `bench/tasks/t29_generic_type_mismatch/*`
- README, grammar, docs, prompt, example-index, benchmark-index, and run-all
  documentation files updated for the new syntax.

## Syntax

Supported:

```aether
id<Int>(5)
choose<Int>(1, 2)
makeResult<Int, String>(5)
id<List<Int>>([1, 2])
id<Result<List<Int>, String>>(value)
```

Unsupported repair forms remain rejected:

- `id[Integer](5)`
- `id::<Int>(5)`
- malformed forms such as `id<Int(5)`

Explicit type arguments are checked statically and erased before runtime.

## Diagnostics

- `GENERIC_CALL_ON_NON_GENERIC`
- `GENERIC_TYPE_ARG_ARITY`
- `GENERIC_TYPE_ARG_MISMATCH`
- `GENERIC_RETURN_TYPE_MISMATCH`

Prelint code `E0008` now targets wrong generic-call spellings and suggests
`f<Int>(x)`.

## Verification Results

Commands run on this checkout:

| Command | Result |
|---|---|
| `python -B tests\test_explicit_generic_calls.py` | pass: `EXPLICIT GENERIC CALL TESTS PASS` |
| `python -B tests\test_generic_typechecking.py` | pass: `GENERIC TYPECHECKING TESTS PASS` |
| `python -B tests\test_regressions.py` | pass: `ALL REGRESSION TESTS PASS` |
| `python -m pytest -q` | pass: `133 passed` |
| `python -B scripts\run_all.py` | pass: references `10/10`, bench `27/27`, python equivalents `24/24`, additional `15 scripts`, fuzz pass |
| `python -B validation\run_validation.py` | pass: `10/10 validation references pass` |
| `python -B validation\run_python_validation.py` | pass: `10/10 python validation references pass` |
| `python -m bench.harness run-reference` | pass: `27/27 reference solutions pass` |
| `python -m bench.harness run-python-equivalents` | pass: `24/24 python equivalents pass` |
| `python -B -m transpiler.aether.cli check examples\20_explicit_generic_id.aeth` | pass |
| `python -B -m transpiler.aether.cli run examples\20_explicit_generic_id.aeth` | pass: prints `5`, `explicit`, `2` |
| `python -B -m transpiler.aether.cli check examples\21_explicit_generic_collections.aeth` | pass |
| `python -B -m transpiler.aether.cli run examples\21_explicit_generic_collections.aeth` | pass: prints `5`, `2`, `7`, `9` |

## Remaining Limitations

Aether is still a research prototype. Explicit generic calls are implemented for
supported user generic functions and container types, but the checker is not a
complete generic inference or proof system. Explicit type arguments are not
runtime values and do not add runtime reflection.

## Follow-Up: Quantifiers And Aggregates

The next pass added list quantifiers and aggregate helpers that compose with the
explicit generic work: `forall x in xs: predicate`, `exists x in xs: predicate`,
`sum(xs)`, `min(xs)`, `max(xs)`, `sorted(xs)`, and
`permutation(xs, ys)`. These features are documented in
`docs/AETHER_QUANTIFIERS_REPORT.md` and covered by
`tests/test_quantifiers_and_aggregates.py`.

## Recommended Next Task

Add richer generic constraint diagnostics and, if needed, support explicit type
arguments on future qualified generic callees.
