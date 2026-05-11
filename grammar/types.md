# Aether Type System (v0.1)

Aether is gradually typed at function bodies and explicit at function/module
boundaries. The current repository has a structural type diagnostic pass for
the implemented subset: it tracks `List<T>` element types, nested lists,
selected `Map<K,V>` / `Option<T>` / `Result<T,E>` helper flows, `append`, user
generic function argument/return relationships, primitive mismatches, and
obvious index bounds. It is still not a complete verifier. Refinement
predicates are checked at runtime when values cross function boundaries.

## Primitive types

    Int        // 64-bit signed integer
    Float      // 64-bit IEEE-754
    Bool       // true | false
    String     // immutable UTF-8 string
    Bytes      // immutable byte sequence
    Unit       // the trivial type, sole value `()`

## Parameterised types

    List<T>          // ordered sequence
    Map<K, V>        // key-value map, K must be hashable
    Set<T>           // unordered set, T must be hashable
    Option<T>        // Some(T) | None
    Result<T, E>     // Ok(T) | Err(E)

These are the *only* built-in collection and sum-type families. There is no `Array`, `Tuple` (records cover that), `Either`, or `Maybe`.

## List quantifiers and aggregates

Quantifier expressions iterate over `List<T>` and return `Bool`:

```aether
forall x in xs: x >= 0
exists x in xs: x > 100
forall i in 0..length(xs) - 1: xs[i] <= xs[i + 1]
```

The current aggregate helpers are intentionally small:

```aether
sum(xs: List<Int>) -> Int
min(xs: List<Int>) -> Int
max(xs: List<Int>) -> Int
sorted(xs: List<Int>) -> Bool
permutation(xs: List<T>, ys: List<T>) -> Bool
```

`sum`, `min`, and `max` require non-empty lists. `permutation` requires the two
lists to have the same element type; known unequal literal lengths are reported
by the checker.

Range expressions such as `0..n` produce a half-open `List<Int>` containing
`0` through `n - 1`. They are most useful in quantifiers and loop invariants.

## Loop annotations

`while` loops may carry Boolean invariants and an arithmetic variant:

```aether
while i < n
invariant i >= 0
variant n - i
do
  i = i + 1
end
```

The type checker requires each `invariant` to be `Bool` and the `variant` to be
`Int`. The SMT pass proves simple arithmetic decreases when it can. Dynamic or
unsupported cases are checked by runtime diagnostics such as
`LOOP_INVARIANT_FAILED` and `LOOP_VARIANT_NOT_DECREASING`.

## Records

    record Point do
      x: Float
      y: Float
    end

Record literal syntax creates a record from named fields:

    let p1 = Point { x = 0.0, y = 0.0 }

The checker requires every declared field and rejects extra fields.

Record update syntax copies an existing record and replaces named fields:

    let p2 = p1 { x = p1.x + 1.0 }

Positional constructors such as `Point(0.0, 0.0)` also remain supported.

Records have structural equality and are immutable by default. Record literals
create new values; copy-update expressions update existing values. Both forms
return new records.

## Tagged unions

    union Shape do
      case Circle(radius: Float)
      case Rectangle(width: Float, height: Float)
      case Triangle(base: Float, height: Float)
    end

Constructors are accessed as `Shape.Circle(2.0)`. The current implementation
checks match exhaustiveness for statically known `Option<T>`, `Result<T,E>`,
and user-defined union scrutinee types. If the scrutinee type is unknown, the
checker does not guess; a runtime fallback raises `MATCH_NON_EXHAUSTIVE_RUNTIME`
if no arm matches.

## Refinement types

    type Email = String where matches?(self, EMAIL_REGEX)
    type PositiveInt = Int where self > 0
    type Probability = Float where self >= 0.0 and self <= 1.0

Inside the refinement clause, `self` is the candidate value. The predicate is checked at runtime when a value crosses a function or module boundary into the refined type. Inside a function body, the refinement is *assumed* вЂ” the type checker does not re-prove it.

