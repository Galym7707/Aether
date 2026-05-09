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
- Use `safeAt(xs, i)` for safe dynamic access; handle `Some(value)` and `None()`.
- Use `updateAt(xs, i, value)` for safe replacement; handle `Ok(updated)` and `Err(message)`.
- Use `safeSlice(xs, start, end)` for safe slicing; handle `Ok(part)` and `Err(message)`.
- Do not use `xs.append(x)` or `xs.push(x)`.
- Do not write `xs[i] = value`.
- Do not write Python slicing syntax like `xs[start:end]`.
- Do not write method-style access like `xs.get(i)`.
- Annotate empty lists: `let xs: List<Int> = []`.
- Call generic functions normally: `identity(5)`, not `identity<Int>(5)`.
- Use `Point(1, 2)`, not `Point { x = 1, y = 2 }`.

Good list update pattern:

```aether
match updateAt(xs, index, value) do
  case Ok(updated) do
    return updated
  end
  case Err(message) do
    return xs
  end
end
```
