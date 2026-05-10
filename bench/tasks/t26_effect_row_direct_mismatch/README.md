# t26 effect row direct mismatch

This task demonstrates precise `net.fetch(...)` effect rows for direct calls.

Python calls the billing fetcher even when the intended row is limited to
`https://api.example.com/*`. Aether rejects the program with
`EFFECT_NOT_COVERED` because the called function requires
`net.fetch("https://billing.example.com/*")`.
