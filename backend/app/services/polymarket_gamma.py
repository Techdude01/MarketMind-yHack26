"""Fetch and normalize Polymarket Gamma API market payloads for Postgres upsert."""

from __future__ import annotations

import json
import logging
import math
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import requests

from psycopg.types.json import Json

logger = logging.getLogger(__name__)

GAMMA_MARKETS_URL = "https://gamma-api.polymarket.com/markets"


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _end_date_min_at_least_days_ahead(days: int) -> str:
    """ISO date (YYYY-MM-DD) for UTC today + *days* (used as Gamma ``end_date_min``)."""
    return (_utc_today() + timedelta(days=days)).isoformat()


def fetch_filtered_markets(
    *,
    limit: int = 100,
    volume_num_min: int = 500_000,
    min_days_until_end: int = 2,
    end_date_min: str | None = None,
    end_date_max: str | None = None,
    timeout: float = 60.0,
) -> list[dict[str, Any]]:
    """GET Gamma markets list; returns a list of raw market dicts (ignores events table).

    By default, ``end_date_min`` is UTC today + ``min_days_until_end`` days (default **2**),
    i.e. markets that end at least two days from now. Combined with ``volume_num_min``
    (default **$500K+**) to cast a wide net — downstream ``filter_and_rank_markets`` narrows
    to the best ~30. Override with ``end_date_min`` / ``end_date_max`` if needed.
    """
    resolved_min = (
        end_date_min
        if end_date_min is not None
        else _end_date_min_at_least_days_ahead(min_days_until_end)
    )
    params: dict[str, Any] = {
        "limit": limit,
        "volume_num_min": volume_num_min,
        "end_date_min": resolved_min,
    }
    if end_date_max is not None:
        params["end_date_max"] = end_date_max
    resp = requests.get(GAMMA_MARKETS_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    logger.info(
        "Gamma markets fetched: status=%s end_date_min=%s volume_num_min=%s",
        resp.status_code,
        resolved_min,
        volume_num_min,
    )
    data = resp.json()
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array from Gamma API, got {type(data).__name__}")
    return data


def _parse_bool(v: Any) -> bool | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        low = v.strip().lower()
        if low in ("true", "1", "yes"):
            return True
        if low in ("false", "0", "no"):
            return False
    return None


def _parse_decimal(v: Any) -> Decimal | None:
    if v is None or v == "":
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float)):
        return Decimal(str(v))
    if isinstance(v, str):
        try:
            return Decimal(v.strip())
        except InvalidOperation:
            return None
    return None


def _parse_json_array(v: Any) -> list[Any] | None:
    if v is None:
        return None
    if isinstance(v, tuple):
        v = list(v)
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            parsed = json.loads(s)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, list) else None
    return None


def _jsonb_array(v: Any) -> Json | None:
    """JSONB column value. Raw Python lists are adapted as Postgres arrays, not JSON; use Json()."""
    arr = _parse_json_array(v)
    if arr is None:
        return None
    return Json(arr)


_TS_SPACE_PLUS = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})(\+00)$")


def _parse_timestamptz(v: Any) -> datetime | None:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
    if not isinstance(v, str):
        return None
    s = v.strip()
    if not s:
        return None
    m = _TS_SPACE_PLUS.match(s)
    if m:
        s = f"{m.group(1)}T{m.group(2)}{m.group(3)}:00"
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _parse_date(v: Any) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        s = v.strip()[:10]
        try:
            return date.fromisoformat(s)
        except ValueError:
            return None
    return None


def _require_polymarket_id(raw: dict[str, Any]) -> int:
    rid = raw.get("id")
    if rid is None:
        raise ValueError("market missing id")
    try:
        return int(rid)
    except (TypeError, ValueError) as e:
        raise ValueError(f"invalid market id: {rid!r}") from e


_PRICE_LO = 0.03
_PRICE_HI = 0.97
_DEFAULT_TOP_N = 30


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def is_good_market(market: dict[str, Any]) -> bool:
    """Hard-filter a raw Gamma market dict for demo quality.

    Only rejects markets that are clearly unsuitable — closed, archived, or
    near-certain (price pinned at 0/1).  Fields that Gamma sometimes omits
    (``acceptingOrders``, ``bestBid``, ``bestAsk``) are treated as OK when
    absent so we don't silently drop most of the dataset.
    """
    active = _parse_bool(market.get("active"))
    if active is False:
        return False

    if _parse_bool(market.get("closed")):
        return False

    if _parse_bool(market.get("archived")):
        return False

    accepting = _parse_bool(market.get("acceptingOrders"))
    if accepting is False:
        return False

    ltp = _to_float(market.get("lastTradePrice"))
    if ltp is not None and (ltp < _PRICE_LO or ltp > _PRICE_HI):
        return False

    return True


