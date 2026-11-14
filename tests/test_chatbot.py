import pytest
from app.services.chatbot_service import process_chat_query

def test_chatbot_savings_intent():
    """Test chatbot matches queries about savings and emergency funds."""
    res = process_chat_query("How much should I keep in my emergency savings fund?")
    assert res["success"] is True
    assert "Savings" in res["topic"]
    assert "emergency fund" in res["reply"].lower()
    assert "DISCLAIMER" in res["disclaimer"]


def test_chatbot_budgeting_intent():
    """Test chatbot matches 50/30/20 budgeting rule queries."""
    res = process_chat_query("Explain how the 50/30/20 budget framework works")
    assert res["success"] is True
    assert "Budgeting" in res["topic"]
    assert "50% Needs" in res["reply"]


def test_chatbot_debt_snowball_intent():
    """Test chatbot explains debt avalanche and snowball strategies."""
    res = process_chat_query("What is the difference between debt avalanche and debt snowball?")
    assert res["success"] is True
    assert "Debt" in res["topic"]
    assert "Avalanche" in res["reply"]
    assert "Snowball" in res["reply"]


def test_chatbot_inflation_intent():
    """Test chatbot addresses inflation and purchasing power loss."""
    res = process_chat_query("How does inflation impact my cash purchasing power?")
    assert res["success"] is True
    assert "Inflation" in res["topic"]
    assert "Rule of 72" in res["reply"]


def test_chatbot_fallback_unsupported_query():
    """Test chatbot gracefully falls back for unsupported or out-of-domain queries."""
    res = process_chat_query("What is the recipe for chocolate chip cookies?")
    assert res["success"] is True
    assert res.get("is_fallback") is True
    assert "could not locate an exact match" in res["reply"]
    assert "suggested_prompts" in res
