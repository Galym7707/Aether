def count_vowels(s: str) -> int:
    """Effects: pure."""
    return sum(1 for c in s.lower() if c in {"a", "e", "i", "o", "u"})


def main() -> None:
    """Effects: log."""
    print(count_vowels("hello"))
    print(count_vowels("AEIOU"))
    print(count_vowels("rhythm"))
    print(count_vowels("The Aether Programming Language"))


if __name__ == "__main__":
    main()
