# Phase 4.2 Comparative Report - v0.2 vs v0.3

Run directory: `runs/phase4/20260509_113046_+0600`

Compared against accepted Phase 2 run:
`runs/phase2/20260508_155402_+0600`

Protocol source: `EXPERIMENT.md`

## Source Artifacts

This report uses only repository artifacts:

- v0.2 accepted run: `runs/phase2/20260508_155402_+0600/SUMMARY.json`
- v0.2 manifest: `runs/phase2/20260508_155402_+0600/MANIFEST.json`
- v0.2 report: `runs/phase2/20260508_155402_+0600/REPORT.md`
- v0.3 rerun: `runs/phase4/20260509_113046_+0600/SUMMARY.json`
- v0.3 manifest: `runs/phase4/20260509_113046_+0600/MANIFEST.json`
- v0.3 experiment snapshot:
  `runs/phase4/20260509_113046_+0600/EXPERIMENT_SNAPSHOT.md`

The active protocol has one model label: `codex-current-session`. The exact
backend model identifier is not exposed to repository scripts. No external
Claude Opus/Sonnet run is represented here.

## Run Metadata

| Run | Directory | Git Head | Model | Tasks | Languages |
|---|---|---|---|---:|---|
| v0.2 accepted Phase 2 | `runs/phase2/20260508_155402_+0600` | `d9fb5c3255a8c99aee95cbeec528f3988331244a` | `codex-current-session` | `8` | `aether`, `python` |
| v0.3 Phase 4 rerun | `runs/phase4/20260509_113046_+0600` | `83abc45ddfde9fa53ccfbbe123e3e97c497f629e` | `codex-current-session` | `8` | `aether`, `python` |

Both runs used the same task list:

- `t03_count_vowels`
- `t04_balanced_brackets`
- `t05_safe_average`
- `t06_contract_non_empty_minimum`
- `t07_contract_sorted_binary_search`
- `t08_contract_positive_divisor`
- `t09_contract_bounded_index_update`
- `t10_contract_normalized_probability`

## Headline Comparison

| Model | Language | v0.2 first-attempt success | v0.3 first-attempt success | Change |
|---|---|---:|---:|---:|
| `codex-current-session` | Aether | `8/8` = `100.0%` | `8/8` = `100.0%` | `0.0pp` |
| `codex-current-session` | Python | `8/8` = `100.0%` | `8/8` = `100.0%` | `0.0pp` |

The v0.3 rerun does not change first-attempt success rates. Both language arms
were already at `8/8` in the accepted v0.2 run and stayed at `8/8`.

The aggregate Aether-vs-Python gap is `0.0pp` in both runs. Under the
`EXPERIMENT.md` threshold, this remains inconclusive.

## Secondary Metrics

### Within-3-Retries Success

| Run | Language | Success within 3 retries | Total tasks | Rate | Retries used |
|---|---|---:|---:|---:|---:|
| v0.2 | Aether | `8` | `8` | `100.0%` | `0` |
| v0.2 | Python | `8` | `8` | `100.0%` | `0` |
| v0.3 | Aether | `8` | `8` | `100.0%` | `0` |
| v0.3 | Python | `8` | `8` | `100.0%` | `0` |

No fix-loop retry was used in either run.

### Token Counts To Success

Provider/tool-reported token counts are unavailable for
`codex-current-session` in both runs. The table below shows the saved
whitespace estimates only; these are not the official token metric.

| Run | Language | Provider input | Provider output | Provider total | Whitespace input | Whitespace output | Whitespace total |
|---|---|---:|---:|---:|---:|---:|---:|
| v0.2 | Aether | `not_available` | `not_available` | `not_available` | `7251` | `766` | `8017` |
| v0.2 | Python | `not_available` | `not_available` | `not_available` | `7195` | `668` | `7863` |
| v0.3 | Aether | `not_available` | `not_available` | `not_available` | `7251` | `766` | `8017` |
| v0.3 | Python | `not_available` | `not_available` | `not_available` | `7195` | `668` | `7863` |

