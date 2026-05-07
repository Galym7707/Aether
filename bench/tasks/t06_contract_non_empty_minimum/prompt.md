# Task: contract non-empty minimum

Write an Aether function `minimum(xs: NonEmptyIntList) returns Int` where
`NonEmptyIntList` is a refinement type requiring `length(self) > 0`.

The reference program must call `minimum([])` in `main`. This is intentionally
invalid input: the correct benchmark behavior is for Aether to reject the empty
list with a structured refinement or contract diagnostic rather than printing a
sentinel minimum value.

Expected benchmark behavior:

    stdout: ""
    exit_code: 2
    stderr matches: (?i)(refinement|contract).*non.?empty
