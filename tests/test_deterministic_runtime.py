from __future__ import annotations

from datetime import datetime, timezone
import os
import subprocess
import sys
import tempfile
from textwrap import dedent


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_aether(source: str, *args: str) -> subprocess.CompletedProcess[str]:
    with tempfile.NamedTemporaryFile("w", suffix=".aeth", delete=False, encoding="utf-8") as f:
        f.write(dedent(source).strip() + "\n")
        path = f.name
    try:
        return subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "transpiler.aether.cli",
                "run",
                *args,
                path,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
    finally:
        os.unlink(path)


RANDOM_PROGRAM = """
function main() returns Unit
  effects random, log
do
  print(intToString(random()))
  print(intToString(random()))
  print(intToString(random()))
end
"""


def test_deterministic_seed_replays_random_sequence():
    first = _run_aether(RANDOM_PROGRAM, "--deterministic", "--seed=123")
    second = _run_aether(RANDOM_PROGRAM, "--deterministic", "--seed=123")
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert first.stdout == second.stdout


def test_different_deterministic_seeds_produce_different_sequences():
    first = _run_aether(RANDOM_PROGRAM, "--deterministic", "--seed=123")
    second = _run_aether(RANDOM_PROGRAM, "--deterministic", "--seed=456")
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert first.stdout != second.stdout


def test_fixed_time_controls_time_now():
    fixed = "2026-05-10T00:00:00"
    expected = int(datetime.fromisoformat(fixed).replace(tzinfo=timezone.utc).timestamp() * 1000)
    program = """
    function main() returns Unit
      effects time.now, log
    do
      print(intToString(time.now().epochMillis))
    end
    """
    result = _run_aether(program, "--deterministic", f"--fixed-time={fixed}")
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{expected}\n"


if __name__ == "__main__":
    test_deterministic_seed_replays_random_sequence()
    test_different_deterministic_seeds_produce_different_sequences()
    test_fixed_time_controls_time_now()
    print("DETERMINISTIC RUNTIME TESTS PASS")
