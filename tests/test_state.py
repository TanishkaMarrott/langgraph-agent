"""Tests for AuditState — no external dependencies."""

import pytest

from agent.models import Finding, Severity
from agent.state import AuditState


def _finding(severity=Severity.CRITICAL, rid="x"):
    return Finding(
        resource_id=rid,
        resource_type="EC2",
        severity=severity,
        title="t",
        description="d",
        recommendation="r",
    )


class TestAuditState:
    def test_defaults(self):
        state = AuditState()
        assert state.audit_request == ""
        assert state.audit_plan == []
        assert state.findings == []
        assert state.violations == []
        assert state.report is None
        assert state.phase == "plan"

    def test_with_audit_request(self):
        state = AuditState(audit_request="check IAM for MFA issues")
        assert state.audit_request == "check IAM for MFA issues"

    def test_with_findings(self):
        f = _finding()
        state = AuditState(findings=[f])
        assert len(state.findings) == 1
        assert state.findings[0].severity == Severity.CRITICAL

    def test_violations_separate_from_findings(self):
        critical = _finding(Severity.CRITICAL, "a")
        info = _finding(Severity.INFO, "b")
        state = AuditState(
            findings=[critical, info],
            violations=[critical],
        )
        assert len(state.findings) == 2
        assert len(state.violations) == 1

    def test_audit_plan_stored(self):
        state = AuditState(audit_plan=["EC2", "S3", "IAM"])
        assert "IAM" in state.audit_plan

    def test_phase_transitions(self):
        for phase in ["plan", "discover", "deep_dive", "report", "complete"]:
            state = AuditState(phase=phase)
            assert state.phase == phase
