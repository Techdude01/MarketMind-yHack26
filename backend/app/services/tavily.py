"""Tavily web-search service for the research stage of the agent loop."""

from tavily import TavilyClient
from app.config import Config

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
        A list of search-result dictionaries.
    """
    client = _get_client()
    response = client.search(query=query, max_results=max_results)
    return response.get("results", [])
