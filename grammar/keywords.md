# Aether Keywords (v0.1)

Total: 49 reserved words. Locked for v0.1.

Every keyword is a fully spelled English-style word that maps to common natural-language tokens, so model embeddings recall them reliably. No symbolic operators are reserved beyond the standard arithmetic, comparison, and assignment set.

## Declarations

| Keyword     | Meaning                                                                  |
|-------------|--------------------------------------------------------------------------|
| `module`    | Begins a module declaration; closes with `end`.                          |
| `import`    | Imports another module by dotted path.                                   |
| `exports`   | Lists the public names a module exposes.                                 |
| `requires`  | (capability form) Lists capabilities the module needs to be granted.     |
| `function`  | Declares a function.                                                     |
| `type`      | Declares a named type, optionally with refinement clause.                |
| `record`    | Declares a record (named struct of fields).                              |
| `union`     | Declares a tagged union type.                                            |
| `let`       | Introduces an immutable binding.                                         |
| `var`       | Introduces a mutable binding (rare; only inside `do`/`end` blocks).      |
| `const`     | Introduces a module-level compile-time constant.                         |

## Function clauses

| Keyword     | Meaning                                                                  |
|-------------|--------------------------------------------------------------------------|
| `returns`   | Annotates the return type of a function.                                 |
| `requires`  | (contract form) Precondition expression on parameters.                   |
| `ensures`   | Postcondition expression; may reference `result` and `old(x)`.           |
| `effects`   | Lists the effects this function may perform.                             |
| `do`        | Opens a function or block body.                                          |
| `end`       | Closes a function, block, module, type, or match.                        |

`requires` is overloaded between *capability requires* (module level) and *contract requires* (function clause). The overload is unambiguous because the surrounding context fixes which form is legal.

## Control flow

| Keyword     | Meaning                                                                  |
|-------------|--------------------------------------------------------------------------|
| `if`        | Conditional. Has both expression form and statement form.                |
| `then`      | Separator after the `if` condition.                                      |
| `else`      | Alternative branch.                                                      |
| `elif`      | Else-if chain.                                                           |
| `match`     | Pattern match expression/statement.                                      |
| `case`      | Pattern arm in a match.                                                  |
| `for`       | Iteration over an iterable.                                              |
| `in`        | Used inside `for`, also membership test inside expressions.              |
| `forall`    | Quantifier expression over a list: `forall x in xs: predicate`.          |
| `exists`    | Quantifier expression over a list: `exists x in xs: predicate`.          |
| `while`     | Loop while a condition holds.                                            |
| `break`     | Exit the innermost loop.                                                 |
| `continue`  | Skip to the next iteration of the innermost loop.                        |
| `return`    | Return a value from a function.                                          |

## Type / pattern keywords

| Keyword     | Meaning                                                                  |
|-------------|--------------------------------------------------------------------------|
| `where`     | Refinement clause on a type.                                             |
| `as`        | Type ascription / pattern binding.                                       |
| `is`        | Type test (`x is Email`).                                                |
| `_`         | Wildcard pattern.                                                        |

## Literals & identifiers

| Keyword     | Meaning                                                                  |
|-------------|--------------------------------------------------------------------------|
| `true`      | Boolean literal.                                                         |
| `false`     | Boolean literal.                                                         |
| `null`      | The single inhabitant of `Unit?`. Not used for missing values — use `Option`. |
| `self`      | Used inside a refinement to refer to the candidate value.                |
| `result`    | Used inside `ensures` to refer to the function's return value.           |
| `old`       | Used inside `ensures`: `old(expr)` is the value of `expr` at function entry. |

## Logical / boolean operators (spelled, not symbolic)

| Keyword     | Meaning                                                                  |
|-------------|--------------------------------------------------------------------------|
| `and`       | Short-circuit conjunction.                                               |
| `or`        | Short-circuit disjunction.                                               |
| `not`       | Logical negation.                                                        |
| `implies`   | Material implication. `a implies b` ≡ `not a or b`.                      |

## Effects (lexed as keywords for parser simplicity)

| Keyword     | Meaning                                                                  |
|-------------|--------------------------------------------------------------------------|
| `pure`      | Explicit annotation that a function has no effects.                      |

(`fs.read`, `net.fetch`, etc. are dotted paths, not single keywords. See `effects.md`.)

## Reserved but unused (parked for v0.2+)

`async`, `await`, `yield`, `spawn`, `with`, `defer`, `trait`, `impl`.
These are reserved so v0.1 programs are forward-compatible.

## Naming conventions baked into the parser

- Identifiers end with `?` if and only if they are predicates returning `Bool`.
- Identifiers end with `!` if and only if they perform a non-pure effect or panic on failure.
- Constructor / type names start with an uppercase letter; values and functions start with lowercase.

These conventions are syntactic: the lexer accepts `?` and `!` as identifier-trailing characters.

## Identifiers that *aren't* keywords but conflict with mainstream languages

Aether deliberately does not reserve: `class`, `def`, `struct`, `interface`, `trait`, `enum`, `let-mut`, `var-let`. If a user wants to define an identifier called `class`, they may.

## Index of keyword categories used by the parser

The parser identifies a top-level construct by its first keyword:

    module | import | function | type | record | union | const

Inside a function body, a statement begins with one of:

    let | var | if | match | for | while | break | continue | return

This makes parsing LL(1).
