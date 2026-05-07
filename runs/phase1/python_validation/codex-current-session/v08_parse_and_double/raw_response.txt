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


def parse_int(s: str) -> Result[int, str]:
    """Effects: pure."""
    try:
        return Ok(int(s))
    except ValueError:
        return Err(f"could not parse Int: {s!r}")


def parse_and_double(s: str) -> Result[int, str]:
    """Effects: pure."""
    parsed = parse_int(s)
    match parsed:
        case Ok(n):
            return Ok(2 * n)
        case Err(msg):
            return Err(msg)
    raise AssertionError("unreachable")


def describe(result: Result[int, str]) -> str:
    """Effects: pure."""
    match result:
        case Ok(value):
            return f"ok={value}"
        case Err(message):
            return f"err={message}"
    raise AssertionError("unreachable")


def main() -> None:
    """Effects: log."""
    print(describe(parse_and_double("21")))
    print(describe(parse_and_double("-5")))
    print(describe(parse_and_double("hello")))
    print(describe(parse_and_double("0")))
    print(describe(parse_and_double("")))


if __name__ == "__main__":
    main()
