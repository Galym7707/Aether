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

In v0.1 these are tracked as opaque strings — the runtime stores the declared set and asserts that operations not listed in the set are not invoked at runtime when running in `--effect-strict` mode. Static enforcement of subset relations on dotted paths (e.g. `net.fetch("https://api.x/*")` ⊆ `net.fetch`) is parked for v0.2.

## Composition rule

A function `f` may invoke another function `g` only if every effect in `g`'s declared set is also in `f`'s declared set, **except** that `pure` is the bottom element: a `pure` function may only call `pure` functions.

The type checker enforces this conservatively in v0.1: literal effect strings are compared as plain strings.

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

The runtime grants only declared capabilities. A module that doesn't request `net` cannot make network calls even if its dependencies declare a `net.fetch` effect: those dependencies must be loaded under a module that *does* hold `net`, and the effect propagates as a tracked permission.

In v0.1 the capability check is a runtime assertion at module load time and at the first effect invocation. Static analysis is parked.

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

A model proposing a function body must declare which effects it performs. If the body ends up calling something with effects not declared, the type checker rejects it with a structured error pointing to the call site. This makes "I think this function is pure" a checkable claim, which is the foundation for safe composition of generated functions.
