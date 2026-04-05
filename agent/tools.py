"""
AWS Audit Tools

Tools used by the discover and deep_dive nodes to scan AWS resources.

All tools run in DEMO_MODE by default — realistic simulated data,
no AWS credentials required. Set DEMO_MODE=false and provide
AWS credentials to scan real accounts.

Tools:
  list_ec2_instances(region)          — untagged instances, public IPs
  list_s3_buckets()                   — public access, missing encryption
  list_iam_users()                    — MFA disabled, stale accounts, excess keys
  check_security_groups(region)       — open admin ports from 0.0.0.0/0
  describe_finding(resource_id, type) — deep detail on a specific resource
"""

from __future__ import annotations

import os
from datetime import datetime

from langchain_core.tools import tool

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

_DEMO_EC2 = [
    {
        "instance_id": "i-0abc123def456",
        "type": "t3.large",
        "tags": {},
        "public_ip": "54.21.33.100",
    },
    {
        "instance_id": "i-0def789ghi012",
        "type": "t2.micro",
        "tags": {"Name": "web-server", "Env": "prod"},
        "public_ip": None,
    },
]

_DEMO_S3 = [
    {"bucket": "my-app-backups-2024", "public_access_blocked": False, "encryption": None},
    {"bucket": "prod-assets-bucket", "public_access_blocked": True, "encryption": "AES256"},
]

_DEMO_IAM = [
    {"username": "deploy-bot", "mfa_enabled": False, "last_active": "2026-01-15", "access_keys": 2},
    {"username": "alice", "mfa_enabled": True, "last_active": "2026-04-30", "access_keys": 1},
    {"username": "old-jenkins", "mfa_enabled": False, "last_active": "2025-08-10", "access_keys": 1},
]

_DEMO_SGS = [
    {
        "sg_id": "sg-0abc111",
        "name": "launch-wizard-1",
        "open_ingress": ["0.0.0.0/0:22", "0.0.0.0/0:3389"],
    },
    {
        "sg_id": "sg-0def222",
        "name": "web-sg",
        "open_ingress": ["0.0.0.0/0:443"],
    },
    {
        "sg_id": "sg-0ghi333",
        "name": "internal-sg",
        "open_ingress": [],
    },
]

_DEMO_DETAILS = {
    "i-0abc123def456": (
        "EC2 i-0abc123def456 (t3.large): running since 2026-03-01. No tags at all. "
        "Public IP 54.21.33.100 is internet-facing. Associated with sg-0abc111 which "
        "allows SSH from 0.0.0.0/0. Risk: untagged + public IP + open SSH."
    ),
    "my-app-backups-2024": (
        "S3 bucket my-app-backups-2024: 45 objects, 2.3 GB. Public access block DISABLED. "
        "No default encryption. Files named backup_users_*.sql — likely contains PII. "
        "Risk: CRITICAL — publicly readable bucket with potential PII data."
    ),
    "deploy-bot": (
        "IAM user deploy-bot: MFA disabled. 2 active access keys. "
        "Attached policy: AdministratorAccess. Last active: 2026-01-15. "
        "Risk: CRITICAL — admin user, no MFA, 2 keys, dormant 107 days."
    ),
    "sg-0abc111": (
        "Security group sg-0abc111 (launch-wizard-1): allows SSH (22) and RDP (3389) "
        "from 0.0.0.0/0. Attached to i-0abc123def456 which has a public IP. "
        "Risk: CRITICAL — direct internet exposure on admin ports."
    ),
}

_SENSITIVE_PORTS = {22: "SSH", 3389: "RDP", 5432: "PostgreSQL", 3306: "MySQL"}


@tool
def list_ec2_instances(region: str = "us-east-1") -> str:
    """
    List running EC2 instances and flag untagged instances and public IPs.
    Returns one issue per line prefixed with issue type (UNTAGGED, PUBLIC_IP).
    """
    if DEMO_MODE:
        issues = []
        for inst in _DEMO_EC2:
            if not inst["tags"]:
                issues.append(f"UNTAGGED: {inst['instance_id']} ({inst['type']}) has no resource tags")
            if inst["public_ip"]:
                issues.append(f"PUBLIC_IP: {inst['instance_id']} has public IP {inst['public_ip']}")
        return "\n".join(issues) if issues else "No EC2 issues found."

    import boto3
    ec2 = boto3.client("ec2", region_name=region)
    issues = []
    for r in ec2.describe_instances()["Reservations"]:
        for inst in r["Instances"]:
            if inst["State"]["Name"] != "running":
                continue
            iid = inst["InstanceId"]
            itype = inst["InstanceType"]
            if not inst.get("Tags"):
                issues.append(f"UNTAGGED: {iid} ({itype}) has no resource tags")
            if inst.get("PublicIpAddress"):
                issues.append(f"PUBLIC_IP: {iid} has public IP {inst['PublicIpAddress']}")
    return "\n".join(issues) if issues else "No EC2 issues found."


