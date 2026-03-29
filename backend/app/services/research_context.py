"""Format Tavily hits into a single research string for Gemini."""

from __future__ import annotations

from typing import Any

# Rough cap so prompts stay within practical context limits
_DEFAULT_MAX_CHARS = 24_000
_CONTENT_PER_RESULT_CAP = 4_000

# Tavily API rejects queries longer than this (documented / observed limit).
_TAVILY_MAX_QUERY_CHARS = 400


def _clean_whitespace(s: str) -> str:
    """Collapse all runs of whitespace (spaces, newlines, tabs) to a single space."""
    return " ".join(s.split())


def clean_tavily_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a copy of Tavily ``results`` with string fields whitespace-normalized."""
    out: list[dict[str, Any]] = []
    for item in results:
        cleaned: dict[str, Any] = {}
        for key, val in item.items():
            if isinstance(val, str):
                cleaned[key] = _clean_whitespace(val)
            else:
                cleaned[key] = val
        out.append(cleaned)
    return out


def format_tavily_results_for_gemini(
    results: list[dict[str, Any]],
    *,
    max_total_chars: int = _DEFAULT_MAX_CHARS,
    max_content_chars: int = _CONTENT_PER_RESULT_CAP,
) -> str:
    """Turn Tavily ``results`` into numbered markdown-style research notes.

    Truncates each result's ``content`` and the overall string to stay under
    ``max_total_chars``.
    """
    if not results:
        return "No web search results were returned for this query."

    parts: list[str] = []
    used = 0
    for i, item in enumerate(results, start=1):
        title = _clean_whitespace(str(item.get("title") or "")) or "(no title)"
        url = _clean_whitespace(str(item.get("url") or "")) or "(no url)"
        content = _clean_whitespace(str(item.get("content") or ""))
        if len(content) > max_content_chars:
            content = content[:max_content_chars].rstrip() + "…"

        block = (
            f"### {i}. {title}\n"
            f"URL: {url}\n"
            f"{content}\n"
        )
        if used + len(block) > max_total_chars:
            remain = max_total_chars - used
            if remain > 80:
                parts.append(block[:remain].rstrip() + "…")
            break
        parts.append(block)
        used += len(block)

    return "\n".join(parts)


def _truncate_to_max(s: str, max_chars: int) -> str:
    if len(s) <= max_chars:
        return s
    if max_chars <= 1:
        return ""
    return s[: max_chars - 1].rstrip() + "…"


def build_tavily_search_query(question: str, description: str | None) -> str:
    """Search query sent to Tavily: market title (``question``) plus ``description``.

    Plain text, one space between parts when both exist — no extra labels or
    newlines. Whitespace is normalized. Capped at ``_TAVILY_MAX_QUERY_CHARS``.
    """
    q = _clean_whitespace(str(question or ""))
    d = _clean_whitespace(str(description or ""))

    if not q and not d:
        return _truncate_to_max("prediction market", _TAVILY_MAX_QUERY_CHARS)
    if not d:
        return _truncate_to_max(q, _TAVILY_MAX_QUERY_CHARS)
    if not q:
        return _truncate_to_max(d, _TAVILY_MAX_QUERY_CHARS)

    combined = f"{q} {d}"
    return _truncate_to_max(combined, _TAVILY_MAX_QUERY_CHARS)
