"""
LangGraph Agent Graph

Defines the state graph and compiles it into a runnable agent.

Graph structure:
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  research   │◄──────────┐
                    └──────┬──────┘           │
                           │                  │
               should_continue()              │
                  /           \\               │
           "tools"         "synthesise"       │
              │                  │            │
       ┌──────▼──────┐    ┌──────▼──────┐     │
       │    tools    │    │  synthesise │     │
       └──────┬──────┘    └──────┬──────┘     │
              │                  │            │
              └──────────────────┘            │
                   back to research ──────────┘
                   (if more tool calls)
                          │
                         END

Key LangGraph concepts shown:
  - StateGraph with typed state (AgentState)
  - Conditional edges (should_continue)
  - ToolNode for automatic tool execution
  - Checkpointing (in-memory saver)
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from agent.nodes import research_node, synthesise_node, should_continue, tool_node
from agent.state import AgentState


def build_graph() -> object:
    """
    Build and compile the research + synthesis agent graph.

    Returns a compiled LangGraph that can be invoked with:
      graph.invoke({"query": "your question"})
    """
    builder = StateGraph(AgentState)

    # Register nodes
    builder.add_node("research", research_node)
    builder.add_node("tools", tool_node)
    builder.add_node("synthesise", synthesise_node)

    # Entry point
    builder.add_edge(START, "research")

    # Conditional edge from research: tools or synthesise
    builder.add_conditional_edges(
        "research",
        should_continue,
        {
            "tools": "tools",
            "synthesise": "synthesise",
        },
    )

    # After tools execute, return to research
    builder.add_edge("tools", "research")

    # Synthesis is the terminal node
    builder.add_edge("synthesise", END)

    # Compile with in-memory checkpointing
    # Replace MemorySaver with SqliteSaver or RedisSaver for persistence
    memory = MemorySaver()
    return builder.compile(checkpointer=memory)


# Module-level compiled graph — import and use directly
graph = build_graph()
