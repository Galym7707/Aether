# Aether Language Guide

This guide describes the current repository implementation audited on
2026-05-09. It is for humans and AI models that need to write valid Aether
programs. Implementation evidence: `transpiler/aether/parser.py`,
`transpiler/aether/emitter.py`, `transpiler/aether/runtime.py`,
`grammar/grammar.ebnf`, `grammar/stdlib.md`, and `tests/test_regressions.py`.

Aether is a research prototype. Treat this guide as a practical guide to what
the compiler accepts now, not as a production language reference.

## Minimal Function Syntax

```aether
function name(param: Type) returns ReturnType
  requires condition
  ensures condition
  effects pure
do
  return value
end
```

Every function must declare `effects`. Use `effects pure` when it has no
observable effect. A function that prints must declare `effects log`.

## Do / Do Not Table

| Concept | Correct Aether | Wrong syntax to avoid |
|---|---|---|
| Function | `function f(x: Int) returns Int` | `fn f(x: Int) -> Int` |
| List type | `List<Int>` | `List[Int]` |
| Length | `length(xs)` | `xs.len()` |
| Blocks | `do ... end` | `{ ... }` |
| Conditions | `if cond then ... end` | `if (...) { ... }` |
| Loops | `while cond do ... end` | `while (...) { ... }` |
| Contracts | `requires x > 0` | comment-only validation |
| Effects | `effects pure` | omitted effects when pure |
| Lambdas | helper functions | `(x) => ...` |

## Supported Syntax

### Functions

```aether
function add(a: Int, b: Int) returns Int
  effects pure
do
  return a + b
end
```

Generic function declarations are supported for argument/return relationships
that appear in the implemented subset:

```aether
function identity<T>(x: T) returns T
  effects pure
do
  return x
end
```

Call generic functions normally, for example `identity(5)`. Explicit generic
call syntax such as `identity<Int>(5)` is not supported.

### Parameters And Return Types

Parameters use `name: Type`. Return types use the `returns` keyword.

```aether
function first(xs: List<Int>) returns Int
  requires length(xs) > 0
  effects pure
do
  return xs[0]
end
```

### Contracts

`requires` clauses are checked at runtime before the function body. `ensures`
clauses are checked at runtime before returning. The scoped SMT pass can also
reject some impossible arithmetic contracts before execution.

```aether
function positiveOnly(x: Int) returns Int
  requires x > 0
  ensures result > 0
  effects pure
do
  return x
end
```

### Effects

Effects are mandatory. The static effect checker runs by default for direct
calls to known functions.

```aether
function sayHello() returns Unit
  effects log
do
  print("hello")
end
```

### If / Else

```aether
if x > 0 then
  return "positive"
else
  return "zero-or-negative"
end
```

### While

```aether
var i: Int = 0
while i < length(xs) do
  i = i + 1
end
```

### Let, Var, And Assignment

Use `let` for immutable-style bindings and `var` for variables that will be
assigned later. Assignment is by variable name.

```aether
let start: Int = 0
var total: Int = 0
total = total + 1
```

### List Literals, Indexing, And Append

```aether
let xs: List<Int> = [10, 20, 30]
let second: Int = xs[1]
let ys: List<Int> = append(xs, 40)
```

The checker tracks list element types, nested list types, and known literal
lengths in simple cases. These fail with structured diagnostics:

```aether
let xs: List<Int> = [1, "bad"]     // TYPE_LIST_ELEMENT_MISMATCH
let ys: List<Int> = append(xs, "x") // TYPE_LIST_APPEND_MISMATCH
let zs = []                         // TYPE_EMPTY_LIST_NEEDS_ANNOTATION
let bad: Int = xs["0"]              // INDEX_TYPE_INVALID
let oob: Int = [1, 2, 3][3]         // INDEX_OUT_OF_BOUNDS_STATIC
```

Direct list item assignment such as `xs[0] = 99` is not supported. Build a new
list with `append`.

### Helper Predicates

Use named helper predicates instead of lambdas.

```aether
function sorted?(xs: List<Int>) returns Bool
  effects pure
do
  if length(xs) <= 1 then
    return true
  end
  var i: Int = 1
  while i < length(xs) do
    if xs[i - 1] > xs[i] then
      return false
    end
    i = i + 1
  end
  return true
end
```

