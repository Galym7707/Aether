# SPEC_ISSUES - post-v0.3 issue ledger

This file tracks implementation gaps against the Aether design/spec. Items in
the v0.3 scope are now either resolved below or explicitly left outside v0.3 as
v0.4+ work.

Last audited against the repository implementation on 2026-05-08 during Phase
3.6. Evidence referenced here is local repository evidence: source files,
regression tests, and the commands recorded in `STATUS.md` and
`V03_CLOSEOUT.md`.

## Open - v0.4+

### S-005 - Pattern-match expressions allocate a helper function per use site
`match ... do ... end` in expression position lowers to a generated
`def _ae_matchexprN(_ae_scrut)` defined at module top. This is correct but
verbose for nested cases. v0.4+ should consider lowering to an inline closure
expression or using Python pattern matching at emit time.

### S-006 - No support for record-update literal `Foo { x = ... }`
The grammar / `types.md` describe a brace-init form. The current parser does
not accept `Point { x = 1.0, y = 2.0 }`; it parses `{...}` only as a map
literal, and the diagnostic can suggest the wrong fix. Current workaround: use
positional construction such as `Point(1.0, 2.0)`. v0.4+ should either
implement a `RecordLit` AST kind or remove the form from the spec.

### S-007 - Generic functions are accepted but not type-checked
`function map<T, U>(...)` parses, and generic names flow through emission
because they appear only in type positions. v0.4+ should add a type-check pass
that verifies generic parameters are used consistently.

### S-009 - `time.now` and `random` are not seedable for deterministic mode
The runtime still calls Python wall-clock / random behavior directly where
available. v0.4+ should add deterministic-mode hooks for reproducible runs.

### S-010 - CLI compile-cache friction with mounted filesystems
`__pycache__` files on mounted Windows filesystems can create stale-bytecode
friction. Current workaround: run with `python -B` or
`PYTHONDONTWRITEBYTECODE=1`. v0.4+ should make this less visible in launcher
scripts if the CLI packaging grows.

### S-013 - `as` is parsed only as a pattern alias, not a value-level cast
`types.md` describes `let y = (3.14 as Float)` as a legal value-cast form, but
the parser only accepts `as` inside pattern aliases and import aliases. v0.4+
should either implement an `As` expression node and runtime check or remove the
example from the spec.

### S-014 - Contract diagnostic positions are zero
`requires` / `ensures` / refinement failures still commonly report line 0,
column 0 instead of the call site or failing return. The function name,
contract kind, and clause text are present, which is enough for the current
agent loop, but human jump-to-source remains weak. v0.4+ should thread source
positions through runtime contract assertions.

### S-015 - `result` is reserved as a keyword everywhere, not contextually
The lexer reserves `result` so `ensures` clauses can refer to the return value.
This means `let result = computeAnswer()` fails. v0.4+ should make `result`
contextual to `ensures` parsing if the parser architecture permits it.

### S-016 - Mangling collision between `foo?` / `foo_q` and `foo!` / `foo_e`
Predicate/effectful identifiers can collide with user identifiers after
mangling. This is latent in the current corpus. v0.4+ should either use a
non-identifier separator or reject user identifiers that collide after
mangling.

## Resolved

### S-001 - `ensures` clauses fire at runtime (resolved 2026-05-03)
The emitter threads each function's `ensures` clauses through return emission
and raises structured contract diagnostics on failure. Regression coverage:
`tests/test_regressions.py::test_S001_*`.

### S-002 - Refinement-type runtime checks fire at boundaries (resolved 2026-05-03)
The emitter collects `TypeDecl` refinements and inserts
`_ae_check_refinement(...)` at function entry for refined parameters. Runtime
diagnostics use `E0302` for predicate false and `E0303` for predicate crash.
Regression coverage: `tests/test_regressions.py::test_S002_*`.

### S-003 - Higher-order functions work (resolved 2026-05-03; original issue was stale)
Audit confirmed function-typed parameters and stdlib higher-order calls parse,
emit, and execute. The original issue entry was incorrect.

