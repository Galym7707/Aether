# Task: GPA lookup with default

Build a constant dictionary `GPA: dict[str, int]` with the entries `A=4`,
`B=3`, `C=2`, `D=1`, `F=0`. Write `gpa_of(grade: str) -> int` that looks up
the grade and returns the value, defaulting to `0` for unknown grades.

In `main`, print one GPA per line for the inputs:

    "A"
    "C"
    "F"
    "X"
    ""

Expected output:

    4
    2
    0
    0
    0
