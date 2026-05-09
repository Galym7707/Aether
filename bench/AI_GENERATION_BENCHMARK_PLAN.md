# AI Generation Benchmark Plan

This is a plan for testing Gemini, Claude, GPT, and other models on Aether
generation. It defines evaluation tasks and metrics. It does not report
benchmark results.

## Tasks

| # | Task | Required idea |
|---|---|---|
| 1 | safeDivide | `requires b != 0`; pure integer division |
| 2 | safeAverage | non-empty list contract or refinement |
| 3 | safeMedian | non-empty sorted list precondition |
| 4 | sortedBinarySearch | `sorted?` helper and bounded result |
| 5 | boundedIndexUpdate | rebuild list with `append`; no item assignment |
| 6 | normalizeWeights | non-empty, non-negative, positive total |
| 7 | transferFunds | account balance precondition; no negative transfer |
| 8 | pure function effect test | pure helper must not call `print` |
| 9 | validEmail refinement | refinement or predicate-guarded email string |
| 10 | safeSlice | valid `lo`/`hi` bounds over a string or list |

## Metrics

Score each generated candidate with 0 or 1 for each criterion:

| Criterion | Score 1 means |
|---|---|
| syntax validity | `aether check candidate.aeth` parses and compiles |
| check success | positive task passes `check` |
| run success | positive task runs and prints expected output |
| uses contracts correctly | invalid inputs are guarded with `requires`, `ensures`, or refinements |
| catches invalid input | negative smoke test produces a structured diagnostic |
| uses effects correctly | pure helpers use `effects pure`; printing uses `effects log` |
| avoids unsupported syntax | no `fn`, `->`, `List[Int]`, `.len()`, braces, lambdas, or list item assignment |
| repair success after diagnostic | after one diagnostic prompt, revised code passes the task |

Maximum score per task: 8.

## Commands

Check a candidate:

```bash
aether check candidate.aeth
```

Run a candidate:

```bash
aether run candidate.aeth
```

Fallback without installation:

```bash
python -B -m transpiler.aether.cli check candidate.aeth
python -B -m transpiler.aether.cli run candidate.aeth
```

JSON diagnostics for repair:

```bash
aether --json check candidate.aeth
aether --json run candidate.aeth
```

## Saving Model Outputs

Use this layout:

```text
runs/ai_generation/<date>/<model>/<task_id>/attempt_0/candidate.aeth
runs/ai_generation/<date>/<model>/<task_id>/attempt_0/prompt.txt
runs/ai_generation/<date>/<model>/<task_id>/attempt_0/check.json
runs/ai_generation/<date>/<model>/<task_id>/attempt_0/run.json
runs/ai_generation/<date>/<model>/<task_id>/attempt_1/candidate.aeth
```

For each attempt, save:

- exact model name
- exact prompt
- raw model output
- extracted Aether file
- `aether --json check` result
- `aether --json run` result
- whether a repair prompt was used

## Result Table Template

| Model | Task | Attempt | Syntax | Check | Run | Contracts | Invalid Input | Effects | Avoids Unsupported Syntax | Repair Success | Total |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gemini | safeDivide | 0 |  |  |  |  |  |  |  |  |  |
| Claude | safeDivide | 0 |  |  |  |  |  |  |  |  |  |
| GPT | safeDivide | 0 |  |  |  |  |  |  |  |  |  |

Do not claim a model result unless the exact candidate and command outputs are
saved.
