# Aether Contract-Wedge Benchmark Tasks

## Overview

These tasks test invalid-input cases where the Python equivalents in this
repository silently accept bad inputs and print misleading results, while the
Aether reference solutions reject the same inputs through contracts,
refinement-typed parameters, explicit safe-list helper results, or
higher-order effect diagnostics for Option/Result callbacks.

The benchmark source of truth for these results is the local harness output from
`python -m bench.harness run-reference`,
`python -m bench.harness run-python-equivalents`, the seven individual
`run-task` commands listed below, and `python scripts\run_all.py`. This checkout
uses per-task `bench/tasks/<task_id>/grader.json` files. No root-level
`grader.json` file was present when the repository was inspected.

## Task Summary Table

| # | Task | Violation Tested | Python Behavior | Aether Behavior | Expected Diagnostic |
|---|------|------------------|-----------------|-----------------|---------------------|
| 1 | t06_contract_non_empty_minimum | Empty list passed to a minimum function requiring a non-empty list. | Prints `0` with exit code `0` and empty stderr. | Fails before producing stdout with exit code `2`. | `(?i)(refinement\|contract).*non.?empty` |
| 2 | t07_contract_sorted_binary_search | Unsorted list passed to binary search requiring sorted input. | Prints `-1` even though `5` is present, with exit code `0` and empty stderr. | Fails before producing stdout with exit code `2`. | `(?i)(contract\|requires\|precondition).*sorted` |
| 3 | t08_contract_positive_divisor | Zero passed as a divisor requiring a positive value. | Prints `10` after silently substituting denominator `1`, with exit code `0` and empty stderr. | Fails before producing stdout with exit code `2`. | `(?i)(refinement\|contract).*(positive\|divisor\|denominator)` |
| 4 | t09_contract_bounded_index_update | Out-of-bounds index passed to an update function requiring an in-bounds index. | Prints `[1, 2, 3]` after silently ignoring the update, with exit code `0` and empty stderr. | Fails before producing stdout with exit code `2`. | `(?i)(contract\|requires\|precondition).*(index\|bounds\|inBounds)` |
| 5 | t10_contract_normalized_probability | Negative probability weight in a list requiring normalized non-negative integer weights. | Prints `bucket=0` after silently clamping the negative weight, with exit code `0` and empty stderr. | Fails before producing stdout with exit code `2`. | `(?i)(contract\|requires\|precondition).*(probability\|weight\|normal)` |
| 6 | t19_safe_list_update_helper | Invalid list update index using helper-based error handling. | Prints `[10, 20, 99]` after clamping the index, with exit code `0` and empty stderr. | Prints `index out of bounds` through `Err`. | none; successful `Result` error path |
| 7 | t20_safe_slice_helper | Invalid slice end bound using helper-based error handling. | Prints `[30]` after Python silently clamps the end bound, with exit code `0` and empty stderr. | Prints `slice bounds out of range` through `Err`. | none; successful `Result` error path |
| 8 | t21_option_unwrap_helper | Missing list element represented with `Option`. | Prints `0` after silently defaulting the invalid index. | Prints `missing` and `-1` through `Option` helpers. | none; successful `Option` path |
| 9 | t22_result_error_handling | Invalid update represented with `Result`. | Prints `99` after silently clamping the invalid index. | Prints `error` and keeps the original list through `Result` helpers. | none; successful `Result` path |
| 10 | t23_map_option_effect_escape | Logging callback passed through `mapOption` from a pure function. | Prints `audit:1` with no effect declaration. | Fails static check with `HIGHER_ORDER_EFFECT_ESCAPE`. | `HIGHER_ORDER_EFFECT_ESCAPE` |
| 11 | t24_map_result_effect_escape | Logging callback passed through `mapResult` from a pure function. | Prints `audit:2` with no effect declaration. | Fails static check with `HIGHER_ORDER_EFFECT_ESCAPE`. | `HIGHER_ORDER_EFFECT_ESCAPE` |
| 12 | t25_map_err_effect_escape | Logging error mapper passed through `mapErr` from a pure function. | Prints `audit:bad` with no effect declaration. | Fails static check with `HIGHER_ORDER_EFFECT_ESCAPE`. | `HIGHER_ORDER_EFFECT_ESCAPE` |

