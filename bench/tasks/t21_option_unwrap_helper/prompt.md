Write an Aether program that safely reads index `9` from `[10, 20]`.

Use `safeAt(xs, index)` and handle the returned `Option<Int>`. Print
`missing` when the value is absent, then print the fallback value from
`unwrapOr(option, -1)`.
