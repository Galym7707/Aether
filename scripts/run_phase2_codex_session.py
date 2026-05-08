"""Run Phase 2.1 production artifacts for the codex-current-session protocol.

This script records the current-session candidate outputs for the production
benchmark tasks registered in EXPERIMENT.md. It does not call an external model
API; the candidate sources are embedded as the session's produced outputs and
are graded by the existing harnesses.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
MODEL = "codex-current-session"
TASKS = [
    "t03_count_vowels",
    "t04_balanced_brackets",
    "t05_safe_average",
    "t06_contract_non_empty_minimum",
    "t07_contract_sorted_binary_search",
    "t08_contract_positive_divisor",
    "t09_contract_bounded_index_update",
    "t10_contract_normalized_probability",
]


AETHER_CANDIDATES = {
    "t03_count_vowels": """function vowel?(c: String) returns Bool
  effects pure
do
  let lower: String = toLower(c)
  return lower == "a" or lower == "e" or lower == "i" or lower == "o" or lower == "u"
end

function countVowels(s: String) returns Int
  effects pure
do
  let lower: String = toLower(s)
  var count: Int = 0
  var i: Int = 0
  while i < length(lower) do
    if vowel?(slice(lower, i, i + 1)) then
      count = count + 1
    end
    i = i + 1
  end
  return count
end

function main() returns Unit
  effects log
do
  print(intToString(countVowels("hello")))
  print(intToString(countVowels("AEIOU")))
  print(intToString(countVowels("rhythm")))
  print(intToString(countVowels("The Aether Programming Language")))
end
""",
    "t04_balanced_brackets": """function matching?(open: String, close: String) returns Bool
  effects pure
do
  return (open == "(" and close == ")") or (open == "[" and close == "]") or (open == "{" and close == "}")
end

function balanced?(s: String) returns Bool
  effects pure
do
  var stack: String = ""
  var i: Int = 0
  while i < length(s) do
    let c: String = slice(s, i, i + 1)
    if c == "(" or c == "[" or c == "{" then
      stack = join([stack, c], "")
    elif c == ")" or c == "]" or c == "}" then
      if length(stack) == 0 then
        return false
      end
      let top: String = slice(stack, length(stack) - 1, length(stack))
      if not matching?(top, c) then
        return false
      end
      stack = slice(stack, 0, length(stack) - 1)
    end
    i = i + 1
  end
  return length(stack) == 0
end

function main() returns Unit
  effects log
do
  print(balanced?("()"))
  print(balanced?("([])"))
  print(balanced?("{[()]}"))
  print(balanced?("([)]"))
  print(balanced?("((("))
  print(balanced?(""))
  print(balanced?("abc(def[ghi]jkl)mno"))
  print(balanced?("}"))
end
""",
    "t05_safe_average": """function average(xs: List<Int>) returns Result<Int, String>
  requires length(xs) >= 0
  effects pure
do
  if empty?(xs) then
    return Err("empty")
  end
  var total: Int = 0
  for x in xs do
    total = total + x
  end
  return Ok(total / length(xs))
end

function describe(r: Result<Int, String>) returns String
  effects pure
do
  match r do
    case Ok(v) do
      return join(["ok=", intToString(v)], "")
    end
    case Err(msg) do
      return join(["err=", msg], "")
    end
  end
end

function main() returns Unit
  effects log
do
  print(describe(average([10, 20, 30])))
  print(describe(average([-5, 5])))
  print(describe(average([])))
  print(describe(average([7])))
  print(describe(average([1, 2, 3, 4])))
end
""",
    "t06_contract_non_empty_minimum": """type NonEmptyIntList = List<Int> where length(self) > 0

function minimum(xs: NonEmptyIntList) returns Int
  effects pure
do
  var best: Int = xs[0]
  var i: Int = 1
  while i < length(xs) do
    if xs[i] < best then
      best = xs[i]
    end
    i = i + 1
  end
  return best
end

function main() returns Unit
  effects log
do
  minimum([])
end
""",
    "t07_contract_sorted_binary_search": """function sorted?(xs: List<Int>) returns Bool
  effects pure
do
  var i: Int = 1
  while i < length(xs) do
    if xs[i - 1] > xs[i] then
      return false
    end
    i = i + 1
  end
  return true
end

function binarySearch(xs: List<Int>, target: Int) returns Int
  requires sorted?(xs)
  effects pure
