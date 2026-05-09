# Aether Effect System (v0.1)

Every function declares its effects. Pure functions write `effects pure` (the explicit form is required — there is no implicit-pure).

An effect is a dotted path: `category.action` or `category.action(arg)`.

## Effect lattice

    pure                 — no observable side effects
    fs.read              — reads from the filesystem
    fs.write             — writes to the filesystem
    net.fetch(url-glob)  — performs an outbound network request matching the glob
    net.serve(port)      — accepts inbound network connections on a port
    db.read              — reads from the configured database
    db.write             — writes to the configured database
    time.now             — observes wall-clock time
    time.sleep           — yields execution to the scheduler
    random               — consumes the random source
    log                  — writes to a structured log sink
    mutate(name)         — mutates a named module-level binding
    panic                — may abort with a structured panic

In v0.1 these were tracked as opaque strings. The current checker preserves
string arguments for effects such as `net.fetch("https://api.x/*")` and
supports prefix/glob-aware subset checks for direct function calls. The runtime
strict checker keeps the same compatibility rule for observed effects.

## Composition rule

A function `f` may invoke another function `g` only if every effect in `g`'s declared set is also in `f`'s declared set, **except** that `pure` is the bottom element: a `pure` function may only call `pure` functions.

The checker enforces this conservatively: dotted path prefixes are allowed, an
unargumented caller declaration such as `net.fetch` covers narrower
argumented callee declarations, and a caller glob can cover concrete matching
URLs or a narrower trailing-star glob. The reverse direction is rejected.

For the implemented higher-order Option/Result helpers (`mapOption`,
`andThenOption`, `mapResult`, `mapErr`, and `andThenResult`), named callback
functions contribute their declared effects to the enclosing function. A pure
function that calls `mapOption(Some(1), logValue)` is rejected if `logValue`
declares `effects log`. The diagnostic code is
`HIGHER_ORDER_EFFECT_ESCAPE`. Unknown function-valued parameters and dynamic
callbacks remain a prototype limitation.

## Capability gating

Effects are *type-level*. To actually perform an effect, the function must be invoked from a module that holds the corresponding capability:

    Effect          Required capability
    fs.read         fs
    fs.write        fs
    net.fetch       net
    net.serve       net
    db.read         db
    db.write        db
    time.now        time
    time.sleep      time
    random          random
    log             log
    mutate(_)       (none — module-local)
    panic           (none — always available)

A module declares the capabilities it needs:

    module BillingService
      requires capability db
      requires capability net
      requires capability log
      exports processInvoice
    end

The current implementation exposes capability checking as an opt-in static CLI
pass through `--capability-strict`. Programs without a `module` declaration have
no declared capabilities under that pass. Runtime capability grants are still
not a complete production security boundary.

## Default effect annotations on standard library functions

See `stdlib.md` for the full list. A few high-frequency examples:

    function readFile(path: String) returns Result<String, IoError>
      effects fs.read

    function writeFile(path: String, contents: String) returns Result<Unit, IoError>
      effects fs.write

    function now() returns Instant
      effects time.now

    function print(s: String) returns Unit
      effects log

## Why effects are first-class for AI generation

A model proposing a function body must declare which effects it performs. If
the body directly calls a known function, or passes a named effectful callback
to a supported Option/Result helper, the static effect checker rejects missing
effect declarations with a structured error. This makes "I think this function
is pure" a checkable claim for the implemented direct and named-callback cases.
