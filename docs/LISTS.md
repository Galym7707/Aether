# Lists In Aether

This file documents current list behavior from `grammar/stdlib.md`,
`transpiler/aether/parser.py`, `transpiler/aether/runtime.py`, and
`tests/test_list_operations.py`.

## Create A List

```aether
let empty: List<Int> = []
let xs: List<Int> = [1, 2, 3]
```

Non-empty list literals infer a single element type. Mixed list literals are
rejected:

```aether
let xs: List<Int> = [1, "bad"]  // TYPE_LIST_ELEMENT_MISMATCH
```

An empty list without annotation or another contextual type is rejected because
the element type is unknown:

```aether
let xs = []  // TYPE_EMPTY_LIST_NEEDS_ANNOTATION
```

## Read By Index

```aether
let first: Int = xs[0]
```

The checker rejects non-Int indexes, negative indexes, and obvious static
out-of-bounds cases when the list length is known:

```aether
let xs = [1, 2, 3]
let a: Int = xs["0"]  // INDEX_TYPE_INVALID
let b: Int = xs[-1]   // INDEX_NEGATIVE_UNSUPPORTED
let c: Int = xs[3]    // INDEX_OUT_OF_BOUNDS_STATIC
```

Dynamic out-of-bounds cases are runtime diagnostics, not Python tracebacks.
Guard direct indexing with a contract when the input is dynamic:

```aether
function first(xs: List<Int>) returns Int
  requires length(xs) > 0
  effects pure
do
  return xs[0]
end
```

## Get Length

```aether
let n: Int = length(xs)
```

Do not write `xs.len()`.

## Build A New List

Lists are used in a pure-functional style. Use `append` to return a new list:

```aether
var out: List<Int> = []
out = append(out, 10)
out = append(out, 20)
```

`append` checks the element type:

```aether
let xs: List<Int> = [1, 2]
let ys: List<Int> = append(xs, "bad")  // TYPE_LIST_APPEND_MISMATCH
```

Do not use method style:

```aether
xs.append(10)  // E0009, unsupported
```

Other helpers documented in `grammar/stdlib.md` include `prepend`, `concat`,
`head`, `tail`, `get`, `map`, `filter`, `foldLeft`, `reverse`, and `range`.

## List Mutation

Direct list item assignment is not supported:

```aether
xs[0] = 99  // unsupported
```

The CLI prelint reports this as `E0006` with a suggestion to rebuild the list
with `append`.

## Correct updateAt Pattern

```aether
function updateAt(xs: List<Int>, index: Int, value: Int) returns List<Int>
  requires index >= 0 and index < length(xs)
  ensures length(result) == length(xs)
  effects pure
do
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
  return out
end
```

## Correct normalizeWeights Pattern

```aether
function safeNormalizeWeights(weights: List<Int>) returns List<Int>
  requires length(weights) > 0
  requires allWeightsNonNegative?(weights)
  requires sumWeights(weights) > 0
  ensures length(result) == length(weights)
  effects pure
do
  let total: Int = sumWeights(weights)
  var out: List<Int> = []
  var i: Int = 0
  while i < length(weights) do
    out = append(out, (weights[i] * 100) / total)
    i = i + 1
  end
  return out
end
```

See `examples/05_safe_normalize_weights.aeth` for a complete runnable file.

## Common AI Mistakes

| Mistake | Correct form |
|---|---|
| `List[Int]` | `List<Int>` |
| `xs.len()` | `length(xs)` |
| `xs.append(x)` | `append(xs, x)` |
| `xs[i] = value` | rebuild with `append` |
| unguarded `xs[0]` on maybe-empty input | add `requires length(xs) > 0` |
| `let xs = []` | `let xs: List<Int> = []` |
| lambdas in list helpers | write named helper functions |
