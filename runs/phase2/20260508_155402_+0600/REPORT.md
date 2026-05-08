# Phase 2.3 Report

Run directory: `runs/phase2/20260508_155402_+0600`

Protocol source: `EXPERIMENT.md`

Accepted run git head recorded in `MANIFEST.json`:
`d9fb5c3255a8c99aee95cbeec528f3988331244a`

Reporting artifact source files:

- `SUMMARY.json`
- `ANOMALY_SCAN.json`
- `MANIFEST.json`
- `EXPERIMENT_SNAPSHOT.md`
- `bench/tasks/*/grader.json`

This report covers the accepted run only. The earlier
`runs/phase2/20260508_154129_+0600` run is retained as historical evidence and
marked superseded.

## Scope

The active pre-registration contains one model label:
`codex-current-session`. The earlier Claude Opus/Sonnet model lineup is not in
the active protocol version and was not run. The exact backend model identifier
for `codex-current-session` is not exposed to repository scripts.

The production benchmark contains 8 tasks:

- 3 standard stdout tasks: `t03_count_vowels`, `t04_balanced_brackets`,
  `t05_safe_average`
- 5 contract-wedge tasks: `t06_contract_non_empty_minimum`,
  `t07_contract_sorted_binary_search`, `t08_contract_positive_divisor`,
  `t09_contract_bounded_index_update`,
  `t10_contract_normalized_probability`

Phase 2.2 anomaly status for this run: `clear`, with `0` anomalies.

## Headline Table

Only one model row is available under the active protocol, so this is a
model-by-language table, not a two-external-model table.

| Model | Aether v0.2 first-attempt success | Python baseline first-attempt success | Gap |
|---|---:|---:|---:|
| `codex-current-session` | `8/8` = `100.0%` | `8/8` = `100.0%` | `0.0pp` |

Per `EXPERIMENT.md`, an aggregate first-attempt gap under `8` percentage points
is inconclusive. This run's aggregate gap is `0.0pp`, so the headline result is
inconclusive.

## Secondary Metrics

### Within-3-Retries Success

| Model | Language | Success within 3 retries | Total tasks | Rate | Retries used |
|---|---|---:|---:|---:|---:|
| `codex-current-session` | Aether v0.2 | `8` | `8` | `100.0%` | `0` |
| `codex-current-session` | Python baseline | `8` | `8` | `100.0%` | `0` |

All accepted-run candidates succeeded on attempt 0. No fix-loop retry was used
in this accepted run.

### Token Counts To Success

Provider/tool-reported token counts are unavailable for
`codex-current-session`; every provider token field in `SUMMARY.json` is
`not_available`. The table below includes the non-official whitespace estimates
saved by the runner. These estimates are not the official token metric.

| Model | Language | Provider input tokens | Provider output tokens | Provider total tokens | Whitespace-estimated input | Whitespace-estimated output | Whitespace-estimated total |
|---|---|---:|---:|---:|---:|---:|---:|
| `codex-current-session` | Aether v0.2 | `not_available` | `not_available` | `not_available` | `7251` | `766` | `8017` |
| `codex-current-session` | Python baseline | `not_available` | `not_available` | `not_available` | `7195` | `668` | `7863` |

Official total tokens to success: not confirmed from the current benchmark run.

### Per-Task Results

| Task | Category | Aether attempts | Aether final verdict | Python attempts | Python final verdict |
|---|---|---:|---|---:|---|
| `t03_count_vowels` | standard | `1` | pass | `1` | pass |
| `t04_balanced_brackets` | standard | `1` | pass | `1` | pass |
| `t05_safe_average` | standard | `1` | pass | `1` | pass |
| `t06_contract_non_empty_minimum` | contract-wedge | `1` | pass | `1` | pass |
| `t07_contract_sorted_binary_search` | contract-wedge | `1` | pass | `1` | pass |
| `t08_contract_positive_divisor` | contract-wedge | `1` | pass | `1` | pass |
| `t09_contract_bounded_index_update` | contract-wedge | `1` | pass | `1` | pass |
| `t10_contract_normalized_probability` | contract-wedge | `1` | pass | `1` | pass |

## Contract-Catch Rate

Contract-catch rate is defined in `EXPERIMENT.md` for the Aether wedge tasks:
count a wedge task as caught when the Aether candidate is graded successful
because it rejects the bad input or invalid state with the expected non-zero
exit code and expected diagnostic pattern/code.

| Task | Aether exit code | Diagnostic code | Diagnostic category | Counted as Aether contract catch |
|---|---:|---|---|---|
| `t06_contract_non_empty_minimum` | `2` | `E0302` | `refinement` | yes |
| `t07_contract_sorted_binary_search` | `2` | `E0301` | `contract` | yes |
| `t08_contract_positive_divisor` | `2` | `E0302` | `refinement` | yes |
| `t09_contract_bounded_index_update` | `2` | `E0301` | `contract` | yes |
| `t10_contract_normalized_probability` | `2` | `E0301` | `contract` | yes |

Aether contract-catch rate: `5/5` = `100.0%`.

Python production candidates for the same 5 wedge tasks also exited with code
`2` and printed contract-like stderr. They are not counted as Aether
contract-catches, and they are not the same artifact as the checked
`python_equivalent.py` files.