This is intentional: v0.1 traded static guarantees for low complexity. The
current toolchain includes a scoped Z3-backed SMT pass for requires/ensures
clauses that fit a pure Int/Float arithmetic fragment; other refinement
predicates remain runtime checks.

## Capability types

    FileHandle<Read>
    FileHandle<Write>
    FileHandle<ReadWrite>
    Connection<Postgres>
    HttpClient<JsonApi>

The parameter is a phantom tag in the design. Current implementation work
focuses on function `effects` plus the opt-in `--capability-strict` pass
rather than full capability-typed handles.

## Type ascription

    let x: Int = parseInt!("42")    // ascription on `let` вЂ” works in v0.1
    let y = (3.14 as Float)         // вќЊ NOT IN v0.1 вЂ” value-level `as` is parked (see SPEC_ISSUES S-013)

Value-level `as` conversion is design text, not current implementation. There
is no implicit numeric coercion in the current examples.

## Type tests

    if x is Email then ... end

`is` parses and emits as a runtime type-style test for the implemented cases.
Branch-local static narrowing is not implemented.

## Generic functions

function map<T, U>(xs: List<T>, f: function(T) returns U) returns List<U>
  effects pure
  ensures length(result) == length(xs)
    do
      ...
    end

Type parameters are written in angle brackets after the function name. They may
appear in parameters, return type, contracts, and effect rows. Calls may rely on
inference, for example `identity(5)`, or supply explicit type arguments:

```aether
identity<Int>(5)
makeResult<Int, String>(5)
identity<List<Int>>([1, 2])
```

Explicit type arguments are checked statically and erased before runtime.
Square-bracket and turbofish forms such as `identity[Int](5)` and
`identity::<Int>(5)` are not Aether syntax.

The current checker validates supported generic relationships in direct user
function calls, for example rejecting `choose(1, "bad")` for
`function choose<T>(a: T, b: T) returns T`. It does not implement full type
inference for every future language construct.

## Function Type Effects

Function types may include an optional effect clause after the return type:

```aether
function(Int) returns Int effects log
function(Int) returns function(Int) returns Bool effects log effects pure
```

If omitted, the function type defaults to `effects pure`. When a function-typed
parameter is called, its annotated effects must be covered by the enclosing
function's own `effects` clause. For example, calling
`f: function(Int) returns Int effects log` from an `effects pure` function
produces `HIGHER_ORDER_EFFECT_ESCAPE`.

Effect arguments are part of function type compatibility. A parameter declared
as `function(Int) returns String effects net.fetch("https://api.example.com/*")`
accepts a callback whose effect is
`net.fetch("https://api.example.com/users/*")`, but rejects one whose effect is
`net.fetch("https://billing.example.com/*")` with
`FUNCTION_TYPE_EFFECT_MISMATCH`.

## Subtyping

There is no implemented general subtyping system. Refinement-typed parameters
are checked at function boundaries; value-level `as` conversion is not
implemented.

## Inference

Non-empty list literals infer a single element type. Empty list literals need
a contextual type or annotation:

    let xs: List<Int> = []      // works
    let ys = []                 // TYPE_EMPTY_LIST_NEEDS_ANNOTATION

Inside a function body, every `let` binding is inferred from its initializer. Function parameters and return types are never inferred вЂ” they are always written.

## Equality and hashability

This section is design intent, not fully enforced by the current compiler.
Runtime values are Python-backed, so Python equality/hashability behavior can
leak through for collections.

## Disallowed in v0.1

- Higher-kinded types (no `F<_>`).
- Trait/typeclass abstraction.
- Subtyping.
- Implicit numeric coercion.
- Variadic arguments.
- Default argument values.
- Method-call syntax (`x.foo(y)`); use `foo(x, y)`. Field access `x.field` is the only `.` form.