## 1. t06_contract_non_empty_minimum

The function computes the minimum value in a list. Its Aether reference uses
`type NonEmptyIntList = List<Int> where length(self) > 0`, and the function
parameter is `xs: NonEmptyIntList`.

Bad input: `minimum([])`.

The Python equivalent returns `0` for an empty list. That avoids an exception,
exits normally, and gives a fake sentinel for an invalid minimum operation.

Aether catches the violation at the refinement boundary before the function
body indexes `xs[0]`. The observed diagnostic was `E0302` in category
`refinement`, with message text containing `fails refinement NonEmptyIntList`.

Expected exit code: `2`.

Expected stderr pattern: `(?i)(refinement|contract).*non.?empty`.

Verification result: confirmed by
`python -m bench.harness run-task t06_contract_non_empty_minimum --candidate bench\tasks\t06_contract_non_empty_minimum\reference.aeth`.
The harness returned `ok: true`, `stdout: ""`, `exit_code: 2`, and
`stderr_pattern_ok: true`.

## 2. t07_contract_sorted_binary_search

The function performs binary search. Its Aether reference defines `sorted?` and
uses `requires sorted?(xs)` before the search. It also has an `ensures` clause
requiring the returned index to be `-1` or within list bounds.

Bad input: `binarySearch([1, 10, 5], 5)`.

The Python equivalent runs binary search without checking sortedness. It prints
`-1` even though `5` exists at index `2`.

Aether catches the violation before the binary-search loop executes. The
observed diagnostic was `E0301` in category `contract`, with message text
containing `requires clause failed in binarySearch: sorted?(...)`.

Expected exit code: `2`.

Expected stderr pattern: `(?i)(contract|requires|precondition).*sorted`.

Verification result: confirmed by
`python -m bench.harness run-task t07_contract_sorted_binary_search --candidate bench\tasks\t07_contract_sorted_binary_search\reference.aeth`.
The harness returned `ok: true`, `stdout: ""`, `exit_code: 2`, and
`stderr_pattern_ok: true`.

## 3. t08_contract_positive_divisor

The function computes an integer ratio. Its Aether reference uses
`type PositiveDivisor = Int where self > 0`, and the denominator parameter is
`denominator: PositiveDivisor`.

Bad input: `safeRatio(10, 0)`.

The Python equivalent silently replaces a non-positive denominator with `1`.
It prints `10`, exits normally, and hides the invalid divisor.

Aether catches the violation at the refinement boundary before division. The
observed diagnostic was `E0302` in category `refinement`, with message text
containing `denominator` and `PositiveDivisor`.

Expected exit code: `2`.

Expected stderr pattern:
`(?i)(refinement|contract).*(positive|divisor|denominator)`.

Verification result: confirmed by
`python -m bench.harness run-task t08_contract_positive_divisor --candidate bench\tasks\t08_contract_positive_divisor\reference.aeth`.
The harness returned `ok: true`, `stdout: ""`, `exit_code: 2`, and
`stderr_pattern_ok: true`.

## 4. t09_contract_bounded_index_update

The function returns a copy of a list with one index updated. Its Aether
reference defines `inBounds?` and uses `requires inBounds?(xs, index)`. It also
has an `ensures` clause requiring `length(result) == length(xs)`.

Bad input: `updateAt([1, 2, 3], 9, 99)`.

The Python equivalent silently ignores out-of-range indexes. It prints
`[1, 2, 3]`, exits normally, and gives no signal that the requested update was
invalid.

Aether catches the violation before constructing the updated list. The observed
diagnostic was `E0301` in category `contract`, with message text containing
`requires clause failed in updateAt: inBounds?(...)`.

Expected exit code: `2`.

Expected stderr pattern:
`(?i)(contract|requires|precondition).*(index|bounds|inBounds)`.

