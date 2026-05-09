# t20_safe_slice_helper

This task checks the standard `safeSlice` helper. Python slicing clamps invalid
bounds and may return a plausible but wrong result. The Aether reference uses
`safeSlice` so invalid bounds produce `Err("slice bounds out of range")`.
