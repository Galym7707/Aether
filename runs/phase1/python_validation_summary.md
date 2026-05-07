# Phase 1.4 Python Baseline Validation Summary

Date: 2026-05-07 18:08:32 +06:00

## Status

Phase 1.4 is completed only as a Codex surrogate run.

This is a protocol deviation requested by the user on 2026-05-07: run the
Python baseline validation with the current Codex session instead of the
originally planned Claude model pair.

The original Phase 1.4 gate is not confirmed:

- `claude-sonnet-4-6`: not confirmed from the current benchmark run.
- `claude-opus-4-6`: not confirmed from the current benchmark run.

Reason: the local Claude CLI is installed but not authenticated, and the Codex
CLI binary is not executable from this PowerShell environment.

## Prompt

Python system prompt:

    prompt/python_system_prompt.md

Prompt size parity check from the local repository:

| Prompt | Chars | Whitespace Tokens | Lines |
|---|---:|---:|---:|
| `prompt/system_prompt.md` | 5613 | 825 | 164 |
| `prompt/python_system_prompt.md` | 5237 | 818 | 209 |

## Codex Surrogate Run

Model/run label:

    codex-current-session

Output directory:

    runs/phase1/python_validation/codex-current-session/

Important limitation:

This run was produced by the active Codex session, not by a separate blind model
subprocess. It is therefore not directly comparable to the preregistered
Claude Opus/Sonnet validation. Treat it as a local prompt/grader apparatus
check, not as the original model gate.

## Task Results

Command:

    python -B scripts\grade_phase1_python.py --model codex-current-session

Result:

| Task | First-Attempt Result | Stage | Notes |
|---|---|---|---|
| v01_tagged_union_evaluator | pass | exec | stdout matched |
| v02_map_filter_chain | pass | exec | stdout matched |
| v03_lookup_with_default | pass | exec | stdout matched |
| v04_result_threading | pass | exec | stdout matched |
| v05_shape_area | pass | exec | stdout matched |
| v06_record_distance | pass | exec | stdout matched |
| v07_partition_by_parity | pass | exec | stdout matched |
| v08_parse_and_double | pass | exec | stdout matched |
| v09_gcd_with_contracts | pass | exec | stdout matched |
| v10_caesar_shift | pass | exec | stdout matched |

Codex surrogate score:

    10 / 10 = 100.0%

## Original Model Blockers

Command:

    claude auth status

Observed earlier in this workspace:

    {
      "loggedIn": false,
      "authMethod": "none",
      "apiProvider": "firstParty"
    }

Command:

    codex --version

Observed in this workspace:

    Program 'codex.exe' failed to run: Access is denied

No `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` environment variable was available
when checked.

## Verification Commands

Command:

    python -B validation\run_python_validation.py

Result:

    10/10 python validation references pass

Command:

    python -B validation\run_validation.py

Result:

    10/10 validation references pass
    5 deprecated task(s) skipped

Command:

    python -B scripts\run_all.py

Result:

    reference: 10/10
    bench: 8/8
    python eq: 5/5
    regression: PASS
    fuzz: PASS (200 rounds x 3 modes)

## Gate Verdict

Codex surrogate validation passes at 100.0%.

Original Phase 1.4 gate for `claude-opus-4-6` and `claude-sonnet-4-6` is not
confirmed from the current benchmark run.

Do not enter Phase 1.5 under the original protocol unless the user explicitly
accepts this Codex surrogate run as a replacement for the Claude model pair, or
unless the Claude model validation is later completed.
