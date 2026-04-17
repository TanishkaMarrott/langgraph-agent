"""
Agent State

LangGraph passes state through every node in the graph.
Each node reads from state and returns updates to it.

State is the key difference between LangGraph and a plain agent loop:
  - It persists across nodes
  - It can be checkpointed (paused + resumed)
  - It makes data flow between nodes explicit and inspectable
"""

from __future__ import annotations

from typing import Annotated, Optional
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage


class AgentState(BaseModel):
    """
    Shared state passed between all nodes in the graph.

    messages:        full conversation history (append-only via add_messages)
    query:           the original user question
    research_notes:  raw notes gathered during the research node
    sources:         URLs or references collected
    final_answer:    synthesised answer produced by the synthesis node
    iteration:       how many research iterations have run
    """

    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)
    query: str = ""
    research_notes: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    final_answer: str = ""
    iteration: int = 0
