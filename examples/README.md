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
```

Run one example:

```powershell
python -B -m transpiler.aether.cli run examples\01_safe_divide.aeth
```

Expected output:

```text
5
```

## Negative Examples

Negative examples are under `examples/negative/`. They are supposed to fail.

```powershell
python -B -m transpiler.aether.cli --json run examples\negative\01_empty_average_contract.aeth
python -B -m transpiler.aether.cli --json check examples\negative\06_effect_violation_demo.aeth
```

Expected diagnostics:

| File | Command | Expected diagnostic |
|---|---|---|
| `negative/01_empty_average_contract.aeth` | `run` | `E0302`, category `refinement` |
| `negative/06_effect_violation_demo.aeth` | `check` | `E0801`, category `effect` |

## Best Files For AI Imitation

Start with:

1. `01_safe_divide.aeth`
2. `02_non_empty_average.aeth`
3. `04_bounded_index_update.aeth`
4. `05_safe_normalize_weights.aeth`

Avoid copying from `examples/negative/` unless you are intentionally writing a
program that demonstrates a diagnostic.
