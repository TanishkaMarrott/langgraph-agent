"""
LangGraph Agent — Entry Point

Usage:
  python main.py                     # interactive mode
  python main.py "your question"     # single query
"""

from __future__ import annotations

import sys
import uuid
from dotenv import load_dotenv

load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from agent.graph import graph

console = Console()


def run_query(query: str, thread_id: str | None = None) -> str:
    """Run a single query through the agent graph."""
    config = {"configurable": {"thread_id": thread_id or str(uuid.uuid4())}}

    console.print(f"\n[bold cyan]Query:[/bold cyan] {query}")
    console.print("[dim]Running research → synthesis graph...[/dim]\n")

    final_state = graph.invoke({"query": query}, config=config)

    answer = final_state.get("final_answer", "No answer generated.")
    notes = final_state.get("research_notes", [])
    iterations = final_state.get("iteration", 0)

    console.print(Rule("Final Answer"))
    console.print(answer)
    console.print(f"\n[dim]Research iterations: {iterations} | Notes gathered: {len(notes)}[/dim]")

    return answer


def interactive_mode() -> None:
    console.print(Panel(
        "[bold]LangGraph Agent[/bold]\n"
        "Research + Synthesis graph with persistent state\n"
        "Type your question. Ctrl+C to exit.",
        expand=False,
    ))

    thread_id = str(uuid.uuid4())
    console.print(f"[dim]Session: {thread_id}[/dim]\n")

    while True:
        try:
            query = input("Query: ").strip()
            if query:
                run_query(query, thread_id=thread_id)
        except KeyboardInterrupt:
            console.print("\n[dim]Exiting.[/dim]")
            break


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_query(" ".join(sys.argv[1:]))
    else:
        interactive_mode()
