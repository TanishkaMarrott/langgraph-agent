"""
Tests for graph structure and conditional routing logic.
No LLM calls — tests the routing function directly.
"""

import os

import pytest

os.environ["DEMO_MODE"] = "true"
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-dummy")

from agent.models import Finding, Severity
from agent.nodes import route_after_discovery
from agent.state import AuditState


def _finding(severity: Severity, rid: str = "x") -> Finding:
    return Finding(
        resource_id=rid,
        resource_type="EC2",
        severity=severity,
        title="t",
        description="d",
        recommendation="r",
    )


class TestRouteAfterDiscovery:
    def test_routes_to_deep_dive_on_critical(self):
        state = AuditState(violations=[_finding(Severity.CRITICAL)])
        assert route_after_discovery(state) == "deep_dive"

    def test_routes_to_deep_dive_on_medium(self):
        state = AuditState(violations=[_finding(Severity.MEDIUM)])
        assert route_after_discovery(state) == "deep_dive"

    def test_routes_to_report_when_clean(self):
        state = AuditState(violations=[])
        assert route_after_discovery(state) == "report"

    def test_routes_to_deep_dive_on_mixed_violations(self):
        state = AuditState(violations=[
            _finding(Severity.CRITICAL, "a"),
            _finding(Severity.MEDIUM, "b"),
        ])
        assert route_after_discovery(state) == "deep_dive"

    def test_info_only_routes_to_report(self):
        # INFO findings are NOT added to violations — only critical + medium are
        state = AuditState(
            findings=[_finding(Severity.INFO)],
            violations=[],
        )
        assert route_after_discovery(state) == "report"


class TestGraphStructure:
    def test_graph_has_all_nodes(self):
        from agent.graph import graph

        node_names = set(graph.nodes.keys())
        assert "plan" in node_names
        assert "discover" in node_names
        assert "deep_dive" in node_names
        assert "report" in node_names

    def test_graph_compiles_without_error(self):
        from agent.graph import build_graph

        g = build_graph()
        assert g is not None
