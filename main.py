"""
AWS Infrastructure Audit Agent — Entry Point

Usage:
  python main.py                                           # interactive mode
  python main.py "check IAM for MFA issues"               # single audit
  python main.py "scan all services for security issues"  # full scan
"""

from __future__ import annotations

import sys
import uuid
from dotenv import load_dotenv

load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from agent.graph import graph
from agent.models import Severity

console = Console()

_SEVERITY_COLOR = {
    Severity.CRITICAL: "bold red",
    Severity.MEDIUM: "yellow",
    Severity.INFO: "dim cyan",
}

_SEVERITY_ORDER = [Severity.CRITICAL, Severity.MEDIUM, Severity.INFO]


def run_audit(request: str, thread_id: str | None = None) -> None:
    config = {"configurable": {"thread_id": thread_id or str(uuid.uuid4())}}

    console.print(Panel(
        f"[bold cyan]Audit Request:[/bold cyan] {request}",
        title="AWS Infrastructure Audit Agent",
        expand=False,
    ))

    final_state = graph.invoke({"audit_request": request}, config=config)

    findings = final_state.get("findings", [])
    report = final_state.get("report")
    phase = final_state.get("phase", "")

    if findings:
        table = Table(title="Findings", show_header=True, header_style="bold")
        table.add_column("Severity", min_width=10)
        table.add_column("Type", min_width=14)
        table.add_column("Resource", min_width=22)
        table.add_column("Issue")

        sorted_findings = sorted(
            findings,
            key=lambda f: _SEVERITY_ORDER.index(f.severity) if f.severity in _SEVERITY_ORDER else 99,
        )
        for f in sorted_findings:
            color = _SEVERITY_COLOR.get(f.severity, "")
            table.add_row(
                f"[{color}]{f.severity}[/{color}]",
                f.resource_type,
                f.resource_id,
                f.title[:70],
            )
        console.print(table)
    else:
        console.print("[green]No findings — account appears clean.[/green]")

    if report:
        console.print(Rule("Audit Report"))
        console.print(report.summary)
        console.print(f"\n[dim]{report.formatted_summary()}[/dim]")

    audit_plan = final_state.get("audit_plan", [])
    if audit_plan:
        console.print(f"\n[dim]Services audited: {', '.join(audit_plan)} | Phase reached: {phase}[/dim]")


def interactive_mode() -> None:
    console.print(Panel(
        "[bold]AWS Infrastructure Audit Agent[/bold]\n"
        "LangGraph stateful pipeline: plan → discover → [deep_dive] → report\n"
        "Conditional routing: violations trigger deep investigation automatically\n\n"
        "[dim]Set DEMO_MODE=false + AWS credentials to scan real accounts[/dim]",
        expand=False,
    ))

    thread_id = str(uuid.uuid4())
    console.print(f"[dim]Session: {thread_id} (checkpointed — can resume)[/dim]\n")

    while True:
        try:
            request = input("Audit request: ").strip()
            if request:
                run_audit(request, thread_id=thread_id)
        except KeyboardInterrupt:
            console.print("\n[dim]Exiting.[/dim]")
            break


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_audit(" ".join(sys.argv[1:]))
    else:
        interactive_mode()
