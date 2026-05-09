"""Stable Python API for compiler and benchmark-agent integrations.

This module is deliberately independent of CLI parsing. Agent runners can call
parse/check/run directly and can grade benchmark candidates without importing
the benchmark harness internals.
"""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
import io
import os
import re
import signal
import subprocess
import sys
import time
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .diagnostics import AetherError, Diagnostic, attach_source_context
from .emitter import emit
from .parser import parse
from .prelint import lint_common_ai_syntax
from .passes.capability import check_capabilities
from .passes.effects import check_effects
from .passes.smt import check_smt_contracts
from .passes.types import check_types
from .runtime import build_namespace, set_effect_strict


@dataclass
class AetherResult:
    stage: str
    ok: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    elapsed_ms: int = 0
    diagnostic: Optional[Dict[str, Any]] = None
    diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    ast: Optional[Dict[str, Any]] = None
    python_source: Optional[str] = None

    def to_dict(self, include_artifacts: bool = False) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "stage": self.stage,
            "ok": self.ok,
            "diagnostic": self.diagnostic,
            "stdout": self.stdout,
            "actual": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "elapsed_ms": self.elapsed_ms,
        }
        if self.diagnostics:
            out["diagnostics"] = self.diagnostics
        if include_artifacts:
            if self.ast is not None:
                out["ast"] = self.ast
            if self.python_source is not None:
                out["python_source"] = self.python_source
        return out


class _CandidateTimeout(Exception):
    """Raised by SIGALRM when candidate execution exceeds timeout_ms."""


def _alarm_handler(signum, frame):
    raise _CandidateTimeout("candidate exceeded timeout_ms")


def _elapsed_ms(t0: float) -> int:
    return int((time.time() - t0) * 1000)


def _diag_to_dict(diag: Diagnostic) -> Dict[str, Any]:
    return diag.to_dict()


def format_diagnostic_stderr(diag: Diagnostic | Mapping[str, Any]) -> str:
    """Format diagnostics in the same non-JSON shape as the CLI."""
    if isinstance(diag, Diagnostic):
        d = diag.to_dict()
    else:
        d = dict(diag)
    code = d.get("code", "?")
    severity = d.get("severity", "error")
    category = d.get("category", "unknown")
    pos = d.get("position") or {}
    line = pos.get("line", 0) if isinstance(pos, Mapping) else 0
    col = pos.get("column", 0) if isinstance(pos, Mapping) else 0
    msg = d.get("message", "")
    out = f"[{code}] {severity} ({category}) at line {line}, col {col}: {msg}\n"
    suggestion = d.get("suggestion")
    if suggestion:
        out += f"  hint: {suggestion}\n"
    return out


def parse_source(source: str, filename: str = "<input>") -> AetherResult:
    """Parse Aether source and return a structured result with the AST."""
    t0 = time.time()
    prelint_diags = lint_common_ai_syntax(source, filename)
    if prelint_diags:
        diag = prelint_diags[0]
        return AetherResult(
            stage="parse",
            ok=False,
            stderr=format_diagnostic_stderr(diag),
            exit_code=2,
            elapsed_ms=_elapsed_ms(t0),
            diagnostic=_diag_to_dict(diag),
            diagnostics=[_diag_to_dict(d) for d in prelint_diags],
        )
    try:
        ast = parse(source, filename)
    except AetherError as e:
        attach_source_context(e.diag, source)
        return AetherResult(
            stage="parse",
            ok=False,
            stderr=format_diagnostic_stderr(e.diag),
            exit_code=2,
            elapsed_ms=_elapsed_ms(t0),
            diagnostic=_diag_to_dict(e.diag),
        )
    return AetherResult(
        stage="parse",
        ok=True,
        exit_code=0,
        elapsed_ms=_elapsed_ms(t0),
        ast=ast,
    )


