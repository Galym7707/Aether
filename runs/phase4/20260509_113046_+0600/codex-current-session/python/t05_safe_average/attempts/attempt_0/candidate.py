from dataclasses import dataclass
from typing import Generic, TypeAlias, TypeVar


T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T


@dataclass(frozen=True)
class Err(Generic[E]):
    error: E


Result: TypeAlias = Ok[T] | Err[E]


def average(xs: list[int]) -> Result[int, str]:
    """Effects: pure.

    Requires:
      - len(xs) >= 0
    """
    assert len(xs) >= 0, "requires: length must be non-negative"
    if not xs:
        return Err("empty")
    return Ok(sum(xs) // len(xs))


def describe(result_value: Result[int, str]) -> str:
    """Effects: pure."""
    match result_value:
        case Ok(value):
            return f"ok={value}"
        case Err(message):
            return f"err={message}"
    raise AssertionError("unreachable")


def main() -> None:
    """Effects: log."""
    for xs in ([10, 20, 30], [-5, 5], [], [7], [1, 2, 3, 4]):
        print(describe(average(list(xs))))


if __name__ == "__main__":
    main()