The benchmark's Python equivalents are checked separately by
`bench.harness run-python-equivalents`, as required by `EXPERIMENT.md`. The
latest `scripts/run_all.py` verification in this session reported the intended
silent-wrong Python-equivalent behavior:

| Task | Python-equivalent exit code | Python-equivalent stdout | Python-equivalent stderr |
|---|---:|---|---|
| `t06_contract_non_empty_minimum` | `0` | `0\n` | empty |
| `t07_contract_sorted_binary_search` | `0` | `-1\n` | empty |
| `t08_contract_positive_divisor` | `0` | `10\n` | empty |
| `t09_contract_bounded_index_update` | `0` | `[1, 2, 3]\n` | empty |
| `t10_contract_normalized_probability` | `0` | `bucket=0\n` | empty |

Python-equivalent silent-wrong behavior: `5/5` confirmed by the local
regression command in this session. These Python-equivalent runs are a baseline
comparison artifact, not the production Python candidate results.

## Interpretation

### Aether Helped This Model

Not demonstrated by the headline success metric. For `codex-current-session`,
both language arms achieved `8/8` first-attempt success and `8/8`
within-3-retries success. There is no observed first-attempt success advantage
for Aether in this accepted run.

Aether did provide structured contract/refinement diagnostics on all 5
contract-wedge Aether candidates: `E0301` for contract failures and `E0302` for
refinement failures. That is evidence that the Aether arm exercised the
language's contract/refinement machinery, but it did not translate into a
higher task success rate in this run.

### Aether Helped This Task Type

Partially demonstrated for the contract-wedge task type. The Aether wedge
candidates rejected invalid inputs with structured non-zero failures on `5/5`
tasks. The Python-equivalent baseline files silently accepted the same bad
inputs on `5/5` tasks and printed misleading outputs with exit code `0`.

However, the production Python candidates generated under
`prompt/python_system_prompt.md` also wrote explicit contract-style checks and
passed the wedge prompts on `5/5` tasks. Therefore this run supports a narrower
claim: Aether's native contract/refinement path worked on these tasks, and the
predefined Python equivalents demonstrate the silent-wrong baseline, but the
model was also able to implement explicit Python checks when prompted.

### Aether Did Not Help

Aether did not improve first-attempt success on the 3 standard stdout tasks:
both language arms passed `3/3`.

Aether did not improve aggregate first-attempt success in this accepted run:
both language arms passed `8/8`.

Aether did not reduce retries in this accepted run: both language arms used
`0` retries.

An official token-efficiency comparison is not available because provider token
counts were `not_available`. The whitespace estimates were `8017` for Aether
and `7863` for Python, but those are explicitly non-official diagnostics.

## Training-Data Asymmetry

Training-data asymmetry remains the dominant caveat for first-attempt syntax
fluency. Python is a widely represented language, while Aether is a local
experimental language with a project-specific prompt and transpiler. This run
cannot quantify that asymmetry because both arms reached `100.0%`
first-attempt success, but any syntax-fluency interpretation should treat the
asymmetry as the main confound.

The exact backend model identity for `codex-current-session` was not exposed to
repository scripts, and no external Claude Opus/Sonnet run was performed under
this active protocol.

## v0.2 Limit-Induced Failures

No final failures occurred in the accepted run. No failed attempts occurred in
the accepted run. Therefore there are no accepted-run failures to classify as
model-induced, task-induced, or limit-induced.

Known Aether v0.2 limitations did appear as caveats rather than failures:

| Limit | Evidence in accepted run | Classification |
|---|---|---|
| `S-014` contract diagnostic positions are zero | Contract/refinement stderr reports line `0`, col `0` on wedge tasks. | v0.2 diagnostic-quality limitation, not a task failure |
| Provider token counts unavailable | `provider_token_counts` is `not_available` in the manifest and every result. | measurement limitation, not a task failure |

No accepted-run failure is attributed to an Aether v0.2 limitation.

## Anomaly Follow-Up

The accepted run's Phase 2.2 scan reported:

- model/language first-attempt gap over `20pp`: not found
- diagnostic clustering on a failed-attempt pattern: not found
- tasks where both languages failed: not found
- Python silent wrong output scored as production pass: not found
- total anomalies: `0`
- gate status: `clear`

The superseded run `runs/phase2/20260508_154129_+0600` is not used for the
metrics above. It is retained because it records the anomaly that led to the
rerun.

## Final Assessment

The accepted Phase 2 result is inconclusive by the pre-registered threshold:
Aether first-attempt success was `8/8` and Python first-attempt success was
`8/8`, a `0.0pp` gap.

The clearest positive result for Aether is the contract-catch breakout:
Aether rejected all 5 invalid-input wedge tasks with structured
contract/refinement diagnostics.

The clearest limitation of the comparison is that the production Python arm
also implemented explicit contract-style checks on all 5 wedge tasks, while
the Python-equivalent silent-wrong behavior is measured separately as a
baseline artifact.

No claim that Aether is universally better than Python is supported by this
run. The supported finding is limited to the concrete benchmark behavior
recorded above.
