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


def _diag(source: str, command: str = "check") -> dict:
    proc = _run_cli(source, command)
    assert proc.returncode != 0, proc.stdout + proc.stderr
    return json.loads(proc.stderr.splitlines()[0])["diagnostic"]


def _point_program(body: str) -> str:
    return f"""
record Point do
  x: Int
  y: Int
end

function main() returns Unit
  effects log
do
{body}
end
"""


def test_record_literal_creates_value():
    out = _run_ok(
        _point_program(
            """
  let p: Point = Point { x = 1, y = 2 }
  print(intToString(p.x))
  print(intToString(p.y))
"""
        )
    )
    assert out == "1\n2\n"


def test_ast_preserves_record_literal():
    proc = _run_cli(
        _point_program(
            """
  let p: Point = Point { x = 1, y = 2 }
"""
        ),
        "ast",
    )
    assert proc.returncode == 0, proc.stderr
    ast = json.loads(proc.stdout)
    value = ast["decls"][1]["body"][0]["value"]
    assert value["kind"] == "RecordLiteral"
    assert value["name"] == "Point"


def test_record_literal_missing_field_diagnostic():
    diag = _diag(
        _point_program(
            """
  let p: Point = Point { x = 1 }
"""
        )
    )
    assert diag["code"] == "RECORD_LITERAL_MISSING_FIELD", diag
    assert diag["extra"]["field"] == "y", diag


def test_record_literal_extra_field_diagnostic():
    diag = _diag(
        _point_program(
            """
  let p: Point = Point { x = 1, y = 2, z = 3 }
"""
        )
    )
    assert diag["code"] == "RECORD_LITERAL_EXTRA_FIELD", diag
    assert diag["extra"]["field"] == "z", diag


def test_record_literal_field_type_diagnostic():
    diag = _diag(
        _point_program(
            """
  let p: Point = Point { x = "bad", y = 2 }
"""
        )
    )
    assert diag["code"] == "RECORD_LITERAL_FIELD_TYPE", diag
    assert diag["expected"] == "Int", diag
    assert diag["actual"] == "String", diag


def test_record_literal_and_copy_update_both_work():
    out = _run_ok(
        _point_program(
            """
  let p: Point = Point { x = 1, y = 2 }
  let q: Point = p { y = 9 }
  print(intToString(p.y))
  print(intToString(q.y))
"""
        )
    )
    assert out == "2\n9\n"


if __name__ == "__main__":
    test_record_literal_creates_value()
    test_ast_preserves_record_literal()
    test_record_literal_missing_field_diagnostic()
    test_record_literal_extra_field_diagnostic()
    test_record_literal_field_type_diagnostic()
    test_record_literal_and_copy_update_both_work()
    print("RECORD LITERAL TESTS PASS")