def check_ast(
    ast: Dict[str, Any],
    *,
    capability_strict: bool = False,
) -> Tuple[List[Diagnostic], List[Diagnostic]]:
    """Run static checks and return ``(errors, infos)`` diagnostics."""
    errors: List[Diagnostic] = []
    infos: List[Diagnostic] = []

    errors.extend(check_types(ast))
    errors.extend(check_effects(ast))
    for diag in check_smt_contracts(ast):
        if diag.severity == "error":
            errors.append(diag)
        else:
            infos.append(diag)
    if capability_strict:
        errors.extend(check_capabilities(ast))
    return errors, infos


def check_source(
    source: str,
    filename: str = "<input>",
    *,
    capability_strict: bool = False,
) -> AetherResult:
    """Parse, statically check, emit, and Python-compile an Aether program."""
    t0 = time.time()
    parsed = parse_source(source, filename)
    if not parsed.ok:
        parsed.elapsed_ms = _elapsed_ms(t0)
        return parsed
    ast = parsed.ast or {"kind": "Program", "decls": []}

    errors, infos = check_ast(ast, capability_strict=capability_strict)
    if errors:
        for diag in errors + infos:
            attach_source_context(diag, source)
        return AetherResult(
            stage="check",
            ok=False,
            stderr="".join(format_diagnostic_stderr(d) for d in errors),
            exit_code=2,
            elapsed_ms=_elapsed_ms(t0),
            diagnostic=_diag_to_dict(errors[0]),
            diagnostics=[_diag_to_dict(d) for d in errors + infos],
            ast=ast,
        )

    try:
        py = emit(ast)
    except Exception as e:
        diag = {"message": str(e), "category": "emit", "code": "E9001"}
        return AetherResult(
            stage="emit",
            ok=False,
            stderr=f"emit error: {e}\n",
            exit_code=1,
            elapsed_ms=_elapsed_ms(t0),
            diagnostic=diag,
            diagnostics=[_diag_to_dict(d) for d in infos],
            ast=ast,
        )

    try:
        compile(py, filename + ".py", "exec")
    except SyntaxError as e:
        diag = {"message": str(e), "category": "internal", "code": "E9002"}
        return AetherResult(
            stage="emit-compile",
            ok=False,
            stderr=f"internal error (emitter produced bad python): {e}\n",
            exit_code=1,
            elapsed_ms=_elapsed_ms(t0),
            diagnostic=diag,
            diagnostics=[_diag_to_dict(d) for d in infos],
            ast=ast,
            python_source=py,
        )

    return AetherResult(
        stage="check",
        ok=True,
        exit_code=0,
        elapsed_ms=_elapsed_ms(t0),
        diagnostics=[_diag_to_dict(d) for d in infos],
        ast=ast,
        python_source=py,
    )


