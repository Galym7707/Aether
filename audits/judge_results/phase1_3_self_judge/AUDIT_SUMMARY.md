# Phase 1.3 Self-Judge Audit Summary

Status: gate failed because one new same-problem pair was found.

## Protocol Note

The original Phase 1.3 default judge was Gemini 2.5 Pro. The run in this
directory uses an explicit user-approved override: current Codex/GPT acted as
the judge model because no Gemini API key was available in the environment.

These self-judge outputs must not be used as generation hints for later
candidate-production phases.

## Corpus

- Active programs: `28`
- Reference programs: `10`
- Benchmark programs: `8`
- Active validation programs: `10`
- Unordered pairs: `378`
- Directional judgments: `756`

Raw directional JSON files are saved under:

```text
audits\judge_results\phase1_3_self_judge\raw\
```

Summary JSON:

```text
audits\judge_results\phase1_3_self_judge\summary.json
```

## Findings

New same-problem pairs at confidence `>= 0.7`:

| Pair | Directional confidence | Reason |
|---|---:|---|
| `bench:t05_safe_average` ↔ `bench:t06_contract_non_empty_average` | `0.84` / `0.84` | Both compute integer average over a list of integers; they mainly differ in how empty input is handled. |

Manual-review pairs: `0`.

Known same-problem pairs not counted as new:

| Pair | Reason |
|---|---|
| `ref:02_factorial_recursive` ↔ `ref:03_factorial_iterative` | Already known duplicate problem implemented with recursive vs iterative technique. |

## Gate Result

Phase 1.3 gate is not green. The protocol says to stop and propose
replacements when new contamination is found.

## Replacement Proposal

Recommended minimal replacement:

1. Replace `bench:t06_contract_non_empty_average` with a non-empty contract
   task that is not an average task.
2. Keep the same wedge pattern: Python silently accepts invalid empty input,
   while Aether rejects it through a refinement or requires clause.
3. Suggested replacement task: `t06_contract_non_empty_minimum`.

Why this replacement:

- It still tests a non-empty-list contract.
- It avoids duplicating `bench:t05_safe_average`.
- The Python equivalent can silently return a misleading sentinel such as `0`
  for an empty list.
- The Aether solution can use `type NonEmptyIntList = List<Int> where
  length(self) > 0` and compute a minimum only after the boundary check.

Alternative:

- Replace the older `bench:t05_safe_average` standard task instead. This is more
  invasive because it changes an existing benchmark task rather than the newly
  added wedge task.
