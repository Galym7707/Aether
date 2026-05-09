# Aether Examples

These examples are intentionally small. They are the best files for AI models
to imitate when generating Aether code.

## Positive Examples

Run `check` on every positive example:

```powershell
python -B -m transpiler.aether.cli check examples\01_safe_divide.aeth
python -B -m transpiler.aether.cli check examples\02_non_empty_average.aeth
python -B -m transpiler.aether.cli check examples\03_sorted_binary_search.aeth
python -B -m transpiler.aether.cli check examples\04_bounded_index_update.aeth
python -B -m transpiler.aether.cli check examples\05_safe_normalize_weights.aeth
python -B -m transpiler.aether.cli check examples\06_safe_at.aeth
python -B -m transpiler.aether.cli check examples\07_update_at.aeth
python -B -m transpiler.aether.cli check examples\08_safe_slice.aeth
```

Run a few examples:

```powershell
python -B -m transpiler.aether.cli run examples\01_safe_divide.aeth
python -B -m transpiler.aether.cli run examples\06_safe_at.aeth
python -B -m transpiler.aether.cli run examples\07_update_at.aeth
python -B -m transpiler.aether.cli run examples\08_safe_slice.aeth
```

Expected output from those commands, in order:

```text
5
20
none
99
index out of bounds
2:20,30
slice bounds out of range
```

## Negative Examples

Negative examples are under `examples/negative/`. They are supposed to fail.

```powershell
python -B -m transpiler.aether.cli --json run examples\negative\01_empty_average_contract.aeth
python -B -m transpiler.aether.cli --json check examples\negative\02_bad_update_at_type.aeth
python -B -m transpiler.aether.cli --json check examples\negative\03_bad_safe_slice_bounds_type.aeth
python -B -m transpiler.aether.cli --json check examples\negative\06_effect_violation_demo.aeth
```

Expected diagnostics:

| File | Command | Expected diagnostic |
|---|---|---|
| `negative/01_empty_average_contract.aeth` | `run` | `E0302`, category `refinement` |
| `negative/02_bad_update_at_type.aeth` | `check` | `LIST_HELPER_VALUE_TYPE`, category `type` |
| `negative/03_bad_safe_slice_bounds_type.aeth` | `check` | `LIST_HELPER_BOUND_TYPE`, category `type` |
| `negative/06_effect_violation_demo.aeth` | `check` | `E0801`, category `effect` |

## Best Files For AI Imitation

Start with:

1. `01_safe_divide.aeth`
2. `02_non_empty_average.aeth`
3. `06_safe_at.aeth`
4. `07_update_at.aeth`
5. `08_safe_slice.aeth`
6. `05_safe_normalize_weights.aeth`

Avoid copying from `examples/negative/` unless you are intentionally writing a
program that demonstrates a diagnostic.
