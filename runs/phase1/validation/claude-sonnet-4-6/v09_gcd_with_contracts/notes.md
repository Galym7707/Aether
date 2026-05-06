# v09 — GCD with contracts

**Status:** PASS (first attempt)

Euclidean algorithm using two mutable bindings `x` and `y`, `while y != 0`
loop, temporary `tmp` binding for the swap. All four contract clauses
included: `requires a >= 0 and b >= 0`, `requires a > 0 or b > 0`,
`ensures result > 0`, `effects pure`. The `ensures result > 0` clause is
runtime-checked by the emitter's contract wrapper.
