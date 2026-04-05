from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    MEDIUM = "MEDIUM"
    INFO = "INFO"


class Finding(BaseModel):
    resource_id: str
    resource_type: str
    severity: Severity
    title: str
    description: str
    recommendation: str
    region: str = "us-east-1"


class AuditReport(BaseModel):
    audit_request: str
    summary: str = ""
    findings: list[Finding] = Field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.MEDIUM)

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.INFO)

    def formatted_summary(self) -> str:
        return (
            f"Audit complete: {self.critical_count} critical, "
            f"{self.medium_count} medium, {self.info_count} info findings."
        )
