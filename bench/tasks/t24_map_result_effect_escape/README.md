# t24 mapResult effect escape

This task shows a logging callback passed to `mapResult` from a function
declared `effects pure`.

Python runs the mapper and prints the audit line. Aether rejects the missing
effect declaration with `HIGHER_ORDER_EFFECT_ESCAPE`.
