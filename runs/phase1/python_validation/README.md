# Phase 1.4 runs - Python baseline prompt validation

This directory is for raw Phase 1.4 Python baseline validation outputs.

Each model gets its own subdirectory:

    runs/phase1/python_validation/<model>/<task_id>/
        prompt_sent.txt     The exact Python system prompt plus task prompt.
        candidate.py        The model response after removing optional fences.
        raw_stdout.json     Raw Claude CLI stdout when using the Claude runner.
        raw_stderr.txt      Raw Claude CLI stderr when using the Claude runner.
        raw_payload.json    Parsed raw JSON payload when available.
        grade.json          Output of scripts/grade_phase1_python.py.

The Python system prompt is:

    prompt/python_system_prompt.md

The Python task prompts are:

    validation/tasks/<task_id>/python_prompt.md

The Python reference sanity check is:

    python -B validation/run_python_validation.py

The candidate grader is:

    python -B scripts/grade_phase1_python.py --model <model>

If Claude Code CLI is authenticated, the runner is:

    python -B scripts/run_claude_phase1_python_validation.py --model <model> --force

The required Phase 1.4 model labels from the protocol are:

    claude-opus-4-6
    claude-sonnet-4-6

As of this workspace run, Claude Code CLI was not logged in, so model
validation is blocked. See BLOCKED.md.

## Codex surrogate

The user later requested a Codex-based surrogate completion of Phase 1.4.
Artifacts are stored under:

    runs/phase1/python_validation/codex-current-session/

The summary is:

    runs/phase1/python_validation_summary.md

This is not the original Claude Opus/Sonnet gate. It is documented as a
protocol deviation.
