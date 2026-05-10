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

## Records

    record Point do
      x: Float
      y: Float
    end

Records have structural equality and are immutable by default. In v0.1, construct
records positionally — the record decl emits a constructor with parameters in
declared order:

    let p1 = Point(0.0, 0.0)
    let p2 = Point(p1.x + 1.0, p1.y)        // works in v0.1

A planned brace-init form is **not in v0.1** (see SPEC_ISSUES S-006):

    let p2 = Point { x = p.x + 1.0, y = p.y }   // ❌ parses as map literal, will fail

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

Inside the refinement clause, `self` is the candidate value. The predicate is checked at runtime when a value crosses a function or module boundary into the refined type. Inside a function body, the refinement is *assumed* — the type checker does not re-prove it.

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

    let x: Int = parseInt!("42")    // ascription on `let` — works in v0.1
    let y = (3.14 as Float)         // ❌ NOT IN v0.1 — value-level `as` is parked (see SPEC_ISSUES S-013)

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

Inside a function body, every `let` binding is inferred from its initializer. Function parameters and return types are never inferred — they are always written.

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
