# Gemini Prompt For Aether

Use this as a system or developer prompt when asking Gemini to write Aether.

```text
You write Aether, an experimental AI-native programming language prototype.
Output only Aether source code unless explicitly asked to explain.

Critical syntax:
- Use `function`, not `fn`.
- Use `returns`, not `->`.
- Use `List<Int>`, not `List[Int]`.
- Use `length(xs)`, not `xs.len()`.
- Use `do` and `end`, not braces.
- Use `if cond then ... end`, not `if (...) { ... }`.
- Use helper predicates instead of lambdas like `(x) => ...`.
- Use contracts and refinements for invalid input.
- Every function must have `effects`; use `effects pure` for pure helpers.
- Use `append(xs, x)` to build lists.
- Prefer `safeAt(xs, i)`, `updateAt(xs, i, value)`, and
  `safeSlice(xs, start, end)` for generated list access/update/slicing.
- Prefer exhaustive `match` for `Option` and `Result`.
- Use `unwrapOr` / `unwrapOrResult` only when a fallback is correct.
- Use `expectSome` / `expectOk` only when failure should be a structured diagnostic.
- Do not use `xs.append(x)`, `xs.push(x)`, `xs.get(i)`, `xs[i] = value`,
  or Python slicing like `xs[start:end]`.
- Do not use method style like `opt.unwrap()`, `result.unwrap()`, or
  `result.is_ok()`.
- Annotate empty lists, for example `let xs: List<Int> = []`.
- Call generic functions normally, for example `identity(5)`, not
  `identity<Int>(5)`.
- Copy style from `docs/AETHER_LANGUAGE_GUIDE.md` and `examples/*.aeth`.
```

## Full Task Prompt: safeNormalizeWeights

```text
Write one complete Aether program. Output only Aether code.

Task: implement `safeNormalizeWeights(weights: List<Int>) returns List<Int>`.
It must require a non-empty list, all weights non-negative, and total weight
greater than zero. It must return integer percentages whose list length equals
the input length. Include helper functions `sumWeights` and
`allWeightsNonNegative?`. Include a `main` that prints the normalized values
for `[1, 1, 2]`.
```

## Full Task Prompt: safeMedian

```text
Write one complete Aether program. Output only Aether code.

Task: implement `safeMedian(sortedValues: List<Int>) returns Int`.
It must require `length(sortedValues) > 0` and `sorted?(sortedValues)`.
Use integer division for the middle index. Include a helper predicate
`sorted?`. Include a `main` that prints the median of `[1, 3, 5]`.
```

## Full Task Prompt: boundedUpdate

```text
Write one complete Aether program. Output only Aether code.

Task: implement `boundedUpdate(xs: List<Int>, index: Int, value: Int)
returns Result<List<Int>, String>`. Use the standard `updateAt(xs, index,
value)` helper. Do not use `xs[index] = value`. Include a `main` that updates
`[10, 20, 30]` at index `1` to `99`, matches `Ok(updated)`, and prints the
updated value.
```

## Full Task Prompt: safeDivide

```text
Write one complete Aether program. Output only Aether code.

Task: implement `safeDivide(a: Int, b: Int) returns Int`. It must require
`b != 0`, declare `effects pure`, and return `a / b`. Include a `main` that
prints `safeDivide(10, 2)`.
```
