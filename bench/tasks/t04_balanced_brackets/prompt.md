# Task: balanced brackets

Write an Aether function `balanced?(s: String) returns Bool` that returns
`true` if the string's brackets `(`, `[`, `{` are balanced and properly nested
with their counterparts `)`, `]`, `}`. Other characters are ignored.

Then in `main`, print the result (`true` or `false`) for each test, one per line:

    "()"
    "([])"
    "{[()]}"
    "([)]"
    "((("
    ""
    "abc(def[ghi]jkl)mno"
    "}"

Expected output:

    true
    true
    true
    false
    false
    true
    true
    false
