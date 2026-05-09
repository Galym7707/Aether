# Task: safe index access

Write `safeAt(xs: List<Int>, index: Int) returns Int` with an explicit
`requires inBounds?(xs, index)` contract. The reference program must call an
out-of-range index.
