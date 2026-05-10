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
- Prefer exhaustive `match` for `Option` and `Result`.
- When passing a named callback to `mapOption`, `andThenOption`, `mapResult`, `mapErr`, or `andThenResult`, declare any callback effects on the enclosing function.
- Annotate effectful function-typed parameters: `function(Int) returns Int effects log`.
- Omitted function type effects default to pure.
- For network effects, use precise rows: `net.fetch` covers all fetches, `net.fetch("*")` covers all argumented fetches, and `net.fetch("https://api.example.com/*")` covers only that URL prefix.
- `net.fetch("https://api.example.com/*")` does not cover `net.fetch("https://billing.example.com/*")`.
- `random()` requires `effects random`; `time.now()` and `now()` require `effects time.now`.
- Use `aether run --deterministic --seed=123` and optional `--fixed-time=2026-05-10T00:00:00` for reproducible examples.
- Use `unwrapOr(opt, default)` only when a fallback is correct.
- Use `unwrapOrResult(res, default)` only when a fallback is correct.
- Use `expectSome(opt, message)` or `expectOk(res, message)` only when failure should be a diagnostic.
- Do not use `xs.append(x)` or `xs.push(x)`.
- Do not write `xs[i] = value`.
- Do not write Python slicing syntax like `xs[start:end]`.
- Do not write method-style access like `xs.get(i)`.
- Do not write `opt.unwrap()`, `result.unwrap()`, or `result.is_ok()`.
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

Good Option pattern:

```aether
match safeAt(xs, index) do
  case Some(value) do
    return intToString(value)
  end
  case None() do
    return "missing"
  end
end
```

Good effect-aware helper pattern:

```aether
function logValue(x: Int) returns Int
  effects log
do
  print(intToString(x))
  return x
end

function main() returns Unit
  effects log
do
  let value: Option<Int> = mapOption(Some(1), logValue)
end
```

Good function-typed parameter pattern:

```aether
function applyLogged(f: function(Int) returns Int effects log, x: Int) returns Int
  effects log
do
  return f(x)
end
```

Good precise network-effect pattern:

```aether
function fetchUser(id: Int) returns String
  effects net.fetch("https://api.example.com/users/*")
do
  return "user"
end

function main() returns Unit
  effects net.fetch("https://api.example.com/*")
do
  let value: String = fetchUser(1)
end
```