def score_market(market: dict[str, Any]) -> float:
    """Soft-rank a raw Gamma dict that already passed hard filters.

    Higher is better.  Volume dominates, with bonuses for featured status,
    recent trading activity, and having a two-sided book.
    """
    vol = _to_float(market.get("volumeNum")) or 1
    score = math.log(vol + 1)

    if _parse_bool(market.get("featured")):
        score += 2.0

    vol24 = _to_float(market.get("volume24hr"))
    vol1w = _to_float(market.get("volume1wk"))
    if vol24 and vol24 > 50_000:
        score += 1.0
    elif vol1w and vol1w > 200_000:
        score += 0.5

    if _to_float(market.get("bestBid")) and _to_float(market.get("bestAsk")):
        score += 0.5

    return score


def filter_and_rank_markets(
    raw_markets: list[dict[str, Any]], *, top_n: int = _DEFAULT_TOP_N
) -> list[dict[str, Any]]:
    """Apply hard filters, score, sort, and return top *top_n* raw Gamma dicts."""
    good = [m for m in raw_markets if is_good_market(m)]
    good.sort(key=score_market, reverse=True)
    kept = good[:top_n]
    logger.info(
        "filter_and_rank: %d raw → %d passed hard filters → %d kept (top_n=%d)",
        len(raw_markets), len(good), len(kept), top_n,
    )
    return kept


def market_row_from_gamma(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a Gamma market dict to columns for polymarket_markets (excluding first_seen_at)."""
    pid = _require_polymarket_id(raw)

    return {
        "polymarket_id": pid,
        "slug": raw.get("slug") if raw.get("slug") else None,
        "question": (raw.get("question") or "").strip() or "(no question)",
        "description": raw.get("description") if raw.get("description") else None,
        "resolution_source": raw.get("resolutionSource")
        if raw.get("resolutionSource")
        else None,
        "image_url": raw.get("image") if raw.get("image") else None,
        "icon_url": raw.get("icon") if raw.get("icon") else None,
        "start_date": _parse_timestamptz(raw.get("startDate")),
        "end_date": _parse_timestamptz(raw.get("endDate")),
        "created_at_api": _parse_timestamptz(raw.get("createdAt")),
        "updated_at_api": _parse_timestamptz(raw.get("updatedAt")),
        "closed_time": _parse_timestamptz(raw.get("closedTime")),
        "start_date_iso": _parse_date(raw.get("startDateIso")),
        "end_date_iso": _parse_date(raw.get("endDateIso")),
        "active": _parse_bool(raw.get("active")),
        "closed": _parse_bool(raw.get("closed")),
        "archived": _parse_bool(raw.get("archived")),
        "featured": _parse_bool(raw.get("featured")),
        "new": _parse_bool(raw.get("new")),
        "restricted": _parse_bool(raw.get("restricted")),
        "last_trade_price": _parse_decimal(raw.get("lastTradePrice")),
        "best_bid": _parse_decimal(raw.get("bestBid")),
        "best_ask": _parse_decimal(raw.get("bestAsk")),
        "spread": _parse_decimal(raw.get("spread")),
        "volume": _parse_decimal(raw.get("volume")),
        "volume_num": _parse_decimal(raw.get("volumeNum")),
        "volume_1wk": _parse_decimal(raw.get("volume1wk")),
        "volume_1mo": _parse_decimal(raw.get("volume1mo")),
        "volume_1yr": _parse_decimal(raw.get("volume1yr")),
        "liquidity": _parse_decimal(raw.get("liquidity")),
        "outcomes": _jsonb_array(raw.get("outcomes")),
        "outcome_prices": _jsonb_array(raw.get("outcomePrices")),
        "clob_token_ids": _jsonb_array(raw.get("clobTokenIds")),
        "raw_json": Json(raw),
    }


def rows_for_upsert(raw_markets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse a list of Gamma payloads into DB rows."""
    return [market_row_from_gamma(m) for m in raw_markets]