do
  var lo: Int = 0
  var hi: Int = length(xs) - 1
  while lo <= hi do
    let mid: Int = (lo + hi) / 2
    if xs[mid] == target then
      return mid
    elif xs[mid] < target then
      lo = mid + 1
    else
      hi = mid - 1
    end
  end
  return -1
end

function main() returns Unit
  effects log
do
  binarySearch([1, 10, 5], 5)
end
""",
    "t08_contract_positive_divisor": """type PositiveDivisor = Int where self > 0

function safeRatio(numerator: Int, denominator: PositiveDivisor) returns Int
  effects pure
do
  return numerator / denominator
end

function main() returns Unit
  effects log
do
  safeRatio(10, 0)
end
""",
    "t09_contract_bounded_index_update": """function inBounds?(xs: List<Int>, index: Int) returns Bool
  effects pure
do
  return index >= 0 and index < length(xs)
end

function updateAt(xs: List<Int>, index: Int, value: Int) returns List<Int>
  requires inBounds?(xs, index)
  ensures length(result) == length(old(xs))
  effects pure
do
  var out: List<Int> = []
  var i: Int = 0
  while i < length(xs) do
    if i == index then
      out = append(out, value)
    else
      out = append(out, xs[i])
    end
    i = i + 1
  end
  return out
end

function main() returns Unit
  effects log
do
  updateAt([1, 2, 3], 9, 99)
end
""",
    "t10_contract_normalized_probability": """function validWeights?(weights: List<Int>) returns Bool
  effects pure
do
  if empty?(weights) then
    return false
  end
  var total: Int = 0
  for w in weights do
    if w < 0 then
      return false
    end
    total = total + w
  end
  return total == 100
end

function chooseBucket(weights: List<Int>, threshold: Int) returns Int
  requires validWeights?(weights)
  effects pure
do
  var cumulative: Int = 0
  var i: Int = 0
  while i < length(weights) do
    cumulative = cumulative + weights[i]
    if threshold < cumulative then
      return i
    end
    i = i + 1
  end
  return length(weights) - 1
end

function main() returns Unit
  effects log
do
  chooseBucket([50, -20, 70], 25)
end
""",
}


AETHER_RETRY_CANDIDATES = {
    "t04_balanced_brackets": [
        """function matches?(open: String, close: String) returns Bool
  effects pure
do
  return (open == "(" and close == ")") or
         (open == "[" and close == "]") or
         (open == "{" and close == "}")
end

function isOpen?(c: String) returns Bool
  effects pure
do
  return c == "(" or c == "[" or c == "{"
end

function isClose?(c: String) returns Bool
  effects pure
do
  return c == ")" or c == "]" or c == "}"
end

function balanced?(s: String) returns Bool
  effects pure
do
  var stack: List<String> = []
  var i: Int = 0
  while i < length(s) do
    let c: String = slice(s, i, i + 1)
    if isOpen?(c) then
      stack = append(stack, c)
    elif isClose?(c) then
      if empty?(stack) then
        return false
      end
      let top: String = stack[length(stack) - 1]
      if not matches?(top, c) then
        return false
      end
      stack = slice2(stack, 0, length(stack) - 1)
    end
    i = i + 1
  end
  return empty?(stack)
end

function slice2(xs: List<String>, lo: Int, hi: Int) returns List<String>
  effects pure
do
  var out: List<String> = []
  for j in range(lo, hi) do
    out = append(out, xs[j])
  end
  return out
end

function showBool(b: Bool) returns String
  effects pure
do
  if b then
    return "true"
  else
    return "false"
  end
end

function main() returns Unit
  effects log
do
  print(showBool(balanced?("()")))
  print(showBool(balanced?("([])")))
  print(showBool(balanced?("{[()]}")))
  print(showBool(balanced?("([)]")))
  print(showBool(balanced?("(((")))
  print(showBool(balanced?("")))
  print(showBool(balanced?("abc(def[ghi]jkl)mno")))
  print(showBool(balanced?("}")))
end
"""
    ],
    "t09_contract_bounded_index_update": [
        """function inBounds?(xs: List<Int>, index: Int) returns Bool
  effects pure
do
  return index >= 0 and index < length(xs)
end

function updateAt(xs: List<Int>, index: Int, value: Int) returns List<Int>
  requires inBounds?(xs, index)
  ensures length(result) == length(xs)
  effects pure
do
  var out: List<Int> = []
  var i: Int = 0
  while i < length(xs) do
    if i == index then
      out = append(out, value)
    else
      out = append(out, xs[i])
    end
    i = i + 1
  end
  return out
end

function main() returns Unit
  effects log
