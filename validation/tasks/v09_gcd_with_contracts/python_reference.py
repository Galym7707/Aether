def gcd(a: int, b: int) -> int:
    """Effects: pure.

    Requires:
      - a >= 0 and b >= 0
      - a > 0 or b > 0
    Ensures:
      - result > 0
    """
    assert a >= 0 and b >= 0, "requires: inputs must be non-negative"
    assert a > 0 or b > 0, "requires: at least one input must be positive"
    x = a
    y = b
    while y != 0:
        x, y = y, x % y
    result = x
    assert result > 0, "ensures: result must be positive"
    return result


def main() -> None:
    """Effects: log."""
    print(gcd(54, 24))
    print(gcd(7, 1))
    print(gcd(0, 9))
    print(gcd(48, 18))


if __name__ == "__main__":
    main()