Verification result: confirmed by
`python -m bench.harness run-task t09_contract_bounded_index_update --candidate bench\tasks\t09_contract_bounded_index_update\reference.aeth`.
The harness returned `ok: true`, `stdout: ""`, `exit_code: 2`, and
`stderr_pattern_ok: true`.

## 5. t10_contract_normalized_probability

The function chooses a bucket from integer percentage weights. Its Aether
reference defines `validNormalizedProbabilityWeights?` and requires a non-empty
list, non-negative weights, and total weight exactly `100`. It also requires
`0 <= threshold < 100` and ensures the returned bucket is within list bounds.

Bad input: `chooseBucket([50, -20, 70], 25)`.

The Python equivalent silently clamps the negative weight to `0` and then
chooses a bucket. It prints `bucket=0`, exits normally, and accepts invalid
probability data.

Aether catches the violation before bucket selection. The observed diagnostic
was `E0301` in category `contract`, with message text containing
`requires clause failed in chooseBucket: validNormalizedProbabilityWeights?(...)`.

Expected exit code: `2`.

Expected stderr pattern:
`(?i)(contract|requires|precondition).*(probability|weight|normal)`.

Verification result: confirmed by
`python -m bench.harness run-task t10_contract_normalized_probability --candidate bench\tasks\t10_contract_normalized_probability\reference.aeth`.
The harness returned `ok: true`, `stdout: ""`, `exit_code: 2`, and
`stderr_pattern_ok: true`.

## 6. t19_safe_list_update_helper

The reference program attempts to update `[10, 20, 30]` at index `9` with
`updateAt(xs, 9, 99)`.

Bad input: an update index outside the list bounds.

The Python equivalent clamps the invalid index to the final element and prints
`[10, 20, 99]`, which hides the invalid request.

Aether uses the standard `updateAt` helper and handles the returned
`Result<List<Int>, String>`. The invalid index follows the `Err` branch and
prints `index out of bounds` without mutating the original list.

Expected stdout: `index out of bounds\n`.

Verification result: confirmed by
`python -m bench.harness run-task t19_safe_list_update_helper --candidate bench\tasks\t19_safe_list_update_helper\reference.aeth`.
The harness returned `ok: true`, `stdout: "index out of bounds\n"`, and
`exit_code: 0`.

## 7. t20_safe_slice_helper

The reference program attempts to slice `[10, 20, 30]` from index `2` to `9`
with `safeSlice(xs, 2, 9)`.

Bad input: a slice end bound greater than `length(xs)`.

The Python equivalent evaluates `xs[2:9]` and prints `[30]`, silently clamping
the invalid end bound.

Aether uses the standard `safeSlice` helper and handles the returned
`Result<List<Int>, String>`. The invalid bounds follow the `Err` branch and
print `slice bounds out of range`.

Expected stdout: `slice bounds out of range\n`.

Verification result: confirmed by
`python -m bench.harness run-task t20_safe_slice_helper --candidate bench\tasks\t20_safe_slice_helper\reference.aeth`.
The harness returned `ok: true`, `stdout: "slice bounds out of range\n"`, and
`exit_code: 0`.

## 8. t21_option_unwrap_helper

The reference program safely reads index `9` from `[10, 20]` using `safeAt`,
checks absence with `isNone`, and then uses `unwrapOr(value, -1)`.

Bad input: a missing list element.

The Python equivalent catches `IndexError` and silently returns `0`. It exits
normally with empty stderr, so the missing value is not explicit in the output.

Aether prints `missing` and then the deliberate fallback `-1`.

Expected stdout: `missing\n-1\n`.

Verification result: confirmed by
`python -m bench.harness run-task t21_option_unwrap_helper --candidate bench\tasks\t21_option_unwrap_helper\reference.aeth`.
The harness returned `ok: true`, `stdout: "missing\n-1\n"`, and
`exit_code: 0`.

## 9. t22_result_error_handling

The reference program attempts to update `[10, 20, 30]` at index `9` with
`updateAt`, checks the error with `isErr`, and keeps the original list with
`unwrapOrResult`.

