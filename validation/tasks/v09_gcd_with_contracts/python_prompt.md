# Task: GCD with contracts

Write `gcd(a: int, b: int) -> int` using the Euclidean algorithm.

Required checks:
- precondition assert: `a >= 0 and b >= 0`
- precondition assert: `a > 0 or b > 0`
- postcondition assert: returned result is greater than `0`

Use a `while` loop and `%`. Track two mutable local bindings.

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