def run_source(
    source: str,
    filename: str = "<input>",
    *,
    stdin_text: str = "",
    timeout_ms: int = 5000,
    effect_strict: bool = False,
    capability_strict: bool = False,
) -> AetherResult:
    """Parse, check, emit, compile, and execute an Aether program."""
    t0 = time.time()
    checked = check_source(
        source,
        filename,
        capability_strict=capability_strict,
    )
    if not checked.ok:
        checked.elapsed_ms = _elapsed_ms(t0)
        return checked

    py = checked.python_source or ""
    try:
        code = compile(py, filename + ".py", "exec")
    except SyntaxError as e:
        diag = {"message": str(e), "category": "internal", "code": "E9002"}
        return AetherResult(
            stage="emit-compile",
            ok=False,
            stderr=f"internal error (emitter produced bad python): {e}\n",
            exit_code=1,
            elapsed_ms=_elapsed_ms(t0),
            diagnostic=diag,
            diagnostics=checked.diagnostics,
            ast=checked.ast,
            python_source=py,
        )

    globals_dict = build_namespace()
    globals_dict["__name__"] = "__main__"
    globals_dict["__file__"] = filename + ".py"
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    saved_stdin = sys.stdin
    sys.stdin = io.StringIO(stdin_text)

    have_alarm = hasattr(signal, "SIGALRM")
    prev_handler = None
    if have_alarm and timeout_ms and timeout_ms > 0:
        prev_handler = signal.signal(signal.SIGALRM, _alarm_handler)
        signal.setitimer(signal.ITIMER_REAL, timeout_ms / 1000.0)

    set_effect_strict(effect_strict)
    try:
        try:
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                exec(code, globals_dict)
        except _CandidateTimeout:
            timeout_diag = {
                "code": "E0601",
                "category": "timeout",
                "severity": "error",
                "message": f"candidate exceeded timeout_ms={timeout_ms}",
                "suggestion": "check for infinite loops or runaway recursion",
                "position": {"line": 0, "column": 0},
            }
            stdout = stdout_buf.getvalue()
            stderr = stderr_buf.getvalue() + format_diagnostic_stderr(timeout_diag)
            return AetherResult(
                stage="exec",
                ok=False,
                stdout=stdout,
                stderr=stderr,
                exit_code=124,
                elapsed_ms=_elapsed_ms(t0),
                diagnostic=timeout_diag,
                diagnostics=checked.diagnostics,
            )
        except AetherError as e:
            attach_source_context(e.diag, source)
            stdout = stdout_buf.getvalue()
            stderr = stderr_buf.getvalue() + format_diagnostic_stderr(e.diag)
            return AetherResult(
                stage="exec",
                ok=False,
                stdout=stdout,
                stderr=stderr,
                exit_code=2,
                elapsed_ms=_elapsed_ms(t0),
                diagnostic=_diag_to_dict(e.diag),
                diagnostics=checked.diagnostics,
            )
        except Exception as e:
            stdout = stdout_buf.getvalue()
            stderr = stderr_buf.getvalue() + f"runtime error: {type(e).__name__}: {e}\n"
            return AetherResult(
                stage="exec",
                ok=False,
                stdout=stdout,
                stderr=stderr,
                exit_code=1,
                elapsed_ms=_elapsed_ms(t0),
                diagnostic={
                    "message": f"{type(e).__name__}: {e}",
                    "category": "runtime",
                    "code": "E9003",
                },
                diagnostics=checked.diagnostics,
            )
    finally:
        set_effect_strict(False)
        if have_alarm and timeout_ms and timeout_ms > 0:
            signal.setitimer(signal.ITIMER_REAL, 0)
            if prev_handler is not None:
                signal.signal(signal.SIGALRM, prev_handler)
        sys.stdin = saved_stdin

    return AetherResult(
        stage="exec",
        ok=True,
        stdout=stdout_buf.getvalue(),
        stderr=stderr_buf.getvalue(),
        exit_code=0,
        elapsed_ms=_elapsed_ms(t0),
        diagnostics=checked.diagnostics,
    )


def _regex_search(pattern: str, text: str) -> Tuple[bool, Optional[str]]:
    try:
        return bool(re.search(pattern, text)), None
    except re.error as e:
        return False, str(e)


