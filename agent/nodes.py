"""
Graph Nodes

Each node is a function: (AuditState) → dict of state updates.
LangGraph merges the returned dict into the current state.

Nodes:
  plan_node       — Claude parses the audit request, produces audit_plan
  discover_node   — Claude uses tools to scan all services, produces findings
  deep_dive_node  — Claude investigates critical/medium violations in detail
  report_node     — Claude generates the final AuditReport

Routing:
  route_after_discovery — conditional edge: violations? deep_dive : report
"""

from __future__ import annotations

import json
import os
import re

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import ToolNode

from agent.models import AuditReport, Finding, Severity
from agent.state import AuditState
from agent.tools import RECOMMENDATIONS, TOOLS

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-6")

_llm = ChatAnthropic(model=MODEL, temperature=0)
_llm_with_tools = _llm.bind_tools(TOOLS)

tool_node = ToolNode(TOOLS)

_SEVERITY_MAP = {
    "NO_MFA": Severity.CRITICAL,
    "PUBLIC_ACCESS": Severity.CRITICAL,
    "OPEN_PORT": Severity.CRITICAL,
    "PUBLIC_IP": Severity.MEDIUM,
    "UNTAGGED": Severity.INFO,
    "NO_ENCRYPTION": Severity.MEDIUM,
    "MULTIPLE_KEYS": Severity.MEDIUM,
    "STALE_USER": Severity.MEDIUM,
}

_RESOURCE_TYPE_MAP = {
    "NO_MFA": "IAM",
    "PUBLIC_ACCESS": "S3",
    "OPEN_PORT": "SecurityGroup",
    "PUBLIC_IP": "EC2",
    "UNTAGGED": "EC2",
    "NO_ENCRYPTION": "S3",
    "MULTIPLE_KEYS": "IAM",
    "STALE_USER": "IAM",
}


def _parse_findings(text: str) -> list[Finding]:
    """Parse structured findings from tool output text."""
    findings = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        for prefix, severity in _SEVERITY_MAP.items():
            if line.startswith(prefix + ":"):
                rest = line[len(prefix) + 1:].strip()
                resource_id = rest.split(" ")[0] if rest else "unknown"
                findings.append(Finding(
                    resource_id=resource_id,
                    resource_type=_RESOURCE_TYPE_MAP.get(prefix, "Unknown"),
                    severity=severity,
                    title=line[:100],
                    description=line,
                    recommendation=RECOMMENDATIONS.get(prefix, "Review and remediate."),
                ))
                break
    return findings


def _run_tool_loop(messages: list, max_rounds: int = 5) -> list:
    """Run Claude + tool execution until no more tool calls or max_rounds hit."""
    for _ in range(max_rounds):
        response = _llm_with_tools.invoke(messages)
        messages = messages + [response]
        if not (hasattr(response, "tool_calls") and response.tool_calls):
            break
        tool_results = tool_node.invoke({"messages": messages})
        messages = tool_results.get("messages", messages)
    return messages


def plan_node(state: AuditState) -> dict:
    """
    Parses the audit request and decides which AWS services to check.
    Returns audit_plan: list of service names to audit.
    """
    response = _llm.invoke([
        SystemMessage(content=(
            "You are an AWS security auditor. Given an audit request, decide which AWS services "
            "to check. Return ONLY a JSON array from: [\"EC2\", \"S3\", \"IAM\", \"SecurityGroups\"]. "
            "Example: [\"EC2\", \"IAM\"]"
        )),
        HumanMessage(content=f"Audit request: {state.audit_request}"),
    ])

    content = response.content if isinstance(response.content, str) else str(response.content)
    try:
        match = re.search(r"\[.*?\]", content, re.DOTALL)
        plan = json.loads(match.group()) if match else ["EC2", "S3", "IAM", "SecurityGroups"]
    except Exception:
        plan = ["EC2", "S3", "IAM", "SecurityGroups"]

    return {
        "messages": [response],
        "audit_plan": plan,
        "phase": "discover",
    }


def discover_node(state: AuditState) -> dict:
    """
    Scans all services in the audit_plan using AWS tools.
    Produces findings and filters violations (CRITICAL + MEDIUM).
    """
    plan_text = ", ".join(state.audit_plan)
    messages = [
        SystemMessage(content=(
            "You are an AWS security auditor. Use the tools to scan each service "
            "in the audit plan. Call one tool per service. After scanning all services, "
            "stop — do not call any more tools."
        )),
        HumanMessage(content=(
            f"Audit request: {state.audit_request}\n"
            f"Services to check: {plan_text}\n\n"
            "Call the appropriate tool for each service listed."
        )),
    ]

    messages = _run_tool_loop(messages, max_rounds=6)

    # Extract findings from all tool results
    all_tool_text = ""
    for msg in messages:
        content = msg.content if hasattr(msg, "content") else ""
        if isinstance(content, str):
            all_tool_text += content + "\n"
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    all_tool_text += block.get("text", "") + "\n"

    findings = _parse_findings(all_tool_text)
    violations = [f for f in findings if f.severity in (Severity.CRITICAL, Severity.MEDIUM)]

    return {
        "messages": messages[-4:],
        "findings": findings,
        "violations": violations,
        "phase": "deep_dive" if violations else "report",
    }


def deep_dive_node(state: AuditState) -> dict:
    """
    Investigates critical and medium violations using describe_finding.
    Enriches findings with risk detail before report generation.
    """
    top_violations = state.violations[:4]
    violation_summary = "\n".join(
        f"- [{v.severity}] {v.resource_type} {v.resource_id}: {v.title}"
        for v in top_violations
    )

    messages = [
        SystemMessage(content=(
            "You are an AWS security auditor investigating violations. "
            "For each violation listed, call describe_finding to get full details. "
            "After investigating all violations, stop."
        )),
        HumanMessage(content=(
            f"Violations found during discovery:\n{violation_summary}\n\n"
            "Investigate each one using describe_finding."
        )),
    ]

    messages = _run_tool_loop(messages, max_rounds=4)

    return {
        "messages": messages[-4:],
        "phase": "report",
    }


def report_node(state: AuditState) -> dict:
    """
    Generates the final structured AuditReport from all findings.
    """
    findings_text = "\n".join(
        f"[{f.severity}] {f.resource_type} {f.resource_id}: {f.description}\n"
        f"  → Recommendation: {f.recommendation}"
        for f in state.findings
    ) or "No findings — account appears clean."

    response = _llm.invoke([
        SystemMessage(content=(
            "You are an AWS security auditor writing a final report. "
            "Structure your report: one-line SUMMARY, then CRITICAL findings, "
            "then MEDIUM findings, then INFO. Be specific and actionable."
        )),
        HumanMessage(content=(
            f"Audit request: {state.audit_request}\n\n"
            f"Findings:\n{findings_text}\n\n"
            "Write the final audit report."
        )),
    ])

    report_text = response.content if isinstance(response.content, str) else str(response.content)

    report = AuditReport(
        audit_request=state.audit_request,
        summary=report_text,
        findings=state.findings,
    )

    return {
        "messages": [response],
        "report": report,
        "phase": "complete",
    }


def route_after_discovery(state: AuditState) -> str:
    """
    Conditional edge after discover_node.

    Violations (CRITICAL or MEDIUM) found → deep_dive for detailed investigation.
    Account is clean → skip deep_dive, go straight to report.
    """
    if state.violations:
        return "deep_dive"
    return "report"
