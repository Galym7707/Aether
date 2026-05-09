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
- Aether uses `append(xs, x)`, not `xs.append(x)` or `xs.push(x)`.
- Aether requires a contextual type for empty lists, for example
  `let xs: List<Int> = []`.
- Aether calls generic functions normally, for example `identity(5)`, not
  `identity<Int>(5)`.
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
List<Int>`. Require an in-bounds index. Ensure output length equals input
length. Do not mutate `xs`; use a loop and `append` to create `out`.
```

## Full Task Prompt: safeDivide

```text
Write one complete Aether program. Output only Aether code.

Implement `safeDivide(a: Int, b: Int) returns Int` with `requires b != 0` and
`effects pure`. Include `main` with `effects log` that prints the result for
`safeDivide(10, 2)`.
```
