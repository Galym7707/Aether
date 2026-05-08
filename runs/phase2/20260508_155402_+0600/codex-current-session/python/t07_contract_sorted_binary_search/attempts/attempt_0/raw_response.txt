import sys


def fail_contract(message: str) -> None:
    """Effects: log, panic."""
    sys.stderr.write(message + "\n")
    raise SystemExit(2)


def is_sorted(xs: list[int]) -> bool:
    """Effects: pure."""
    return all(xs[i - 1] <= xs[i] for i in range(1, len(xs)))


def binary_search(xs: list[int], target: int) -> int:
    """Effects: pure.

    Requires:
      - input must be sorted
    """
    if not is_sorted(xs):
        fail_contract("contract requires sorted input violation")
    lo = 0
    hi = len(xs) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if xs[mid] == target:
            return mid
        if xs[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def main() -> None:
    """Effects: log, panic."""
    binary_search([1, 10, 5], 5)


if __name__ == "__main__":
    main()