Bad input: an invalid update index.

The Python equivalent clamps the index and updates the final element, printing
`99` without any error signal.

Aether prints `error` and then `20`, showing that the invalid update did not
change element `1`.

Expected stdout: `error\n20\n`.

Verification result: confirmed by
`python -m bench.harness run-task t22_result_error_handling --candidate bench\tasks\t22_result_error_handling\reference.aeth`.
The harness returned `ok: true`, `stdout: "error\n20\n"`, and `exit_code: 0`.

## 10. t23_map_option_effect_escape

The reference program passes `auditInt`, a callback declaring `effects log`, to
`mapOption` from a `main` function declared `effects pure`.

The Python equivalent runs the callback and prints `audit:1` without any
effect declaration or static signal.

Aether rejects the reference at check time with
`HIGHER_ORDER_EFFECT_ESCAPE`, pointing at the `mapOption` call and reporting
the escaped `log` effect.

Expected exit code: `2`.

Expected diagnostic: `HIGHER_ORDER_EFFECT_ESCAPE`, category `effect`.

Verification result: confirmed by
`python -m bench.harness run-task t23_map_option_effect_escape --candidate bench\tasks\t23_map_option_effect_escape\reference.aeth`.

## 11. t24_map_result_effect_escape

The reference program passes `auditInt`, a callback declaring `effects log`, to
`mapResult` from a pure function.

The Python equivalent runs the mapper and prints `audit:2` with no static
effect tracking.

Aether rejects the reference at check time with
`HIGHER_ORDER_EFFECT_ESCAPE`.

Expected exit code: `2`.

Expected diagnostic: `HIGHER_ORDER_EFFECT_ESCAPE`, category `effect`.

Verification result: confirmed by
`python -m bench.harness run-task t24_map_result_effect_escape --candidate bench\tasks\t24_map_result_effect_escape\reference.aeth`.

## 12. t25_map_err_effect_escape

The reference program passes `auditError`, a callback declaring `effects log`,
to `mapErr` from a pure function.

The Python equivalent runs the error mapper and prints `audit:bad` with no
static effect tracking.

Aether rejects the reference at check time with
`HIGHER_ORDER_EFFECT_ESCAPE`.

Expected exit code: `2`.

Expected diagnostic: `HIGHER_ORDER_EFFECT_ESCAPE`, category `effect`.

Verification result: confirmed by
`python -m bench.harness run-task t25_map_err_effect_escape --candidate bench\tasks\t25_map_err_effect_escape\reference.aeth`.

## Harness Changes

`compile_and_run` now returns `stdout`, `stderr`, and `exit_code` for parse,
emit, compile, runtime-error, timeout, and successful execution paths. The
existing `actual` field is preserved as an alias for captured stdout so older
callers continue to work.

The per-task `grader.json` format supports `expected_exit_code` and
`expected_stderr_pattern`. It also supports `expected_diagnostic_code` and
`expected_diagnostic_category` for stable structured diagnostic checks. When any
of these fields is present, the harness enters wedge mode and checks stdout,
exit code, diagnostic metadata, and the stderr regex. Existing tasks without
these fields keep the normal stdout-based grading path, with the added
requirement that the run itself completed successfully.

The harness now supports Python comparison metadata through
`python_equivalent`, `python_expected_exit_code`, `python_expected_stdout`,
`python_expected_stderr`, and `python_forbidden_stderr_pattern`. The command
`python -m bench.harness run-python-equivalents` runs all configured Python
equivalents and verifies their documented silent-wrong-output behavior.

The harness now records `failure_messages` for stdout mismatch, exit-code
mismatch, stderr regex mismatch, timeout, compile-stage failure, and unexpected
runtime failure.

`scripts\run_all.py` now uses the current Python executable instead of a
hard-coded `python3`, and it includes the Python-equivalent benchmark check.

## Verification Results

Command: `python -m bench.harness run-reference`

Result: passed. The latest command in this pass reported
`# 20/20 reference solutions pass`. The safe-list and Option/Result helper
tasks were marked `ok: true`; the contract-wedge tasks remained in wedge mode.

