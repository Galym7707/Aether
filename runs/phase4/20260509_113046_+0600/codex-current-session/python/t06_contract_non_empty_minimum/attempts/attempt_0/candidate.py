import sys


def fail_contract(message: str) -> None:
    """Effects: log, panic."""
    sys.stderr.write(message + "\n")
    raise SystemExit(2)


def minimum(xs: list[int]) -> int:
    """Effects: pure.

    Requires:
      - list must be non-empty
    """
    if not xs:
        fail_contract("contract requires non-empty list violation")
    return min(xs)


def main() -> None:
    """Effects: log, panic."""
    minimum([])


if __name__ == "__main__":
    main()
