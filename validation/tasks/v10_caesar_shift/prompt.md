# Task: Caesar shift on lowercase letters

Write `caesarChar(c: String, k: Int) returns String` that shifts a lowercase letter by k positions (wrapping mod 26). For non-letter input, return the character unchanged. Then `caesar(s: String, k: Int) returns String` applies it to the whole string.

Hint: there's no character/code-point primitive in v0.1, so use a small helper that maps each of the 26 lowercase letters via a constant lookup list and returns the index, then the inverse to map an index back to a letter.

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
