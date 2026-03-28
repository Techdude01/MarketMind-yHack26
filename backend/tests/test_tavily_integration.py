"""Integration tests for Tavily search service.

These tests hit the REAL Tavily API — they require a valid TAVILY_API_KEY
in the backend/.env file.
"""

import os
import sys
import pytest

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import tavily as tavily_svc
from app.config import Config

skip_no_key = pytest.mark.skipif(
    not Config.TAVILY_API_KEY,
    reason="TAVILY_API_KEY not set — skipping live API test",
)


@skip_no_key
def test_search_returns_results():
    """A basic search should return a non-empty list."""
    results = tavily_svc.search("latest US election polls 2026", max_results=3)
    assert isinstance(results, list)
    assert len(results) > 0


@skip_no_key
def test_search_result_structure():
    """Each result should contain title, url, and content keys."""
    results = tavily_svc.search("Bitcoin price prediction", max_results=2)
    for r in results:
        assert "title" in r, f"Missing 'title' key in result: {r}"
        assert "url" in r, f"Missing 'url' key in result: {r}"
        assert "content" in r, f"Missing 'content' key in result: {r}"
        assert isinstance(r["title"], str) and len(r["title"]) > 0
        assert isinstance(r["url"], str) and r["url"].startswith("http")


@skip_no_key
def test_search_max_results_honored():
    """Requesting max_results=1 should return at most 1 result."""
    results = tavily_svc.search("SpaceX Starship launch date", max_results=1)
    assert len(results) <= 1