@tool
def list_s3_buckets() -> str:
    """
    List S3 buckets and flag missing public access blocks and unencrypted buckets.
    Returns one issue per line prefixed with issue type (PUBLIC_ACCESS, NO_ENCRYPTION).
    """
    if DEMO_MODE:
        issues = []
        for b in _DEMO_S3:
            if not b["public_access_blocked"]:
                issues.append(f"PUBLIC_ACCESS: s3://{b['bucket']} does not block public access")
            if not b["encryption"]:
                issues.append(f"NO_ENCRYPTION: s3://{b['bucket']} has no default encryption")
        return "\n".join(issues) if issues else "No S3 issues found."

    import boto3
    s3 = boto3.client("s3")
    issues = []
    for bucket in s3.list_buckets()["Buckets"]:
        name = bucket["Name"]
        try:
            pab = s3.get_public_access_block(Bucket=name)["PublicAccessBlockConfiguration"]
            if not all(pab.values()):
                issues.append(f"PUBLIC_ACCESS: s3://{name}")
        except Exception:
            issues.append(f"PUBLIC_ACCESS: s3://{name} (no public access block configured)")
        try:
            s3.get_bucket_encryption(Bucket=name)
        except Exception:
            issues.append(f"NO_ENCRYPTION: s3://{name}")
    return "\n".join(issues) if issues else "No S3 issues found."


@tool
def list_iam_users() -> str:
    """
    List IAM users and flag: MFA disabled, multiple active access keys, inactive accounts.
    Returns one issue per line prefixed with issue type (NO_MFA, MULTIPLE_KEYS, STALE_USER).
    """
    if DEMO_MODE:
        issues = []
        now = datetime(2026, 5, 2)
        for user in _DEMO_IAM:
            if not user["mfa_enabled"]:
                issues.append(f"NO_MFA: {user['username']} does not have MFA enabled")
            if user["access_keys"] > 1:
                issues.append(
                    f"MULTIPLE_KEYS: {user['username']} has {user['access_keys']} active access keys"
                )
            last = datetime.strptime(user["last_active"], "%Y-%m-%d")
            if (now - last).days > 90:
                issues.append(
                    f"STALE_USER: {user['username']} inactive for {(now - last).days} days"
                )
        return "\n".join(issues) if issues else "No IAM issues found."

    import boto3
    iam = boto3.client("iam")
    issues = []
    for user in iam.list_users()["Users"]:
        uname = user["UserName"]
        if not iam.list_mfa_devices(UserName=uname)["MFADevices"]:
            issues.append(f"NO_MFA: {uname}")
        keys = iam.list_access_keys(UserName=uname)["AccessKeyMetadata"]
        if len(keys) > 1:
            issues.append(f"MULTIPLE_KEYS: {uname} has {len(keys)} active access keys")
    return "\n".join(issues) if issues else "No IAM issues found."


@tool
def check_security_groups(region: str = "us-east-1") -> str:
    """
    Check security groups for open inbound rules on sensitive ports from 0.0.0.0/0.
    Flags SSH (22), RDP (3389), PostgreSQL (5432), MySQL (3306).
    Returns one issue per line prefixed with OPEN_PORT.
    """
    if DEMO_MODE:
        issues = []
        for sg in _DEMO_SGS:
            for rule in sg["open_ingress"]:
                if "0.0.0.0/0" in rule:
                    port = int(rule.split(":")[1])
                    if port in _SENSITIVE_PORTS:
                        issues.append(
                            f"OPEN_PORT: {sg['sg_id']} ({sg['name']}) allows "
                            f"{_SENSITIVE_PORTS[port]} port {port} from 0.0.0.0/0"
                        )
        return "\n".join(issues) if issues else "No security group issues found."

    import boto3
    ec2 = boto3.client("ec2", region_name=region)
    issues = []
    for sg in ec2.describe_security_groups()["SecurityGroups"]:
        for rule in sg.get("IpPermissions", []):
            port = rule.get("FromPort", 0)
            for ip in rule.get("IpRanges", []):
                if ip.get("CidrIp") == "0.0.0.0/0" and port in _SENSITIVE_PORTS:
                    issues.append(
                        f"OPEN_PORT: {sg['GroupId']} ({sg['GroupName']}) allows "
                        f"{_SENSITIVE_PORTS[port]} port {port} from 0.0.0.0/0"
                    )
    return "\n".join(issues) if issues else "No security group issues found."


@tool
def describe_finding(resource_id: str, resource_type: str) -> str:
    """
    Get deep detail on a specific resource for investigation.
    resource_type: EC2 | S3 | IAM | SecurityGroup
    resource_id: the instance ID, bucket name, username, or security group ID.
    """
    if DEMO_MODE:
        return _DEMO_DETAILS.get(
            resource_id,
            f"{resource_type} {resource_id}: no additional detail available in demo mode.",
        )

    return f"describe_finding: set DEMO_MODE=false and provide AWS credentials to fetch live data."


TOOLS = [list_ec2_instances, list_s3_buckets, list_iam_users, check_security_groups, describe_finding]

RECOMMENDATIONS = {
    "NO_MFA": "Enable MFA immediately. For service accounts, use IAM roles instead of users.",
    "PUBLIC_ACCESS": "Enable S3 Block Public Access at account level. Audit bucket policies.",
    "OPEN_PORT": "Restrict to specific CIDR ranges or use a bastion host / VPN.",
    "PUBLIC_IP": "Move behind a load balancer or NAT Gateway if external access not required.",
    "UNTAGGED": "Add Name, Environment, and Owner tags for cost attribution and governance.",
    "NO_ENCRYPTION": "Enable default encryption (AES-256 or KMS) on the S3 bucket.",
    "MULTIPLE_KEYS": "Rotate and delete unused keys. Maximum one active key per user.",
    "STALE_USER": "Deactivate or delete IAM users inactive for more than 90 days.",
}
