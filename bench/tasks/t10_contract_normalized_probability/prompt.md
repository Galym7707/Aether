# Task: contract normalized probability

Write an Aether function `chooseBucket(weights: List<Int>, threshold: Int)
returns Int` that requires a non-empty list of integer percentage weights, no
negative weights, and total weight exactly `100`.

The reference program must call `chooseBucket([50, -20, 70], 25)` in `main`.
This is intentionally invalid because one weight is negative. The desired
benchmark behavior is for Aether to reject the invalid probability weights with
a structured contract diagnostic instead of silently clamping or normalizing the
bad data.

Expected benchmark behavior:

    stdout: ""
    exit_code: 2
    stderr matches: (?i)(contract|requires|precondition).*(probability|weight|normal)
