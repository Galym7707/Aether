# Lists In Aether

This file documents current list behavior from `grammar/stdlib.md`,
`transpiler/aether/parser.py`, `transpiler/aether/runtime.py`, and
`tests/test_list_operations.py`, and `tests/test_safe_list_helpers.py`.

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
For safe dynamic access, prefer `safeAt(xs, index)`:

```aether
match safeAt(xs, index) do
  case Some(value) do
    return intToString(value)
  end
  case None() do
    return "none"
  end
end
```

Guard direct indexing with a contract when the input is dynamic and a missing
value should be rejected instead of represented as `None()`:

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

Lists are used in a pure-functional style. Use `append` to return a new list
when you are intentionally building a list:

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
`head`, `tail`, `get`, `safeAt`, `updateAt`, `safeSlice`, `inBounds`,
`validSliceBounds`, `map`, `filter`, `foldLeft`, `reverse`, and `range`.

## Standard Safe List Helpers

Prefer these helpers for generated code:

```aether
let present: Option<Int> = safeAt([10, 20], 1)
let missing: Option<Int> = safeAt([10, 20], 9)
let updated: Result<List<Int>, String> = updateAt([10, 20], 1, 99)
let sliced: Result<List<Int>, String> = safeSlice([10, 20, 30], 0, 2)
let okIndex: Bool = inBounds([10, 20], 1)
let okSlice: Bool = validSliceBounds([10, 20, 30], 0, 2)
```

Type relationships are checked:

```aether
safeAt([1, 2], "0")        // LIST_HELPER_INDEX_TYPE
updateAt([1, 2], 0, "bad") // LIST_HELPER_VALUE_TYPE
safeSlice([1, 2], "0", 1)  // LIST_HELPER_BOUND_TYPE
```

`updateAt` returns a new list and does not mutate the original list. Invalid
indexes return `Err("index out of bounds")`. Invalid slice bounds return
`Err("slice bounds out of range")`.

## List Mutation

Direct list item assignment is not supported:

```aether
xs[0] = 99  // unsupported
```

The CLI prelint reports this as `E0006` with a suggestion to rebuild the list
with `updateAt(xs, i, value)` and handle the returned `Result`.

## Correct updateAt Pattern

```aether
function describeUpdate(res: Result<List<Int>, String>) returns String
  effects pure
do
  match res do
    case Ok(updated) do
      return intToString(updated[1])
    end
    case Err(message) do
      return message
    end
  end
end
```

When a fallback is correct, use `unwrapOr` with `safeAt`:

```aether
let value: Int = unwrapOr(safeAt(xs, index), -1)
```

When absence should be explicit, prefer an exhaustive `match` over `Option`.

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
Manual `append` loops are still appropriate for transformations that build a
new list element by element. For single-index access, update, or slicing,
prefer `safeAt`, `updateAt`, and `safeSlice`.

## Common AI Mistakes

| Mistake | Correct form |
|---|---|
| `List[Int]` | `List<Int>` |
| `xs.len()` | `length(xs)` |
| `xs.append(x)` | `append(xs, x)` |
| `xs[i] = value` | `updateAt(xs, i, value)` and handle `Result` |
| `xs[start:end]` | `safeSlice(xs, start, end)` |
| `xs.get(i)` | `safeAt(xs, i)` |
| unguarded `xs[0]` on maybe-empty input | `safeAt(xs, 0)` or add `requires length(xs) > 0` |
| `let xs = []` | `let xs: List<Int> = []` |
| lambdas in list helpers | write named helper functions |
