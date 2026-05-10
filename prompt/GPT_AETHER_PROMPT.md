# GPT Prompt For Aether

Use this as a system or developer prompt when asking GPT to write Aether.

```text
Write valid Aether for the current repository. Output only Aether source code
when the user asks for code. Do not output Markdown fences.

Syntax constraints:
- Aether uses `function`, not `fn`.
- Aether uses `returns`, not `->`.
- Aether uses `List<Int>`, not `List[Int]`.
- Aether uses `length(xs)`, not `xs.len()`.
- Aether uses `do/end`, not `{}`.
- Aether uses helper predicates instead of lambdas.
- Aether uses contracts/refinements for invalid input.
- Aether uses `effects pure` for pure functions.
- Aether uses `effects log` for functions that call `print`.
- Aether uses `append(xs, x)` to build lists.
- Aether prefers `safeAt(xs, i)`, `updateAt(xs, i, value)`, and
  `safeSlice(xs, start, end)` for generated list access/update/slicing.
- Aether prefers exhaustive `match` for `Option` and `Result`.
- Aether uses `unwrapOr` / `unwrapOrResult` only when a fallback is correct.
- Aether uses `expectSome` / `expectOk` only when failure should be a structured diagnostic.
- Aether requires enclosing functions to declare effects from named callbacks passed to `mapOption`, `andThenOption`, `mapResult`, `mapErr`, or `andThenResult`.
- Aether supports effect-annotated function types such as `function(Int) returns Int effects log`; omitted function type effects default to pure.
- Aether checks argumented network effects precisely: `net.fetch("https://api.example.com/*")` covers only that URL prefix.
- Aether does not support `xs.append(x)`, `xs.push(x)`, `xs.get(i)`,
  `xs[i] = value`, or Python slicing like `xs[start:end]`.
- Aether does not support `opt.unwrap()`, `result.unwrap()`, or
  `result.is_ok()`.
- Aether requires a contextual type for empty lists, for example
  `let xs: List<Int> = []`.
- Aether generic calls may be inferred, for example `identity(5)`, or explicit,
  for example `identity<Int>(5)` and `makeResult<Int, String>(5)`.
- Use `f<Int>(x)`, not `f[Integer](x)` or `f::<Int>(x)`.
- Use list invariants directly: `forall x in xs: x >= 0`,
  `exists x in xs: x > 100`, `sum(xs)`, `sorted(xs)`, and
  `permutation(xs, ys)`.
- Do not write `for all`, `exists(x)`, or quantifiers without `:`.
- Use examples from `docs/AETHER_LANGUAGE_GUIDE.md` and `examples/`.
```

## Full Task Prompt: safeNormalizeWeights

```text
Write one complete Aether program. Output only Aether code.

Create helper functions `sumWeights` and `allWeightsNonNegative?`. Implement
`safeNormalizeWeights(weights: List<Int>) returns List<Int>` with `requires`
clauses for non-empty input, non-negative weights, and positive total. Ensure
the output length equals input length. Use `append` to build the result.
```

## Full Task Prompt: safeMedian

```text
Write one complete Aether program. Output only Aether code.

Implement `sorted?(xs: List<Int>) returns Bool` and
`safeMedian(sortedValues: List<Int>) returns Int`. Require non-empty sorted
input. Use integer middle index. Include a `main` that prints a result.
```

## Full Task Prompt: boundedUpdate

```text
Write one complete Aether program. Output only Aether code.

Implement `boundedUpdate(xs: List<Int>, index: Int, value: Int) returns
Result<List<Int>, String>`. Use `updateAt(xs, index, value)` and return its
`Result`. Do not mutate `xs` and do not use method calls.
```

## Full Task Prompt: safeDivide

```text
Write one complete Aether program. Output only Aether code.

Implement `safeDivide(a: Int, b: Int) returns Int` with `requires b != 0` and
`effects pure`. Include `main` with `effects log` that prints the result for
`safeDivide(10, 2)`.
```
