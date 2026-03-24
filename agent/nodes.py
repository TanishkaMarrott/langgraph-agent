"""
Graph Nodes

Each node is a pure function: (state) → state updates.
LangGraph calls them in order based on the graph edges.

Nodes:
  research_node    — Claude uses tools to gather information
  synthesise_node  — Claude synthesises research into a final answer
  should_continue  — conditional edge: loop back or proceed to synthesis
"""

from __future__ import annotations

import os
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import ToolNode

from agent.state import AgentState
from agent.tools import TOOLS

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-6")

# Claude bound to the tools — used in research node
_llm = ChatAnthropic(model=MODEL, temperature=0)
_llm_with_tools = _llm.bind_tools(TOOLS)

# ToolNode handles tool execution automatically
tool_node = ToolNode(TOOLS)

RESEARCH_SYSTEM = """You are a research agent. Your job is to gather information to answer a question.

Use the available tools to search for relevant information.
Gather 2-3 pieces of evidence before concluding your research.
Be thorough but concise in your notes."""

SYNTHESIS_SYSTEM = """You are a synthesis agent. You receive research notes and must produce a clear,
well-structured final answer.

Guidelines:
- Lead with the direct answer
- Support with evidence from the research notes
- Cite sources where available
- Be concise — no more than 3 paragraphs"""


def research_node(state: AgentState) -> dict:
    """
    Research node — Claude uses tools to gather information.

    Reads: state.query, state.messages
    Writes: messages (with tool calls), research_notes, sources, iteration
    """
    messages = list(state.messages)

    # First iteration: inject the query as a human message
    if state.iteration == 0:
        messages = [
            SystemMessage(content=RESEARCH_SYSTEM),
            HumanMessage(content=f"Research this question thoroughly: {state.query}"),
        ]

    response = _llm_with_tools.invoke(messages)

    # Extract any text content as research notes
    notes = list(state.research_notes)
    if hasattr(response, "content") and isinstance(response.content, str) and response.content:
        notes.append(response.content)

    return {
        "messages": [response],
        "research_notes": notes,
        "iteration": state.iteration + 1,
    }


def synthesise_node(state: AgentState) -> dict:
    """
    Synthesis node — Claude produces the final answer from research notes.

    Reads: state.query, state.research_notes, state.messages
    Writes: messages, final_answer
    """
    # Compile research context from notes and tool results
    tool_results = []
    for msg in state.messages:
        if hasattr(msg, "type") and msg.type == "tool":
            tool_results.append(str(msg.content))

    research_context = "\n\n".join(
        [f"Research note {i+1}: {note}" for i, note in enumerate(state.research_notes)]
        + [f"Tool result: {r}" for r in tool_results[:5]]
    )

    synthesis_messages = [
        SystemMessage(content=SYNTHESIS_SYSTEM),
        HumanMessage(content=(
            f"Question: {state.query}\n\n"
            f"Research gathered:\n{research_context or 'No research notes available.'}\n\n"
            "Produce a clear, concise final answer."
        )),
    ]

    response = _llm.invoke(synthesis_messages)
    answer = response.content if isinstance(response.content, str) else str(response.content)

    return {
        "messages": [response],
        "final_answer": answer,
    }


def should_continue(state: AgentState) -> str:
    """
    Conditional edge — decides whether to continue tool use or move to synthesis.

    Returns "tools"     → execute pending tool calls
    Returns "synthesise" → proceed to synthesis node
    """
    last_message = state.messages[-1] if state.messages else None

    # If the last message has tool calls, execute them
    if last_message and hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    # If we've done enough research (or no more tool calls), synthesise
    return "synthesise"
