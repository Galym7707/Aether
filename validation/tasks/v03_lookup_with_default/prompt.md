# Task: GPA lookup with default

Build a `const GPA: Map<String, Int>` with the entries `A=4, B=3, C=2, D=1, F=0`. Write `gpaOf(grade: String) returns Int` that looks up the grade in the map and returns the value, defaulting to `0` for unknown grades. Use the stdlib `get` (returns `Option<V>`) and `unwrapOrElse`.

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
