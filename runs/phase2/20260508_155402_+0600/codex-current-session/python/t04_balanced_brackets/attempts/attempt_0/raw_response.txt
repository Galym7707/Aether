def balanced(s: str) -> bool:
    """Effects: pure."""
    stack: list[str] = []
    pairs: dict[str, str] = {")": "(", "]": "[", "}": "{"}
    for c in s:
        if c in "([{":
            stack.append(c)
        elif c in pairs:
            if not stack or stack[-1] != pairs[c]:
                return False
            stack.pop()
    return not stack


def show(value: bool) -> str:
    """Effects: pure."""
    return "true" if value else "false"


def main() -> None:
    """Effects: log."""
    tests = ["()", "([])", "{[()]}", "([)]", "(((", "", "abc(def[ghi]jkl)mno", "}"]
    for item in tests:
        print(show(balanced(item)))


if __name__ == "__main__":
    main()
