# v0.3 Close-out - what shipped, what did not, and why

**Date:** 2026-05-08
**Scope:** Phase 3 items 3.1 through 3.6 from the current project plan.

## Gate Result

Phase 3 items are either implemented or explicitly deferred in
`SPEC_ISSUES.md` as v0.4+ work.

Local verification on Windows:

| Command | Result |
|---|---|
| `python -m py_compile transpiler\aether\agent_sdk.py bench\harness.py tests\test_regressions.py` | pass |
| `python -B tests\test_regressions.py` | pass; `S-012` timeout test skipped because Windows has no `SIGALRM` |
| `python -B scripts\run_all.py` | pass: reference `10/10`, bench `8/8`, python equivalents `5/5`, regression PASS, fuzz PASS |
| `python -B validation\run_validation.py` | pass: `10/10` active validation references |
| `python -B validation\run_python_validation.py` | pass: `10/10` python validation references |
| `git diff --check` | pass; Windows line-ending warnings only |

## What Shipped

### 3.1 Static effect checking

Shipped.

New pass:

- `transpiler/aether/passes/effects.py`

Behavior:

- Walks every `FunctionDecl`.
- Checks direct calls to known local functions, record constructors, union
  constructors, and stdlib functions.
- Verifies the callee's declared effects are covered by the caller's declared
  effects.
- Emits diagnostic `E0801`, category `effect`, on violation.
- Is wired by default into `aether check`, `aether run`, `aether test`, the
  benchmark harness, and the agent SDK.

Evidence:

- `tests/test_regressions.py::test_static_effect_check_blocks_pure_print`
- `tests/test_regressions.py::test_cli_check_rejects_pure_print_before_exec`

Known limits:

- Unknown callees, higher-order function parameters, and dynamic field calls
  are intentionally left for future type analysis/runtime behavior.

### 3.2 Effect-glob matching

Shipped.

Behavior:

- `net.fetch` covers narrower declarations such as
  `net.fetch("https://api.x/users/42")`.
- `net.fetch("https://api.x/*")` covers matching concrete URLs and narrower
  trailing-star patterns.
- Narrower caller declarations do not cover broader callee declarations.
- Runtime strict effect matching accepts the legacy tuple format and the new
  argumented effect shape.

Evidence:

- `tests/test_regressions.py::test_S004_static_effect_glob_matching`
- `tests/test_regressions.py::test_S004_runtime_effect_glob_matching`

Known limits:

- General glob-subset solving is intentionally out of scope. The implementation
  supports exact match, concrete-string coverage, and trailing-star subset
  cases.

### 3.3 Canonical AST round-trip

Shipped.

New module:

- `transpiler/aether/printer.py`

Behavior:

- Prints canonical Aether source from parsed ASTs.
- Provides position-stripping helpers for AST comparison.
- Regression test parses, prints, reparses, and compares every corpus program
  under `reference/`, `bench/tasks/`, and `validation/tasks/`.

Evidence:

- `tests/test_regressions.py::test_canonical_ast_roundtrip_corpus`
- Current regression output: `canonical AST round-trip: 33 corpus programs pass`

Known limits:

- The printer is canonical for the currently exercised AST surface. It should
  be extended alongside any future grammar additions.

### 3.4 Scoped SMT contract pass

Shipped.

New pass:

- `transpiler/aether/passes/smt.py`

Behavior:

- Uses `z3-solver` when importable.
- Handles a scoped arithmetic fragment over `Int`/`Float` parameters, simple
  arithmetic `let` bindings, comparisons, and boolean connectives.
- Emits `E0901` for statically disproved contract clauses.
- Emits informational `E0902` for statically proved clauses when called
  directly.
- Leaves unsupported clauses to existing runtime contract checks.
- Is wired into CLI/harness/SDK as a pre-execution check for error-severity
  diagnostics.

Evidence:

- `tests/test_regressions.py::test_smt_contract_pass_arithmetic_fragment`
- `tests/test_regressions.py::test_cli_run_rejects_smt_disproof_before_exec`

Known limits:

