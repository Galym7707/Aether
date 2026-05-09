# Aether Standard Library (v0.1)

Brutally minimal. The list is small enough that a model can hold all of it in working memory.

## Core types (re-exported, always in scope)

    Int Float Bool String Bytes Unit
    List<T> Map<K,V> Set<T>
    Option<T> Result<T,E>

The constructors `Some`, `None`, `Ok`, `Err` are also always in scope.

## List<T>

    function length<T>(xs: List<T>) returns Int
      effects pure
      ensures result >= 0

    function empty?<T>(xs: List<T>) returns Bool
      effects pure
      ensures result == (length(xs) == 0)

    function head<T>(xs: List<T>) returns Option<T>
      effects pure

    function tail<T>(xs: List<T>) returns List<T>
      effects pure
      requires not empty?(xs)
      ensures length(result) == length(xs) - 1

    function append<T>(xs: List<T>, x: T) returns List<T>
      effects pure
      ensures length(result) == length(xs) + 1

    function prepend<T>(x: T, xs: List<T>) returns List<T>
      effects pure
      ensures length(result) == length(xs) + 1

    function concat<T>(xs: List<T>, ys: List<T>) returns List<T>
      effects pure
      ensures length(result) == length(xs) + length(ys)

    function get<T>(xs: List<T>, i: Int) returns Option<T>
      effects pure

    function safeAt<T>(xs: List<T>, index: Int) returns Option<T>
      effects pure

    function updateAt<T>(xs: List<T>, index: Int, value: T) returns Result<List<T>, String>
      effects pure
      ensures isOk?(result) implies length(unwrapOr(result, xs)) == length(xs)

    function safeSlice<T>(xs: List<T>, start: Int, end: Int) returns Result<List<T>, String>
      effects pure

    function inBounds<T>(xs: List<T>, index: Int) returns Bool
      effects pure
      ensures result == (index >= 0 and index < length(xs))

    function validSliceBounds<T>(xs: List<T>, start: Int, end: Int) returns Bool
      effects pure
      ensures result == (start >= 0 and start <= end and end <= length(xs))

    function map<T, U>(xs: List<T>, f: function(T) returns U) returns List<U>
      effects pure
      ensures length(result) == length(xs)

    function filter<T>(xs: List<T>, p: function(T) returns Bool) returns List<T>
      effects pure
      ensures length(result) <= length(xs)

    function foldLeft<T, A>(xs: List<T>, z: A, f: function(A, T) returns A) returns A
      effects pure

    function reverse<T>(xs: List<T>) returns List<T>
      effects pure
      ensures length(result) == length(xs)

    function range(lo: Int, hi: Int) returns List<Int>
      effects pure
      requires lo <= hi
      ensures length(result) == hi - lo

## Map<K,V>

    function size<K, V>(m: Map<K, V>) returns Int
      effects pure
      ensures result >= 0

    function get<K, V>(m: Map<K, V>, k: K) returns Option<V>
      effects pure

    function set<K, V>(m: Map<K, V>, k: K, v: V) returns Map<K, V>
      effects pure
      ensures size(result) >= size(m)

    function remove<K, V>(m: Map<K, V>, k: K) returns Map<K, V>
      effects pure
      ensures size(result) <= size(m)

    function has?<K, V>(m: Map<K, V>, k: K) returns Bool
      effects pure

    function keys<K, V>(m: Map<K, V>) returns List<K>
      effects pure

    function values<K, V>(m: Map<K, V>) returns List<V>
      effects pure

## Set<T>

    function size<T>(s: Set<T>) returns Int
      effects pure
    function add<T>(s: Set<T>, x: T) returns Set<T>
      effects pure
    function remove<T>(s: Set<T>, x: T) returns Set<T>
      effects pure
    function contains?<T>(s: Set<T>, x: T) returns Bool
      effects pure

## String

    function length(s: String) returns Int
      effects pure
      ensures result >= 0

    function slice(s: String, lo: Int, hi: Int) returns String
      effects pure
      requires 0 <= lo and lo <= hi and hi <= length(s)

    function split(s: String, sep: String) returns List<String>
      effects pure

    function join(parts: List<String>, sep: String) returns String
      effects pure

    function contains?(s: String, needle: String) returns Bool
      effects pure

    function trim(s: String) returns String
      effects pure

    function toLower(s: String) returns String
      effects pure
    function toUpper(s: String) returns String
      effects pure

    function replace(s: String, from: String, to: String) returns String
      effects pure

    function startsWith?(s: String, prefix: String) returns Bool
      effects pure
    function endsWith?(s: String, suffix: String) returns Bool
      effects pure

    function parseInt(s: String) returns Result<Int, String>
      effects pure
    function parseFloat(s: String) returns Result<Float, String>
      effects pure

    function intToString(n: Int) returns String
      effects pure

