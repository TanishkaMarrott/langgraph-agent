"""
Tests for graph structure and conditional routing logic.
"""

import pytest
from langchain_core.messages import AIMessage
from agent.graph import graph
from agent.nodes import should_continue
from agent.state import AgentState


def test_graph_has_required_nodes():
    # Compiled graph exposes node names
    node_names = set(graph.nodes.keys())
    assert "research" in node_names
    assert "tools" in node_names
    assert "synthesise" in node_names


def test_should_continue_routes_to_synthesise_when_no_tool_calls():
    state = AgentState(
        query="test",
        messages=[AIMessage(content="I have enough information.")],
    )
    assert should_continue(state) == "synthesise"


def test_should_continue_routes_to_tools_when_tool_calls_present():
    msg = AIMessage(content="")
    msg.tool_calls = [{"name": "search_web", "args": {"query": "test"}, "id": "abc"}]
    state = AgentState(query="test", messages=[msg])
    assert should_continue(state) == "tools"


def test_should_continue_empty_messages_goes_to_synthesise():
    state = AgentState(query="test", messages=[])
    assert should_continue(state) == "synthesise"
