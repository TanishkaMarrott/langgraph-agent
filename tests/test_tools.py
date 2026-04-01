"""
Tests for agent tools — calculate, get_current_date, search_web.
"""

import pytest
from datetime import datetime
from agent.tools import calculate, get_current_date, search_web


def test_calculate_addition():
    assert calculate.invoke({"expression": "2 + 3"}) == "5"


def test_calculate_power():
    assert calculate.invoke({"expression": "2 ** 10"}) == "1024"


def test_calculate_division():
    result = calculate.invoke({"expression": "10 / 4"})
    assert result == "2.5"


def test_calculate_negative():
    assert calculate.invoke({"expression": "-5 + 3"}) == "-2"


def test_calculate_invalid():
    result = calculate.invoke({"expression": "import os"})
    assert result.startswith("Error")


def test_get_current_date_format():
    result = get_current_date.invoke({})
    # Should be YYYY-MM-DD
    datetime.strptime(result, "%Y-%m-%d")


def test_search_web_returns_string():
    result = search_web.invoke({"query": "LangGraph tutorial"})
    assert isinstance(result, str)
    assert len(result) > 0


def test_search_web_contains_query():
    result = search_web.invoke({"query": "test query"})
    assert "test query" in result
