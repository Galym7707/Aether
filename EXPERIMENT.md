# Aether Experiment Pre-registration

Date: 2026-05-07

Repository baseline at pre-registration authoring:

    d967aedcfb073430c79fc6fc0118cef764e9b840

This document pre-registers the next experiment protocol for the current
Aether repository state.

## Protocol Status

The original plan named external Claude model targets. On 2026-05-07 the user
explicitly changed the execution rule: do not use Claude going forward; the
current Codex session is the model runner for the remaining tasks.

This is a protocol deviation from the earlier plan. Results produced under this
document must be reported as Codex-session results, not as Claude Opus/Sonnet
results.

## Model List

| Model Label | Description | Status |
|---|---|---|
| `codex-current-session` | The active Codex coding-agent session used to generate, repair, and evaluate candidates. The exact backend model identifier is not exposed to local repository scripts. | Active |

No Claude model is in the active model list for this protocol version.

If a future runner exposes an exact Codex model identifier, record it in the
run directory before analysis. Do not retroactively rewrite this
pre-registration.

## Language List

| Language Arm | Prompt / Tooling | Locked Hash |
|---|---|---|
| Aether v0.2 | `prompt/system_prompt.md`; compile/run with `bench.harness` and the Aether transpiler in this repository. The prompt file still labels itself v0.1, but the repository closeout documents v0.2 runtime/refinement additions. | `2774705fb03d08313700757d290bcb71a1db856b7b258081f024a15631a1f0ae` |
| Python baseline | `prompt/python_system_prompt.md`; run with CPython through `scripts/grade_phase1_python.py`. | `7e252d83f096db74d9e73e98e83f4a9daa45f894a7dbe2b29aaf3869a06d67f5` |

Both prompts are locked after Phase 1 closes. Editing either prompt after Phase
1 closes invalidates comparisons against runs made under this document unless a
new pre-registration version is written first.

## Task Set Policy

The repository currently contains:

- 8 benchmark tasks under `bench/tasks/`, including 5 contract-wedge tasks.
- 10 active validation tasks under `validation/tasks/`.
- 10 reference sanity programs under `reference/`.

The earlier high-level plan mentions a 25-task production benchmark. That exact
25-task production benchmark is not present as `bench/tasks/` in the current
repository tree. This document does not invent missing benchmark tasks.

Production benchmark reporting uses the 8 current benchmark tasks. Validation
and reference corpora remain recorded here because they are part of the Phase 1
apparatus and regression gate.

## Content Hash Method

Task hashes are SHA-256 digests over the task-defining files listed in each row.
For each file, the hash input includes the relative path, a NUL byte, the
file's own SHA-256 hex digest, and a newline. Files are sorted by relative path
before hashing.

## Production Benchmark Tasks