Command:
`python -m bench.harness run-task t06_contract_non_empty_minimum --candidate bench\tasks\t06_contract_non_empty_minimum\reference.aeth`

Result: passed. Observed `E0302`, `category: refinement`, `exit_code: 2`,
`stdout: ""`, and `stderr_pattern_ok: true`.

Command:
`python -m bench.harness run-task t07_contract_sorted_binary_search --candidate bench\tasks\t07_contract_sorted_binary_search\reference.aeth`

Result: passed. Observed `E0301`, `category: contract`, `exit_code: 2`,
`stdout: ""`, and `stderr_pattern_ok: true`.

Command:
`python -m bench.harness run-task t08_contract_positive_divisor --candidate bench\tasks\t08_contract_positive_divisor\reference.aeth`

Result: passed. Observed `E0302`, `category: refinement`, `exit_code: 2`,
`stdout: ""`, and `stderr_pattern_ok: true`.

Command:
`python -m bench.harness run-task t09_contract_bounded_index_update --candidate bench\tasks\t09_contract_bounded_index_update\reference.aeth`

Result: passed. Observed `E0301`, `category: contract`, `exit_code: 2`,
`stdout: ""`, and `stderr_pattern_ok: true`.

Command:
`python -m bench.harness run-task t10_contract_normalized_probability --candidate bench\tasks\t10_contract_normalized_probability\reference.aeth`

Result: passed. Observed `E0301`, `category: contract`, `exit_code: 2`,
`stdout: ""`, and `stderr_pattern_ok: true`.

Command: `python -m bench.harness run-python-equivalents`

Result: passed for the intended Python behavior. Observed outputs were:

| Task | Python exit code | Python stdout | Python stderr |
|------|------------------|---------------|---------------|
| t06_contract_non_empty_minimum | `0` | `0\n` | empty |
| t07_contract_sorted_binary_search | `0` | `-1\n` | empty |
| t08_contract_positive_divisor | `0` | `10\n` | empty |
| t09_contract_bounded_index_update | `0` | `[1, 2, 3]\n` | empty |
| t10_contract_normalized_probability | `0` | `bucket=0\n` | empty |
| t19_safe_list_update_helper | `0` | `[10, 20, 99]\n` | empty |
| t20_safe_slice_helper | `0` | `[30]\n` | empty |
| t21_option_unwrap_helper | `0` | `0\n` | empty |
| t22_result_error_handling | `0` | `99\n` | empty |

Command: `python tests\test_regressions.py`

Result: passed. The command printed `ALL REGRESSION TESTS PASS`. The timeout
regression `S-012` was skipped because this platform does not expose
`SIGALRM`.

Command: `python scripts\run_all.py`

Result: passed. The latest command in this pass reported `# reference: 10/10`,
`# bench: 20/20`, `# python eq: 17/17`, `# regression: PASS`,
`# additional: PASS`, and `# fuzz: PASS`.

Command: `python -B scripts\fuzz_parser.py --rounds 200 --mode all`

Result: passed. The command reported `violations: 0` and
`emit_violations: 0` for random, mutate, and tokens modes.

# Comparative Analysis: Aether vs Python

## 1. What Aether Does Better Than Python

Contract enforcement: in the original five detailed contract-wedge tasks,
Aether rejects invalid inputs before
printing a misleading result. The observed evidence is that every Aether
reference had `stdout: ""`, `exit_code: 2`, and a structured diagnostic matching
the task's stderr pattern. The Python equivalents all exited with code `0`,
empty stderr, and a misleading stdout value.

Requires / ensures: preconditions make hidden assumptions explicit in the
Aether task files. Examples are `requires sorted?(xs)`, `requires inBounds?(xs,
index)`, and `requires validNormalizedProbabilityWeights?(weights)`. The
`binarySearch`, `updateAt`, and `chooseBucket` tasks also include non-trivial
`ensures` clauses about result bounds or output length. The observed violations
in the current run were requires/refinement failures; ensures failures were not
triggered by these bad-input cases.