- This is not a full SMT integration.
- Calls, strings, collections, conditionals, field/index access, and other
  unsupported syntax are skipped by design.
- If `z3-solver` is unavailable, the pass returns no SMT diagnostics.

### 3.5 Agent SDK skeleton

Shipped.

New module:

- `transpiler/aether/agent_sdk.py`

Public API:

- `AetherResult`
- `parse_source`
- `check_ast`
- `check_source`
- `run_source`
- `grade_candidate_source`
- `grade_candidate_file`
- `run_python_equivalent_file`
- `format_diagnostic_stderr`

Harness integration:

- `bench/harness.py` delegates compile/run/grading behavior to the SDK.
- Existing harness wrapper functions and CLI commands remain available.

Evidence:

- `tests/test_regressions.py::test_agent_sdk_parse_check_run_and_grade`
- `scripts/run_all.py` still passes benchmark/reference/python-equivalent gates.

Known limits:

- This is a skeleton API surface, not a full remote agent service.
- It exposes current compiler/harness behavior; future consumers may need
  versioning once the API is used outside this repository.

### 3.6 SPEC_ISSUES and STATUS update

Shipped by this documentation update.

Updated/created files:

- `SPEC_ISSUES.md`
- `STATUS.md`
- `V03_CLOSEOUT.md`

## What Did Not Ship

The following are explicitly outside v0.3 and remain open as v0.4+ work in
`SPEC_ISSUES.md`:

| ID | Deferred item | Reason |
|---|---|---|
| S-005 | Pattern-match expression helper verbosity | Correctness is not blocked; this is emitter ergonomics. |
| S-006 | Brace record-update literal | Requires grammar/AST/emitter expansion outside the v0.3 scope. |
| S-007 | Generic-function type checking | Requires a real type-check pass, not a small patch. |
| S-009 | Deterministic time/random mode | Not needed for current gates; should be designed with runtime config. |
| S-010 | Compile-cache launcher ergonomics | Workaround exists with `python -B`; packaging-level work deferred. |
| S-013 | Value-level `as` cast | Requires expression grammar and runtime semantics. |
| S-014 | Contract diagnostic source positions | Important, but not required for current agent loop correctness. |
| S-015 | Contextual `result` keyword | Requires parser/lexer coordination. |
| S-016 | Mangling-collision avoidance | Latent issue; no current corpus failure. |

## Relationship To Phase 2

The accepted Phase 2 run is:

`runs/phase2/20260508_155402_+0600`

Its report records:

- Aether first-attempt success: `8/8`.
- Python first-attempt success: `8/8`.
- Aggregate gap: `0.0pp`.
- Result: inconclusive under the pre-registered 8 percentage point threshold.
- Aether contract-catch rate: `5/5`.
- Provider token counts: not available.
- Anomaly scan: clear.

This closeout does not reinterpret Phase 2 as evidence that Aether is
universally better than Python. It records that the v0.3 substrate now supports
the specific compiler/tooling claims scoped in Phase 3.

## Final Evaluation

### Summary Judgment

Partially demonstrated.

The v0.3 engineering claims are demonstrated on the current local corpus:
static effect checks, effect-glob matching, canonical AST round-trip, scoped SMT
contract checking, and SDK-based harness execution all have regression coverage
and passed the current gate commands.

The broader experimental claim remains inconclusive from the accepted Phase 2
run because both Aether and Python scored `8/8` first-attempt success under the
active Codex-session protocol.

### Strongest Demonstrated Strength

Aether's strongest demonstrated strength in this repository state is structured
diagnostic enforcement for correctness constraints: contract/refinement
diagnostics on wedge tasks, static `E0801` effect diagnostics, and scoped SMT
`E0901` diagnostics before execution.

### Biggest Current Weakness

The biggest current weakness is diagnostic precision and language-depth
coverage. Contract runtime failures still often report line 0, column 0, and
generic type checking / several spec forms remain v0.4+ work.

### Recommended Next Step

Improve diagnostic source positions for contract/refinement failures
(`S-014`). This would make the existing contract and agent feedback loop more
useful without expanding language scope.