def grade_candidate_source(
    task_id: str,
    config: Mapping[str, Any],
    candidate_path: str,
    source: str,
) -> Dict[str, Any]:
    """Run and grade an Aether candidate against benchmark task metadata."""
    result = run_source(
        source,
        candidate_path,
        stdin_text=config.get("stdin", "") or "",
        timeout_ms=int(config.get("timeout_ms", 5000)),
    ).to_dict()
    out: Dict[str, Any] = {"task_id": task_id, "candidate": candidate_path}
    out.update(result)

    expected_stdout = config.get("expected_stdout", "")
    expected_exit_code = config.get("expected_exit_code")
    expected_stderr_pattern = config.get("expected_stderr_pattern")
    expected_diagnostic_code = config.get("expected_diagnostic_code")
    expected_diagnostic_category = config.get("expected_diagnostic_category")

    actual_stdout = result.get("stdout", result.get("actual", ""))
    actual_stderr = result.get("stderr", "")
    actual_exit_code = result.get("exit_code", 0 if result.get("ok") else 1)
    actual_diagnostic = result.get("diagnostic") or {}
    if not isinstance(actual_diagnostic, Mapping):
        actual_diagnostic = {}
    actual_diagnostic_code = actual_diagnostic.get("code")
    actual_diagnostic_category = actual_diagnostic.get("category")

    stdout_ok = actual_stdout == expected_stdout
    exit_ok = expected_exit_code is None or actual_exit_code == expected_exit_code
    stderr_ok = True
    stderr_regex_error = None
    if expected_stderr_pattern:
        stderr_ok, stderr_regex_error = _regex_search(
            expected_stderr_pattern,
            actual_stderr,
        )
    diagnostic_code_ok = (
        expected_diagnostic_code is None
        or actual_diagnostic_code == expected_diagnostic_code
    )
    diagnostic_category_ok = (
        expected_diagnostic_category is None
        or actual_diagnostic_category == expected_diagnostic_category
    )

    wedge_mode = (
        expected_exit_code is not None
        or expected_stderr_pattern is not None
        or expected_diagnostic_code is not None
        or expected_diagnostic_category is not None
    )
    if wedge_mode:
        match = (
            stdout_ok
            and exit_ok
            and stderr_ok
            and diagnostic_code_ok
            and diagnostic_category_ok
        )
    else:
        match = bool(result.get("ok")) and stdout_ok

    failure_messages: List[str] = []
    if not stdout_ok:
        failure_messages.append(
            f"stdout mismatch: expected {expected_stdout!r}, got {actual_stdout!r}"
        )
    if expected_exit_code is not None and not exit_ok:
        failure_messages.append(
            f"exit_code mismatch: expected {expected_exit_code}, got {actual_exit_code}"
        )
    if expected_stderr_pattern and not stderr_ok:
        if stderr_regex_error:
            failure_messages.append(f"stderr regex is invalid: {stderr_regex_error}")
        else:
            failure_messages.append(
                f"stderr did not match pattern {expected_stderr_pattern!r}: "
                f"actual stderr was {actual_stderr!r}"
            )
    if expected_diagnostic_code is not None and not diagnostic_code_ok:
        failure_messages.append(
            f"diagnostic code mismatch: expected {expected_diagnostic_code!r}, "
            f"got {actual_diagnostic_code!r}"
        )
    if expected_diagnostic_category is not None and not diagnostic_category_ok:
        failure_messages.append(
            f"diagnostic category mismatch: expected {expected_diagnostic_category!r}, "
            f"got {actual_diagnostic_category!r}"
        )
    if actual_exit_code == 124:
        failure_messages.append(
            f"process timed out after timeout_ms={int(config.get('timeout_ms', 5000))}"
        )
    if result.get("stage") in {"parse", "check", "emit", "emit-compile"} and not result.get("ok"):
        failure_messages.append(f"compilation failed during {result.get('stage')}")
    if (not wedge_mode) and result.get("stage") == "exec" and not result.get("ok"):
        failure_messages.append(
            f"runtime failed unexpectedly with exit_code={actual_exit_code}"
        )

    out["expected"] = expected_stdout
    out["stdout"] = actual_stdout
    out["match"] = match
    out["ok"] = match
    out["wedge_mode"] = wedge_mode
    out["failure_messages"] = failure_messages
    out["checks"] = {
        "stdout_ok": stdout_ok,
        "exit_code_ok": exit_ok,
        "stderr_pattern_ok": stderr_ok,
        "expected_exit_code": expected_exit_code,
        "expected_stderr_pattern": expected_stderr_pattern,
        "actual_exit_code": actual_exit_code,
        "expected_diagnostic_code": expected_diagnostic_code,
        "expected_diagnostic_category": expected_diagnostic_category,
        "actual_diagnostic_code": actual_diagnostic_code,
        "actual_diagnostic_category": actual_diagnostic_category,
        "diagnostic_code_ok": diagnostic_code_ok,
        "diagnostic_category_ok": diagnostic_category_ok,
    }
    return out


def grade_candidate_file(
    task_id: str,
    config: Mapping[str, Any],
    candidate_path: str,
) -> Dict[str, Any]:
    """Load an Aether candidate file and grade it with task metadata."""
    if not os.path.isfile(candidate_path):
        return {
            "task_id": task_id,
            "candidate": candidate_path,
            "ok": False,
            "stage": "missing",
            "diagnostic": {"message": "candidate file not found"},
        }
    with open(candidate_path, "r", encoding="utf-8") as f:
        source = f.read()
    return grade_candidate_source(task_id, config, candidate_path, source)


