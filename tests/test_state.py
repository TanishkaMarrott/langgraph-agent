"""
Tests for AgentState schema and message accumulation.
"""

import pytest
from langchain_core.messages import HumanMessage, AIMessage
from agent.state import AgentState


def test_agent_state_defaults():
    state = AgentState(query="What is RAG?")
    assert state.query == "What is RAG?"
    assert state.messages == []
    assert state.research_notes == []
    assert state.sources == []
    assert state.final_answer == ""
    assert state.iteration == 0


def test_agent_state_with_messages():
    msgs = [HumanMessage(content="Hello"), AIMessage(content="Hi")]
    state = AgentState(query="test", messages=msgs)
    assert len(state.messages) == 2


def test_agent_state_iteration_tracking():
    state = AgentState(query="test", iteration=3)
    assert state.iteration == 3


def test_research_notes_accumulation():
    notes = ["Note 1", "Note 2", "Note 3"]
    state = AgentState(query="test", research_notes=notes)
    assert len(state.research_notes) == 3
    assert state.research_notes[0] == "Note 1"


def test_final_answer_field():
    state = AgentState(query="test", final_answer="The answer is 42.")
    assert state.final_answer == "The answer is 42."
