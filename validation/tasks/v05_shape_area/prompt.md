# Task: area of a tagged-union shape with payload

Declare a `union Shape` with three cases: `Square(side: Int)`, `Rectangle(width: Int, height: Int)`, and `Triangle(base: Int, height: Int)`. Write `area(s: Shape) returns Int` that pattern-matches over the union and computes the area (use integer division by 2 for triangle).

In `main`, print the area for each shape, one per line:

    Shape.Square(4)
    Shape.Rectangle(3, 5)
    Shape.Triangle(4, 6)
    Shape.Square(0)

Expected output:

    16
    15
    12
    0
