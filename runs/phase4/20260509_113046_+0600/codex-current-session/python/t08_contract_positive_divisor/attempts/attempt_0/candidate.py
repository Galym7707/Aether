import sys


def fail_contract(message: str) -> None:
    """Effects: log, panic."""
    sys.stderr.write(message + "\n")
    raise SystemExit(2)


def safe_ratio(numerator: int, denominator: int) -> int:
    """Effects: pure.

    Requires:
      - denominator must be a positive divisor
    """
    if denominator <= 0:
        fail_contract("contract requires positive divisor denominator violation")
    return numerator // denominator


def main() -> None:
    """Effects: log, panic."""
    safe_ratio(10, 0)


if __name__ == "__main__":
    main()
