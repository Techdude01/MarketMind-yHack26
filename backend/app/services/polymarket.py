"""Polymarket CLOB API service.

Uses ``requests`` and ``web3.py`` to interact with the Polymarket CLOB REST
API, following the approach demonstrated in ``agent/polymarket_example.py``.

Functions match the skeleton defined in ``backend.md``:
  - get_markets(limit)   — paginated list of active markets
  - get_market(market_id) — single market by condition_id
  - get_order_book(token_id) — order-book snapshot for a token
  - place_order(...)      — raises ``NotImplementedError`` (paper-trade guard)

All config is pulled from ``app.config.Config`` (env vars).  A Builder API Key
is used if available; otherwise unauthenticated requests are made.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from app.config import Config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
POLYMARKET_CLOB_URL = "https://clob.polymarket.com"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _headers() -> dict[str, str]:
    """Build HTTP headers, including the Builder API Key when available."""
    headers: dict[str, str] = {"Accept": "application/json"}
    api_key = Config.POLYMARKET_API_KEY
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    """Issue a GET request to the CLOB API and return the parsed JSON body.

    Raises:
        requests.exceptions.HTTPError: on 4xx / 5xx responses.
    """
    url = f"{POLYMARKET_CLOB_URL}{path}"
    response = requests.get(url, headers=_headers(), params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def _post(path: str, payload: Any) -> Any:
    """Issue a POST request to the CLOB API and return the parsed JSON body.

    Raises:
        requests.exceptions.HTTPError: on 4xx / 5xx responses.
    """
    url = f"{POLYMARKET_CLOB_URL}{path}"
    response = requests.post(url, headers=_headers(), json=payload, timeout=15)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_markets(limit: int = 20, next_cursor: str = "") -> dict[str, Any]:
    """Fetch active prediction markets from Polymarket.

    Args:
        limit: Max number of markets to return (1-100).
        next_cursor: Pagination cursor returned by a previous call.

    Returns:
        Raw JSON dict from the ``/markets`` endpoint, typically containing
        ``data`` (list of market dicts) and ``next_cursor``.
    """
    params: dict[str, Any] = {"limit": limit}
    if next_cursor:
        params["next_cursor"] = next_cursor

    data = _get("/markets", params=params)
    logger.info("Fetched %d markets from Polymarket", len(data.get("data", [])))
    return data


def get_market(condition_id: str) -> dict[str, Any]:
    """Fetch a single market by its condition ID.

    Args:
        condition_id: The on-chain condition ID for the market.

    Returns:
        Market detail dict.
    """
    data = _get(f"/markets/{condition_id}")
    logger.info("Fetched market: %s", data.get("question", "N/A"))
    return data


def get_prices_history(
    market_token_id: str,
    *,
    start_ts: int,
    end_ts: int,
    interval: str = "1h",
) -> dict[str, Any]:
    """Fetch CLOB price history for an outcome token (YES/NO asset id).

    Polymarket caps ``startTs``–``endTs`` to a short window (~7 days); callers
    that need longer ranges should issue multiple requests.

    Args:
        market_token_id: CLOB token id (first ``clob_token_ids`` entry for YES).
        start_ts: Unix seconds (inclusive).
        end_ts: Unix seconds (inclusive).
        interval: Aggregation bucket per OpenAPI (``1h``, ``1d``, etc.).

    Returns:
        Parsed JSON, typically ``{"history": [{"t": int, "p": float}, ...]}``.
    """
    params: dict[str, Any] = {
        "market": market_token_id,
        "startTs": start_ts,
        "endTs": end_ts,
        "interval": interval,
    }
    return _get("/prices-history", params=params)


def get_order_book(token_id: str) -> dict[str, Any]:
    """Fetch the order-book snapshot for a token.

    Uses ``POST /books`` with a JSON array body — the correct CLOB endpoint.
    The response is a list; this function returns the first element (the book
    for the requested token) or an empty dict with empty bids/asks when the
    market has no active orders.

    Args:
        token_id: The Polymarket token ID.

    Returns:
        Order-book dict with ``bids`` and ``asks`` arrays.
    """
    results = _post("/books", [{"token_id": token_id}])
    if results:
        return results[0]
    # Market exists but has no active orders yet
    return {"bids": [], "asks": [], "token_id": token_id}


def place_order(
    token_id: str,
    side: str,
    size: float,
    price: float,
) -> dict[str, Any]:
    """Place an order on Polymarket via the CLOB client.

    .. warning::
        Permanently raises ``NotImplementedError`` — real execution is
        forbidden per CLAUDE.md hard-rules.  Paper trading only.

    Args:
        token_id: The Polymarket token ID.
        side: ``"YES"`` or ``"NO"``.
        size: Number of shares.
        price: Limit price (0–1).

    Raises:
        NotImplementedError: Always.
    """
    raise NotImplementedError("Paper trading only during hackathon")
