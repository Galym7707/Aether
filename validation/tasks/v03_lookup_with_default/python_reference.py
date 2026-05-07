GPA: dict[str, int] = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}


def gpa_of(grade: str) -> int:
    """Effects: pure."""
    return GPA.get(grade, 0)


def main() -> None:
    """Effects: log."""
    print(gpa_of("A"))
    print(gpa_of("C"))
    print(gpa_of("F"))
    print(gpa_of("X"))
    print(gpa_of(""))


if __name__ == "__main__":
    main()