| Corpus | Task | SHA-256 Content Hash | Files Included |
|---|---|---|---|
| benchmark | `t03_count_vowels` | `6aa51fb32fddf8932871df9d89d6434b0e5f11f1efc0eeaafb003713ce692f1b` | `bench/tasks/t03_count_vowels/prompt.md, bench/tasks/t03_count_vowels/grader.json, bench/tasks/t03_count_vowels/reference.aeth` |
| benchmark | `t04_balanced_brackets` | `74c22dcdd600ab8e90b4dbaea7443fa4fd3248b804c463943a51765c6aeb8d25` | `bench/tasks/t04_balanced_brackets/prompt.md, bench/tasks/t04_balanced_brackets/grader.json, bench/tasks/t04_balanced_brackets/reference.aeth` |
| benchmark | `t05_safe_average` | `1ad54729166366bc4b9bad962069f699598e4f16c932b260f2c704a7e45e57c2` | `bench/tasks/t05_safe_average/prompt.md, bench/tasks/t05_safe_average/grader.json, bench/tasks/t05_safe_average/reference.aeth` |
| benchmark | `t06_contract_non_empty_minimum` | `67b6d082347339d3d1903259050e633c0e9666a70a410e0ba2ff2afc278b30e7` | `bench/tasks/t06_contract_non_empty_minimum/prompt.md, bench/tasks/t06_contract_non_empty_minimum/grader.json, bench/tasks/t06_contract_non_empty_minimum/reference.aeth, bench/tasks/t06_contract_non_empty_minimum/python_equivalent.py` |
| benchmark | `t07_contract_sorted_binary_search` | `ef8b0acf310995a9f19c38dc1a270a2045cccf3132a08b8e76fd658ac07317c7` | `bench/tasks/t07_contract_sorted_binary_search/prompt.md, bench/tasks/t07_contract_sorted_binary_search/grader.json, bench/tasks/t07_contract_sorted_binary_search/reference.aeth, bench/tasks/t07_contract_sorted_binary_search/python_equivalent.py` |
| benchmark | `t08_contract_positive_divisor` | `cfaf36c3607b2c09b0c201b7c0b9c728b33995a9a2175c948596a84c67e55198` | `bench/tasks/t08_contract_positive_divisor/prompt.md, bench/tasks/t08_contract_positive_divisor/grader.json, bench/tasks/t08_contract_positive_divisor/reference.aeth, bench/tasks/t08_contract_positive_divisor/python_equivalent.py` |
| benchmark | `t09_contract_bounded_index_update` | `c0428c63a5c4e3c11e0bed21bfd5a2ea2e577ea3baa2dd8f6f00c0056554a5e9` | `bench/tasks/t09_contract_bounded_index_update/prompt.md, bench/tasks/t09_contract_bounded_index_update/grader.json, bench/tasks/t09_contract_bounded_index_update/reference.aeth, bench/tasks/t09_contract_bounded_index_update/python_equivalent.py` |
| benchmark | `t10_contract_normalized_probability` | `122316c3325750415bc58c67ca3ebc1d1fe50d8a7fead331514af1c316b2258a` | `bench/tasks/t10_contract_normalized_probability/prompt.md, bench/tasks/t10_contract_normalized_probability/grader.json, bench/tasks/t10_contract_normalized_probability/reference.aeth, bench/tasks/t10_contract_normalized_probability/python_equivalent.py` |

The contract-wedge task subset is:

- `t06_contract_non_empty_minimum`
- `t07_contract_sorted_binary_search`
- `t08_contract_positive_divisor`
- `t09_contract_bounded_index_update`
- `t10_contract_normalized_probability`

## Validation Corpus

