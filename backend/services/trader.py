import os
from typing import Any, Dict

import psycopg
from dotenv import load_dotenv


def _load_env() -> None:
    load_dotenv()


def _get_conn():
    _load_env()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("Missing DATABASE_URL in environment.")
    return psycopg.connect(db_url)


def process_signed_mock_trade(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts signed trade payload from frontend and stores a mock/paper trade.
    This does NOT submit to Polymarket.
    """
    required = [
        "walletAddress",
        "conditionId",
        "tokenId",
        "side",
        "amountUsd",
        "price",
        "signature",
    ]
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Missing fields: {', '.join(missing)}")

    wallet_address = str(data["walletAddress"])
    condition_id = str(data["conditionId"])
    token_id = str(data["tokenId"])
    side = str(data["side"]).upper()
    amount_usd = float(data["amountUsd"])
    price = float(data["price"])
    signature = str(data["signature"])
    market_question = data.get("marketQuestion")

    if side not in ("BUY", "SELL"):
        raise ValueError("side must be BUY or SELL")
    if amount_usd <= 0:
        raise ValueError("amountUsd must be > 0")
    if not (0 < price < 1):
        raise ValueError("price must be between 0 and 1")

    sql = """
    INSERT INTO paper_trades (
        condition_id,
        token_id,
        side,
        amount_usd,
        price,
        wallet_address,
        signature
    ) VALUES (
        %(condition_id)s,
        %(token_id)s,
        %(side)s,
        %(amount_usd)s,
        %(price)s,
        %(wallet_address)s,
        %(signature)s
    )
    RETURNING id, created_at;
    """

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                {
                    "condition_id": condition_id,
                    "token_id": token_id,
                    "side": side,
                    "amount_usd": amount_usd,
                    "price": price,
                    "wallet_address": wallet_address,
                    "signature": signature,
                },
            )
            row = cur.fetchone()
        conn.commit()

    return {
        "ok": True,
        "mockTradeId": row[0],
        "createdAt": row[1].isoformat() if row and row[1] else None,
        "saved": {
            "walletAddress": wallet_address,
            "conditionId": condition_id,
            "tokenId": token_id,
            "side": side,
            "amountUsd": amount_usd,
            "price": price,
            "marketQuestion": market_question,
        },
    }


def list_mock_trades(limit: int = 100) -> Dict[str, Any]:
    sql = """
    SELECT
        id,
        created_at,
        condition_id,
        token_id,
        side,
        amount_usd,
        price,
        wallet_address
    FROM paper_trades
    ORDER BY id DESC
    LIMIT %(limit)s;
    """

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"limit": int(limit)})
            rows = cur.fetchall()

    data = [
        {
            "id": r[0],
            "createdAt": r[1].isoformat() if r[1] else None,
            "conditionId": r[2],
            "tokenId": str(r[3]),
            "side": r[4],
            "amountUsd": float(r[5]),
            "price": float(r[6]),
            "walletAddress": r[7],
        }
        for r in rows
    ]

    return {"ok": True, "count": len(data), "data": data}
