from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    x: int
    y: int


def dist_squared(a: Point, b: Point) -> int:
    """Effects: pure."""
    dx = a.x - b.x
    dy = a.y - b.y
    return dx * dx + dy * dy


def main() -> None:
    """Effects: log."""
    print(dist_squared(Point(0, 0), Point(3, 4)))
    print(dist_squared(Point(1, 1), Point(1, 1)))
    print(dist_squared(Point(-2, 0), Point(2, 0)))
    print(dist_squared(Point(5, 5), Point(2, 1)))


if __name__ == "__main__":
    main()
