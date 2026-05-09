# t25 mapErr effect escape

This task shows a logging error mapper passed to `mapErr` from a pure context.

Python runs the error mapper and prints an audit line. Aether rejects the
program with `HIGHER_ORDER_EFFECT_ESCAPE` because the enclosing function did
not declare `effects log`.
