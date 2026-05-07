# Task: result-threading parse + range check

Read three lines from stdin. For each line, parse it as an int. If parsing
succeeds and the value is in the inclusive range `[1, 100]`, print `ok=N`.
If parsing fails, print `parse error`. If parsing succeeds but the value is
out of range, print `out of range`.

Use structured `Result[int, str]` style with frozen dataclasses `Ok` and `Err`
end-to-end.

Stdin:

    42
    abc
    150

Expected output:

    ok=42
    parse error
    out of range
