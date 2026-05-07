# Task: parse a string to int, double it, return Result

Write `parse_and_double(s: str) -> Result[int, str]` that parses an integer
and, on success, returns `Ok(2 * n)`. On parse failure, propagate an `Err`
with the message format `could not parse Int: 'VALUE'`. Use frozen dataclasses
`Ok` and `Err`.

Then write `describe(r: Result[int, str]) -> str` returning `ok=N` or
`err=MSG`.

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
