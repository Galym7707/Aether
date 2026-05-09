# t23 mapOption effect escape

This task shows a callback with a logging side effect passed through
`mapOption` from a function declared `effects pure`.

Python runs the callback and prints an audit line. Aether rejects the program
with `HIGHER_ORDER_EFFECT_ESCAPE` unless the enclosing function declares
`effects log` or uses a pure callback.
