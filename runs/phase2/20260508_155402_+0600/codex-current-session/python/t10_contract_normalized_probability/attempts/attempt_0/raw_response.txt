import sys


def fail_contract(message: str) -> None:
    """Effects: log, panic."""
    sys.stderr.write(message + "\n")
    raise SystemExit(2)


def valid_weights(weights: list[int]) -> bool:
    """Effects: pure."""
    return bool(weights) and all(w >= 0 for w in weights) and sum(weights) == 100


def choose_bucket(weights: list[int], threshold: int) -> int:
    """Effects: pure.

    Requires:
      - probability weights are non-empty, non-negative, and normalized to 100
    """
    if not valid_weights(weights):
        fail_contract("contract requires probability weight normalization violation")
    cumulative = 0
    for index, weight in enumerate(weights):
        cumulative += weight
        if threshold < cumulative:
            return index
    return len(weights) - 1


def main() -> None:
    """Effects: log, panic."""
    choose_bucket([50, -20, 70], 25)


if __name__ == "__main__":
    main()
