# t27 effect row callback mismatch

This task demonstrates precise effect rows for callbacks passed to
Option/Result helpers.

Python silently runs a callback that reaches the billing domain. Aether rejects
the program with `HIGHER_ORDER_EFFECT_ESCAPE` because the enclosing function
declares only `net.fetch("https://api.example.com/*")`.
