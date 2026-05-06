# Task: tagged-union arithmetic evaluator

Define a `union Op` with three cases (no payloads): `Add`, `Sub`, `Mul`. Write `apply(op: Op, a: Int, b: Int) returns Int` that uses `match` to compute the result. Use the qualified-constructor form `Op.Add()` etc. when constructing the union values.

In `main`, evaluate four expressions and print one per line:

    apply(Op.Add(), 3, 4)
    apply(Op.Sub(), 10, 7)
    apply(Op.Mul(), 6, 7)
    apply(Op.Add(), -5, 5)

Expected output:

    7
    3
    42
    0