Refinement-typed parameters: this was demonstrated by `NonEmptyIntList` in
`t06_contract_non_empty_minimum` and `PositiveDivisor` in
`t08_contract_positive_divisor`. The observed diagnostics were `E0302`
refinement failures before function bodies produced output.

Structured diagnostics: Aether produced machine-readable result fields and
stderr text such as `E0302` with category `refinement` and `E0301` with category
`contract`. The diagnostics are more useful than the Python equivalents'
empty stderr because the harness can verify `exit_code`, diagnostic code,
diagnostic category, and regex-matched stderr.

Benchmark value: these tasks are useful correctness benchmarks because the
invalid inputs are plausible edge cases: empty lists, unsorted search inputs,
zero divisors, out-of-bounds indexes, and invalid probability weights.

## 2. Aether's Main Advantages

Explicit contracts make assumptions visible. In `t07_contract_sorted_binary_search`,
the sortedness assumption is part of the function boundary through
`requires sorted?(xs)`. The Python file has no equivalent check and prints `-1`.

Invalid inputs can be rejected early. In `t08_contract_positive_divisor`, Aether
rejects `0` as a `PositiveDivisor` before division. The Python file substitutes
`1` and prints `10`.

Diagnostics support debugging and grading. The harness observed `E0301` or
`E0302`, diagnostic categories, exit code `2`, and stderr text that matched the
configured patterns.

Silent logical errors are reduced for these cases. In the original five
detailed contract-wedge tasks, the Python equivalent printed a result while
Aether produced no stdout and reported a violation.

The tasks are a good fit for educational examples of contracts and refinement
types. Each task isolates one domain assumption and gives a direct Python
comparison. This is an observed property of the added files, not a general
claim about every Aether or Python program.

## 3. Aether's Main Disadvantages

Writing contracts requires extra code and judgment. The Aether tasks include
helper predicates such as `sorted?`, `inBounds?`, and
`validNormalizedProbabilityWeights?`. Weak or incorrect predicates would reduce
the value of the benchmark. This risk is visible from the fact that the harness
trusts the task's own predicate logic.

Diagnostics are still somewhat generic. The observed stderr reports line `0`,
column `0` for runtime contract and refinement failures. That is structured, but
not source-location precise.

The benchmark still includes stderr regex patterns. Stable diagnostic code and
category checks reduce the risk, but regex wording can still become fragile if
diagnostic messages change while the semantic error remains the same.

More metadata is required for negative tests. Each wedge task needs
`expected_exit_code`, structured diagnostic expectations, and stderr pattern
metadata. Python comparison also needs expected output and stderr metadata.

Runtime or compile-time overhead was not measured. Not confirmed from the
current benchmark run.

Static-vs-runtime checking was not established by these commands. Not confirmed
from the current benchmark run.

## 4. Where Aether Shows Good Results

| Area | Evidence From Tasks | Why Aether Performs Well |
|------|--------------------|--------------------------|
| Input validation | The original five detailed Aether references returned `exit_code: 2` for invalid inputs. | Contracts and refinements sit at function boundaries. |
| Edge-case detection | Empty list, unsorted list, zero divisor, bad index, and negative weight were all rejected. | The invalid cases are encoded directly as predicates or refinement clauses. |
| Contract diagnostics | `E0301` and `E0302` were observed with categories `contract` and `refinement`. | The harness receives structured fields and stderr text. |
| Preventing silent wrong output | Aether produced empty stdout for the original five detailed bad inputs while Python printed a value. | Violations stop execution before misleading output is emitted. |
| Correctness-sensitive functions | Search, arithmetic, indexing, and weighted-choice examples all rely on domain assumptions. | These assumptions can be made explicit and tested. |

Empty minimum: Aether rejects empty lists through `NonEmptyIntList` instead of
allowing a fake sentinel minimum value.

Binary search: Aether rejects unsorted inputs through `requires sorted?(xs)`
instead of returning an incorrect search result.

Positive divisor: Aether rejects zero as a `PositiveDivisor` instead of silently
substituting or clamping the denominator.

