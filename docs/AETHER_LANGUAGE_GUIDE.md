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
| Safe access | `safeAt(xs, i)` | `xs.get(i)` |
| Safe update | `updateAt(xs, i, value)` | `xs[i] = value` |
| Safe slice | `safeSlice(xs, start, end)` | `xs[start:end]` |
| Option fallback | `unwrapOr(opt, default)` | `opt.unwrap()` |
| Result fallback | `unwrapOrResult(res, default)` | `res.unwrap()` |
| Result predicate | `isOk(res)` | `res.is_ok()` |
| Blocks | `do ... end` | `{ ... }` |
| Conditions | `if cond then ... end` | `if (...) { ... }` |
| Loops | `while cond do ... end` | `while (...) { ... }` |
| Loop invariant | `invariant i >= 0` inside `while` header | comments that only describe the invariant |
| Loop variant | `variant n - i` inside `while` header | non-decreasing loop counters |
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

Call generic functions either by inference, for example `identity(5)`, or with
explicit type arguments when inference would be unclear:

```aether
let a: Int = identity<Int>(5)
let xs: List<Int> = identity<List<Int>>([1, 2])
```

Use `f<Int>(x)`, `f<Int, String>(x)`, and nested forms such as
`f<Result<List<Int>, String>>(x)`. Do not use `f[Integer](x)` or
`f::<Int>(x)`.

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

### Quantifiers And List Aggregates

Aether supports list quantifiers and a small collection-property stdlib for
contracts and pure helper functions:

```aether
requires forall x in xs: x >= 0
requires exists y in xs: y > 100
ensures sum(result) == sum(xs)
ensures min(result) == min(xs)
ensures max(result) >= max(xs)
ensures sorted(result)
ensures permutation(xs, result)
```

`forall` and `exists` return `Bool`. `sum`, `min`, `max`, and `sorted` currently
operate on `List<Int>`. `permutation(xs, ys)` accepts two lists with the same
element type and returns `Bool`; when both literal lengths are known and differ,
the checker reports a length diagnostic. `sum`, `min`, and `max` require
non-empty lists and raise structured diagnostics if an empty dynamic list
reaches runtime.

Use this syntax exactly:

```aether
let ok: Bool = forall x in [1, 2, 3]: x > 0
let hasLarge: Bool = exists x in xs: x > 100
let adjacentOk: Bool = forall i in 0..length(xs) - 1: xs[i] <= xs[i + 1]
let total: Int = sum(xs)
```

Do not write `for all x in xs`, `exists(x)`, or omit the colon before the
predicate.

Range expressions such as `0..n` are half-open `List<Int>` values. `0..3`
iterates `0`, `1`, and `2`. They are intended for quantifiers and small
checked loops, not as a replacement for all list construction.

### Loop Invariants And Variants

`while` loops can include zero or more invariants and one arithmetic variant
between the condition and `do`:

```aether
while i < n
invariant i >= 0
invariant forall j in 0..i: xs[j] >= 0
variant n - i
do
  i = i + 1
end
```

Each `invariant` must be a `Bool`. The `variant` must be an `Int` expression
that is strictly smaller after each iteration. The checks run at the normal end
of an iteration and before a `continue` jumps to the next iteration. The SMT
pass proves simple arithmetic decreases when it can; otherwise runtime checks
raise structured diagnostics such as `LOOP_INVARIANT_FAILED` or
`LOOP_VARIANT_NOT_DECREASING`.

### Record Literals And Updates

Records can be created with positional constructors or field literals. Record
literals must provide every declared field exactly once and may not include
extra fields:

```aether
record Account do
  id: Int
  balance: Int
end

let account: Account = Account { id = 1, balance = 100 }
let updated: Account = account { balance = account.balance + amount }
```

The update expression does not mutate `account`; it creates a new record value.
Missing or extra fields in a record literal produce
`RECORD_LITERAL_MISSING_FIELD` or `RECORD_LITERAL_EXTRA_FIELD`.

### Effects

Effects are mandatory. The static effect checker runs by default for direct
calls to known functions and for named callbacks passed to the standard
`Option` / `Result` higher-order helpers.

```aether
function sayHello() returns Unit
  effects log
do
  print("hello")
end
```

When a callback passed to `mapOption`, `andThenOption`, `mapResult`, `mapErr`,
or `andThenResult` declares an effect, the enclosing function must declare a
covering effect too:

```aether
function logAndDouble(x: Int) returns Int
  effects log
do
  print(intToString(x))
  return x * 2
end

function ok() returns Unit
  effects log
do
  let value: Option<Int> = mapOption(Some(1), logAndDouble)
end
```

This is rejected because `logAndDouble` is effectful but `bad` claims to be
pure:

```aether
function bad() returns Unit
  effects pure
do
  let value: Option<Int> = mapOption(Some(1), logAndDouble)
end
```

