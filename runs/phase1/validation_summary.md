# Phase 1.1 — prompt validation results (Sonnet 4.6, canonical)

**Date:** 2026-05-05 (re-grade), original run 2026-05-04
**Model:** claude-sonnet-4-6 (single-model headline)
**Prompt:** `prompt/system_prompt.md` (locked, unchanged)
**Source of record:** `runs/phase1/validation/claude-sonnet-4-6/` —
candidates and grades on disk, independently re-runnable via
`python3 -B -m bench.harness run-task <task_id> --candidate runs/phase1/validation/claude-sonnet-4-6/<task_id>/candidate.aeth`.

## Headline

| Metric | Value | Gate |
|---|---|---|
| Final state (committed candidates re-graded) | **10 / 10 = 100%** | — |
| First-attempt success (raw) | **8 / 10 = 80%** | ≥75% ✓ |
| First-attempt success (limit-adjusted, S-010 tooling excluded) | **8 / 10 = 80%** | ≥75% ✓ |
| Within-2-attempts success | **10 / 10 = 100%** | — |

The limit-adjusted figure is identical to raw because both first-attempt
failures involved S-015 (a real model error). v10 *additionally* hit S-010
(null-byte tooling) on top of its S-015 model error, but that doesn't change
the model-failure count for that task.

## Per-task

| Task | First-attempt | Failure cause | Retry result |
|---|---|---|---|
| v01_tagged_union_evaluator | ✓ | — | — |
| v02_map_filter_chain | ✓ | — | — |
| v03_lookup_with_default | ✗ | S-015: `result` used as variable name | ✓ on retry (renamed to `found`) |
| v04_result_threading | ✓ | — | — |
| v05_shape_area | ✓ | — | — |
| v06_record_distance | ✓ | — | — |
| v07_partition_by_parity | ✓ | — | — |
| v08_parse_and_double | ✓ | — | — |
| v09_gcd_with_contracts | ✓ | — | — |
| v10_caesar_shift | ✗ | S-015: `result` used as variable name; **also** S-010: null-byte file artifact | ✓ on second retry (renamed + bash rewrite) |

## Findings carried forward to EXPERIMENT.md

1. **S-015 fired on 2 of 10 tasks** — stronger evidence than the prior
   single-instance read. Two independent task contexts (both unrelated
   to contracts) led the model to use `result` as a local-variable name.
   The system prompt's common-mistake #9 already warns about it; the
   warning didn't prevent the slip on either task. **This is the
   highest-priority v0.3 fix.** Contextual reservation of `result` only
   inside `ensures` clauses would eliminate this footgun entirely.

2. **S-010 manifested as a real-world failure mode.** v10 hit the
   workspace-mount null-byte truncation that's been logged since the
   project started. It compounded the model error rather than causing
   it independently — the model still made the keyword mistake. But the
   tooling issue meant a second retry was needed even after the keyword
   fix. v0.3 should bake `PYTHONDONTWRITEBYTECODE=1 python3 -B` into
   the CLI launcher so this never bites a downstream user.

3. **The model handles the language semantics correctly.** 8 of 10 tasks
   passed first try without any prompting other than `prompt/system_prompt.md`.
   No structural failures (no parse-error patterns clustering, no effect-
   clause confusion, no record-construction mistakes, no Result/Option
   mix-ups beyond the `result` collision). Tagged unions with payloads,
   match patterns with bindings, contract clauses, HOF chains, Map
   construction with stdlib helpers, Result threading via match — all
   handled cleanly first try.

## Auditability

Anyone can re-run the canonical record:

    cd <project-root>
    python3 -B scripts/grade_phase1.py --model claude-sonnet-4-6

The script walks `runs/phase1/validation/claude-sonnet-4-6/<task>/candidate.aeth`,
runs each through `bench.harness.compile_and_run`, and writes
`<task>/grade.json` plus `_summary.json`. Result: 10/10 ok=true.

Per-task `notes.md` documents the historical first-attempt failures
(both v03 and v10 hit S-015 on first try). The committed `candidate.aeth`
files are the post-fix versions, so re-grading shows 10/10 — that's the
final-state metric, not the first-attempt metric.

## Contamination caveat

This session read the grammar, stdlib, and reference programs before
writing validation candidates. First-attempt pass rates should be read
as **toolchain-acceptance signal under informed authorship**, not clean
fresh-model fluency. A blind run by an external model on the same
prompts would be a stronger gate. Without that, we have what we have,
documented honestly. (Same caveat the run's own `_PREFLIGHT.md` records.)

## Older directories

- `runs/phase1/validation/claude-opus-4-7/` — earlier preflight run by
  the session model; carries the same contamination caveat. Marked
  `_PREFLIGHT.md` as not the canonical Phase 1.1 record.
- `runs/phase1/validation/sonnet-4-6/` — placeholder created during the
  narrative-only phase before actual files were committed. Marked
  `_SUPERSEDED.md`. Workspace mount blocks file deletion, so it remains
  visible; ignore.

## Gate verdict

**Phase 1.1 gate clears at 80% first-attempt ≥ 75% threshold.** Both
documented failure modes are well-understood and have v0.3 fixes
specified. The protocol allows proceeding to Phase 1.2 (5 contract-
wedge tasks + harness extension to grade exit code + stderr).

Stopping here for explicit Phase 1.2 approval per the protocol.
