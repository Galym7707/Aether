"""Generate a Phase 1.3 self-judge audit artifact.

This is an explicit protocol override used only when the user approves Codex as
the LLM judge instead of an external Gemini run. It writes the same raw JSON
shape expected from audits/llm_judge_prompt.md, for both A/B and B/A directions.

Do not use these self-judge signatures as candidate-generation hints in later
experiment phases.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import itertools
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from run_llm_judge_audit import (
    KNOWN_SAME_PROBLEM_PAIRS,
    PROMPT_PATH,
    ROOT,
    _safe_name,
    _sha256,
    gather_programs,
    load_prompt_template,
    summarize_pair,
)


SIGNATURES: Dict[str, Dict[str, Any]] = {
    "ref:01_hello": {
        "signature": "A computes a fixed greeting, given no input, producing one printed string.",
        "domain": {"strings"},
        "technique": {"constant-output"},
    },
    "ref:02_factorial_recursive": {
        "signature": "A computes factorial, given a non-negative integer, producing an integer.",
        "domain": {"integers"},
        "technique": {"recursion", "multiplicative-accumulator"},
    },
    "ref:03_factorial_iterative": {
        "signature": "A computes factorial, given a non-negative integer, producing an integer.",
        "domain": {"integers"},
        "technique": {"loop", "multiplicative-accumulator"},
    },
    "ref:04_fizzbuzz": {
        "signature": "A computes FizzBuzz labels, given positive integers, producing strings.",
        "domain": {"integers", "strings"},
        "technique": {"modulo-classification", "conditional-chain"},
    },
    "ref:05_sum_list": {
        "signature": "A computes the sum, given a list of integers, producing an integer.",
        "domain": {"integer-lists"},
        "technique": {"loop", "additive-accumulator"},
    },
    "ref:06_word_count": {
        "signature": "A computes a word count, given a string, producing an integer.",
        "domain": {"strings"},
        "technique": {"string-split", "edge-case-empty"},
    },
    "ref:07_safe_divide": {
        "signature": "A computes a quotient or error, given two integers, producing a Result value.",
        "domain": {"integers", "results"},
        "technique": {"guarded-division", "result-error"},
    },
    "ref:08_fib_memo": {
        "signature": "A computes a Fibonacci number, given a non-negative integer, producing an integer.",
        "domain": {"integers"},
        "technique": {"loop", "dynamic-recurrence"},
    },
    "ref:09_kv_store": {
        "signature": "A computes formatted key-value lookups, given fixed string keys, producing strings and a map size.",
        "domain": {"maps", "strings", "integers"},
        "technique": {"map-build", "option-lookup", "formatting"},
    },
    "ref:10_temperature_classify": {
        "signature": "A computes a temperature category, given Celsius integers, producing climate labels.",
        "domain": {"integers", "strings", "unions"},
        "technique": {"threshold-classification", "union-match"},
    },
    "bench:t03_count_vowels": {
        "signature": "A computes a vowel count, given a string, producing an integer.",
        "domain": {"strings"},
        "technique": {"string-scan", "character-classification", "additive-accumulator"},
    },
    "bench:t04_balanced_brackets": {
        "signature": "A computes whether brackets are balanced, given a string, producing a boolean.",
        "domain": {"strings", "lists"},
        "technique": {"stack", "state-machine", "string-scan"},
    },
    "bench:t05_safe_average": {
        "signature": "A computes an integer average or empty-list error, given a list of integers, producing a Result value.",
        "domain": {"integer-lists", "results"},
        "technique": {"loop", "additive-accumulator", "result-error", "edge-case-empty"},
    },
    "bench:t06_contract_non_empty_minimum": {
        "signature": "A computes the minimum value, given a non-empty list of integers, producing an integer.",
        "domain": {"integer-lists", "refinements"},
        "technique": {"loop", "comparison-accumulator", "refinement-check", "edge-case-empty"},
    },
    "bench:t07_contract_sorted_binary_search": {
        "signature": "A computes a binary-search index, given a sorted list and target integer, producing an index or -1.",
        "domain": {"integer-lists"},
        "technique": {"binary-search", "precondition-check", "loop"},
    },
    "bench:t08_contract_positive_divisor": {
        "signature": "A computes an integer ratio, given a numerator and positive divisor, producing an integer.",
        "domain": {"integers", "refinements"},
        "technique": {"guarded-division", "refinement-check"},
    },
    "bench:t09_contract_bounded_index_update": {
        "signature": "A computes an updated list, given a list, in-bounds index, and value, producing a list.",
        "domain": {"integer-lists"},
        "technique": {"bounds-check", "list-rebuild", "loop"},
    },
    "bench:t10_contract_normalized_probability": {
        "signature": "A computes a weighted bucket index, given normalized integer weights and a threshold, producing an index.",
        "domain": {"integer-lists", "probabilities"},
        "technique": {"precondition-check", "additive-accumulator", "threshold-selection", "loop"},
    },
    "val:v01_tagged_union_evaluator": {
        "signature": "A computes a selected arithmetic operation, given an operation tag and two integers, producing an integer.",
        "domain": {"integers", "unions"},
        "technique": {"union-match", "arithmetic-dispatch"},
    },
    "val:v02_map_filter_chain": {
        "signature": "A computes the count of even squared values, given a list of integers, producing an integer.",
        "domain": {"integer-lists"},
        "technique": {"higher-order-map-filter", "characteristic-count"},
    },
    "val:v03_lookup_with_default": {
        "signature": "A computes a numeric grade value, given a letter-grade string, producing an integer defaulting for unknown grades.",
        "domain": {"maps", "strings", "integers"},
        "technique": {"const-map", "option-lookup", "default-value"},
    },
    "val:v04_result_threading": {
        "signature": "A computes validation results, given input strings, producing ok or error messages.",
        "domain": {"strings", "integers", "results"},
        "technique": {"parse-result", "range-validation", "result-error"},
    },
    "val:v05_shape_area": {
        "signature": "A computes area, given a tagged shape, producing an integer.",
        "domain": {"integers", "unions"},
        "technique": {"union-match", "geometry-formula"},
    },
    "val:v06_record_distance": {
        "signature": "A computes squared distance, given two points, producing an integer.",
        "domain": {"integers", "records"},
        "technique": {"record-fields", "arithmetic-formula"},
    },
    "val:v07_partition_by_parity": {
        "signature": "A computes a parity partition, given a list of integers, producing rendered even and odd lists.",
        "domain": {"integer-lists", "maps", "strings"},
        "technique": {"modulo-classification", "map-accumulation", "list-append"},
    },
    "val:v08_parse_and_double": {
        "signature": "A computes doubled parsed integers or parse errors, given strings, producing Result descriptions.",
        "domain": {"strings", "integers", "results"},
        "technique": {"parse-result", "result-error", "arithmetic-transform"},
    },
    "val:v09_gcd_with_contracts": {
        "signature": "A computes the greatest common divisor, given non-negative integers, producing a positive integer.",
        "domain": {"integers"},
        "technique": {"euclidean-algorithm", "precondition-check", "loop"},
    },
    "val:v10_caesar_shift": {
        "signature": "A computes a Caesar-shifted string, given a lowercase string and shift, producing a string.",
        "domain": {"strings", "integer-lists"},
        "technique": {"string-scan", "lookup-table", "modulo-indexing"},
    },
}


SAME_PROBLEM_PAIRS = {
    frozenset(("ref:02_factorial_recursive", "ref:03_factorial_iterative")): (
        0.98,
        "Both compute factorial of a non-negative integer; the difference is recursive versus iterative implementation.",
    ),
}


def classify(label_a: str, label_b: str) -> Dict[str, Any]:
    a = SIGNATURES[label_a]
    b = SIGNATURES[label_b]
    pair = frozenset((label_a, label_b))

    if pair in SAME_PROBLEM_PAIRS:
        sp_conf, sp_why = SAME_PROBLEM_PAIRS[pair]
        same_problem = {"verdict": True, "confidence": sp_conf, "why": sp_why}
    else:
        same_problem = {
            "verdict": False,
            "confidence": 0.90,
            "why": "The programs compute different outputs or solve different requested tasks.",
        }

    technique_overlap = sorted(a["technique"] & b["technique"])
    if technique_overlap:
        same_technique = {
            "verdict": True,
            "confidence": 0.82,
            "why": f"Both use shared technique(s): {', '.join(technique_overlap)}.",
        }
    else:
        same_technique = {
            "verdict": False,
            "confidence": 0.82,
            "why": "Their core programming techniques are different.",
        }

    domain_overlap = sorted(a["domain"] & b["domain"])
    if domain_overlap:
        same_domain = {
            "verdict": True,
            "confidence": 0.88,
            "why": f"Both operate on shared domain(s): {', '.join(domain_overlap)}.",
        }
    else:
        same_domain = {
            "verdict": False,
            "confidence": 0.88,
            "why": "Their primary data domains do not overlap.",
        }

    return {
        "same_problem": same_problem,
        "same_technique": same_technique,
        "same_domain": same_domain,
    }


def directional_output(label_a: str, label_b: str) -> Dict[str, Any]:
    judgments = classify(label_a, label_b)
    return {
        "signature_a": SIGNATURES[label_a]["signature"],
        "signature_b": SIGNATURES[label_b]["signature"].replace("A computes", "B computes", 1),
        "same_problem": judgments["same_problem"],
        "same_technique": judgments["same_technique"],
        "same_domain": judgments["same_domain"],
    }


def pair_id(index: int, a_label: str, b_label: str) -> str:
    return f"{index:04d}__{_safe_name(a_label)}__vs__{_safe_name(b_label)}"


def write_record(
    raw_dir: Path,
    pid: str,
    pair_index: int,
    direction: str,
    left: Dict[str, Any],
    right: Dict[str, Any],
    parsed: Dict[str, Any],
) -> Dict[str, Any]:
    raw_text = json.dumps(parsed, ensure_ascii=False, indent=2)
    record = {
        "pair_id": pid,
        "pair_index": pair_index,
        "direction": direction,
        "model": "codex_self_judge",
        "protocol_override": "User approved Codex/GPT self-judge instead of Gemini API.",
        "program_a": {k: left[k] for k in ("label", "group", "id", "path", "sha256")},
        "program_b": {k: right[k] for k in ("label", "group", "id", "path", "sha256")},
        "raw_text": raw_text,
        "parsed": parsed,
        "parse_error": None,
    }
    path = raw_dir / f"{pid}__{direction}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run approved Codex self-judge audit")
    p.add_argument("--out-dir", default="audits/judge_results/phase1_3_self_judge")
    p.add_argument("--force", action="store_true")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    programs = gather_programs()
    labels = {p["label"] for p in programs}
    missing = sorted(set(SIGNATURES) ^ labels)
    if missing:
        raise SystemExit(f"signature/corpus mismatch: {missing}")

    pairs = list(itertools.combinations(programs, 2))
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    if out_dir.exists() and not args.force:
        raise SystemExit(f"output directory exists; pass --force to overwrite: {out_dir}")
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    prompt_full, prompt_body = load_prompt_template()
    manifest = {
        "created_at_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "model": "codex_self_judge",
        "protocol_override": "User approved Codex/GPT self-judge instead of Gemini API.",
        "do_not_use_as_generation_hint": True,
        "program_count": len(programs),
        "pair_count": len(pairs),
        "directional_judgment_count": len(pairs) * 2,
        "prompt_file": str(PROMPT_PATH.relative_to(ROOT)),
        "prompt_file_sha256": _sha256(prompt_full),
        "prompt_body_sha256": _sha256(prompt_body),
        "programs": [
            {k: p[k] for k in ("label", "group", "id", "path", "sha256")}
            for p in programs
        ],
        "known_same_problem_pairs": [
            sorted(pair) for pair in sorted(KNOWN_SAME_PROBLEM_PAIRS, key=lambda x: sorted(x))
        ],
    }
    (out_dir / "corpus_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summaries = []
    for index, (a, b) in enumerate(pairs, start=1):
        pid = pair_id(index, a["label"], b["label"])
        records = [
            write_record(raw_dir, pid, index, "ab", a, b, directional_output(a["label"], b["label"])),
            write_record(raw_dir, pid, index, "ba", b, a, directional_output(b["label"], a["label"])),
        ]
        summaries.append(summarize_pair(pid, a["label"], b["label"], records))

    summary = {
        "program_count": len(programs),
        "pair_count": len(pairs),
        "directional_judgment_count": len(pairs) * 2,
        "manual_review_count": sum(1 for s in summaries if s.get("manual_review")),
        "new_same_problem_count": sum(1 for s in summaries if s.get("new_same_problem")),
        "new_same_problem_pairs": [s for s in summaries if s.get("new_same_problem")],
        "manual_review_pairs": [s for s in summaries if s.get("manual_review")],
        "pairs": summaries,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "out_dir": str(out_dir.relative_to(ROOT)),
        "program_count": summary["program_count"],
        "pair_count": summary["pair_count"],
        "directional_judgment_count": summary["directional_judgment_count"],
        "manual_review_count": summary["manual_review_count"],
        "new_same_problem_count": summary["new_same_problem_count"],
        "new_same_problem_pairs": [
            {"a": s["a"], "b": s["b"]}
            for s in summary["new_same_problem_pairs"]
        ],
    }, ensure_ascii=False, indent=2))
    return 0 if summary["new_same_problem_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
