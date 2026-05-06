# Task: result-threading parse + range check

Read three lines from stdin. For each line, parse it as an Int. If parsing succeeds AND the value is in the inclusive range `[1, 100]`, print `ok=N` (with N being the parsed value). If parsing fails, print `parse error`. If parsing succeeds but the value is out of range, print `out of range`.

Use `Result<Int, String>` end-to-end:
- `parseInt` returns `Result<Int, String>`. `match` it.
- On `Ok(n)`, check the range; return `Ok(n)` or a fresh `Err".
- On `Err`, propagate as a parse error.

Stdin:

    42
    abc
    150

Expected output:

    ok=42
    parse error
    out of range
