# Task: parse a string to Int, double it, return Result

Write `parseAndDouble(s: String) returns Result<Int, String>` that calls `parseInt(s)` and, on success, returns `Ok(2 * n)`. On parse failure, propagate the `Err`. Use `match` to destructure.

Then write `describe(r: Result<Int, String>) returns String` returning `ok=N` or `err=MSG`.

In `main`, print the description for each input, one per line:

    "21"
    "-5"
    "hello"
    "0"
    ""

Expected output:

    ok=42
    ok=-10
    err=could not parse Int: 'hello'
    ok=0
    err=could not parse Int: ''
