"""Tests for Finding and AuditReport models — no external dependencies."""

import pytest

from agent.models import AuditReport, Finding, Severity


class TestFinding:
    def _make(self, severity=Severity.CRITICAL, resource_id="i-123", resource_type="EC2"):
        return Finding(
            resource_id=resource_id,
            resource_type=resource_type,
            severity=severity,
            title="test finding",
            description="description",
            recommendation="fix it",
        )

    def test_creation(self):
        f = self._make()
        assert f.resource_id == "i-123"
        assert f.severity == Severity.CRITICAL

    def test_severity_enum_values(self):
        assert Severity.CRITICAL == "CRITICAL"
        assert Severity.MEDIUM == "MEDIUM"
        assert Severity.INFO == "INFO"

    def test_default_region(self):
        f = self._make()
        assert f.region == "us-east-1"

    def test_custom_region(self):
        f = Finding(
            resource_id="bucket",
            resource_type="S3",
            severity=Severity.MEDIUM,
            title="t",
            description="d",
            recommendation="r",
            region="eu-west-1",
        )
        assert f.region == "eu-west-1"


class TestAuditReport:
    def _make_finding(self, severity: Severity, rid: str = "x") -> Finding:
        return Finding(
            resource_id=rid,
            resource_type="EC2",
            severity=severity,
            title="t",
            description="d",
            recommendation="r",
        )

    def test_empty_report(self):
        report = AuditReport(audit_request="check everything")
        assert report.critical_count == 0
        assert report.medium_count == 0
        assert report.info_count == 0

    def test_counts_by_severity(self):
        findings = [
            self._make_finding(Severity.CRITICAL, "a"),
            self._make_finding(Severity.CRITICAL, "b"),
            self._make_finding(Severity.MEDIUM, "c"),
            self._make_finding(Severity.INFO, "d"),
            self._make_finding(Severity.INFO, "e"),
        ]
        report = AuditReport(audit_request="test", findings=findings)
        assert report.critical_count == 2
        assert report.medium_count == 1
        assert report.info_count == 2

    def test_formatted_summary_contains_counts(self):
        findings = [self._make_finding(Severity.CRITICAL, "a")]
        report = AuditReport(audit_request="test", findings=findings)
        summary = report.formatted_summary()
        assert "1 critical" in summary
        assert "0 medium" in summary

    def test_formatted_summary_zero_counts(self):
        report = AuditReport(audit_request="test")
        assert "0 critical" in report.formatted_summary()

    def test_summary_field_stored(self):
        report = AuditReport(audit_request="test", summary="All clear.")
        assert report.summary == "All clear."