| Corpus | Task | SHA-256 Content Hash | Files Included |
|---|---|---|---|
| validation | `v01_tagged_union_evaluator` | `bc43cc4058184e18e8c45eb6e326df6c8ca2bd2ad9fdf5a71757ba98a6b9d60f` | `validation/tasks/v01_tagged_union_evaluator/prompt.md, validation/tasks/v01_tagged_union_evaluator/python_prompt.md, validation/tasks/v01_tagged_union_evaluator/grader.json, validation/tasks/v01_tagged_union_evaluator/reference.aeth, validation/tasks/v01_tagged_union_evaluator/python_reference.py` |
| validation | `v02_map_filter_chain` | `7c71864e6a1cb934a6ae3f0f57601f5cb8e2e421a910fa0b58995d78b72011f1` | `validation/tasks/v02_map_filter_chain/prompt.md, validation/tasks/v02_map_filter_chain/python_prompt.md, validation/tasks/v02_map_filter_chain/grader.json, validation/tasks/v02_map_filter_chain/reference.aeth, validation/tasks/v02_map_filter_chain/python_reference.py` |
| validation | `v03_lookup_with_default` | `30c2a59d21526e08a21ae9b4d8c33eae32fc9c0c23959e04719eb2a7b4483d16` | `validation/tasks/v03_lookup_with_default/prompt.md, validation/tasks/v03_lookup_with_default/python_prompt.md, validation/tasks/v03_lookup_with_default/grader.json, validation/tasks/v03_lookup_with_default/reference.aeth, validation/tasks/v03_lookup_with_default/python_reference.py` |
| validation | `v04_result_threading` | `f490bd14fbb5e3a71adfb7a82d3f10bcd95a901db74c810050f1efb2f011089a` | `validation/tasks/v04_result_threading/prompt.md, validation/tasks/v04_result_threading/python_prompt.md, validation/tasks/v04_result_threading/grader.json, validation/tasks/v04_result_threading/reference.aeth, validation/tasks/v04_result_threading/python_reference.py` |
| validation | `v05_shape_area` | `eae41255c0daad2c9ed2a09e7185fc05b8bf76ee931fe117d096a5acbc6c9ce2` | `validation/tasks/v05_shape_area/prompt.md, validation/tasks/v05_shape_area/python_prompt.md, validation/tasks/v05_shape_area/grader.json, validation/tasks/v05_shape_area/reference.aeth, validation/tasks/v05_shape_area/python_reference.py` |
| validation | `v06_record_distance` | `6a75d383e7b8b132d30ed027594d8403c0ffa0186b770f0c2bc95487e54293af` | `validation/tasks/v06_record_distance/prompt.md, validation/tasks/v06_record_distance/python_prompt.md, validation/tasks/v06_record_distance/grader.json, validation/tasks/v06_record_distance/reference.aeth, validation/tasks/v06_record_distance/python_reference.py` |
| validation | `v07_partition_by_parity` | `9b5088de07577a7f8a1d6fab75f670434896c276235f15cee3b5001a536125b1` | `validation/tasks/v07_partition_by_parity/prompt.md, validation/tasks/v07_partition_by_parity/python_prompt.md, validation/tasks/v07_partition_by_parity/grader.json, validation/tasks/v07_partition_by_parity/reference.aeth, validation/tasks/v07_partition_by_parity/python_reference.py` |
| validation | `v08_parse_and_double` | `8aa1d27c788312da293af804ad577468d3cf308e8eb2686cb1c7853d06872f83` | `validation/tasks/v08_parse_and_double/prompt.md, validation/tasks/v08_parse_and_double/python_prompt.md, validation/tasks/v08_parse_and_double/grader.json, validation/tasks/v08_parse_and_double/reference.aeth, validation/tasks/v08_parse_and_double/python_reference.py` |
| validation | `v09_gcd_with_contracts` | `03d274e7955e4f1029663afb8994369255ee3143cd9b512b6365b02c127842d9` | `validation/tasks/v09_gcd_with_contracts/prompt.md, validation/tasks/v09_gcd_with_contracts/python_prompt.md, validation/tasks/v09_gcd_with_contracts/grader.json, validation/tasks/v09_gcd_with_contracts/reference.aeth, validation/tasks/v09_gcd_with_contracts/python_reference.py` |
| validation | `v10_caesar_shift` | `19d47ad1834fd36a032f6dcbc4ba68f33f100586be35f9cff14a7526fac00692` | `validation/tasks/v10_caesar_shift/prompt.md, validation/tasks/v10_caesar_shift/python_prompt.md, validation/tasks/v10_caesar_shift/grader.json, validation/tasks/v10_caesar_shift/reference.aeth, validation/tasks/v10_caesar_shift/python_reference.py` |

## Reference Sanity Corpus

These programs are used as Aether implementation sanity checks, not as
candidate-generation tasks, because they do not contain task prompts.

| Corpus | Task | SHA-256 Content Hash | Files Included |
|---|---|---|---|
| reference | `01_hello` | `36159cb76e0340c7547fcb3a6a89b1a91048a4fa5a0dfae555f38da8af632569` | `reference/01_hello/program.aeth, reference/01_hello/expected_stdout.txt` |
| reference | `02_factorial_recursive` | `1241add39f183cf439d78f6860ac9f2898e799046f8cf4a434bd2c207ccb1285` | `reference/02_factorial_recursive/program.aeth, reference/02_factorial_recursive/expected_stdout.txt` |
| reference | `03_factorial_iterative` | `cc51e4cc1b5844382d99ac7386ef1fedd8119b50ced24d9372369f1fff6dd953` | `reference/03_factorial_iterative/program.aeth, reference/03_factorial_iterative/expected_stdout.txt` |
| reference | `04_fizzbuzz` | `529c09641648d2da9ec43898e1a0648d234ecba1df9f09a3980871e2a1c219b5` | `reference/04_fizzbuzz/program.aeth, reference/04_fizzbuzz/expected_stdout.txt` |
| reference | `05_sum_list` | `2b6a47b20fe83be50de3c9587a6ae7f5100bab5b9309139b16fd2d4ddcbe2af1` | `reference/05_sum_list/program.aeth, reference/05_sum_list/expected_stdout.txt` |
| reference | `06_word_count` | `f106e50442afce241590cc0935fa5974b289313194bcdab381866125700236bd` | `reference/06_word_count/program.aeth, reference/06_word_count/expected_stdout.txt` |
| reference | `07_safe_divide` | `582745ef9a6749f262bad9613710d297359eaa8812451d989b98b6f72a3b4f32` | `reference/07_safe_divide/program.aeth, reference/07_safe_divide/expected_stdout.txt` |
| reference | `08_fib_memo` | `4112202494e7c294100ac92b1e9f38b1e23572aca0684cc3db0a427b3cacf03d` | `reference/08_fib_memo/program.aeth, reference/08_fib_memo/expected_stdout.txt` |
| reference | `09_kv_store` | `cc1ecf910e42cccba9cccdf9a4deb28d90b0298329ab035a257d13c6236d71c8` | `reference/09_kv_store/program.aeth, reference/09_kv_store/expected_stdout.txt` |
| reference | `10_temperature_classify` | `74c71959ff9597059b6399c7ac198ed20b0994710575b59435b04d3798f3f170` | `reference/10_temperature_classify/program.aeth, reference/10_temperature_classify/expected_stdout.txt` |

