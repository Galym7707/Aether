# Task: area of a tagged-union shape with payload

Declare frozen dataclasses `Square(side: int)`, `Rectangle(width: int,
height: int)`, and `Triangle(base: int, height: int)`. Define a type alias
`Shape` for their union. Write `area(s: Shape) -> int` that computes the area
using integer division by 2 for triangle.

In `main`, print the area for each shape, one per line:

    Square(4)
    Rectangle(3, 5)
    Triangle(4, 6)
    Square(0)

Expected output:

    16
    15
    12
    0
