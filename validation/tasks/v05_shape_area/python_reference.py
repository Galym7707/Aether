from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True)
class Square:
    side: int


@dataclass(frozen=True)
class Rectangle:
    width: int
    height: int


@dataclass(frozen=True)
class Triangle:
    base: int
    height: int


Shape: TypeAlias = Square | Rectangle | Triangle


def area(s: Shape) -> int:
    """Effects: pure."""
    match s:
        case Square(side):
            return side * side
        case Rectangle(width, height):
            return width * height
        case Triangle(base, height):
            return (base * height) // 2
    raise AssertionError("unreachable")


def main() -> None:
    """Effects: log."""
    print(area(Square(4)))
    print(area(Rectangle(3, 5)))
    print(area(Triangle(4, 6)))
    print(area(Square(0)))


if __name__ == "__main__":
    main()
