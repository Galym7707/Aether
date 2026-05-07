from dataclasses import dataclass
from typing import Generic, TypeAlias, TypeVar
import sys


T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T


@dataclass(frozen=True)
class Err(Generic[E]):
    error: E


Result: TypeAlias = Ok[T] | Err[E]


def parse_int(s: str) -> Result[int, str]:
    """Effects: pure."""
    try:
        return Ok(int(s))
    except ValueError:
        return Err("parse error")


def validate(s: str) -> Result[int, str]:
    """Effects: pure."""
    parsed = parse_int(s)
    match parsed:
        case Ok(n):
            if 1 <= n <= 100:
                return Ok(n)
            return Err("out of range")
        case Err(msg):
            return Err(msg)
    raise AssertionError("unreachable")


def describe(result: Result[int, str]) -> str:
    """Effects: pure."""
    match result:
        case Ok(value):
            return f"ok={value}"
        case Err(message):
            return message
    raise AssertionError("unreachable")


def main() -> None:
    """Effects: fs.read, log."""
    for line in sys.stdin.read().splitlines()[:3]:
        print(describe(validate(line)))


if __name__ == "__main__":
    main()
