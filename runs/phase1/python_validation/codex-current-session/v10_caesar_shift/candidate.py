ALPHA: list[str] = list("abcdefghijklmnopqrstuvwxyz")


def letter_index(c: str) -> int:
    """Effects: pure."""
    try:
        return ALPHA.index(c)
    except ValueError:
        return -1


def caesar_char(c: str, k: int) -> str:
    """Effects: pure."""
    idx = letter_index(c)
    if idx < 0:
        return c
    return ALPHA[(idx + k) % 26]


def caesar(s: str, k: int) -> str:
    """Effects: pure."""
    return "".join(caesar_char(c, k) for c in s)


def main() -> None:
    """Effects: log."""
    print(caesar("abc", 1))
    print(caesar("xyz", 1))
    print(caesar("hello", 13))
    print(caesar("hi!", 25))


if __name__ == "__main__":
    main()
