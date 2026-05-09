"""Structured diagnostics. Every error has a code, a category, a position,
a human-readable message, and a machine-readable suggestion."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Position:
    line: int       # 1-based
    column: int     # 1-based

    def to_dict(self) -> dict:
        return {"line": self.line, "column": self.column}


@dataclass
class Diagnostic:
    code: str             # e.g. "E0101"
    category: str         # e.g. lex|parse|type|contract|refinement|effect|capability|runtime
    severity: str         # one of: error|warning|info
    message: str
    position: Position
    suggestion: Optional[str] = None
    confidence: float = 0.0
    source_snippet: Optional[str] = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        line = self.position.line
        column = self.position.column
        out = {
            "code": self.code,
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "line": line,
            "column": column,
            "position": self.position.to_dict(),
            "source_snippet": self.source_snippet,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            "extra": self.extra,
        }
        if self.suggestion is not None:
            out["hint"] = self.suggestion
        for key in (
            "expected",
            "actual",
            "valid_range",
            "actual_index",
            "callsite_line",
            "callsite_column",
            "callsite_source_snippet",
            "contract_line",
            "contract_column",
            "function",
            "argument",
            "actual_value",
            "contract",
            "contract_kind",
            "type_name",
        ):
            if key in self.extra:
                out[key] = self.extra[key]
        return out


class AetherError(Exception):
    """Wrapped diagnostic. Always carries a single Diagnostic.

    The CLI catches these and emits structured JSON when --json is set."""

    def __init__(self, diag: Diagnostic):
        super().__init__(f"[{diag.code}] {diag.message} at line {diag.position.line}, col {diag.position.column}")
        self.diag = diag


def attach_source_context(diag: Diagnostic, source: str) -> Diagnostic:
    """Attach the source line for diagnostics whose position points at source."""
    if diag.source_snippet is not None:
        return diag
    line = diag.position.line
    if line <= 0:
        return diag
    lines = source.splitlines()
    if line <= len(lines):
        diag.source_snippet = lines[line - 1]
    callsite_line = diag.extra.get("callsite_line")
    if (
        isinstance(callsite_line, int)
        and callsite_line > 0
        and "callsite_source_snippet" not in diag.extra
        and callsite_line <= len(lines)
    ):
        diag.extra["callsite_source_snippet"] = lines[callsite_line - 1]
    return diag
