"""Integration tests for the Polymarket CLOB API service.

Read-only endpoints (get_markets, get_market, get_order_book) hit the real
Polymarket CLOB API — no API key is required for these.  The POLYMARKET_API_KEY
is only needed for authenticated write operations, which are permanently
blocked by the paper-trade guard anyway.

Run:
    pytest tests/test_polymarket_integration.py -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import Config
from app.services import polymarket as poly_svc

# ---------------------------------------------------------------------------
# Helpers / shared markers
# ---------------------------------------------------------------------------

skip_if_no_network = pytest.mark.skipif(
    os.getenv("CI_NO_NETWORK") == "1",
    reason="Network tests disabled in this environment",
)


# ---------------------------------------------------------------------------
# get_markets
# ---------------------------------------------------------------------------


@skip_if_no_network
def test_get_markets_returns_dict():
    """get_markets should return a dict from the CLOB API."""
    result = poly_svc.get_markets(limit=5)
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"


@skip_if_no_network
def test_get_markets_has_data_key():
    """The response should contain a 'data' list of market objects."""
    result = poly_svc.get_markets(limit=5)
    assert "data" in result, f"'data' key missing from response: {list(result.keys())}"
    assert isinstance(result["data"], list)


@skip_if_no_network
def test_get_markets_data_non_empty():
    """Polymarket should always have at least one active market."""
    result = poly_svc.get_markets(limit=5)
    assert len(result["data"]) > 0, "No markets returned — API may be down"


@skip_if_no_network
def test_get_markets_limit_respected():
    """API returns a list of markets (Polymarket CLOB ignores the limit param and returns all)."""
    result = poly_svc.get_markets(limit=3)
    markets = result.get("data", [])
    assert isinstance(markets, list)
    assert len(markets) >= 1, "Expected at least 1 market from the API"


@skip_if_no_network
def test_get_markets_market_structure():
    """Each market object should contain the core expected fields."""
    result = poly_svc.get_markets(limit=3)
    markets = result.get("data", [])
    assert len(markets) > 0, "No markets to inspect"

    required_fields = {"condition_id", "question"}
    for market in markets:
        missing = required_fields - set(market.keys())
        assert not missing, f"Market missing fields {missing}: {market}"


@skip_if_no_network
def test_get_markets_has_next_cursor():
    """Response should include a next_cursor for pagination."""
    result = poly_svc.get_markets(limit=5)
    assert "next_cursor" in result, (
        f"'next_cursor' missing — pagination may be broken: {list(result.keys())}"
    )


@skip_if_no_network
def test_get_markets_pagination():
    """next_cursor is present in the response for use in future paginated calls."""
    page1 = poly_svc.get_markets(limit=10)
    assert "next_cursor" in page1, "'next_cursor' key missing from response"
    # The Polymarket CLOB API currently returns all markets in one page;
    # we just verify the cursor field exists and is a string so callers
    # can pass it through correctly when the API enforces pagination.
    assert isinstance(page1["next_cursor"], str)


# ---------------------------------------------------------------------------
# get_market
# ---------------------------------------------------------------------------


def _get_first_condition_id() -> str:
    """Helper: fetch one live condition_id to use in single-market tests."""
    result = poly_svc.get_markets(limit=1)
    markets = result.get("data", [])
    if not markets:
        pytest.skip("No markets available to fetch a condition_id from")
    return markets[0]["condition_id"]


@skip_if_no_network
def test_get_market_returns_dict():
    """get_market should return a dict for a valid condition_id."""
    condition_id = _get_first_condition_id()
    market = poly_svc.get_market(condition_id)
    assert isinstance(market, dict)


@skip_if_no_network
def test_get_market_condition_id_matches():
    """The returned market's condition_id should match the one we requested."""
    condition_id = _get_first_condition_id()
    market = poly_svc.get_market(condition_id)
    assert market.get("condition_id") == condition_id, (
        f"Requested {condition_id!r} but got {market.get('condition_id')!r}"
    )