Official token-count comparison is not confirmed from the current benchmark
run.

## Per-Task Comparison

| Task | Language | v0.2 attempts | v0.2 verdict | v0.2 stage | v0.2 exit | v0.3 attempts | v0.3 verdict | v0.3 stage | v0.3 exit |
|---|---|---:|---|---|---:|---:|---|---|---:|
| `t03_count_vowels` | Aether | `1` | pass | `exec` | `0` | `1` | pass | `exec` | `0` |
| `t03_count_vowels` | Python | `1` | pass | `exec` | `0` | `1` | pass | `exec` | `0` |
| `t04_balanced_brackets` | Aether | `1` | pass | `exec` | `0` | `1` | pass | `exec` | `0` |
| `t04_balanced_brackets` | Python | `1` | pass | `exec` | `0` | `1` | pass | `exec` | `0` |
| `t05_safe_average` | Aether | `1` | pass | `exec` | `0` | `1` | pass | `exec` | `0` |
| `t05_safe_average` | Python | `1` | pass | `exec` | `0` | `1` | pass | `exec` | `0` |
| `t06_contract_non_empty_minimum` | Aether | `1` | pass | `exec` | `2` | `1` | pass | `exec` | `2` |
| `t06_contract_non_empty_minimum` | Python | `1` | pass | `exec` | `2` | `1` | pass | `exec` | `2` |
| `t07_contract_sorted_binary_search` | Aether | `1` | pass | `exec` | `2` | `1` | pass | `exec` | `2` |
| `t07_contract_sorted_binary_search` | Python | `1` | pass | `exec` | `2` | `1` | pass | `exec` | `2` |
| `t08_contract_positive_divisor` | Aether | `1` | pass | `exec` | `2` | `1` | pass | `exec` | `2` |
| `t08_contract_positive_divisor` | Python | `1` | pass | `exec` | `2` | `1` | pass | `exec` | `2` |
| `t09_contract_bounded_index_update` | Aether | `1` | pass | `exec` | `2` | `1` | pass | `exec` | `2` |
| `t09_contract_bounded_index_update` | Python | `1` | pass | `exec` | `2` | `1` | pass | `exec` | `2` |
| `t10_contract_normalized_probability` | Aether | `1` | pass | `exec` | `2` | `1` | pass | `exec` | `2` |
| `t10_contract_normalized_probability` | Python | `1` | pass | `exec` | `2` | `1` | pass | `exec` | `2` |

## Contract-Catch Comparison

Contract-catch is counted for Aether wedge tasks when the candidate rejects the
bad input or invalid state with the expected non-zero exit code and structured
diagnostic.

| Run | Aether contract catches | Wedge tasks | Rate |
|---|---:|---:|---:|
| v0.2 | `5` | `5` | `100.0%` |
| v0.3 | `5` | `5` | `100.0%` |

Observed Aether diagnostic codes on wedge tasks:

| Run | `E0301` contract diagnostics | `E0302` refinement diagnostics | `E0801` effect diagnostics | `E0901` SMT diagnostics |
|---|---:|---:|---:|---:|
| v0.2 | `3` | `2` | `0` | `0` |
| v0.3 | `3` | `2` | `0` | `0` |

The v0.3 run did not change the observed contract-catch rate.

## Required v0.3 Questions

### Did static effect checking change first-attempt rates?

No observed change.

Evidence:

- Aether first-attempt success remained `8/8`.
- Python first-attempt success remained `8/8`.
- No v0.3 result returned diagnostic `E0801`.
- Every v0.3 final stage was `exec`; no task stopped at static effect checking.

Why:

The Phase 4 candidates did not contain an observed effect-subset violation.
Static effect checking is present in the v0.3 toolchain, but this benchmark
rerun did not exercise a failing effect case. Therefore its effect on
first-attempt rates is not demonstrated by this run.

### Did the SMT pass catch contract violations earlier in the loop, reducing retries?

No observed retry reduction and no observed earlier SMT catch.

Evidence:

