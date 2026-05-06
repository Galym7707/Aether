# v10 — Caesar shift

**Status:** PASS (second attempt — one fix required + file corruption fix)

**First attempt failure:** Used `result` as the accumulator variable name
inside `caesar`. Same reserved-keyword collision as v03.

**Fix 1:** Renamed to `chars`.

**File corruption:** The in-place Edit tool left trailing null bytes
(`\x00`) in the file, causing a lex error E0101. Rewrote the file via
bash `cat >` to produce a clean byte sequence.

**Logic:** Constant `ALPHA` list of 26 lowercase letters. `letterIndex`
does a linear scan (no char primitives in v0.1). `caesarChar` uses
`(idx + k) % 26` for wraparound. `caesar` iterates over `slice(s, i, i+1)`
characters and joins the result.
