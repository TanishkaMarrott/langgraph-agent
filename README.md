# langgraph-agent

Stateful research + synthesis agent built with LangGraph and Claude — demonstrates conditional graph edges, tool use, and in-memory checkpointing.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![LangGraph](https://img.shields.io/badge/Framework-LangGraph-orange)
![Claude](https://img.shields.io/badge/LLM-Claude-purple)
![LangChain](https://img.shields.io/badge/LangChain-Anthropic-green)

---

## What This Is

A two-node LangGraph agent that separates **research** from **synthesis**. The research node uses tools to gather information; the synthesis node turns those notes into a clean final answer. State persists across both nodes via LangGraph's typed state graph.

---

## Graph

```
START
  │
  ▼
research ──► should_continue() ──► "tools" ──► tool_node ──┐
  ▲                │                                        │
  └────────────────┘ (loop back after tools)                │
                   │
              "synthesise"
                   │
                   ▼
              synthesise
                   │
                   ▼
                 END
```

### Key LangGraph Concepts

| Concept | Where it's used |
|---|---|
| `StateGraph` | `agent/graph.py` — typed state passed between nodes |
| `AgentState` | `agent/state.py` — Pydantic model with `add_messages` annotation |
| Conditional edges | `should_continue()` — routes to tools or synthesis |
| `ToolNode` | Automatic tool execution after Claude's tool calls |
| `MemorySaver` | In-memory checkpointing — pause + resume across calls |

---

## State Schema

```python
class AgentState(BaseModel):
    messages: Annotated[list[BaseMessage], add_messages]  # append-only history
    query: str                 # original question
    research_notes: list[str]  # notes from research node
    sources: list[str]         # references collected
    final_answer: str          # output from synthesis node
    iteration: int             # research loop count
```

State flows through every node. Each node returns only the fields it updates — LangGraph merges them.

---

## Tools

| Tool | Description |
|---|---|
| `search_web(query)` | Web search (simulated — swap with TavilySearch) |
| `get_current_date()` | Returns today's date for time-aware queries |
| `calculate(expression)` | Safe arithmetic evaluation |

---

## Quick Start

```bash
git clone https://github.com/TanishkaMarrott/langgraph-agent.git
cd langgraph-agent
pip install -r requirements.txt
cp .env.example .env
# Add ANTHROPIC_API_KEY

# Single query
python main.py "What are the key differences between RAG and fine-tuning?"

# Interactive mode
python main.py
```

---

## LangSmith Tracing (Optional)

```bash
# .env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-key
LANGCHAIN_PROJECT=langgraph-agent
```

With tracing enabled, every node execution, tool call, and state transition is recorded in LangSmith.

---

## Project Structure

```
langgraph-agent/
├── agent/
│   ├── state.py     # AgentState — typed state schema
│   ├── tools.py     # search_web, calculate, get_current_date
│   ├── nodes.py     # research_node, synthesise_node, should_continue
│   └── graph.py     # StateGraph definition + compilation
└── main.py          # Entry point — interactive + single query
```

---

## Author

Built by [Tanishka Marrott](https://github.com/TanishkaMarrott) — AI Agent Systems Engineer
