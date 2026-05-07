"""Run the Phase 1.3 LLM-judge corpus audit.

The audit scans active reference + benchmark + validation programs pairwise.
For each pair it sends the judge prompt twice, once as A/B and once swapped as
B/A, then writes raw model output and a summary under audits/judge_results/.

Default provider is Gemini through the installed google.generativeai SDK. The
script intentionally fails if no API key is present; it does not substitute a
local heuristic for the LLM judge.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import itertools
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT / "audits" / "llm_judge_prompt.md"
RESULTS_DIR = ROOT / "audits" / "judge_results"

API_KEY_ENV_NAMES = (
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_GENAI_API_KEY",
)

# Known same-problem pairs are not surfaced as new contamination. This list is
# deliberately small; structural-similarity false positives from PHASE_A_AUDIT
# are not included because they were judged different problems.
KNOWN_SAME_PROBLEM_PAIRS = {
    frozenset(("ref:02_factorial_recursive", "ref:03_factorial_iterative")),
}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _safe_name(label: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", label)


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(_read_text(path))


def gather_programs() -> List[Dict[str, Any]]:
    programs: List[Dict[str, Any]] = []

    for d in sorted((ROOT / "reference").iterdir()):
        path = d / "program.aeth"
        if d.is_dir() and path.is_file():
            src = _read_text(path)
            programs.append({
                "label": f"ref:{d.name}",
                "group": "reference",
                "id": d.name,
                "path": str(path.relative_to(ROOT)),
                "sha256": _sha256(src),
                "source": src,
            })

    for d in sorted((ROOT / "bench" / "tasks").iterdir()):
        path = d / "reference.aeth"
        if d.is_dir() and path.is_file():
            src = _read_text(path)
            programs.append({
                "label": f"bench:{d.name}",
                "group": "bench",
                "id": d.name,
                "path": str(path.relative_to(ROOT)),
                "sha256": _sha256(src),
                "source": src,
            })

    for d in sorted((ROOT / "validation" / "tasks").iterdir()):
        path = d / "reference.aeth"
        cfg_path = d / "grader.json"
        if not (d.is_dir() and path.is_file() and cfg_path.is_file()):
            continue
        cfg = _load_json(cfg_path)
        if cfg.get("deprecated"):
            continue
        src = _read_text(path)
        programs.append({
            "label": f"val:{d.name}",
            "group": "validation",
            "id": d.name,
            "path": str(path.relative_to(ROOT)),
            "sha256": _sha256(src),
            "source": src,
        })

    return programs


def pair_id(index: int, a: Dict[str, Any], b: Dict[str, Any]) -> str:
    return f"{index:04d}__{_safe_name(a['label'])}__vs__{_safe_name(b['label'])}"


def load_prompt_template() -> Tuple[str, str]:
    full = _read_text(PROMPT_PATH)
    marker = "## Prompt body (copy below this line)"
    if marker not in full:
        raise SystemExit(f"missing prompt marker in {PROMPT_PATH}")
    body = full.split(marker, 1)[1].strip()
    return full, body


def render_prompt(template: str, a_source: str, b_source: str) -> str:
    out = template.replace("<paste A's source here>", a_source, 1)
    out = out.replace("<paste B's source here>", b_source, 1)
    if "<paste A's source here>" in out or "<paste B's source here>" in out:
        raise RuntimeError("judge prompt placeholders were not fully replaced")
    return out


def parse_model_json(raw_text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        return None, str(e)
    return parsed, None


def find_api_key() -> Optional[str]:
    for name in API_KEY_ENV_NAMES:
        value = os.environ.get(name)
        if value:
            return value
    return None


def call_gemini(prompt: str, model_name: str, temperature: float) -> str:
    api_key = find_api_key()
    if not api_key:
        names = ", ".join(API_KEY_ENV_NAMES)
        raise RuntimeError(f"missing Gemini API key; set one of: {names}")

    try:
        import google.generativeai as genai
    except ImportError as e:
        raise RuntimeError("google.generativeai is not installed") from e

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": temperature,
            "candidate_count": 1,
            "response_mime_type": "application/json",
        },
    )
    text = getattr(response, "text", None)
    if text is None:
        text = str(response)
    return text


def judge_pair(
    out_dir: Path,
    pair_index: int,
    a: Dict[str, Any],
    b: Dict[str, Any],
    template: str,
    model_name: str,
    temperature: float,
    sleep_seconds: float,
    force: bool,
) -> Dict[str, Any]:
    pid = pair_id(pair_index, a, b)
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    records = []

    for direction, left, right in (("ab", a, b), ("ba", b, a)):
        path = raw_dir / f"{pid}__{direction}.json"
        if path.exists() and not force:
            record = _load_json(path)
            records.append(record)
            continue

        prompt = render_prompt(template, left["source"], right["source"])
        prompt_hash = _sha256(prompt)
        raw_text = call_gemini(prompt, model_name, temperature)
        parsed, parse_error = parse_model_json(raw_text)
        record = {
            "pair_id": pid,
            "pair_index": pair_index,
            "direction": direction,
            "model": model_name,
            "program_a": {k: left[k] for k in ("label", "group", "id", "path", "sha256")},
            "program_b": {k: right[k] for k in ("label", "group", "id", "path", "sha256")},
            "prompt_sha256": prompt_hash,
            "raw_text": raw_text,
            "parsed": parsed,
            "parse_error": parse_error,
        }
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        records.append(record)
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    return summarize_pair(pid, a["label"], b["label"], records)


def _judgment(record: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
    parsed = record.get("parsed")
    if not isinstance(parsed, dict):
        return None
    value = parsed.get(key)
    return value if isinstance(value, dict) else None


def _verdict_conf(record: Dict[str, Any], key: str) -> Tuple[Optional[bool], Optional[float]]:
    judgment = _judgment(record, key)
    if not judgment:
        return None, None
    verdict = judgment.get("verdict")
    confidence = judgment.get("confidence")
    if not isinstance(verdict, bool):
        verdict = None
    if not isinstance(confidence, (int, float)):
        confidence = None
    return verdict, float(confidence) if confidence is not None else None


def summarize_pair(
    pid: str,
    label_a: str,
    label_b: str,
    records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    by_direction = {r.get("direction"): r for r in records}
    ab = by_direction.get("ab")
    ba = by_direction.get("ba")
    summary: Dict[str, Any] = {
        "pair_id": pid,
        "a": label_a,
        "b": label_b,
        "known_same_problem": frozenset((label_a, label_b)) in KNOWN_SAME_PROBLEM_PAIRS,
        "parse_ok": bool(ab and ba and ab.get("parsed") and ba.get("parsed")),
        "manual_review": False,
        "new_same_problem": False,
        "judgments": {},
    }

    for key in ("same_problem", "same_technique", "same_domain"):
        if not (ab and ba):
            summary["manual_review"] = True
            continue
        verdict_ab, conf_ab = _verdict_conf(ab, key)
        verdict_ba, conf_ba = _verdict_conf(ba, key)
        disagree = verdict_ab is None or verdict_ba is None or verdict_ab != verdict_ba
        low_conf = (
            conf_ab is None or conf_ba is None
            or conf_ab < 0.7 or conf_ba < 0.7
        )
        min_conf = min(conf_ab, conf_ba) if conf_ab is not None and conf_ba is not None else None
        summary["judgments"][key] = {
            "verdict_ab": verdict_ab,
            "confidence_ab": conf_ab,
            "verdict_ba": verdict_ba,
            "confidence_ba": conf_ba,
            "disagree": disagree,
            "low_confidence": low_conf,
            "min_confidence": min_conf,
        }
        if disagree or low_conf:
            summary["manual_review"] = True

    sp = summary["judgments"].get("same_problem", {})
    if (
        sp.get("verdict_ab") is True
        and sp.get("verdict_ba") is True
        and sp.get("min_confidence") is not None
        and sp["min_confidence"] >= 0.7
        and not summary["known_same_problem"]
    ):
        summary["new_same_problem"] = True

    return summary


def write_run_metadata(
    out_dir: Path,
    args: argparse.Namespace,
    programs: List[Dict[str, Any]],
    prompt_full: str,
    prompt_body: str,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "created_at_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "model": args.model,
        "temperature": args.temperature,
        "program_count": len(programs),
        "pair_count": len(list(itertools.combinations(programs, 2))),
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
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run Phase 1.3 LLM-judge audit")
    p.add_argument("--model", default="gemini-2.5-pro")
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--out-dir")
    p.add_argument("--dry-run", action="store_true",
                   help="Only print corpus and pair counts; do not call the model")
    p.add_argument("--force", action="store_true",
                   help="Re-run and overwrite existing raw output files")
    p.add_argument("--sleep-seconds", type=float, default=0.0)
    p.add_argument("--limit-pairs", type=int,
                   help="Debug only. Do not use for the Phase 1.3 gate.")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    programs = gather_programs()
    pairs = list(itertools.combinations(programs, 2))
    prompt_full, prompt_body = load_prompt_template()

    if args.dry_run:
        print(json.dumps({
            "program_count": len(programs),
            "pair_count": len(pairs),
            "groups": {
                "reference": sum(1 for p in programs if p["group"] == "reference"),
                "bench": sum(1 for p in programs if p["group"] == "bench"),
                "validation": sum(1 for p in programs if p["group"] == "validation"),
            },
            "programs": [p["label"] for p in programs],
        }, indent=2))
        return 0

    if args.limit_pairs:
        pairs = pairs[:args.limit_pairs]

    if args.out_dir:
        out_dir = Path(args.out_dir)
        if not out_dir.is_absolute():
            out_dir = ROOT / out_dir
    else:
        ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = RESULTS_DIR / f"{ts}__{_safe_name(args.model)}"

    write_run_metadata(out_dir, args, programs, prompt_full, prompt_body)
    summaries = []
    for index, (a, b) in enumerate(pairs, start=1):
        print(f"[{index}/{len(pairs)}] {a['label']} <-> {b['label']}", file=sys.stderr)
        summaries.append(judge_pair(
            out_dir=out_dir,
            pair_index=index,
            a=a,
            b=b,
            template=prompt_body,
            model_name=args.model,
            temperature=args.temperature,
            sleep_seconds=args.sleep_seconds,
            force=args.force,
        ))

    summary = {
        "program_count": len(programs),
        "pair_count": len(pairs),
        "directional_model_calls_expected": len(pairs) * 2,
        "manual_review_count": sum(1 for s in summaries if s.get("manual_review")),
        "new_same_problem_count": sum(1 for s in summaries if s.get("new_same_problem")),
        "new_same_problem_pairs": [
            s for s in summaries if s.get("new_same_problem")
        ],
        "manual_review_pairs": [
            s for s in summaries if s.get("manual_review")
        ],
        "pairs": summaries,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps({
        "out_dir": str(out_dir.relative_to(ROOT)),
        "program_count": summary["program_count"],
        "pair_count": summary["pair_count"],
        "manual_review_count": summary["manual_review_count"],
        "new_same_problem_count": summary["new_same_problem_count"],
    }, indent=2))
    return 0 if summary["new_same_problem_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
