"""K2 Think V2 reasoning LLM — OpenAI-compatible client.

Uses the MBZUAI-IFM/K2-Think-v2 model via the k2think.ai API,
which exposes an OpenAI-compatible /chat/completions endpoint.

NOTE: K2's non-streaming endpoint (/chat/completions with stream=False)
returns HTTP 503 "Server is busy" in the current API version. We work
around this by always using stream=True and accumulating the delta chunks.

# ── Gemini drop-in replacement ─────────────────────────────────────────────
# If you need to swap K2 for Gemini, install `google-generativeai` and
# replace _get_client() / the completions calls with:
#
#   import google.generativeai as genai
#   genai.configure(api_key=Config.GEMINI_API_KEY)
#   model = genai.GenerativeModel("gemini-2.0-flash")
#   response = model.generate_content(prompt)
#   return response.text
#
# Or, via the OpenAI-compatible Gemini endpoint:
#   client = OpenAI(
#       api_key=Config.GEMINI_API_KEY,
#       base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
#   )
# ───────────────────────────────────────────────────────────────────────────
"""

import json
import logging
import re

from openai import OpenAI
from app.config import Config

logger = logging.getLogger(__name__)

_client: OpenAI | None = None

MODEL = "MBZUAI-IFM/K2-Think-v2"


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not Config.K2_THINK_V2_API_KEY:
            raise RuntimeError("K2_THINK_V2_API_KEY is not set in .env")
        _client = OpenAI(
            api_key=Config.K2_THINK_V2_API_KEY,
            base_url=Config.K2_THINK_V2_BASE_URL,
            timeout=60.0,
        )
    return _client


def _collect_stream(stream) -> str:
    """Consume a streaming chat-completions response and return the full text."""
    content = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            content += delta
    return content


def reason(market: dict) -> str:
    """Deep-reason about a market event and return structured analysis.

    Args:
        market: dict with at least ``question`` and ``description`` keys.

    Returns:
        The reasoning text as a plain string.
    """
    client = _get_client()

    prompt = (
        "You are MarketMind, a deep-reasoning AI analyst for prediction markets.\n\n"
        f"## Market\n"
        f"Question: {market.get('question', 'N/A')}\n"
        f"Description: {market.get('description', 'N/A')}\n\n"
        "Analyse this market thoroughly. Consider:\n"
        "1. Historical precedents and base rates\n"
        "2. Current conditions and recent developments\n"
        "3. Key uncertainties and unknowns\n"
        "4. Arguments for YES and for NO\n"
        "5. Your overall probability estimate (0-100%)\n\n"
        "Provide detailed, step-by-step reasoning."
    )

    # K2 non-streaming endpoint returns 503; use stream=True as workaround.
    # To switch to Gemini: see module-level docstring.
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        stream=True,  # required — K2's non-streaming endpoint is unreliable
    )
    return _collect_stream(stream)


_SEARCH_QUERY_PROMPT = """\
You are MarketMind, an AI research strategist for prediction markets.

## Market
Question: {question}
Description: {description}

## Task
Generate {num_queries} highly specific web search queries that will find \
real-world news articles, expert analyses, data reports, and primary sources \
relevant to predicting the outcome of this market.

CRITICAL RULES:
- Do NOT include the market title or question verbatim as a search query.
- Do NOT generate queries that would return the Polymarket listing page itself.
- Each query should target a DIFFERENT angle: recent news, historical data, \
expert opinion, regulatory filings, statistical trends, etc.
- Queries should be phrased the way a professional researcher would type into \
Google — short, keyword-rich, no filler words.
- Return ONLY a JSON array of strings, nothing else. No markdown fences.

Example output:
["BTC price forecast Q4 2026 analyst consensus", "Bitcoin halving cycle historical returns", "institutional crypto adoption 2025 2026 trends"]
"""

_DEFAULT_NUM_QUERIES = 4
_MAX_NUM_QUERIES = 8
_TAVILY_MAX_QUERY_CHARS = 400


def _parse_search_queries(raw: str, fallback_max: int) -> list[str]:
    """Extract a list of query strings from K2's response.

    Tries JSON first, then falls back to line-by-line extraction.
    """
    text = raw.strip()

    # Strip markdown fences if K2 wraps the answer
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            queries = [str(q).strip() for q in parsed if str(q).strip()]
            return queries[:fallback_max]
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: extract lines that look like queries
    lines = [
        re.sub(r"^\d+[\.\)]\s*", "", line).strip().strip('"').strip("'")
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    return [l for l in lines if len(l) > 10][:fallback_max]


def generate_search_queries(
    market: dict,
    num_queries: int = _DEFAULT_NUM_QUERIES,
) -> list[str]:
    """Ask K2 to produce targeted search queries for a prediction market.

    Instead of naively searching for the market question (which returns the
    Polymarket listing page), K2 identifies the underlying topics, entities,
    and data sources that would inform a probability estimate.

    Args:
        market: dict with ``question`` and ``description`` keys.
        num_queries: How many queries to request (capped at 8).

    Returns:
        A list of search-query strings ready for Tavily.
    """
    client = _get_client()
    num_queries = min(max(num_queries, 1), _MAX_NUM_QUERIES)

    prompt = _SEARCH_QUERY_PROMPT.format(
        question=market.get("question", "N/A"),
        description=market.get("description", "N/A"),
        num_queries=num_queries,
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
        stream=False,
    )
    raw_text = response.choices[0].message.content or ""
    queries = _parse_search_queries(raw_text, fallback_max=num_queries)

    if not queries:
        logger.warning(
            "K2 returned no parseable search queries for market %r; "
            "falling back to question-based query",
            market.get("question", ""),
        )
        q = market.get("question", "prediction market")
        queries = [q]

    return [q[:_TAVILY_MAX_QUERY_CHARS] for q in queries]


def chat(message: str, system_prompt: str | None = None) -> str:
    """General-purpose chat completion with K2.

    Args:
        message: The user message to send.
        system_prompt: Optional system prompt for context.

    Returns:
        The assistant's reply as a plain string.
    """
    client = _get_client()

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": message})

    # K2 non-streaming endpoint returns 503; use stream=True as workaround.
    # To switch to Gemini: see module-level docstring.
    stream = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=1024,
        stream=True,  # required — K2's non-streaming endpoint is unreliable
    )
    return _collect_stream(stream)
