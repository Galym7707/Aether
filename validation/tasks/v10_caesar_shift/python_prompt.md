# Task: Caesar shift on lowercase letters

Write `caesar_char(c: str, k: int) -> str` that shifts a lowercase letter by
`k` positions, wrapping mod 26. For non-letter input, return the character
unchanged. Then `caesar(s: str, k: int) -> str` applies it to the whole string.

Use a small helper that maps each lowercase letter to an index and the inverse
mapping from index back to a letter. Do not use external packages.

In `main`, print one shifted string per line:

    caesar("abc", 1)
    caesar("xyz", 1)
    caesar("hello", 13)
    caesar("hi!", 25)

Expected output:

    bcd
    yza
    uryyb
    gh!
