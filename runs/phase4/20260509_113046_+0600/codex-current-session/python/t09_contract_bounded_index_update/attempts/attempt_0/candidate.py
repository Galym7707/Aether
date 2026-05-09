import sys


def fail_contract(message: str) -> None:
    """Effects: log, panic."""
    sys.stderr.write(message + "\n")
    raise SystemExit(2)


def in_bounds(xs: list[int], index: int) -> bool:
    """Effects: pure."""
    return 0 <= index < len(xs)


def update_at(xs: list[int], index: int, value: int) -> list[int]:
    """Effects: pure.

    Requires:
      - index must be in bounds
    Ensures:
      - output length equals input length
    """
    if not in_bounds(xs, index):
        fail_contract("contract requires index in bounds violation")
    out = list(xs)
    out[index] = value
    assert len(out) == len(xs), "ensures: output length must match input length"
    return out


def main() -> None:
    """Effects: log, panic."""
    update_at([1, 2, 3], 9, 99)


if __name__ == "__main__":
    main()
