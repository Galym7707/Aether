# Phase 1.1 Sonnet 4.6 — v10_caesar_shift

**Source:** narrative-reported run; raw `candidate.aeth` not on disk
in this session. If candidates are dropped in later, re-grade via
`python3 -B scripts/grade_phase1.py --model sonnet-4-6`.

**First-attempt:** ✗ fail (TOOLING-INDUCED, NOT MODEL ERROR).
**Failure mode:** Trailing null bytes from the workspace-mount truncation
behavior (see SPEC_ISSUES S-010). The model produced correct Aether
source; the file-write step left null padding that broke compilation.
**Diagnostic:** `SyntaxError: source code string cannot contain null bytes`.
**Retry:** ✓ pass after writing the file via bash to bypass the mount issue.
**Classification:** Per the experiment's hard constraint, this is a
**limit-induced** failure (S-010), not a model failure. It should be
excluded from the model-fluency rate.
