# Aether Syntax Cheatsheet

Output only Aether code unless the user asks for explanation.

```aether
function name(param: Type) returns ReturnType
  requires condition
  ensures condition
  effects pure
do
  return value
end
```

Rules:

- Use `function`, not `fn`.
- Use `returns`, not `->`.
- Use `List<Int>`, not `List[Int]`.
- Use `length(xs)`, not `xs.len()`.
- Use `do`/`end`, not `{}` blocks.
- Use `if cond then ... else ... end`.
- Use `while cond do ... end`.
- Use helper predicates, not lambdas.
- Every function needs `effects`; use `effects pure` for pure helpers.
- Use `append(xs, x)` to build lists.
- Do not use `xs.append(x)` or `xs.push(x)`.
- Do not write `xs[i] = value`; rebuild a list instead.
- Annotate empty lists: `let xs: List<Int> = []`.
- Call generic functions normally: `identity(5)`, not `identity<Int>(5)`.
- Use `Point(1, 2)`, not `Point { x = 1, y = 2 }`.

Good list update pattern:

```aether
var out: List<Int> = []
var i: Int = 0
while i < length(xs) do
  if i == index then
    out = append(out, value)
  else
    out = append(out, xs[i])
  end
  i = i + 1
end
```
