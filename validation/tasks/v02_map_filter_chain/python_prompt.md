# Task: map + filter pipeline

Write helpers `square(x: int) -> int` and `is_even(x: int) -> bool`.
Compose map/filter-style logic to produce, for each input list, the count of
even squares, then print that count. Do not use an explicit `for` or `while`
loop for the counting helper.

Test with:

    [1, 2, 3, 4]
    [1, 3, 5]
    []
    [2, 2, 2]

Expected output:

    2
    0
    0
    3
