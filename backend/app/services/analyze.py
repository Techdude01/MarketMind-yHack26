"""K2 ReAct agent market analysis — shared by HTTP analyze route and ingest pipeline."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage

from app.repositories.market_research import (
    get_latest_tavily,
    get_latest_thesis,
    insert_gemini_summary,
    insert_tavily_search,
)
from app.repositories.polymarket_markets import get_market_by_id
from app.services.llm.k2_agent import (
    K2_REACT_AGENT_MODEL_LABEL,
    analyze_market_with_agent,
    extract_tavily_hits_from_langgraph_messages,
    thesis_markdown_for_display,
)
from app.services.thesis_parse import parse_structured_thesis_fields

DEFAULT_TAVILY_MAX = 5
MAX_TAVILY_MAX = 15


class MarketNotFoundError(Exception):
    """Raised when ``polymarket_id`` has no row."""


class AnalysisPipelineError(Exception):
    """Wraps a failure during ``agent`` stage for ingest error reporting."""

    def __init__(self, stage: str, cause: BaseException) -> None:
        self.stage = stage
        self.cause = cause
        super().__init__(str(cause))


def clamp_tavily_max(raw: int | None) -> int:
    """Clamp Tavily ``max_results`` to the allowed range (LangChain tool)."""
    if raw is None or raw < 1:
        v = DEFAULT_TAVILY_MAX
    else:
        v = raw
    return min(v, MAX_TAVILY_MAX)


def _market_dict_for_agent(m: dict[str, Any]) -> dict[str, Any]:
    q = str(m.get("question") or "N/A")
    d = m.get("description")
    desc = str(d) if d is not None else "N/A"
    ed = m.get("end_date_iso") or m.get("end_date")
    if ed is None:
        ed_s = "unknown"
    elif hasattr(ed, "isoformat"):
        ed_s = ed.isoformat()
    else:
        ed_s = str(ed)
    price = m.get("last_trade_price") or m.get("best_bid") or m.get("best_ask")
    price_s = str(price) if price is not None else "unknown"
    return {
        "question": q,
        "description": desc,
        "end_date": ed_s,
        "current_price": price_s,
    }


def _raw_final_answer_from_messages(messages: list) -> str:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            c = msg.content
            if isinstance(c, str) and c.strip():
                return c
    return ""


def run_market_analysis(
    conn: Any,
    polymarket_id: int,
    *,
    tavily_max: int,
    market_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Run the K2 ReAct agent (Tavily inside LangGraph), persist Tavily + thesis rows.

    Does not commit ``conn``. Callers must commit or use savepoints.

    ``market_row`` is accepted for API compatibility; the full row is always
    loaded via ``get_market_by_id`` for agent context.

    Raises:
        MarketNotFoundError: if the market is missing.
        AnalysisPipelineError: on agent or persistence failure (stage ``agent``).
    """
    _ = market_row
    m = get_market_by_id(conn, polymarket_id)
    if m is None:
        raise MarketNotFoundError(polymarket_id)
    agent_market = _market_dict_for_agent(m)
    try:
        result = analyze_market_with_agent(
            agent_market,
            include_messages=True,
            verbose=False,
            tavily_max_results=tavily_max,
        )
        messages = result.get("messages") or []
        hits = extract_tavily_hits_from_langgraph_messages(messages)
        raw_final = _raw_final_answer_from_messages(messages)
        if raw_final:
            thesis_text = thesis_markdown_for_display(raw_final)
        else:
            thesis_text = thesis_markdown_for_display(result.get("analysis") or "")
        search_query = "k2_react_agent"
        results_list: list[dict[str, Any]] = hits
        tavily_id = insert_tavily_search(
            conn,
            polymarket_id=polymarket_id,
            search_query=search_query,
            results=results_list,
            max_results=tavily_max,
        )
        thinking = result.get("thinking") or ""
        reasoning_input = json.dumps(
            {
                "agent_thinking_excerpt": thinking[:8000],
                "reasoning_steps": result.get("reasoning_steps", 0),
            },
            ensure_ascii=False,
        )
        insert_gemini_summary(
            conn,
            polymarket_id=polymarket_id,
            tavily_search_id=tavily_id,
            thesis_text=thesis_text,
            reasoning_input=reasoning_input,
            model=K2_REACT_AGENT_MODEL_LABEL,
        )
    except MarketNotFoundError:
        raise
    except Exception as exc:
        raise AnalysisPipelineError("agent", exc) from exc

    thesis = get_latest_thesis(conn, polymarket_id)
    if isinstance(thesis, dict):
        structured = parse_structured_thesis_fields(thesis.get("thesis_text"))
        thesis = {**thesis, **structured}
    news_results = get_latest_tavily(conn, polymarket_id)
    news = sorted(
        (r for r in news_results if isinstance(r, dict)),
        key=lambda r: float(r.get("score", 0)),
        reverse=True,
    )
    return {"market_id": polymarket_id, "thesis": thesis, "news": news}