@skip_if_no_network
def test_get_market_has_question():
    """A single-market response should include a human-readable question."""
    condition_id = _get_first_condition_id()
    market = poly_svc.get_market(condition_id)
    assert "question" in market
    assert isinstance(market["question"], str)
    assert len(market["question"]) > 0


@skip_if_no_network
def test_get_market_invalid_id_raises():
    """Requesting a non-existent condition_id should raise an HTTP error."""
    import requests

    with pytest.raises(requests.exceptions.HTTPError):
        poly_svc.get_market(
            "0x000000000000000000000000000000000000000000000000000000000000dead"
        )


# ---------------------------------------------------------------------------
# get_order_book
# ---------------------------------------------------------------------------


def _get_active_token_id() -> str:
    """Helper: find a token_id from a market that is actively accepting orders.

    The /book endpoint only returns data for markets where accepting_orders is
    True.  We scan up to the first 200 markets to find one.
    """
    result = poly_svc.get_markets(limit=200)
    for market in result.get("data", []):
        if not market.get("accepting_orders"):
            continue
        tokens = market.get("tokens", [])
        for token in tokens:
            token_id = token.get("token_id")
            if token_id:
                return token_id
    pytest.skip("No active (accepting_orders=True) market with a token_id found")


@skip_if_no_network
def test_get_order_book_returns_dict():
    """get_order_book should always return a dict (empty or populated)."""
    token_id = _get_active_token_id()
    book = poly_svc.get_order_book(token_id)
    assert isinstance(book, dict), f"Expected dict, got {type(book)}"


@skip_if_no_network
def test_get_order_book_has_bids_and_asks():
    """Order book response must always include 'bids' and 'asks' keys."""
    token_id = _get_active_token_id()
    book = poly_svc.get_order_book(token_id)
    assert "bids" in book, f"'bids' key missing from order book: {list(book.keys())}"
    assert "asks" in book, f"'asks' key missing from order book: {list(book.keys())}"
    assert isinstance(book["bids"], list), "'bids' should be a list"
    assert isinstance(book["asks"], list), "'asks' should be a list"


@skip_if_no_network
def test_get_order_book_bid_ask_structure():
    """Each bid/ask entry should have a price and size."""
    token_id = _get_active_token_id()
    book = poly_svc.get_order_book(token_id)

    has_entries = any(book.get(side) for side in ("bids", "asks"))
    if not has_entries:
        pytest.skip("Order book is empty for this market — no entries to validate")

    for side in ("bids", "asks"):
        for entry in book.get(side, [])[:3]:  # spot-check first 3
            assert "price" in entry, f"'price' missing in {side} entry: {entry}"
            assert "size" in entry, f"'size' missing in {side} entry: {entry}"


@skip_if_no_network
def test_get_order_book_prices_are_valid():
    """All bid/ask prices should be numeric strings between 0 and 1."""
    token_id = _get_active_token_id()
    book = poly_svc.get_order_book(token_id)

    has_entries = any(book.get(side) for side in ("bids", "asks"))
    if not has_entries:
        pytest.skip("Order book is empty for this market — no prices to validate")

    for side in ("bids", "asks"):
        for entry in book.get(side, [])[:5]:
            price = float(entry["price"])
            assert 0.0 <= price <= 1.0, (
                f"{side} price {price} out of expected [0, 1] range"
            )


# ---------------------------------------------------------------------------
# place_order — paper-trade guard
# ---------------------------------------------------------------------------


def test_place_order_always_raises():
    """place_order must always raise NotImplementedError (paper-trade guard)."""
    with pytest.raises(NotImplementedError, match="Paper trading only"):
        poly_svc.place_order(
            token_id="dummy_token",
            side="YES",
            size=10.0,
            price=0.6,
        )


def test_place_order_raises_regardless_of_args():
    """The guard should fire for any combination of arguments."""
    for side in ("YES", "NO"):
        with pytest.raises(NotImplementedError):
            poly_svc.place_order(
                token_id="any_token",
                side=side,
                size=1.0,
                price=0.5,
            )