- v0.2 Aether retries: `0`.
- v0.3 Aether retries: `0`.
- No v0.3 result returned diagnostic `E0901`.
- The five v0.3 Aether wedge tasks still failed at stage `exec` with runtime
  `E0301` or `E0302` diagnostics.

Why:

The current wedge candidates use runtime contracts/refinements that are not
statically discharged by the scoped arithmetic SMT fragment in this run. Since
there were already zero retries in v0.2, the v0.3 SMT pass had no measured
retry count to reduce.

### Did the round-trip enable any new agent-loop behavior?

Not confirmed from the current benchmark run.

Evidence:

- The Phase 4 runner saved prompts, raw responses, candidates, grades,
  diagnostics, token-count artifacts, and final records.
- The run did not record any use of canonical AST printing in the candidate
  generation or fix loop.
- No retry loop was entered in either v0.2 or v0.3.

Interpretation:

The canonical AST printer is regression-tested in the repository, but this
Phase 4 run does not demonstrate new agent-loop behavior from it. A future
agent-loop experiment would need to explicitly use canonical AST output for
diffing, repair, or structural feedback and log that behavior.

## v0.3 Effects On Observed Behavior

| Area | Observed v0.2 | Observed v0.3 | Change |
|---|---|---|---|
| Aether first-attempt success | `8/8` | `8/8` | none |
| Python first-attempt success | `8/8` | `8/8` | none |
| Aether within-3 success | `8/8` | `8/8` | none |
| Python within-3 success | `8/8` | `8/8` | none |
| Aether retries used | `0` | `0` | none |
| Python retries used | `0` | `0` | none |
| Aether contract-catch rate | `5/5` | `5/5` | none |
| Static effect diagnostics | `0` | `0` | none observed |
| SMT disproval diagnostics | `0` | `0` | none observed |
| Round-trip-driven agent behavior | not recorded | not recorded | not confirmed |

## Limit-Induced Failures

No final failures occurred in the v0.3 rerun. No failed attempts occurred in
the v0.3 rerun. Therefore there are no v0.3 run failures to classify as
model-induced, task-induced, or limit-induced.

Known limitations visible as caveats:

| Limit | Evidence | Classification |
|---|---|---|
| Provider token counts unavailable | `provider_token_counts` is `not_available` in both manifests and all result records. | measurement limitation |
| Contract diagnostic positions are still zero | v0.3 wedge diagnostics still report line `0`, col `0`. | diagnostic-quality limitation |
| Static effect checking not exercised by a failing task | No `E0801` diagnostics in Phase 4. | benchmark coverage limitation |
| SMT pass not exercised by a statically disproved production task | No `E0901` diagnostics in Phase 4. | benchmark coverage limitation |
| Round-trip printer not used by the runner | No artifact records AST-print/diff behavior. | agent-loop coverage limitation |

## Training-Data And Protocol Caveats

Training-data asymmetry remains a caveat for syntax-fluency interpretation:
Python is a widely represented language, while Aether is a local experimental
language with a repository-specific prompt and transpiler. This comparative
report cannot quantify that asymmetry because both language arms scored
`8/8` in both runs.

The active protocol uses `codex-current-session`. The exact backend model
identifier is not exposed to repository scripts. The run artifacts record
current-session prompt/candidate/grade files; they do not represent fresh
external Claude Opus/Sonnet API calls.

## Final Assessment

The v0.3 engineering substrate is present in the repository, but the Phase 4
rerun did not change measured benchmark outcomes relative to the accepted v0.2
run. Both runs produced `8/8` Aether success and `8/8` Python success on the
same task set with zero retries.

The v0.3 additions did not harm the current benchmark results. They also did
not produce an observed success-rate, retry-count, or token-count improvement
in this run.

The strongest supported finding remains narrow: Aether contract/refinement
diagnostics catch all five wedge tasks in both v0.2 and v0.3. Claims about
static effect checking, SMT reducing retries, or canonical round-trip improving
agent behavior are not demonstrated by this particular Phase 4 benchmark run.
