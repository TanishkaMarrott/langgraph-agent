"""
Tests for AWS audit tools in DEMO_MODE — no AWS credentials required.
"""

import os

import pytest

os.environ["DEMO_MODE"] = "true"

from agent.tools import (
    check_security_groups,
    describe_finding,
    list_ec2_instances,
    list_iam_users,
    list_s3_buckets,
)


class TestEC2Tool:
    def test_returns_string(self):
        result = list_ec2_instances.invoke({"region": "us-east-1"})
        assert isinstance(result, str) and len(result) > 0

    def test_finds_untagged_instance(self):
        result = list_ec2_instances.invoke({"region": "us-east-1"})
        assert "UNTAGGED" in result

    def test_finds_public_ip(self):
        result = list_ec2_instances.invoke({"region": "us-east-1"})
        assert "PUBLIC_IP" in result

    def test_tagged_instance_not_flagged_as_untagged(self):
        result = list_ec2_instances.invoke({"region": "us-east-1"})
        assert "i-0def789ghi012" not in result.split("UNTAGGED")[1] if "UNTAGGED" in result else True


class TestS3Tool:
    def test_returns_string(self):
        result = list_s3_buckets.invoke({})
        assert isinstance(result, str) and len(result) > 0

    def test_finds_public_bucket(self):
        result = list_s3_buckets.invoke({})
        assert "PUBLIC_ACCESS" in result

    def test_flags_missing_encryption(self):
        result = list_s3_buckets.invoke({})
        assert "NO_ENCRYPTION" in result

    def test_compliant_bucket_not_flagged(self):
        result = list_s3_buckets.invoke({})
        assert "prod-assets-bucket" not in result


class TestIAMTool:
    def test_returns_string(self):
        result = list_iam_users.invoke({})
        assert isinstance(result, str) and len(result) > 0

    def test_finds_user_without_mfa(self):
        result = list_iam_users.invoke({})
        assert "NO_MFA" in result

    def test_finds_multiple_keys(self):
        result = list_iam_users.invoke({})
        assert "MULTIPLE_KEYS" in result

    def test_finds_stale_user(self):
        result = list_iam_users.invoke({})
        assert "STALE_USER" in result

    def test_compliant_user_not_flagged(self):
        result = list_iam_users.invoke({})
        assert "alice" not in result


class TestSecurityGroupTool:
    def test_returns_string(self):
        result = check_security_groups.invoke({"region": "us-east-1"})
        assert isinstance(result, str) and len(result) > 0

    def test_finds_open_ssh(self):
        result = check_security_groups.invoke({"region": "us-east-1"})
        assert "OPEN_PORT" in result
        assert "SSH" in result

    def test_finds_open_rdp(self):
        result = check_security_groups.invoke({"region": "us-east-1"})
        assert "RDP" in result

    def test_http_https_not_flagged(self):
        result = check_security_groups.invoke({"region": "us-east-1"})
        assert "443" not in result or "OPEN_PORT" not in result.split("443")[0]


class TestDescribeFinding:
    def test_returns_detail_for_known_resource(self):
        result = describe_finding.invoke({"resource_id": "deploy-bot", "resource_type": "IAM"})
        assert "MFA" in result
        assert len(result) > 50

    def test_returns_detail_for_s3(self):
        result = describe_finding.invoke({"resource_id": "my-app-backups-2024", "resource_type": "S3"})
        assert "PII" in result or "public" in result.lower()

    def test_returns_detail_for_ec2(self):
        result = describe_finding.invoke({"resource_id": "i-0abc123def456", "resource_type": "EC2"})
        assert "public" in result.lower() or "SSH" in result

    def test_unknown_resource_returns_gracefully(self):
        result = describe_finding.invoke({"resource_id": "i-unknown", "resource_type": "EC2"})
        assert isinstance(result, str) and len(result) > 0
