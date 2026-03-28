"""K2 Think V2 reasoning LLM — OpenAI-compatible client.

Uses the MBZUAI-IFM/K2-Think-v2 model via the k2think.ai API,
which exposes an OpenAI-compatible /chat/completions endpoint.
"""

from openai import OpenAI
from app.config import Config

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

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        stream=False,
    )
    return response.choices[0].message.content


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

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=1024,
        stream=False,
    )
    return response.choices[0].message.content
