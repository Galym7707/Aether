# v08 — parse and double

**Status:** PASS (first attempt)

`parseAndDouble` matches on `parseInt(s)` and returns `Ok(2 * n)` or
propagates the `Err`. `describe` produces `ok=N` or `err=MSG` via `join`.
The exact error message format (`could not parse Int: 'hello'`) is
determined by the runtime's `parseInt` implementation — matched without
modification.
