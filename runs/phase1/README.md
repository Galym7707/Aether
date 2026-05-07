# Phase 1 runs — prompt validation

This directory holds raw outputs and grading results for Phase 1.1 of the
experiment protocol. Each model gets its own subdirectory under
`validation/<model>/`. Per-task content:

    runs/phase1/validation/<model>/<task_id>/
        prompt_sent.txt    The exact prompt sent (system + task)
        candidate.aeth     The model's response saved verbatim
        grade.json         Output of bench.harness.compile_and_run
        notes.md           Any caveats or anomalies

A summary table is generated at `runs/phase1/validation_summary.md`.

## Python baseline validation

Phase 1.4 uses a separate Python baseline prompt:

    prompt/python_system_prompt.md

The same 10 active validation tasks have Python-specific prompts at:

    validation/tasks/<task_id>/python_prompt.md

Python candidate outputs are stored under:

    runs/phase1/python_validation/<model>/<task_id>/candidate.py

Grade Python candidates with:

    python -B scripts/grade_phase1_python.py --model <model>

Run Python reference sanity checks with:

    python -B validation/run_python_validation.py

As of the current workspace run, model validation through Claude Code CLI is
blocked because `claude auth status` reports `loggedIn: false`. Details are in
`runs/phase1/python_validation/BLOCKED.md`.

## Candidate-feeding contract for external runners

If you have API access to a model not running in this session, you can
participate by:

1. For each task in `validation/tasks/<task_id>/`, read `prompt.md`.
2. Send `prompt/system_prompt.md` (system role) plus the task prompt
   (user role) to the model. Capture the model's full response.
3. Save the response as `runs/phase1/validation/<model>/<task_id>/candidate.aeth`.
   Strip any markdown fences if the model wrapped its output.
4. Run `python3 -B scripts/grade_phase1.py --model <model>` to grade
   all candidates for that model.
