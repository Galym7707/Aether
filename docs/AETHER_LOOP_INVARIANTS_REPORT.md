# Aether Loop Invariants And Record Updates Report

## Summary

This pass adds prototype support for annotated `while` loops and record
copy-update expressions. Aether remains a research prototype, not a production
language or complete verifier.

## Implemented Syntax

```aether
while condition
invariant boolExpression
variant intExpression
do
  ...
end
```

`invariant` clauses are checked before the loop and after each completed
iteration. `variant` is evaluated before the loop and after each completed
iteration; it must strictly decrease.

Range expressions are supported as half-open `List<Int>` values:

```aether
forall i in 0..length(xs) - 1: xs[i] <= xs[i + 1]
```

Record update syntax copies an existing record:

```aether
let updated: Account = account { balance = account.balance + amount }
```

It does not create records from field literals; positional constructors remain
the supported construction syntax.

## Compiler And Runtime Changes

- Lexer recognizes `invariant`, `variant`, and `..`.
- Parser stores loop annotations on `While` AST nodes.
- Parser stores `RangeExpr` and `RecordUpdate` expression nodes.
- Printer and `aether ast` preserve the new AST fields.
- Type checker validates invariant `Bool`, variant `Int`, range `Int` bounds,
  and record update field names/types.
- SMT pass proves simple arithmetic variant decreases when supported and emits
  `LOOP_VARIANT_NOT_DECREASING_STATIC` when it can disprove decrease.
- Runtime fallback emits `LOOP_INVARIANT_FAILED`,
  `LOOP_VARIANT_NOT_DECREASING`, and record update diagnostics instead of
  Python tracebacks.

## Examples Added

- `examples/24_loop_invariant_bubble_sort.aeth`
- `examples/25_record_update.aeth`

## Tests Added

- `tests/test_loop_invariants_and_records.py`

The test covers passing loop annotations, range quantifiers, AST preservation,
runtime invariant diagnostics, static and runtime variant diagnostics, record
copy-update behavior, and record field type diagnostics.

## Verification

Commands run on Windows with `python`:

| Command | Result |
|---|---|
| `python -B tests\test_loop_invariants_and_records.py` | pass |
| `python -B tests\test_quantifiers_and_aggregates.py` | pass |
| `python -B tests\test_regressions.py` | pass |
| `python -m pytest -q` | pass, 151 tests |
| `python -B scripts\run_all.py` | pass, 10/10 references, 29/29 benchmark references, 26/26 Python equivalents, 17 additional test scripts, parser fuzz pass |
| `python -B validation\run_validation.py` | pass, 10/10 validation references |
| `python -B validation\run_python_validation.py` | pass, 10/10 Python validation references |
| `python -m bench.harness run-reference` | pass, 29/29 reference solutions |
| `python -m bench.harness run-python-equivalents` | pass, 26/26 Python equivalents |
| `python -B -m transpiler.aether.cli check examples\24_loop_invariant_bubble_sort.aeth` | pass |
| `python -B -m transpiler.aether.cli run examples\24_loop_invariant_bubble_sort.aeth` | pass, prints `1`, `2`, `3` |
| `python -B -m transpiler.aether.cli check examples\25_record_update.aeth` | pass |
| `python -B -m transpiler.aether.cli run examples\25_record_update.aeth` | pass, prints `100`, `125` |
| `git diff --check` | pass; Git reported line-ending conversion warnings only |

## Remaining Limitations

- The SMT fragment is intentionally small. It handles simple arithmetic
  decreases and literal/range quantifier cases, not full loop verification.
- Runtime loop checks run after normal loop-body execution and before
  `continue` jumps to the next iteration.
- Invariants over dynamic collections are mostly runtime checks.
- Record literals are now implemented in the follow-up pass. They require every
  declared field and no extra fields.

## Recommended Next Task

Thread loop source-span metadata through more runtime paths and broaden the SMT
loop fragment beyond simple arithmetic decreases.
