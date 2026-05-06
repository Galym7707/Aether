# Task: safe average

Write an Aether function `average(xs: List<Int>) returns Result<Int, String>`
that returns:
- `Err("empty")` when the list is empty,
- `Ok(avg)` where `avg` is the integer average (sum divided by length, integer division)
  when the list is non-empty.

The function must be `pure` and use a `requires` clause that `length(xs) >= 0`
(trivially true, but exercises the contract syntax).

In `main`, for each list below, print either `ok=N` or `err=MSG`, one per line:

    [10, 20, 30]
    [-5, 5]
    []
    [7]
    [1, 2, 3, 4]

Expected output:

    ok=20
    ok=0
    err=empty
    ok=7
    ok=2