### S-004 - Effect-glob subset matching (resolved 2026-05-08)
`transpiler/aether/passes/effects.py` preserves string arguments in effect
declarations and implements subset checks for broad effects, concrete strings,
and trailing-star globs. Runtime strict mode in
`transpiler/aether/runtime.py` accepts the same argumented effect shape.
Regression coverage: `tests/test_regressions.py::test_S004_*`.

### S-008 - Parser fuzzer added (resolved 2026-05-03)
`scripts/fuzz_parser.py` runs random, mutate, and token-perturbation modes and
is wired into `scripts/run_all.py`. The current fast gate runs 200 rounds per
mode.

### S-011 - Lexer no longer mis-tokenizes `x!=3` (resolved 2026-05-03)
The lexer leaves `!` for the symbol scanner when followed by `=`, so `!=`
lexes as one symbol. Regression coverage:
`tests/test_regressions.py::test_S011_lexer_tight_neq`.

### S-012 - Harness enforces `timeout_ms` on POSIX (resolved 2026-05-03)
`compile_and_run` uses `SIGALRM` where available and returns structured
timeout diagnostic `E0601`. On Windows, `SIGALRM` is unavailable; the current
regression test records that platform limitation as a skip.

### S-017 - Structural AST similarity is not authoritative (resolved 2026-05-03)
The Phase A audit established that structural AST similarity has a high common
floor for this grammar size and should remain a filter, not a contamination
verdict. Pairwise problem-signature checks are the authoritative path.

### S-018 - Capability gating exists as an opt-in static pass (resolved 2026-05-03)
`transpiler/aether/passes/capability.py` checks module-declared capabilities
against function effects when `--capability-strict` is enabled. Regression
coverage: `tests/test_regressions.py::test_capability_*`.

### S-019 - Static effect checking is wired by default (resolved 2026-05-08)
`transpiler/aether/passes/effects.py` walks each `FunctionDecl`, checks direct
calls to known local and stdlib functions, and reports `E0801` when callee
effects are not covered by caller effects. `aether check`, `aether run`,
`aether test`, the benchmark harness, and the agent SDK call this pass by
default. Regression coverage:
`tests/test_regressions.py::test_static_effect_check_blocks_pure_print` and
`tests/test_regressions.py::test_cli_check_rejects_pure_print_before_exec`.

### S-020 - Canonical AST printer round-trips the corpus (resolved 2026-05-08)
`transpiler/aether/printer.py` prints canonical Aether source from parsed ASTs
and provides `strip_positions` / `ast_round_trips` helpers. The regression
suite reparses every `reference/`, `bench/tasks/`, and `validation/tasks/`
program and compares position-stripped ASTs. Current checked corpus size in
the regression output: 33 programs.

### S-021 - Scoped SMT contract pass exists for arithmetic clauses (resolved 2026-05-08)
`transpiler/aether/passes/smt.py` uses `z3-solver` when installed to classify
pure arithmetic `requires` / `ensures` clauses over numeric parameters and
simple arithmetic lets. Statically disproved clauses produce `E0901`;
statically proved clauses produce informational `E0902` for direct pass
callers and remain non-fatal in CLI/harness integration. Unsupported clauses
fall back to runtime checks. Regression coverage:
`tests/test_regressions.py::test_smt_contract_pass_arithmetic_fragment` and
`tests/test_regressions.py::test_cli_run_rejects_smt_disproof_before_exec`.

### S-022 - Agent SDK surface exists (resolved 2026-05-08)
`transpiler/aether/agent_sdk.py` exposes typed, structured functions for
parse/check/run and benchmark grading without CLI parsing:
`parse_source`, `check_ast`, `check_source`, `run_source`,
`grade_candidate_source`, `grade_candidate_file`, and
`run_python_equivalent_file`. `bench/harness.py` now delegates core execution
and grading behavior to this SDK while preserving its CLI wrappers. Regression
coverage: `tests/test_regressions.py::test_agent_sdk_parse_check_run_and_grade`.
