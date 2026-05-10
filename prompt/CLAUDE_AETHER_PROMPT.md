# Claude Prompt For Aether

Use this as a system or project instruction when asking Claude to write Aether.

```text
You write Aether code for the current Aether repository. Aether is a research
prototype, so use only syntax documented in `docs/AETHER_LANGUAGE_GUIDE.md`
and the `examples/` directory. Output only Aether code when asked for code.

Hard rules:
- `function`, never `fn`.
- `returns`, never `->`.
- `List<Int>`, never `List[Int]`.
- `length(xs)`, never `xs.len()`.
- `do`/`end`, never `{}` blocks.
- `if cond then ... end`, never JavaScript/C braces.
- named helper predicates, never lambdas like `(x) => ...`.
- explicit contracts/refinements for invalid inputs.
- `effects pure` for pure helpers and `effects log` for printing.
- use `append(xs, x)` to build lists.
- prefer `safeAt(xs, i)`, `updateAt(xs, i, value)`, and
  `safeSlice(xs, start, end)` for generated list access/update/slicing.
- prefer exhaustive `match` for `Option` and `Result`.
- use `unwrapOr` / `unwrapOrResult` only when a fallback is correct.
- use `expectSome` / `expectOk` only when failure should be a structured diagnostic.
- declare callback effects on the enclosing function when using `mapOption`, `andThenOption`, `mapResult`, `mapErr`, or `andThenResult`.
- annotate function-typed parameters with effects, for example `function(Int) returns Int effects log`; omitted effects default to pure.
- write precise network effect rows: `net.fetch("https://api.example.com/*")` covers only that URL prefix and does not cover other domains.
- do not write `xs.append(x)`, `xs.push(x)`, `xs.get(i)`, `xs[i] = value`,
  or Python slicing like `xs[start:end]`.
- do not write `opt.unwrap()`, `result.unwrap()`, or `result.is_ok()`.
- annotate empty lists, for example `let xs: List<Int> = []`.
- call generic functions by inference, for example `identity(5)`, or explicitly,
  for example `identity<Int>(5)` and `makeResult<Int, String>(5)`.
- use `f<Int>(x)`, not `f[Integer](x)` or `f::<Int>(x)`.
```

## Full Task Prompt: safeNormalizeWeights

```text
Write one complete Aether program. Output only Aether code.

Implement `safeNormalizeWeights(weights: List<Int>) returns List<Int>`.
Preconditions: non-empty list, all weights non-negative, and
`sumWeights(weights) > 0`. Postcondition: `length(result) == length(weights)`.
Use `append` to build the result. Include helper predicates and a `main`.
```

## Full Task Prompt: safeMedian

```text
Write one complete Aether program. Output only Aether code.

Implement `safeMedian(sortedValues: List<Int>) returns Int`. Require
`length(sortedValues) > 0` and `sorted?(sortedValues)`. Include `sorted?`.
Use `let mid: Int = length(sortedValues) / 2`. Include a printing `main`.
```

## Full Task Prompt: boundedUpdate

```text
Write one complete Aether program. Output only Aether code.

Implement `boundedUpdate(xs: List<Int>, index: Int, value: Int) returns
Result<List<Int>, String>`. Use `updateAt(xs, index, value)` and return its
`Result`. Do not use direct list item assignment or method calls.
```

## Full Task Prompt: safeDivide

```text
Write one complete Aether program. Output only Aether code.

Implement `safeDivide(a: Int, b: Int) returns Int` with `requires b != 0`,
`effects pure`, and a `main` that prints `safeDivide(10, 2)`.
```
