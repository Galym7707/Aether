# Task: squared distance between two records

Declare a `record Point` with integer fields `x` and `y`. Write `distSquared(a: Point, b: Point) returns Int` returning `(a.x - b.x)^2 + (a.y - b.y)^2`. Use `Point(x, y)` positional construction.

In `main`, print one squared distance per line:

    Point(0,0) Point(3,4)
    Point(1,1) Point(1,1)
    Point(-2,0) Point(2,0)
    Point(5,5) Point(2,1)

Expected output:

    25
    0
    16
    25
