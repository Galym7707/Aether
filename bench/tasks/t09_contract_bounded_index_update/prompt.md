# Task: contract bounded index update

Write an Aether function `updateAt(xs: List<Int>, index: Int, value: Int)
returns List<Int>` that requires `inBounds?(xs, index)` and preserves the input
list length.

The reference program must call `updateAt([1, 2, 3], 9, 99)` in `main`. This is
intentionally invalid input because index `9` is out of bounds. The desired
benchmark behavior is for Aether to reject the invalid index with a structured
contract diagnostic.

Expected benchmark behavior:

    stdout: ""
    exit_code: 2
    stderr matches: (?i)(contract|requires|precondition).*(index|bounds|inBounds)
