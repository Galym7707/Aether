# Aether post-v0.3 status

**Date:** 2026-05-08
**Scope:** repository state after Phase 3.5 and Phase 3.6 documentation work.
**Protocol note:** Phase 2 was run under the active `EXPERIMENT.md` protocol
with `codex-current-session`, not the earlier external Claude Opus/Sonnet
lineup.

## Current Gate Snapshot

The current repository has passed the local gates below on Windows from
`C:\Users\galym\Desktop\Aether`:

| Command | Result |
|---|---|
| `python -m py_compile transpiler\aether\agent_sdk.py bench\harness.py tests\test_regressions.py` | pass |
| `python -B tests\test_regressions.py` | pass; `S-012` skipped because Windows has no `SIGALRM` |
| `python -B scripts\run_all.py` | pass: reference `10/10`, bench `8/8`, python equivalents `5/5`, regression PASS, fuzz PASS |
| `python -B validation\run_validation.py` | pass: active validation references `10/10`; 5 deprecated tasks skipped |
| `python -B validation\run_python_validation.py` | pass: python validation references `10/10` |
| `git diff --check` | pass; Windows line-ending warnings only |

## What Exists Now

### Core compiler/runtime

| Area | Status | Evidence |
|---|---|---|
| Lexer/parser/emitter/runtime | Working for current reference, benchmark, and validation corpora. | `scripts/run_all.py`, `validation/run_validation.py` |
| Runtime `requires` / `ensures` contracts | Implemented with structured diagnostics. | `tests/test_regressions.py::test_S001_*` |
| Refinement-typed parameter checks | Implemented at function boundaries. | `tests/test_regressions.py::test_S002_*` |
| Capability gating | Implemented as opt-in `--capability-strict`. | `tests/test_regressions.py::test_capability_*` |
| Parser fuzzer | Wired into `scripts/run_all.py`. | run output: fuzz PASS, 200 rounds x 3 modes |

### v0.3 additions

| Phase item | Status | Evidence |
|---|---|---|
| 3.1 Static effect checking | Implemented by default for `aether check`, `aether run`, `aether test`, harness, and SDK. Direct-call violations use `EFFECT_NOT_COVERED`. | `transpiler/aether/passes/effects.py`; CLI check/run regression tests |
| 3.2 Effect-glob matching | Implemented for precise `net.fetch("...")` rows, concrete strings, and trailing-star globs. | `tests/test_regressions.py::test_S004_*`; `tests/test_effect_row_precision.py` |
| 3.3 Canonical AST round-trip | Implemented in `transpiler/aether/printer.py`; corpus round-trip regression passes. | regression output: 33 corpus programs pass |
| 3.4 Scoped SMT contract pass | Implemented in `transpiler/aether/passes/smt.py`; arithmetic `E0901`/`E0902` fragment only. | `tests/test_regressions.py::test_smt_contract_pass_arithmetic_fragment` |
| 3.5 Agent SDK skeleton | Implemented in `transpiler/aether/agent_sdk.py`; harness delegates core execution/grading to it. | `tests/test_regressions.py::test_agent_sdk_parse_check_run_and_grade` |
| 3.6 Status/closeout docs | Implemented by this update. | `SPEC_ISSUES.md`, `STATUS.md`, `V03_CLOSEOUT.md` |

## Experiment State

### Phase 1 apparatus

- `EXPERIMENT.md` exists and records the active Codex-session protocol.
- `prompt/system_prompt.md` and `prompt/python_system_prompt.md` are the locked
  prompt artifacts for that protocol.
- `bench/tasks/` contains 8 active benchmark tasks: 3 standard stdout tasks and
  5 contract-wedge tasks.
- `bench/CONTRACT_TASKS.md` documents the 5 contract-wedge tasks.

### Phase 2 run

Accepted run directory:

`runs/phase2/20260508_155402_+0600`

`runs/phase2/20260508_155402_+0600/REPORT.md` records:

- Aether first-attempt success: `8/8`.
- Python first-attempt success: `8/8`.
- Gap: `0.0pp`, inconclusive under the pre-registered 8 percentage point
  threshold.
- Aether contract-catch rate on wedge tasks: `5/5`.
- Provider token counts: not available for `codex-current-session`.
- Anomaly scan: clear, 0 anomalies.

This is a single active-model run. It is not evidence for external Claude
Opus/Sonnet performance.

## Known Limits

Open v0.4+ items remain in `SPEC_ISSUES.md`:

- S-005 pattern-match expression helper verbosity.
- S-006 brace record-update literal.
- S-007 generic-function type checking.
- S-009 deterministic time/random mode.
- S-010 compile-cache ergonomics on mounted filesystems.
- S-013 value-level `as` cast.
- S-014 non-zero contract diagnostic positions.
- S-015 contextual reservation of `result`.
- S-016 mangling-collision avoidance.

Additional caveats from current verification:

- Timeout enforcement depends on POSIX `SIGALRM`; Windows regression skips
  `S-012`.
- SMT checking depends on `z3-solver` being importable; unsupported clauses are
  intentionally left to runtime checks.
- Official provider token counts were not available in the accepted Phase 2
  run.

## Quick Verification Commands

From the repository root:

```powershell
python -B scripts\run_all.py
python -B validation\run_validation.py
python -B validation\run_python_validation.py
python -B tests\test_regressions.py
```

Use `python -B` on Windows to avoid stale bytecode issues described in S-010.

## Current Assessment

Aether now has a defensible v0.3 substrate for the scoped claims in the project
plan: default static effect checking, effect glob matching, canonical AST
printing, a small SMT-backed contract fragment, and an SDK entrypoint for
agent integrations. The project is still experimental. The strongest verified
behavior is contract/effect diagnostic feedback on the current corpus; the
weakest areas are still type-system depth, diagnostic source positions, and
some spec forms that remain v0.4+ work.
