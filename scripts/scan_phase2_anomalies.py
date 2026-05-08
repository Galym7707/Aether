"""Scan Phase 2 production logs for pre-report anomalies.

This implements the Phase 2.2 gate from EXPERIMENT.md. It reads a Phase 2 run
directory, checks the required anomaly classes, and writes both JSON and
Markdown artifacts back into that run directory.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_TASKS = {
    "t06_contract_non_empty_minimum",
    "t07_contract_sorted_binary_search",
    "t08_contract_positive_divisor",
    "t09_contract_bounded_index_update",
    "t10_contract_normalized_probability",
}
SILENT_WRONG_EXIT_CODE = 0


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_phase2_run() -> Path:
    phase2 = ROOT / "runs" / "phase2"
    runs = sorted(path for path in phase2.iterdir() if path.is_dir())
    if not runs:
        raise FileNotFoundError("no runs/phase2/* directories found")
    return runs[-1]


def pct(part: int, whole: int) -> float:
    if whole == 0:
        return 0.0
    return (part / whole) * 100.0


def first_attempt_ok(result: dict[str, Any], run_dir: Path) -> bool:
    first_path = run_dir / result["attempt_paths"][0] / "grade.json"
    return bool(load_json(first_path).get("ok"))


def attempt_grades(run_dir: Path, result: dict[str, Any]) -> list[dict[str, Any]]:
    grades = []
    for rel in result.get("attempt_paths", []):
        grade_path = run_dir / rel / "grade.json"
        grade = load_json(grade_path)
        grade["_path"] = str(grade_path.relative_to(ROOT))
        grades.append(grade)
    return grades


def diagnostic_key(grade: dict[str, Any]) -> str | None:
    diagnostic = grade.get("diagnostic")
    if diagnostic:
        code = diagnostic.get("code", "no-code")
        category = diagnostic.get("category", "no-category")
        message = diagnostic.get("message", "")
        return f"{code}:{category}:{message}"
    failures = grade.get("failure_messages") or []
    if failures:
        first = failures[0]
        if "stdout mismatch" in first:
            return "stdout_mismatch"
        if "exit_code mismatch" in first:
            return "exit_code_mismatch"
        if "stderr did not match" in first:
            return "stderr_pattern_mismatch"
        return first
    return None


def has_contract_like_stderr(text: str) -> bool:
    return bool(re.search(r"(?i)(contract|requires|refinement|precondition)", text))


def scan(run_dir: Path) -> dict[str, Any]:
    summary = load_json(run_dir / "SUMMARY.json")
    results = summary["results"]
    by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_task: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for result in results:
        by_language[result["language"]].append(result)
        by_task[result["task_id"]][result["language"]] = result

    language_rates = {}
    for language, items in sorted(by_language.items()):
        language_rates[language] = {
            "tasks": len(items),
            "first_attempt_successes": sum(
                1 for item in items if first_attempt_ok(item, run_dir)
            ),
            "final_successes": sum(1 for item in items if item["final_verdict"]),
        }
        language_rates[language]["first_attempt_success_rate"] = pct(
            language_rates[language]["first_attempt_successes"],
            language_rates[language]["tasks"],
        )
        language_rates[language]["final_success_rate"] = pct(
            language_rates[language]["final_successes"],
            language_rates[language]["tasks"],
        )

    anomalies: list[dict[str, Any]] = []
    languages = sorted(language_rates)
    for index, left in enumerate(languages):
        for right in languages[index + 1 :]:
            first_gap = (
                language_rates[left]["first_attempt_success_rate"]
                - language_rates[right]["first_attempt_success_rate"]
            )
            if abs(first_gap) > 20.0:
                winner = left if first_gap > 0 else right
                loser = right if first_gap > 0 else left
                anomalies.append(
                    {
                        "id": "language_first_attempt_gap_gt_20pp",
                        "severity": "high",
                        "summary": (
                            f"{winner} first-attempt success exceeded {loser} "
                            f"by {abs(first_gap):.1f} percentage points."
                        ),
                        "evidence": {
                            "basis": "primary metric: first-attempt success rate",
                            "rates": language_rates,
                        },
                    }
                )

    both_failed_tasks = []
    for task_id, per_language in sorted(by_task.items()):
        if all(not result["final_verdict"] for result in per_language.values()):
            both_failed_tasks.append(task_id)
    if both_failed_tasks:
        anomalies.append(
            {
                "id": "both_languages_failed_final",
                "severity": "high",
                "summary": "At least one task failed in both language arms.",
                "evidence": {"tasks": both_failed_tasks},
            }
        )

    diagnostic_counts: Counter[str] = Counter()
    diagnostic_examples: dict[str, list[str]] = defaultdict(list)
    failed_attempt_count = 0
    for result in results:
        for grade in attempt_grades(run_dir, result):
            if grade.get("ok"):
                continue
            failed_attempt_count += 1
            key = diagnostic_key(grade)
            if key:
                diagnostic_counts[key] += 1
                diagnostic_examples[key].append(grade["_path"])
    diagnostic_clusters = [
        {
            "pattern": key,
            "count": count,
            "example_grade_paths": diagnostic_examples[key][:5],
        }
        for key, count in diagnostic_counts.most_common()
        if count >= 2 and failed_attempt_count > 0
    ]
    if diagnostic_clusters:
        anomalies.append(
            {
                "id": "failed_attempt_diagnostic_cluster",
                "severity": "medium",
                "summary": "Multiple failed attempts share the same diagnostic pattern.",
                "evidence": {
                    "failed_attempt_count": failed_attempt_count,
                    "clusters": diagnostic_clusters,
                },
            }
        )

    silent_wrong_passes = []
    python_contract_semantic_mismatches = []
    for task_id in sorted(CONTRACT_TASKS):
        python_result = by_task.get(task_id, {}).get("python")
        if not python_result:
            continue
        task_grader_path = ROOT / "bench" / "tasks" / task_id / "grader.json"
        task_grader = load_json(task_grader_path)
        final_exit = int(python_result["final_exit_code"])
        final_stdout = python_result["final_stdout"]
        final_stderr = python_result["final_stderr"]
        if (
            python_result["final_verdict"]
            and final_exit == SILENT_WRONG_EXIT_CODE
            and final_stderr == ""
            and final_stdout == task_grader.get("python_expected_stdout")
        ):
            silent_wrong_passes.append(
                {
                    "task_id": task_id,
                    "stdout": final_stdout,
                    "final_json": str(
                        (
                            run_dir
                            / "codex-current-session"
                            / "python"
                            / task_id
                            / "final.json"
                        ).relative_to(ROOT)
                    ),
                }
            )
        if python_result["final_verdict"] and (
            final_exit != int(task_grader.get("python_expected_exit_code", 0))
            or final_stdout != task_grader.get("python_expected_stdout", "")
            or final_stderr != task_grader.get("python_expected_stderr", "")
            or has_contract_like_stderr(final_stderr)
        ):
            python_contract_semantic_mismatches.append(
                {
                    "task_id": task_id,
                    "phase2_exit_code": final_exit,
                    "phase2_stdout": final_stdout,
                    "phase2_stderr": final_stderr,
                    "grader_python_expected_exit_code": task_grader.get(
                        "python_expected_exit_code"
                    ),
                    "grader_python_expected_stdout": task_grader.get(
                        "python_expected_stdout"
                    ),
                    "grader_python_expected_stderr": task_grader.get(
                        "python_expected_stderr"
                    ),
                    "grader_python_forbidden_stderr_pattern": task_grader.get(
                        "python_forbidden_stderr_pattern"
                    ),
                    "final_json": str(
                        (
                            run_dir
                            / "codex-current-session"
                            / "python"
                            / task_id
                            / "final.json"
                        ).relative_to(ROOT)
                    ),
                }
            )
    if silent_wrong_passes:
        anomalies.append(
            {
                "id": "python_silent_wrong_output_scored_pass",
                "severity": "critical",
                "summary": (
                    "Python produced the registered silent-wrong wedge output "
                    "and was scored as pass."
                ),
                "evidence": {"tasks": silent_wrong_passes},
            }
        )
    if python_contract_semantic_mismatches:
        anomalies.append(
            {
                "id": "python_contract_wedge_scored_against_aether_expectations",
                "severity": "critical",
                "summary": (
                    "Python contract-wedge production candidates were scored as "
                    "passes using Aether-style exit/stderr expectations rather "
                    "than the python_expected_* silent-wrong fields."
                ),
                "evidence": {"tasks": python_contract_semantic_mismatches},
            }
        )

    return {
        "run_dir": str(run_dir.relative_to(ROOT)),
        "scan_scope": {
            "models": sorted({item["model"] for item in results}),
            "languages": sorted(by_language),
            "tasks": sorted(by_task),
            "result_count": len(results),
        },
        "language_rates": language_rates,
        "both_failed_tasks": both_failed_tasks,
        "failed_attempt_diagnostics": {
            "failed_attempt_count": failed_attempt_count,
            "counts": dict(diagnostic_counts),
        },
        "python_silent_wrong_output_scored_pass": silent_wrong_passes,
        "python_contract_semantic_mismatches": python_contract_semantic_mismatches,
        "anomalies": anomalies,
        "gate_status": "blocked" if anomalies else "clear",
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Phase 2.2 Anomaly Scan",
        "",
        f"Run directory: `{payload['run_dir']}`",
        "",
        "This file records the required pre-analysis anomaly scan. It is not the Phase 2.3 report.",
        "",
        "## Scope",
        "",
        f"- Models: `{', '.join(payload['scan_scope']['models'])}`",
        f"- Languages: `{', '.join(payload['scan_scope']['languages'])}`",
        f"- Tasks scanned: {len(payload['scan_scope']['tasks'])}",
        f"- Result records scanned: {payload['scan_scope']['result_count']}",
        "",
        "## Language Gap Check",
        "",
        "| Language | First-attempt successes | Tasks | First-attempt rate | Final successes | Final rate |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for language, rates in sorted(payload["language_rates"].items()):
        lines.append(
            "| {language} | {first}/{tasks} | {tasks} | {first_rate:.1f}% | "
            "{final}/{tasks} | {final_rate:.1f}% |".format(
                language=language,
                first=rates["first_attempt_successes"],
                final=rates["final_successes"],
                tasks=rates["tasks"],
                first_rate=rates["first_attempt_success_rate"],
                final_rate=rates["final_success_rate"],
            )
        )

    lines += [
        "",
        "## Required Checks",
        "",
        f"- Model crushing one language unexpectedly (>20pp gap): "
        f"{'FOUND' if any(a['id'] == 'language_first_attempt_gap_gt_20pp' for a in payload['anomalies']) else 'not found'}",
        f"- Diagnostic patterns clustering on a single failed-attempt pattern: "
        f"{'FOUND' if any(a['id'] == 'failed_attempt_diagnostic_cluster' for a in payload['anomalies']) else 'not found'}",
        f"- Tasks where both languages failed: "
        f"{'FOUND' if payload['both_failed_tasks'] else 'not found'}",
        f"- Python silent wrong output scored as pass: "
        f"{'FOUND' if payload['python_silent_wrong_output_scored_pass'] else 'not found'}",
        "",
        "## Anomalies",
        "",
    ]
    if payload["anomalies"]:
        for anomaly in payload["anomalies"]:
            lines += [
                f"### {anomaly['id']}",
                "",
                f"- Severity: `{anomaly['severity']}`",
                f"- Summary: {anomaly['summary']}",
                "",
                "Evidence is recorded in `ANOMALY_SCAN.json`.",
                "",
            ]
    else:
        lines.append("No anomalies found by the required scan.")
        lines.append("")

    lines += [
        "## Gate Status",
        "",
        f"`{payload['gate_status']}`",
        "",
        "If `gate_status` is `blocked`, Phase 2.3 should not start until the anomaly is explicitly accepted or resolved.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", nargs="?", type=Path, default=None)
    args = parser.parse_args()
    run_dir = args.run_dir if args.run_dir else latest_phase2_run()
    if not run_dir.is_absolute():
        run_dir = ROOT / run_dir
    payload = scan(run_dir)
    (run_dir / "ANOMALY_SCAN.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_markdown(run_dir / "ANOMALIES.md", payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 1 if payload["gate_status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
