"""
Agent Tools

Tools available to the research node.
These are standard LangChain tools — any tool can be added here.

Current tools:
  search_web(query)      — simulated web search (real: use TavilySearch)
  get_current_date()     — returns today's date for time-aware queries
  calculate(expression)  — safe arithmetic evaluation
"""

from __future__ import annotations

import ast
import operator
from datetime import datetime

from langchain_core.tools import tool


@tool
def search_web(query: str) -> str:
    """
    Search the web for information about a topic.
    Returns a summary of the most relevant results.

    In production: replace with TavilySearchResults or SerpAPI.
    """
    # Simulated results for demo — replace with real search tool
    simulated_results = {
        "default": (
            f"Search results for '{query}':\n"
            "1. Found relevant information about the topic from multiple sources.\n"
            "2. Key facts: The subject has been studied extensively with varied findings.\n"
            "3. Recent developments suggest continued progress in this area.\n"
            "Note: These are simulated results. "
            "Replace search_web() with TavilySearchResults for real queries."
        )
    }
    return simulated_results.get(query.lower(), simulated_results["default"])


@tool
def get_current_date() -> str:
    """Returns today's date. Use for time-sensitive queries."""
    return datetime.utcnow().strftime("%Y-%m-%d")


@tool
def calculate(expression: str) -> str:
    """
    Safely evaluate a mathematical expression.
    Example: calculate("2 ** 10") → "1024"
    """
    SAFE_OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.BinOp):
            op = SAFE_OPS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {node.op}")
            return op(_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp):
            op = SAFE_OPS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {node.op}")
            return op(_eval(node.operand))
        raise ValueError(f"Unsupported expression type: {type(node)}")

    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval(tree.body)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


TOOLS = [search_web, get_current_date, calculate]
