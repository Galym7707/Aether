from enum import Enum


class Op(Enum):
    ADD = "Add"
    SUB = "Sub"
    MUL = "Mul"


def apply(op: Op, a: int, b: int) -> int:
    """Effects: pure."""
    match op:
        case Op.ADD:
            return a + b
        case Op.SUB:
            return a - b
        case Op.MUL:
            return a * b
    raise AssertionError("unreachable")


def main() -> None:
    """Effects: log."""
    print(apply(Op.ADD, 3, 4))
    print(apply(Op.SUB, 10, 7))
    print(apply(Op.MUL, 6, 7))
    print(apply(Op.ADD, -5, 5))


if __name__ == "__main__":
    main()
