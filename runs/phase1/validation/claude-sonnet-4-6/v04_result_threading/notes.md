# v04 — result-threading parse + range check

**Status:** PASS (first attempt)

Factored repeated read-validate-print into a `processLine()` helper to
avoid duplicating the `match readLine()` block three times. Logic:
`parseInt` → match Ok/Err → range check → describe → print.
