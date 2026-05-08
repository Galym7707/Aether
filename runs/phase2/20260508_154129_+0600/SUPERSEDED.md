# Superseded Phase 2 Run

This run is retained as historical evidence of the initial Phase 2.2 anomaly
scan. It is superseded by `runs/phase2/20260508_155402_+0600`.

Reason:

- The original run had a `language_first_attempt_gap_gt_20pp` anomaly.
- The original anomaly scanner also treated Python production candidate
  contract-style diagnostics as a blocker against `python_expected_*` fields.
  Those fields are used by `bench.harness run-python-equivalents`, not by
  Phase 2 production candidate scoring.

Current gate source:

- `runs/phase2/20260508_155402_+0600/ANOMALY_SCAN.json`
- `runs/phase2/20260508_155402_+0600/ANOMALIES.md`
