# Task: GCD with contracts

Write `gcd(a: Int, b: Int) returns Int` using the Euclidean algorithm.

Required clauses:
- `requires a >= 0 and b >= 0`
- `requires a > 0 or b > 0`
- `ensures result > 0`
- `effects pure`

Use `while` and the `%` operator. Track two mutable bindings.

In `main`, print one result per line:

    gcd(54, 24)
    gcd(7, 1)
    gcd(0, 9)
    gcd(48, 18)

Expected output:

    6
    1
    9
    6