## Candidate Generation Protocol

For each production benchmark task and each language arm:

1. Send the locked language-specific system prompt.
2. Send only the task prompt for the current task.
3. Save the exact prompt material and candidate output under a run directory.
4. Grade the first candidate without edits.
5. If it fails, enter the fix loop below.

Do not inspect the reference solution while generating a candidate. Reference
solutions are only for grading and sanity checks.

## Fix-loop Rules

Maximum retries: 3.

For each retry, the model sees only:

- the original prompt material,
- its own previous candidate output,
- the structured diagnostic from the relevant harness,
- the expected/actual stdout mismatch if the harness produced one.

The model must not see hidden reference solutions, hidden grader internals
except the structured diagnostic, or manual hints not derived from the harness.

Stop conditions:

- Success before or at retry 3.
- Retry 3 fails.
- Tooling/harness failure prevents a trustworthy grade.

All failures must be logged with stage, diagnostic, stdout, stderr, exit code,
and whether the failure is model-induced, task-induced, or limit-induced.

## Metrics

Primary metric:

- First-attempt success rate.

Secondary metrics:

- Within-3-retries success rate.
- Total tokens to success.
- Contract-catch rate on the 5 contract-wedge tasks.

Token-count rule:

- Use provider/tool-reported token counts when available.
- If provider/tool token counts are unavailable for `codex-current-session`,
  record `not_available`.
- Do not substitute estimated token counts as the official metric. Estimated
  whitespace counts may be reported separately as non-official diagnostics.

Contract-catch rate definition:

For the 5 wedge tasks, count a task as caught when the Aether candidate is
graded successful because it rejects the bad input or invalid state with the
expected non-zero exit code and expected diagnostic pattern/code. Report Python
behavior separately using the existing Python-equivalent checks; do not count a
silent Python wrong-output run as a contract catch.

## Inconclusive-result Threshold

If the aggregate first-attempt success-rate gap between Aether and Python is
under 8 percentage points, the result is inconclusive.

Report the full result regardless of whether it is inconclusive.

Do not round in Aether's favor or Python's favor.

## Reporting Commitments

Report both directions:

- Aether wins over Python.
- Python wins over Aether.
- Both fail.
- Both pass.
- Failures caused by known Aether v0.2 limits.
- Failures caused by Python prompt/tooling limits.

Do not describe either language as universally better. Only describe observed
behavior on the pre-registered tasks.

Do not edit `prompt/system_prompt.md` or `prompt/python_system_prompt.md` after
Phase 1 closes. If a prompt must change, write a new pre-registration version
before running any new comparison.

## Required Verification Before Phase 2

Before starting production runs, verify:

    python -B validation\run_python_validation.py
    python -B validation\run_validation.py
    python -B scripts\run_all.py

If any command fails, stop and record the exact command and failure summary.

Not confirmed from the current benchmark run:

- An external blind Codex CLI/API run.
- The earlier 25-task production benchmark claimed by the high-level plan.
- Any Claude Opus/Sonnet result under this revised protocol.
