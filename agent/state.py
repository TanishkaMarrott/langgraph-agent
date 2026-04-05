"""
Audit State

All nodes in the graph read from and write updates to this state.
LangGraph merges return dicts into the current state after each node.

State is the backbone of the audit pipeline:
  - audit_request  : the plain-English instruction from the user
  - audit_plan     : which AWS services to check (set by plan node)
  - findings       : all issues discovered (set by discover node)
  - violations     : critical + medium findings that need deep investigation
  - report         : final structured output (set by report node)
  - phase          : tracks current position in the pipeline
"""

from __future__ import annotations

from typing import Annotated, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from agent.models import AuditReport, Finding


class AuditState(BaseModel):
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)
    audit_request: str = ""
    audit_plan: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    violations: list[Finding] = Field(default_factory=list)
    report: Optional[AuditReport] = None
    phase: str = "plan"
