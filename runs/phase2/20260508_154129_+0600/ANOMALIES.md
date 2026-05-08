# Phase 2.2 Anomaly Scan

Run directory: `runs\phase2\20260508_154129_+0600`

This file records the required pre-analysis anomaly scan. It is not the Phase 2.3 report.

## Scope

- Models: `codex-current-session`
- Languages: `aether, python`
- Tasks scanned: 8
- Result records scanned: 16

## Language Gap Check

| Language | First-attempt successes | Tasks | First-attempt rate | Final successes | Final rate |
|---|---:|---:|---:|---:|---:|
| aether | 6/8 | 8 | 75.0% | 8/8 | 100.0% |
| python | 8/8 | 8 | 100.0% | 8/8 | 100.0% |

## Required Checks

- Model crushing one language unexpectedly (>20pp gap): FOUND
- Diagnostic patterns clustering on a single failed-attempt pattern: not found
- Tasks where both languages failed: not found
- Python silent wrong output scored as pass: not found

## Anomalies

### language_first_attempt_gap_gt_20pp

- Severity: `high`
- Summary: python first-attempt success exceeded aether by 25.0 percentage points.

Evidence is recorded in `ANOMALY_SCAN.json`.

### python_contract_wedge_scored_against_aether_expectations

- Severity: `critical`
- Summary: Python contract-wedge production candidates were scored as passes using Aether-style exit/stderr expectations rather than the python_expected_* silent-wrong fields.

Evidence is recorded in `ANOMALY_SCAN.json`.

## Gate Status

`blocked`

If `gate_status` is `blocked`, Phase 2.3 should not start until the anomaly is explicitly accepted or resolved.
