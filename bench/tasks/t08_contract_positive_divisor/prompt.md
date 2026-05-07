# Task: contract positive divisor

Write an Aether function `safeRatio(numerator: Int, denominator: PositiveDivisor)
returns Int`, where `PositiveDivisor` is a refinement type requiring `self > 0`.

The reference program must call `safeRatio(10, 0)` in `main`. This is
intentionally invalid input. The desired benchmark behavior is for Aether to
reject the zero divisor with a structured refinement or contract diagnostic
instead of silently substituting another denominator.

Expected benchmark behavior:

    stdout: ""
    exit_code: 2
    stderr matches: (?i)(refinement|contract).*(positive|divisor|denominator)
