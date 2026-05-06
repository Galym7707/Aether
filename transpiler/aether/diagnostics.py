"""Structured diagnostics. Every error has a code, a category, a position,
a human-readable message, and a machine-readable suggestion."""

from __future__ import annotations
from dataclasses import dataclass, asdict, field
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
    category: str         # one of: lex|parse|type|contract|effect|capability|runtime
    severity: str         # one of: error|warning|info
    message: str
    position: Position
    suggestion: Optional[str] = None
    confidence: float = 0.0
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "position": self.position.to_dict(),
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            "extra": self.extra,
        }


class AetherError(Exception):
    """Wrapped diagnostic. Always carries a single Diagnostic.

    The CLI catches these and emits structured JSON when --json is set."""

    def __init__(self, diag: Diagnostic):
        super().__init__(f"[{diag.code}] {diag.message} at line {diag.position.line}, col {diag.position.column}")
        self.diag = diag
