# Phase 1.1 Sonnet 4.6 — v03_lookup_with_default

**Source:** narrative-reported run; raw `candidate.aeth` not on disk
in this session. If candidates are dropped in later, re-grade via
`python3 -B scripts/grade_phase1.py --model sonnet-4-6`.

**First-attempt:** ✗ fail (model error).
**Failure mode:** Used `result` as a local variable name. `result` is
reserved as an Aether keyword (binds the return value inside `ensures`
clauses), so the parser rejected it.
**Diagnostic:** parse error on `let result = ...`.
**Retry:** ✓ pass after renaming to a non-reserved identifier.
**Significance:** validates SPEC_ISSUES S-015 — `result` is reserved
unconditionally and should be contextual to `ensures` clauses. v0.3
should fix this; the current system_prompt.md's common-mistake #9 already
warns about it but a fresh model still tripped on it.
