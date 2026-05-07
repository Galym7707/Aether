# Task: tagged-union arithmetic evaluator

Define an `Enum` named `Op` with cases `ADD`, `SUB`, and `MUL`. Write
`apply(op: Op, a: int, b: int) -> int` that uses `match` or explicit branches
to compute the result.

In `main`, evaluate four expressions and print one per line:

    apply(Op.ADD, 3, 4)
    apply(Op.SUB, 10, 7)
    apply(Op.MUL, 6, 7)
    apply(Op.ADD, -5, 5)

Expected output:

    7
    3
    42
    0
