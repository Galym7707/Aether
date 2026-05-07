# Task: contract sorted binary search

Write an Aether function `binarySearch(xs: List<Int>, target: Int) returns Int`
that requires `sorted?(xs)` before running binary search.

The reference program must call `binarySearch([1, 10, 5], 5)` in `main`. This
input is intentionally invalid because the list is not sorted. The desired
benchmark behavior is for Aether to reject the input with a structured contract
diagnostic instead of returning the misleading search result.

Expected benchmark behavior:

    stdout: ""
    exit_code: 2
    stderr matches: (?i)(contract|requires|precondition).*sorted