## IO

    function print(s: String) returns Unit
      effects log

    function readLine() returns Result<String, String>
      effects log

    function readFile(path: String) returns Result<String, String>
      effects fs.read

    function writeFile(path: String, contents: String) returns Result<Unit, String>
      effects fs.write

## Time

    record Instant do
      epochMillis: Int
    end

    record Duration do
      millis: Int
    end

    function now() returns Instant
      effects time.now

    function plus(t: Instant, d: Duration) returns Instant
      effects pure

    function minus(a: Instant, b: Instant) returns Duration
      effects pure

## Hash

    function sha256(b: Bytes) returns Bytes
      effects pure
    function sha1(b: Bytes) returns Bytes
      effects pure
    function md5(b: Bytes) returns Bytes
      effects pure

## Math

    function abs(x: Int) returns Int
      effects pure
    function min(a: Int, b: Int) returns Int
      effects pure
    function max(a: Int, b: Int) returns Int
      effects pure
    function floor(x: Float) returns Int
      effects pure
    function ceil(x: Float) returns Int
      effects pure
    function pow(base: Float, exp: Float) returns Float
      effects pure
    function sqrt(x: Float) returns Float
      effects pure
      requires x >= 0.0

## Result / Option helpers

    function isOk<T, E>(r: Result<T, E>) returns Bool
      effects pure
    function isOk?<T, E>(r: Result<T, E>) returns Bool
      effects pure
    function isErr<T, E>(r: Result<T, E>) returns Bool
      effects pure
    function isErr?<T, E>(r: Result<T, E>) returns Bool
      effects pure
    function unwrapOrResult<T, E>(r: Result<T, E>, default: T) returns T
      effects pure
    function mapResult<T, U, E>(r: Result<T, E>, f: function(T) returns U) returns Result<U, E>
      effects pure
    function mapErr<T, E, F>(r: Result<T, E>, f: function(E) returns F) returns Result<T, F>
      effects pure
    function andThenResult<T, U, E>(r: Result<T, E>, f: function(T) returns Result<U, E>) returns Result<U, E>
      effects pure
    function expectOk<T, E>(r: Result<T, E>, message: String) returns T
      effects pure

    function isSome<T>(o: Option<T>) returns Bool
      effects pure
    function isSome?<T>(o: Option<T>) returns Bool
      effects pure
    function isNone<T>(o: Option<T>) returns Bool
      effects pure
    function isNone?<T>(o: Option<T>) returns Bool
      effects pure
    function unwrapOr<T>(o: Option<T>, default: T) returns T
      effects pure
    function unwrapOrElse<T>(o: Option<T>, default: T) returns T
      effects pure
    function mapOption<T, U>(o: Option<T>, f: function(T) returns U) returns Option<U>
      effects pure
    function andThenOption<T, U>(o: Option<T>, f: function(T) returns Option<U>) returns Option<U>
      effects pure
    function expectSome<T>(o: Option<T>, message: String) returns T
      effects pure

`isOk?`, `isErr?`, `isSome?`, `isNone?`, and `unwrapOrElse` are retained for
compatibility. New AI-generated code should prefer the explicit non-`?`
helpers above and exhaustive `match`.

`mapOption`, `andThenOption`, `mapResult`, `mapErr`, and `andThenResult` are
pure only when their callback is pure. The current static checker propagates
declared effects from named callback functions passed to these helpers. If a
callback declares `effects log`, `effects fs.read`, or another effect not
covered by the enclosing function, the checker emits
`HIGHER_ORDER_EFFECT_ESCAPE`.

## What is *not* in v0.1

- Regex.
- JSON parser/printer (the AST tooling has its own; user code does not get one).
- Crypto beyond hash digests.
- Any kind of async / channel / actor primitive.
- Mutable collections (`var` of a `List` is allowed but operations are still pure-functional).
- Numeric tower (no `BigInt`, `Decimal`, `Rational`).

## Naming and overloading

There is *no* function overloading. `length` is defined separately for `List<T>` and `String`, and the parser dispatches by argument type at the call site. All other names are unique.
