def square(x: int) -> int:
    """Effects: pure."""
    return x * x


def is_even(x: int) -> bool:
    """Effects: pure."""
    return x % 2 == 0


def count_even_squares(xs: list[int]) -> int:
    """Effects: pure."""
    return len(list(filter(is_even, map(square, xs))))


def main() -> None:
    """Effects: log."""
    print(count_even_squares([1, 2, 3, 4]))
    print(count_even_squares([1, 3, 5]))
    print(count_even_squares([]))
    print(count_even_squares([2, 2, 2]))


if __name__ == "__main__":
    main()
