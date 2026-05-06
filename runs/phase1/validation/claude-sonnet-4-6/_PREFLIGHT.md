# Preflight — claude-sonnet-4-6 validation run

## Conditions

- **Model:** claude-sonnet-4-6 (self-reported; running inside Cowork/Aether session)
- **Run date:** 2026-05-05
- **Harness:** `validation/run_validation.py` + `bench/harness.py` (unchanged from reference run)
- **Tasks:** v01–v10 from `validation/tasks/` (5 deprecated tasks skipped)
- **Isolation:** Candidates were written fresh in this session and graded via
  the same `grade_task` path used for the reference solutions. The model had
  read the task `prompt.md` and `grader.json` files but did NOT read the
  `reference.aeth` files before writing candidates.

## What is verifiable

- `candidate.aeth` — the exact bytes submitted to the harness; re-runnable at any time:
  ```
  python3 -m bench.harness run-task <task_id> \
      --candidate runs/phase1/validation/claude-sonnet-4-6/<task_id>/candidate.aeth
  ```
- `grade.json` — output of the harness for that candidate; reproducible from the file above.

## What requires trust

- The claim that candidates were written without reading `reference.aeth`.
  There is no tooling in v0.1 to enforce or log which files the model accessed
  during the session. A reviewer must take this on faith unless the session
  transcript is audited separately.

## Known issues encountered

| Code  | Task | Description |
|-------|------|-------------|
| E0201 | v03  | `result` used as variable name — reserved keyword collision |
| E0201 | v10  | `result` used as variable name — reserved keyword collision |
| E0101 | v10  | Trailing null bytes from in-place Edit tool; fixed by full rewrite via bash |

Both issues were diagnosed from harness output and corrected within the same
session. The `candidate.aeth` files on disk reflect the corrected versions.
The first-attempt files are not preserved (no snapshot was taken before the fix).

## Comparison to claude-opus-4-7 run

The opus-4-7 run (`runs/phase1/validation/claude-opus-4-7/`) notes that the
author of those candidates was the same session that authored the reference
solutions — a significant contamination caveat. The sonnet-4-6 run has the
same caveat: this session read the grammar, stdlib, and several reference
programs from `reference/` before writing the validation candidates. First-
attempt pass rates should be read as toolchain-acceptance signal, not as
clean fluency measurements.
