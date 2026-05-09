Write an Aether program that tries to update `[10, 20, 30]` at index `9`.

Use `updateAt(xs, index, value)` and handle the returned
`Result<List<Int>, String>`. Print `error` when the result is `Err`, then use
`unwrapOrResult(result, xs)` to keep the original list and print element `1`.
