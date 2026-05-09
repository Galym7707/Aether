# t21_option_unwrap_helper

This task checks canonical `Option` helper usage. The Aether reference uses
`safeAt`, `isNone`, and `unwrapOr` so a missing list element is explicit. The
Python equivalent silently defaults an invalid index to `0`.