## Unsupported Or Uncertain Syntax

These forms should not be generated:

- `fn` declarations are unsupported. Use `function`.
- `->` return syntax is unsupported. Use `returns`.
- `List[Int]` is unsupported. Use `List<Int>`.
- JavaScript lambdas such as `(x) => x + 1` are unsupported. Use helper functions.
- Method calls such as `xs.len()` are unsupported. Use `length(xs)`.
- Method-style list updates such as `xs.append(x)` and `xs.push(x)` are
  unsupported. Use `append(xs, x)`.
- General method-call style is unsupported. `Shape.Circle(...)` works for union constructors; field access such as `point.x` works for records.
- Brace blocks are unsupported. Use `do/end` and `if ... then ... end`.
- Record literal syntax `Point { x = 1, y = 2 }` is not implemented. Use positional constructors such as `Point(1, 2)`.
- Value-level casts such as `(x as Float)` are not implemented.
- Direct list item assignment such as `result[i] = value` is unsupported.
- Explicit generic call syntax such as `identity<Int>(5)` is unsupported.
  Call `identity(5)` and let the checker infer the supported type variable.
- Static index checking catches obvious known-length cases only. Dynamic index
  checks remain runtime diagnostics.

## Canonical Examples

### 1. Hello / Simple Return

```aether
function answer() returns Int
  ensures result == 42
  effects pure
do
  return 42
end

function main() returns Unit
  effects log
do
  print(intToString(answer()))
end
```

### 2. safeDivide

```aether
function safeDivide(a: Int, b: Int) returns Int
  requires b != 0
  effects pure
do
  return a / b
end
```

### 3. nonEmptyAverage

```aether
type NonEmptyIntList = List<Int> where length(self) > 0

function sumInts(xs: List<Int>) returns Int
  effects pure
do
  var total: Int = 0
  for x in xs do
    total = total + x
  end
  return total
end

function average(xs: NonEmptyIntList) returns Int
  requires length(xs) > 0
  ensures result == sumInts(xs) / length(xs)
  effects pure
do
  return sumInts(xs) / length(xs)
end
```

### 4. Sorted Binary Search Precondition

```aether
function binarySearch(xs: List<Int>, target: Int) returns Int
  requires sorted?(xs)
  ensures result == -1 or (result >= 0 and result < length(xs))
  effects pure
do
  var lo: Int = 0
  var hi: Int = length(xs) - 1
  while lo <= hi do
    let mid: Int = (lo + hi) / 2
    if xs[mid] == target then
      return mid
    elif xs[mid] < target then
      lo = mid + 1
    else
      hi = mid - 1
    end
  end
  return -1
end
```

This example requires a helper function named `sorted?`; see
`examples/03_sorted_binary_search.aeth`.

### 5. safeNormalizeWeights

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

This example requires helper functions `sumWeights` and
`allWeightsNonNegative?`; see `examples/05_safe_normalize_weights.aeth`.

### 6. Effect Violation Example

```aether
function badPurePrinter() returns Unit
  effects pure
do
  print("bad")
end
```

`aether check` rejects this with `E0801` because `print` requires `log`.

## Ready-To-Copy AI Prompt

Use this prompt with Gemini, Claude, GPT, or another model:

```text
Write one complete Aether program. Output only Aether code, no Markdown.

Aether syntax rules:
- Use `function`, not `fn`.
- Use `returns`, not `->`.
- Use `List<Int>`, not `List[Int]`.
- Use `length(xs)`, not `xs.len()`.
- Use `do` and `end`, not braces.
- Use `if cond then ... end`, not `if (...) { ... }`.
- Use named helper predicates, not lambdas like `(x) => ...`.
- Every function must include an `effects` clause. Use `effects pure` for pure helpers and `effects log` for functions that print.
- Use `requires` and `ensures` for preconditions and postconditions.
- Do not use direct list item assignment like `xs[i] = value`; rebuild lists with `append`.
- For records, use positional construction like `Point(1, 2)`, not `Point { x = 1, y = 2 }`.

Follow the style of `examples/01_safe_divide.aeth`,
`examples/02_non_empty_average.aeth`, and
`examples/05_safe_normalize_weights.aeth`.
```
