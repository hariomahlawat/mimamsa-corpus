from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    where: str = ""
    severity: str = "error"  # "error" rejects; "warning" is reported only

    def __str__(self) -> str:  # pragma: no cover - formatting only
        loc = f" [{self.where}]" if self.where else ""
        return f"{self.severity.upper()} {self.code}{loc}: {self.message}"


@dataclass
class ValidationReport:
    issues: list[Issue] = field(default_factory=list)
    checked_records: int = 0
    checked_files: int = 0
    signature_verified: bool = False

    def add(self, issue: Issue) -> None:
        self.issues.append(issue)

    def extend(self, issues) -> None:
        self.issues.extend(issues)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def codes(self) -> set[str]:
        return {i.code for i in self.issues}
