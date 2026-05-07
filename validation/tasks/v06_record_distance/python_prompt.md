# Task: squared distance between two records

Declare a frozen dataclass `Point` with integer fields `x` and `y`. Write
`dist_squared(a: Point, b: Point) -> int` returning `(a.x - b.x)^2 +
(a.y - b.y)^2`.

In `main`, print one squared distance per line:

    Point(0, 0) Point(3, 4)
    Point(1, 1) Point(1, 1)
    Point(-2, 0) Point(2, 0)
    Point(5, 5) Point(2, 1)

Expected output:

    25
    0
    16
    25
