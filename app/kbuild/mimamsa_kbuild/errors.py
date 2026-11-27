"""Build refusal: any stage that cannot prove its inputs or outputs stops the build with a code (fail closed)."""
from __future__ import annotations


class BuildRefused(RuntimeError):
    def __init__(self, code: str, message: str, stage: str | None = None, details: list | None = None):
        super().__init__(f"[{stage or '-'}] {code}: {message}")
        self.code = code
        self.message = message
        self.stage = stage
        self.details = details or []

    def as_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "stage": self.stage, "details": self.details[:50]}
