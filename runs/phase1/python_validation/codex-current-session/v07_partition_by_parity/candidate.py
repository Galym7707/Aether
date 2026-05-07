def partition(xs: list[int]) -> dict[str, list[int]]:
    """Effects: pure."""
    groups: dict[str, list[int]] = {"even": [], "odd": []}
    for x in xs:
        if x % 2 == 0:
            groups["even"].append(x)
        else:
            groups["odd"].append(x)
    return groups


def show_list(xs: list[int]) -> str:
    """Effects: pure."""
    return "[" + ",".join(str(x) for x in xs) + "]"


def render(m: dict[str, list[int]]) -> str:
    """Effects: pure."""
    return f"even={show_list(m['even'])} odd={show_list(m['odd'])}"


def main() -> None:
    """Effects: log."""
    print(render(partition([1, 2, 3, 4, 5])))
    print(render(partition([])))
    print(render(partition([2, 4, 6])))
    print(render(partition([1])))


if __name__ == "__main__":
    main()
