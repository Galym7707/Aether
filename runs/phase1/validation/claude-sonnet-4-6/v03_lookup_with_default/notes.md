# v03 — GPA lookup with default

**Status:** PASS (second attempt — one fix required)

**First attempt failure:** Used `result` as the local variable name for
the `Option<Int>` returned by `get`. `result` is a reserved keyword in
Aether (bound in `ensures result == ...` contract clauses). The parser
raised E0201 at that token.

**Fix:** Renamed the binding to `found`. No logic change.

The `result` keyword collision is a genuine footgun: the name is
unremarkable in any other language. Noted in SPEC_ISSUES for v0.2.