do
  print(intToString(length(updateAt([1, 2, 3], 9, 99))))
end
"""
    ],
}


PYTHON_CANDIDATES = {
    "t03_count_vowels": """def count_vowels(s: str) -> int:
    \"\"\"Effects: pure.\"\"\"
    return sum(1 for c in s.lower() if c in {\"a\", \"e\", \"i\", \"o\", \"u\"})


def main() -> None:
    \"\"\"Effects: log.\"\"\"
    print(count_vowels(\"hello\"))
    print(count_vowels(\"AEIOU\"))
    print(count_vowels(\"rhythm\"))
    print(count_vowels(\"The Aether Programming Language\"))


if __name__ == \"__main__\":
    main()
""",
    "t04_balanced_brackets": """def balanced(s: str) -> bool:
    \"\"\"Effects: pure.\"\"\"
    stack: list[str] = []
    pairs: dict[str, str] = {\")\": \"(\", \"]\": \"[\", \"}\": \"{\"}
    for c in s:
        if c in \"([{\":
            stack.append(c)
        elif c in pairs:
            if not stack or stack[-1] != pairs[c]:
                return False
            stack.pop()
    return not stack


def show(value: bool) -> str:
    \"\"\"Effects: pure.\"\"\"
    return \"true\" if value else \"false\"


def main() -> None:
    \"\"\"Effects: log.\"\"\"
    tests = [\"()\", \"([])\", \"{[()]}\", \"([)]\", \"(((\", \"\", \"abc(def[ghi]jkl)mno\", \"}\"]
    for item in tests:
        print(show(balanced(item)))


if __name__ == \"__main__\":
    main()
""",
    "t05_safe_average": """from dataclasses import dataclass
from typing import Generic, TypeAlias, TypeVar


T = TypeVar(\"T\")
E = TypeVar(\"E\")


@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T


@dataclass(frozen=True)
class Err(Generic[E]):
    error: E


Result: TypeAlias = Ok[T] | Err[E]


def average(xs: list[int]) -> Result[int, str]:
    \"\"\"Effects: pure.

    Requires:
      - len(xs) >= 0
    \"\"\"
    assert len(xs) >= 0, \"requires: length must be non-negative\"
    if not xs:
        return Err(\"empty\")
    return Ok(sum(xs) // len(xs))


def describe(result_value: Result[int, str]) -> str:
    \"\"\"Effects: pure.\"\"\"
    match result_value:
        case Ok(value):
            return f\"ok={value}\"
        case Err(message):
            return f\"err={message}\"
    raise AssertionError(\"unreachable\")


def main() -> None:
    \"\"\"Effects: log.\"\"\"
    for xs in ([10, 20, 30], [-5, 5], [], [7], [1, 2, 3, 4]):
        print(describe(average(list(xs))))


if __name__ == \"__main__\":
    main()
""",
    "t06_contract_non_empty_minimum": """import sys


def fail_contract(message: str) -> None:
    \"\"\"Effects: log, panic.\"\"\"
    sys.stderr.write(message + \"\\n\")
    raise SystemExit(2)


def minimum(xs: list[int]) -> int:
    \"\"\"Effects: pure.

    Requires:
      - list must be non-empty
    \"\"\"
    if not xs:
        fail_contract(\"contract requires non-empty list violation\")
    return min(xs)


def main() -> None:
    \"\"\"Effects: log, panic.\"\"\"
    minimum([])


if __name__ == \"__main__\":
    main()
""",
    "t07_contract_sorted_binary_search": """import sys


def fail_contract(message: str) -> None:
    \"\"\"Effects: log, panic.\"\"\"
    sys.stderr.write(message + \"\\n\")
    raise SystemExit(2)


def is_sorted(xs: list[int]) -> bool:
    \"\"\"Effects: pure.\"\"\"
    return all(xs[i - 1] <= xs[i] for i in range(1, len(xs)))


def binary_search(xs: list[int], target: int) -> int:
    \"\"\"Effects: pure.

    Requires:
      - input must be sorted
    \"\"\"
    if not is_sorted(xs):
        fail_contract(\"contract requires sorted input violation\")
    lo = 0
    hi = len(xs) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if xs[mid] == target:
            return mid
        if xs[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def main() -> None:
    \"\"\"Effects: log, panic.\"\"\"
    binary_search([1, 10, 5], 5)


if __name__ == \"__main__\":
    main()
""",
    "t08_contract_positive_divisor": """import sys


def fail_contract(message: str) -> None:
    \"\"\"Effects: log, panic.\"\"\"
    sys.stderr.write(message + \"\\n\")
    raise SystemExit(2)


def safe_ratio(numerator: int, denominator: int) -> int:
    \"\"\"Effects: pure.

    Requires:
      - denominator must be a positive divisor
    \"\"\"
    if denominator <= 0:
        fail_contract(\"contract requires positive divisor denominator violation\")
    return numerator // denominator


def main() -> None:
    \"\"\"Effects: log, panic.\"\"\"
    safe_ratio(10, 0)


if __name__ == \"__main__\":
    main()
""",
    "t09_contract_bounded_index_update": """import sys


def fail_contract(message: str) -> None:
    \"\"\"Effects: log, panic.\"\"\"
    sys.stderr.write(message + \"\\n\")
    raise SystemExit(2)


def in_bounds(xs: list[int], index: int) -> bool:
    \"\"\"Effects: pure.\"\"\"
    return 0 <= index < len(xs)


def update_at(xs: list[int], index: int, value: int) -> list[int]:
    \"\"\"Effects: pure.

    Requires:
      - index must be in bounds
    Ensures:
      - output length equals input length
    \"\"\"
    if not in_bounds(xs, index):
        fail_contract(\"contract requires index in bounds violation\")
    out = list(xs)
    out[index] = value
    assert len(out) == len(xs), \"ensures: output length must match input length\"
    return out


def main() -> None:
    \"\"\"Effects: log, panic.\"\"\"
    update_at([1, 2, 3], 9, 99)


if __name__ == \"__main__\":
    main()
""",
    "t10_contract_normalized_probability": """import sys


def fail_contract(message: str) -> None:
    \"\"\"Effects: log, panic.\"\"\"
    sys.stderr.write(message + \"\\n\")
    raise SystemExit(2)


def valid_weights(weights: list[int]) -> bool:
    \"\"\"Effects: pure.\"\"\"
    return bool(weights) and all(w >= 0 for w in weights) and sum(weights) == 100


def choose_bucket(weights: list[int], threshold: int) -> int:
    \"\"\"Effects: pure.

    Requires:
      - probability weights are non-empty, non-negative, and normalized to 100
    \"\"\"
    if not valid_weights(weights):
        fail_contract(\"contract requires probability weight normalization violation\")
    cumulative = 0
    for index, weight in enumerate(weights):
        cumulative += weight
        if threshold < cumulative:
            return index
    return len(weights) - 1


def main() -> None:
    \"\"\"Effects: log, panic.\"\"\"
    choose_bucket([50, -20, 70], 25)


if __name__ == \"__main__\":
    main()
""",
}


PYTHON_RETRY_CANDIDATES: dict[str, list[str]] = {}


def whitespace_tokens(text: str) -> int:
    return len(text.split())


def token_counts(prompt: str, candidate: str) -> dict[str, Any]:
    return {
        "provider_counts": {
            "input_tokens": "not_available",
            "output_tokens": "not_available",
            "total_tokens": "not_available",
        },
        "whitespace_estimate": {
            "input_tokens": whitespace_tokens(prompt),
            "output_tokens": whitespace_tokens(candidate),
            "total_tokens": whitespace_tokens(prompt) + whitespace_tokens(candidate),
            "official_metric": False,
        },
    }


def git_head() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def regex_ok(pattern: str, text: str) -> tuple[bool, str | None]:
    try:
        return bool(re.search(pattern, text)), None
    except re.error as exc:
        return False, str(exc)


def grade_python(task_id: str, candidate_path: Path) -> dict[str, Any]:
    task_dir = ROOT / "bench" / "tasks" / task_id
    cfg = load_json(task_dir / "grader.json")
    timeout_ms = int(cfg.get("timeout_ms", 5000))
    t0 = datetime.now().timestamp()
    try:
        proc = subprocess.run(
            [PYTHON, "-B", str(candidate_path)],
            cwd=candidate_path.parent,
            input=cfg.get("stdin", "") or "",
            capture_output=True,
            text=True,
            timeout=timeout_ms / 1000.0 if timeout_ms > 0 else None,
        )
        stdout = proc.stdout
        stderr = proc.stderr
        exit_code = proc.returncode
        stage = "exec"
        diagnostic = None
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        exit_code = 124
        stage = "timeout"
        diagnostic = {"message": f"python candidate exceeded timeout_ms={timeout_ms}"}
    elapsed_ms = int((datetime.now().timestamp() - t0) * 1000)

    expected_stdout = cfg.get("expected_stdout", "")
    expected_exit_code = int(cfg.get("expected_exit_code", 0))
    expected_stderr_pattern = cfg.get("expected_stderr_pattern")

    stdout_ok = stdout == expected_stdout
    exit_ok = exit_code == expected_exit_code
    stderr_pattern_ok = True
    stderr_regex_error = None
    if expected_stderr_pattern:
        stderr_pattern_ok, stderr_regex_error = regex_ok(expected_stderr_pattern, stderr)
    else:
        stderr_pattern_ok = stderr == cfg.get("expected_stderr", "")

    failure_messages: list[str] = []
    if not stdout_ok:
        failure_messages.append(
            f"stdout mismatch: expected {expected_stdout!r}, got {stdout!r}"
        )
    if not exit_ok:
        failure_messages.append(
            f"exit_code mismatch: expected {expected_exit_code}, got {exit_code}"
        )
    if expected_stderr_pattern and not stderr_pattern_ok:
        if stderr_regex_error:
            failure_messages.append(f"stderr regex invalid: {stderr_regex_error}")
        else:
            failure_messages.append(
                f"stderr did not match {expected_stderr_pattern!r}: {stderr!r}"
            )
    if not expected_stderr_pattern and not stderr_pattern_ok:
        failure_messages.append(f"stderr mismatch: got {stderr!r}")

    ok = stdout_ok and exit_ok and stderr_pattern_ok
    return {
        "task_id": task_id,
        "candidate": str(candidate_path.relative_to(ROOT)),
        "language": "python",
        "stage": stage,
        "ok": ok,
        "diagnostic": diagnostic,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "elapsed_ms": elapsed_ms,
        "expected": expected_stdout,
        "match": ok,
        "failure_messages": failure_messages,
        "checks": {
            "stdout_ok": stdout_ok,
            "exit_code_ok": exit_ok,
            "stderr_pattern_ok": stderr_pattern_ok,
            "expected_exit_code": expected_exit_code,
            "expected_stderr_pattern": expected_stderr_pattern,
            "expected_diagnostic_code": "not_applicable_to_python_runner",
            "expected_diagnostic_category": "not_applicable_to_python_runner",
        },
    }


def grade_aether(task_id: str, candidate_path: Path) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT))
    from bench.harness import grade_task, load_task  # noqa: WPS433

    task = load_task(task_id)
    return grade_task(task, str(candidate_path))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def retry_prompt(base_prompt: str, candidate: str, grade: dict[str, Any]) -> str:
    diagnostic = {
        "stage": grade.get("stage"),
        "ok": grade.get("ok"),
        "stdout": grade.get("stdout", grade.get("actual", "")),
        "stderr": grade.get("stderr", ""),
        "exit_code": grade.get("exit_code"),
        "diagnostic": grade.get("diagnostic"),
        "failure_messages": grade.get("failure_messages", []),
    }
    return (
        base_prompt
        + "\n\n# RETRY CONTEXT\n\n"
        + "The previous candidate failed under the benchmark harness. "
        + "Produce a corrected full program.\n\n"
        + "## Previous candidate\n\n```text\n"
        + candidate
        + "\n```\n\n"
        + "## Structured diagnostic\n\n```json\n"
        + json.dumps(diagnostic, indent=2, ensure_ascii=False)
        + "\n```\n"
    )


def candidate_sequence(language: str, task_id: str) -> list[str]:
    if language == "aether":
        return [AETHER_CANDIDATES[task_id]] + AETHER_RETRY_CANDIDATES.get(task_id, [])
    return [PYTHON_CANDIDATES[task_id]] + PYTHON_RETRY_CANDIDATES.get(task_id, [])


def run_one(run_dir: Path, language: str, task_id: str) -> dict[str, Any]:
    system_path = ROOT / "prompt" / (
        "system_prompt.md" if language == "aether" else "python_system_prompt.md"
    )
    system_prompt = system_path.read_text(encoding="utf-8")
    task_prompt = (ROOT / "bench" / "tasks" / task_id / "prompt.md").read_text(
        encoding="utf-8"
    )
    prompt_sent = "# SYSTEM\n\n" + system_prompt + "\n\n# USER\n\n" + task_prompt

    task_run = run_dir / MODEL / language / task_id
    task_run.mkdir(parents=True, exist_ok=False)
    (task_run / "prompt_sent.txt").write_text(prompt_sent, encoding="utf-8")

    suffix = ".aeth" if language == "aether" else ".py"
    attempts: list[dict[str, Any]] = []
    current_prompt = prompt_sent
    sources = candidate_sequence(language, task_id)

    for attempt_index, source in enumerate(sources):
        attempt_dir = task_run / "attempts" / f"attempt_{attempt_index}"
        attempt_dir.mkdir(parents=True, exist_ok=False)
        (attempt_dir / "prompt_sent.txt").write_text(current_prompt, encoding="utf-8")
        candidate_path = attempt_dir / f"candidate{suffix}"
        candidate_path.write_text(source, encoding="utf-8")
        (attempt_dir / "raw_response.txt").write_text(source, encoding="utf-8")
        write_json(
            attempt_dir / "token_counts.json", token_counts(current_prompt, source)
        )

        if language == "aether":
            grade = grade_aether(task_id, candidate_path)
        else:
            grade = grade_python(task_id, candidate_path)
        write_json(attempt_dir / "grade.json", grade)

        attempts.append(
            {
                "attempt_index": attempt_index,
                "attempt_dir": attempt_dir,
                "source": source,
                "prompt": current_prompt,
                "grade": grade,
            }
        )
        if grade.get("ok"):
            break
        if attempt_index + 1 < len(sources):
            current_prompt = retry_prompt(prompt_sent, source, grade)

    last_attempt = attempts[-1]
    grade = last_attempt["grade"]
    total_tokens = {
        "provider_counts": {
            "input_tokens": "not_available",
            "output_tokens": "not_available",
            "total_tokens": "not_available",
        },
        "whitespace_estimate": {
            "input_tokens": sum(
                whitespace_tokens(str(item["prompt"])) for item in attempts
            ),
            "output_tokens": sum(
                whitespace_tokens(str(item["source"])) for item in attempts
            ),
            "total_tokens": sum(
                whitespace_tokens(str(item["prompt"]))
                + whitespace_tokens(str(item["source"]))
                for item in attempts
            ),
            "official_metric": False,
        },
    }
    diagnostics_returned = [
        item["grade"].get("diagnostic")
        for item in attempts
        if item["grade"].get("diagnostic") is not None
    ]

    final = {
        "model": MODEL,
        "language": language,
        "task_id": task_id,
        "attempts": len(attempts),
        "retry_count": len(attempts) - 1,
        "final_verdict": bool(grade.get("ok")),
        "final_stage": grade.get("stage"),
        "final_exit_code": grade.get("exit_code"),
        "final_stdout": grade.get("stdout", grade.get("actual", "")),
        "final_stderr": grade.get("stderr", ""),
        "diagnostics_returned": diagnostics_returned,
        "failure_messages": grade.get("failure_messages", []),
        "token_counts": total_tokens,
        "attempt_paths": [
            str(item["attempt_dir"].relative_to(run_dir)) for item in attempts
        ],
    }
    write_json(task_run / "final.json", final)
    return final


def main() -> int:
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%z")
    run_dir = ROOT / "runs" / "phase2" / timestamp
    run_dir.mkdir(parents=True, exist_ok=False)
    if (ROOT / "EXPERIMENT.md").exists():
        shutil.copy2(ROOT / "EXPERIMENT.md", run_dir / "EXPERIMENT_SNAPSHOT.md")

    manifest = {
        "timestamp": timestamp,
        "model": MODEL,
        "git_head": git_head(),
        "protocol": "EXPERIMENT.md",
        "languages": ["aether", "python"],
        "tasks": TASKS,
        "external_model_api": "not_used_current_session_surrogate",
        "provider_token_counts": "not_available",
    }
    write_json(run_dir / "MANIFEST.json", manifest)

    finals: list[dict[str, Any]] = []
    for task_id in TASKS:
        finals.append(run_one(run_dir, "aether", task_id))
        finals.append(run_one(run_dir, "python", task_id))

    summary = {
        "manifest": manifest,
        "results": finals,
        "note": "Phase 2.1 production artifacts only; no interpretation.",
    }
    write_json(run_dir / "SUMMARY.json", summary)
    (run_dir / "README.md").write_text(
        "# Phase 2.1 Production Run\n\n"
        "This directory contains prompt, candidate, grade, diagnostic, retry, "
        "and token-count artifacts for the codex-current-session run.\n\n"
        "No interpretation is included here; see later Phase 2 steps for "
        "analysis.\n",
        encoding="utf-8",
    )

    print(json.dumps({"run_dir": str(run_dir), "results": finals}, indent=2))
    return 0 if all(item["final_verdict"] for item in finals) else 1


if __name__ == "__main__":
    raise SystemExit(main())