def run_python_equivalent_file(
    task_id: str,
    task_dir: str,
    config: Mapping[str, Any],
) -> Dict[str, Any]:
    """Run and grade the Python equivalent configured for a benchmark task."""
    rel = config.get("python_equivalent")
    if not rel:
        return {
            "task_id": task_id,
            "ok": False,
            "stage": "python-missing",
            "diagnostic": {"message": "python_equivalent is not configured"},
        }

    path = rel if os.path.isabs(str(rel)) else os.path.join(task_dir, str(rel))
    if not os.path.isfile(path):
        return {
            "task_id": task_id,
            "python_equivalent": path,
            "ok": False,
            "stage": "python-missing",
            "diagnostic": {"message": "python equivalent file not found"},
        }

    timeout_ms = int(config.get("python_timeout_ms", config.get("timeout_ms", 5000)))
    stdin_text = config.get("python_stdin", config.get("stdin", "") or "")
    t0 = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, path],
            cwd=task_dir,
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=timeout_ms / 1000.0 if timeout_ms > 0 else None,
        )
        stdout = proc.stdout
        stderr = proc.stderr
        exit_code = proc.returncode
        stage = "python-exec"
        diagnostic = None
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout or ""
        stderr = e.stderr or ""
        exit_code = 124
        stage = "python-timeout"
        diagnostic = {"message": f"python equivalent exceeded timeout_ms={timeout_ms}"}
    elapsed_ms = _elapsed_ms(t0)

    expected_exit_code = config.get("python_expected_exit_code")
    expected_stdout = config.get("python_expected_stdout")
    expected_stderr = config.get("python_expected_stderr")
    forbidden_stderr_pattern = config.get("python_forbidden_stderr_pattern")

    exit_ok = expected_exit_code is None or exit_code == expected_exit_code
    stdout_ok = expected_stdout is None or stdout == expected_stdout
    stderr_ok = expected_stderr is None or stderr == expected_stderr
    forbidden_ok = True
    forbidden_regex_error = None
    if forbidden_stderr_pattern:
        matched, forbidden_regex_error = _regex_search(forbidden_stderr_pattern, stderr)
        forbidden_ok = not matched and forbidden_regex_error is None

    failure_messages: List[str] = []
    if not exit_ok:
        failure_messages.append(
            f"python exit_code mismatch: expected {expected_exit_code}, got {exit_code}"
        )
    if not stdout_ok:
        failure_messages.append(
            f"python stdout mismatch: expected {expected_stdout!r}, got {stdout!r}"
        )
    if not stderr_ok:
        failure_messages.append(
            f"python stderr mismatch: expected {expected_stderr!r}, got {stderr!r}"
        )
    if forbidden_stderr_pattern and not forbidden_ok:
        if forbidden_regex_error:
            failure_messages.append(
                f"python forbidden stderr regex is invalid: {forbidden_regex_error}"
            )
        else:
            failure_messages.append(
                f"python stderr matched forbidden pattern {forbidden_stderr_pattern!r}"
            )
    if exit_code == 124:
        failure_messages.append(
            f"python equivalent timed out after timeout_ms={timeout_ms}"
        )

    ok = exit_ok and stdout_ok and stderr_ok and forbidden_ok
    return {
        "task_id": task_id,
        "python_equivalent": path,
        "stage": stage,
        "ok": ok,
        "diagnostic": diagnostic,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "elapsed_ms": elapsed_ms,
        "failure_messages": failure_messages,
        "checks": {
            "expected_exit_code": expected_exit_code,
            "expected_stdout": expected_stdout,
            "expected_stderr": expected_stderr,
            "forbidden_stderr_pattern": forbidden_stderr_pattern,
            "exit_code_ok": exit_ok,
            "stdout_ok": stdout_ok,
            "stderr_ok": stderr_ok,
            "forbidden_stderr_pattern_ok": forbidden_ok,
        },
    }
