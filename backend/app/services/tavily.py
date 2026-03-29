"""Tavily web-search service for the research stage of the agent loop."""

from tavily import TavilyClient

from app.config import Config
from app.services.research_context import _clean_whitespace, clean_tavily_results

_client = None


def _get_client():
    global _client
    if _client is None:
        if not Config.TAVILY_API_KEY:
            raise RuntimeError("TAVILY_API_KEY is not set in .env")
        _client = TavilyClient(api_key=Config.TAVILY_API_KEY)
    return _client


def search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web via Tavily and return a list of result dicts.

    Each result dict contains at least:
        - title (str)
        - url (str)
        - content (str)

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default 5).

    Returns:
        A list of search-result dictionaries (string fields whitespace-normalized).
    """
    client = _get_client()
    q = _clean_whitespace(str(query or ""))
    response = client.search(query=q, max_results=max_results)
    return clean_tavily_results(response.get("results", []))
