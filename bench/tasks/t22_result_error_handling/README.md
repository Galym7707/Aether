# t22_result_error_handling

This task checks canonical `Result` helper usage. The Aether reference uses
`updateAt`, `isErr`, and `unwrapOrResult` so an invalid update remains explicit.
The Python equivalent silently clamps the invalid index and updates the wrong
element.