The diagnostic code is `HIGHER_ORDER_EFFECT_ESCAPE`. Fix it by adding the
escaped effect to the enclosing function, passing a pure callback, or moving
the effectful work outside the helper. For argumented effects such as
`net.fetch("https://billing.example.com/*")`, the enclosing function must
declare a row that precisely covers that URL pattern.

Function-typed parameters can also declare callback effects:

```aether
function applyLogged(f: function(Int) returns Int effects log, x: Int) returns Int
  effects log
do
  return f(x)
end
```

The `effects` annotation on a function type is optional and defaults to
`effects pure`. If `applyLogged` above declared `effects pure`, calling `f(x)`
would produce `HIGHER_ORDER_EFFECT_ESCAPE`. Nested function types can carry
effects too:

```aether
function(Int) returns function(Int) returns Bool effects log effects pure
```

Function type effect rows are precise. A parameter typed as
`function(Int) returns String effects net.fetch("https://api.example.com/*")`
can accept a callback with `effects net.fetch("https://api.example.com/users/*")`,
but not one with `effects net.fetch("https://billing.example.com/*")`.
That argument mismatch uses diagnostic code `FUNCTION_TYPE_EFFECT_MISMATCH`.

Direct calls use the same rule. A function with
`effects net.fetch("https://api.example.com/*")` cannot call a callee requiring
`effects net.fetch("https://billing.example.com/*")`; the diagnostic code is
`EFFECT_NOT_COVERED`.

### Deterministic Runtime Hooks

Use `random()` for pseudo-random integers and `time.now()` or `now()` for the
current instant. Both are effectful:

```aether
function main() returns Unit
  effects random, time.now, log
do
  print(intToString(random()))
  print(intToString(time.now().epochMillis))
end
```

Run with deterministic flags when you need reproducible output:

```powershell
aether run --deterministic --seed=123 examples\18_deterministic_random.aeth
aether run --deterministic --fixed-time=2026-05-10T00:00:00 examples\19_deterministic_time.aeth
```

`--seed` controls the deterministic `random()` sequence. If omitted, the seed is
`0`. `--fixed-time` supplies the timestamp returned by `time.now()` and `now()`;
without it, deterministic mode freezes time at Unix epoch `0`. Without
deterministic flags, `time.now()` uses wall-clock time and `random()` uses the
normal non-deterministic Python random source.

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

### List Literals, Indexing, Append, And Safe Helpers

```aether
let xs: List<Int> = [10, 20, 30]
let second: Int = xs[1]
let ys: List<Int> = append(xs, 40)
let maybe: Option<Int> = safeAt(xs, 1)
let changed: Result<List<Int>, String> = updateAt(xs, 1, 99)
let part: Result<List<Int>, String> = safeSlice(xs, 0, 2)
```

The checker tracks list element types, nested list types, and known literal
lengths in simple cases. It also understands the generic relationships for
`safeAt`, `updateAt`, `safeSlice`, `inBounds`, and `validSliceBounds`. These
fail with structured diagnostics:

```aether
let xs: List<Int> = [1, "bad"]     // TYPE_LIST_ELEMENT_MISMATCH
let ys: List<Int> = append(xs, "x") // TYPE_LIST_APPEND_MISMATCH
let zs = []                         // TYPE_EMPTY_LIST_NEEDS_ANNOTATION
let bad: Int = xs["0"]              // INDEX_TYPE_INVALID
let oob: Int = [1, 2, 3][3]         // INDEX_OUT_OF_BOUNDS_STATIC
let a = safeAt(xs, "0")             // LIST_HELPER_INDEX_TYPE
let b = updateAt(xs, 0, "bad")      // LIST_HELPER_VALUE_TYPE
let c = safeSlice(xs, "0", 2)       // LIST_HELPER_BOUND_TYPE
```

Direct list item assignment such as `xs[0] = 99` is not supported. Prefer
`updateAt(xs, index, value)` and handle `Ok(updated)` or `Err(message)`. Python
slicing syntax such as `xs[start:end]` is not supported; use
`safeSlice(xs, start, end)`.

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

### Option, Result, And Exhaustive Match

`Option<T>` values use `Some(value)` and `None()`. `Result<T,E>` values use
`Ok(value)` and `Err(error)`. Prefer exhaustive `match` when the program needs
to handle both cases explicitly:

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

Use `unwrapOr(opt, default)` or `unwrapOrResult(res, default)` when a fallback
value is correct. Use `expectSome(opt, message)` or `expectOk(res, message)`
only when absence/error is a bug and should become a structured runtime
diagnostic.

```aether
let value: Int = unwrapOr(safeAt([10, 20], 9), -1)
let updated: List<Int> = unwrapOrResult(updateAt([10, 20], 1, 99), [10, 20])
```