Bounded index update: Aether rejects an out-of-range index through
`requires inBounds?(xs, index)` instead of silently ignoring the update.

Normalized probability: Aether rejects negative weights through
`requires validNormalizedProbabilityWeights?(weights)` instead of silently
normalizing invalid data.

## 5. Where Aether Shows Poor or Weak Results

| Weak Area | Observed Evidence | Impact | Severity |
|----------|------------------|--------|----------|
| Generic runtime source position | All observed contract/refinement stderr messages used line `0`, col `0`. | Users get structured errors but not precise source locations for these runtime checks. | Medium |
| Regex-based stderr grading | New `grader.json` entries still match diagnostic text with regex, even though code/category checks are also present. | Diagnostic wording changes can require benchmark metadata updates. | Low |
| Contract predicate burden | The new tasks define helper predicates such as `sorted?`, `inBounds?`, and `validNormalizedProbabilityWeights?`. | Incorrect predicates can give false confidence. | Medium |
| Python semantic expectations are task-authored | The harness verifies expected Python stdout/stderr/exit code, but it does not independently prove that the output is semantically wrong. | The benchmark author must document why the Python output is misleading. | Low |
| Static checking scope | These runs show runtime contract/refinement detection only. | Any static-checking advantage is not demonstrated here. | Low |

If diagnostics are too generic beyond these observed line/column values: Not
confirmed from the current benchmark run.

If Aether has measurable runtime overhead for these tasks: Not confirmed from
the current benchmark run.

If Python equivalents are easier to maintain long term: Not confirmed from the
current benchmark run.

## 6. How Aether Can Be Improved

Better diagnostic messages:

- Include stable diagnostic codes for specific contract families if Aether
  supports them.
- Distinguish requires, ensures, and refinement failures in a way that is
  already visible in structured fields and stable enough for benchmarks.
- Include the violated value and source location when safe. Current refinement
  diagnostics include a short `value_repr`; requires diagnostics in these runs
  did not show argument values in stderr.

Better benchmark metadata:

- Keep `expected_exit_code`.
- Keep `expected_stderr_pattern` as a human-readable diagnostic smoke test.
- Prefer `expected_diagnostic_code` and `expected_diagnostic_category` for
  stable grading where possible.

Better task organization:

- Keep the `tNN_contract_...` naming convention used here.
- Add a benchmark index for categories such as normal-output tasks and
  contract-wedge tasks.

Better developer ergonomics:

- Add reusable predicates for common contracts: `non_empty`, `sorted`,
  `positive`, `in_bounds`, and `valid_probability_distribution`.
- Document whether these predicates are intended as runtime checks, static
  refinements, or both.

Better Python comparison harness:

- Add an explicit `python_silent_wrong_output` or `python_wrong_output_reason`
  field.
- Keep expected Python wrong output separate from Aether stdout.
- Report semantic failure separately from runtime failure.

Better testing:

- Add unit tests for `expected_exit_code`.
- Add unit tests for stderr regex matching.
- Add backward-compatibility tests for old `grader.json` entries.

Better static analysis if available:

- Document which violations can be caught before runtime.
- Static detection for the original five detailed tasks was not confirmed from the current
  benchmark run.

## 7. Final Evaluation

### Summary Judgment

Strongly demonstrated.

The detailed contract-wedge tasks successfully demonstrate Aether's value over the
specific Python equivalents implemented here: Aether detects invalid inputs with
structured diagnostics, while the Python equivalents exit normally and print
misleading values. This is not a claim that Aether is universally better than
Python.

### Best Demonstrated Strength

Aether's strongest demonstrated advantage is preventing silent wrong-output
behavior by enforcing explicit contracts and refinement-typed parameters.

### Biggest Current Weakness

The biggest current weakness is that runtime contract/refinement diagnostics in
these runs report line `0`, column `0`, so they are structured but not
source-location precise.

### Recommended Next Step

Improve runtime contract diagnostics with precise source locations and richer
argument/value context, then add an explicit `python_wrong_output_reason` field
for benchmark reports.
