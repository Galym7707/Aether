# Phase 1.3 Self-Judge Audit Summary After t06 Replacement

Status: gate green for the approved self-judge audit protocol override.

## Protocol Note

The original Phase 1.3 default judge was Gemini 2.5 Pro. This run uses the
explicit user-approved override: current Codex/GPT acted as the judge model
because no Gemini API key was available in the environment.

These self-judge outputs must not be used as generation hints for later
candidate-production phases.

## Corpus

- Active programs: `28`
- Reference programs: `10`
- Benchmark programs: `8`
- Active validation programs: `10`
- Unordered pairs: `378`
- Directional judgments: `756`

Task replacement applied before this run:

```text
bench:t06_contract_non_empty_average -> bench:t06_contract_non_empty_minimum
```

Raw directional JSON files are saved under:

```text
audits\judge_results\phase1_3_self_judge_after_t06_replacement\raw\
```

Summary JSON:

```text
audits\judge_results\phase1_3_self_judge_after_t06_replacement\summary.json
```

## Findings

New same-problem pairs at confidence `>= 0.7`: `0`.

Manual-review pairs: `0`.

Known same-problem pairs not counted as new:

| Pair | Reason |
|---|---|
| `ref:02_factorial_recursive` ↔ `ref:03_factorial_iterative` | Already known duplicate problem implemented with recursive vs iterative technique. |

## Gate Result

Phase 1.3 is green under the approved self-judge protocol override.
