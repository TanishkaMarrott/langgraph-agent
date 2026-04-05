"""
AWS Infrastructure Audit Graph

5-node LangGraph pipeline with conditional routing based on findings.

Graph structure:

    START
      │
    plan          ← parses audit request, sets audit_plan
      │
    discover      ← scans AWS services with tools, sets findings + violations
      │
  route_after_discovery()
    /           \\
deep_dive      report    ← clean account skips deep_dive entirely
    \\           /
     report
      │
     END

Key LangGraph concepts:
  StateGraph         — typed state (AuditState) passed between nodes
  Conditional edges  — route_after_discovery() branches on violations found
  MemorySaver        — in-memory checkpointing (pause + resume)
  ToolNode           — automatic tool execution within discover/deep_dive nodes
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agent.nodes import deep_dive_node, discover_node, plan_node, report_node, route_after_discovery
from agent.state import AuditState


def build_graph():
    builder = StateGraph(AuditState)

    builder.add_node("plan", plan_node)
    builder.add_node("discover", discover_node)
    builder.add_node("deep_dive", deep_dive_node)
    builder.add_node("report", report_node)

    builder.add_edge(START, "plan")
    builder.add_edge("plan", "discover")

    # KEY: graph topology changes based on what discover finds
    builder.add_conditional_edges(
        "discover",
        route_after_discovery,
        {
            "deep_dive": "deep_dive",
            "report": "report",
        },
    )

    builder.add_edge("deep_dive", "report")
    builder.add_edge("report", END)

    memory = MemorySaver()
    return builder.compile(checkpointer=memory)


graph = build_graph()
