from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_cli(source: str, command: str = "run") -> subprocess.CompletedProcess[str]:
    path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".aeth", delete=False, encoding="utf-8") as f:
            f.write(source)
            path = f.name
        return subprocess.run(
            [sys.executable, "-B", "-m", "transpiler.aether.cli", "--json", command, path],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
    finally:
        if path and os.path.exists(path):
            os.unlink(path)


def _run_ok(source: str) -> str:
    proc = _run_cli(source, "run")
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def _diag(source: str) -> dict:
    proc = _run_cli(source, "run")
    assert proc.returncode != 0, proc.stdout + proc.stderr
    return json.loads(proc.stderr.splitlines()[0])["diagnostic"]


def test_continue_runs_invariant_and_variant_checks():
    out = _run_ok(
        """
function main() returns Unit
  effects log
do
  var i: Int = 0
  while i < 3
  invariant i >= 0
  variant 3 - i
  do
    i = i + 1
    if i < 3 then
      continue
    end
  end
  print(intToString(i))
end
"""
    )
    assert out == "3\n"


def test_continue_reports_invariant_failure_before_next_iteration():
    diag = _diag(
        """
function main() returns Unit
  effects pure
do
  var i: Int = 0
  while i < 1
  invariant i >= 0
  variant length([1]) - i
  do
    i = -1
    continue
  end
end
"""
    )
    assert diag["code"] == "LOOP_INVARIANT_FAILED", diag
    assert diag["contract_kind"] == "loop invariant", diag


if __name__ == "__main__":
    test_continue_runs_invariant_and_variant_checks()
    test_continue_reports_invariant_failure_before_next_iteration()
    print("CONTINUE LOOP INVARIANT TESTS PASS")
