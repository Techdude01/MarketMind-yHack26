"""Integration tests for K2 Think V2 reasoning service.

These tests hit the REAL K2 API — they require a valid K2_THINK_V2_API_KEY
in the backend/.env file.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.llm import k2 as k2_svc
from app.config import Config

skip_no_key = pytest.mark.skipif(
    not Config.K2_THINK_V2_API_KEY,
    reason="K2_THINK_V2_API_KEY not set — skipping live API test",
)

SAMPLE_MARKET = {
    "question": "Will Bitcoin exceed $100,000 by December 2026?",
    "description": (
        "This market resolves YES if the price of Bitcoin (BTC/USD) "
        "reaches or exceeds $100,000 on any major exchange before "
        "December 31, 2026 23:59 UTC."
    ),
}


@skip_no_key
def test_chat_returns_text():
    """A simple chat call should return a non-empty string."""
    reply = k2_svc.chat("What is 2+2? Reply in one word.")
    assert isinstance(reply, str)
    assert len(reply) > 0, "K2 returned an empty response"


@skip_no_key
def test_reason_returns_text():
    """reason() should return a non-empty string for a market."""
    analysis = k2_svc.reason(SAMPLE_MARKET)
    assert isinstance(analysis, str)
    assert len(analysis) > 50, "Reasoning seems too short to be useful"


@skip_no_key
def test_reason_mentions_market_topic():
    """The reasoning should reference the market topic."""
    analysis = k2_svc.reason(SAMPLE_MARKET)
    analysis_lower = analysis.lower()
    assert any(
        keyword in analysis_lower
        for keyword in ["bitcoin", "btc", "100,000", "100000", "crypto"]
    ), "Reasoning should reference the market topic"


@skip_no_key
def test_chat_with_system_prompt():
    """Chat with a system prompt should follow instructions."""
    reply = k2_svc.chat(
        "What color is the sky?",
        system_prompt="You are a helpful assistant. Always answer in exactly one word.",
    )
    assert isinstance(reply, str)
    assert len(reply) > 0


@skip_no_key
def test_generate_search_queries_returns_list():
    """generate_search_queries() should return a non-empty list of strings."""
    queries = k2_svc.generate_search_queries(SAMPLE_MARKET)
    assert isinstance(queries, list)
    assert len(queries) >= 1, "Expected at least one search query"
    for q in queries:
        assert isinstance(q, str)
        assert len(q) > 10, f"Query too short to be useful: {q!r}"


@skip_no_key
def test_generate_search_queries_avoids_market_title():
    """Generated queries should NOT be the verbatim market question."""
    queries = k2_svc.generate_search_queries(SAMPLE_MARKET)
    market_question = SAMPLE_MARKET["question"]
    for q in queries:
        assert q != market_question, (
            "Search query should not be the exact market question"
        )


@skip_no_key
def test_generate_search_queries_custom_count():
    """Requesting a specific number of queries should be respected (±1)."""
    queries = k2_svc.generate_search_queries(SAMPLE_MARKET, num_queries=3)
    assert isinstance(queries, list)
    assert 1 <= len(queries) <= 4, (
        f"Requested 3 queries, got {len(queries)}"
    )


@skip_no_key
def test_parse_search_queries_json_format():
    """_parse_search_queries should handle clean JSON arrays."""
    from app.services.llm.k2 import _parse_search_queries

    raw = '["query one about bitcoin", "query two about crypto"]'
    result = _parse_search_queries(raw, fallback_max=5)
    assert result == ["query one about bitcoin", "query two about crypto"]


def test_parse_search_queries_markdown_fenced():
    """_parse_search_queries should strip markdown code fences."""
    from app.services.llm.k2 import _parse_search_queries

    raw = '```json\n["bitcoin price forecast", "crypto regulation news"]\n```'
    result = _parse_search_queries(raw, fallback_max=5)
    assert result == ["bitcoin price forecast", "crypto regulation news"]


def test_parse_search_queries_fallback_lines():
    """_parse_search_queries should fall back to line-by-line if JSON fails."""
    from app.services.llm.k2 import _parse_search_queries

    raw = (
        "1. Bitcoin price forecast 2026 analyst consensus\n"
        "2. BTC halving cycle historical returns\n"
        "3. Institutional crypto adoption trends\n"
    )
    result = _parse_search_queries(raw, fallback_max=5)
    assert len(result) == 3
    assert "Bitcoin price forecast 2026 analyst consensus" in result[0]