The checker reports `MATCH_NON_EXHAUSTIVE` when a known `Option`, `Result`, or
user-defined union match misses a case and has no `_` wildcard.

Callbacks passed to `mapOption`, `andThenOption`, `mapResult`, `mapErr`, and
`andThenResult` should be named helper functions. If such a helper declares
`effects log`, `effects fs.read`, or another effect, the caller using the
higher-order helper must declare a covering effect. Pure callbacks remain valid
inside `effects pure` functions.

## Unsupported Or Uncertain Syntax

These forms should not be generated:

- `fn` declarations are unsupported. Use `function`.
- `->` return syntax is unsupported. Use `returns`.
- `List[Int]` is unsupported. Use `List<Int>`.
- JavaScript lambdas such as `(x) => x + 1` are unsupported. Use helper functions.
- Method calls such as `xs.len()` are unsupported. Use `length(xs)`.
- Method-style list updates such as `xs.append(x)` and `xs.push(x)` are
  unsupported. Use `append(xs, x)` for building or `updateAt(xs, i, value)` for
  replacement.
- Method-style safe access such as `xs.get(i)` is unsupported. Use
  `safeAt(xs, i)`.
- Method-style unwraps such as `opt.unwrap()` and `result.unwrap()` are
  unsupported. Use `expectSome`, `expectOk`, `unwrapOr`, `unwrapOrResult`, or
  exhaustive `match`.
- Method-style predicates such as `result.is_ok()` and `option.is_some()` are
  unsupported. Use `isOk(result)` and `isSome(option)`.
- Python slicing syntax such as `xs[start:end]` is unsupported. Use
  `safeSlice(xs, start, end)`.
- Quantifier spellings such as `for all x in xs`, `exists(x)`, or
  `forall x in xs x > 0` are unsupported. Use `forall x in xs: x > 0` or
  `exists x in xs: x > 0`.
- General method-call style is unsupported. `Shape.Circle(...)` works for union constructors; field access such as `point.x` works for records.
- Brace blocks are unsupported. Use `do/end` and `if ... then ... end`.
- Record literals must name a declared record type and provide exactly the declared fields: `Point { x = 1, y = 2 }`.
- Value-level casts such as `(x as Float)` are not implemented.
- Direct list item assignment such as `result[i] = value` is unsupported.
  Use `updateAt(result, i, value)` and handle `Result`.
- Square-bracket or turbofish generic call syntax such as `identity[Int](5)`
  and `identity::<Int>(5)` is unsupported. Use `identity<Int>(5)`.
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

`aether check` rejects this with `EFFECT_NOT_COVERED` because `print` requires
`log`.

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
- For network-like effects, use precise rows such as `effects net.fetch("https://api.example.com/*")`; this does not cover other domains.
- Annotate effectful function-typed parameters, for example `function(Int) returns String effects net.fetch("https://api.example.com/*")`.
- For reproducible randomness or time in examples, run with `aether run --deterministic --seed=123` and optional `--fixed-time=2026-05-10T00:00:00`.
- For complex generic helpers, use explicit generic calls such as `id<Int>(5)`, `makeResult<Int, String>(5)`, and `id<List<Int>>([1, 2])`.
- Use collection contracts like `forall x in xs: x >= 0`, `sum(xs)`, `sorted(xs)`, and `permutation(xs, ys)` when they express the invariant directly.
- For loops whose correctness matters, put `invariant ...` and `variant ...` between the `while` condition and `do`.
- Use half-open ranges in quantifiers, for example `forall i in 0..length(xs) - 1: xs[i] <= xs[i + 1]`.
- Use `requires` and `ensures` for preconditions and postconditions.
- Prefer `safeAt(xs, i)`, `updateAt(xs, i, value)`, and `safeSlice(xs, start, end)` for safe list access/update/slicing.
- Prefer exhaustive `match` for `Option` and `Result`.
- Use `unwrapOr` / `unwrapOrResult` only when a fallback is semantically correct.
- Use `expectSome` / `expectOk` only when absence/error should be a structured runtime diagnostic.
- Do not use direct list item assignment like `xs[i] = value`; handle `updateAt` with `Result`.
- Do not use Python slicing like `xs[start:end]`; handle `safeSlice` with `Result`.
- Do not use method style like `opt.unwrap()`, `result.unwrap()`, or `result.is_ok()`.
- Do not write quantifiers as `for all`, `exists(x)`, or without `:`.
- For records, use `Point { x = 1, y = 2 }` to create by fields, `Point(1, 2)` to create positionally, and `point { x = 3 }` to copy-update an existing record.

Follow the style of `examples/01_safe_divide.aeth`,
`examples/02_non_empty_average.aeth`, and
`examples/06_safe_at.aeth`, `examples/07_update_at.aeth`, and
`examples/08_safe_slice.aeth`.
```
