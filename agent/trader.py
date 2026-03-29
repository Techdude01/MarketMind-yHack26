import os
import random
import time
from typing import Any, Dict, Optional, Tuple

import requests
from dotenv import load_dotenv
from web3 import Web3

API_BASE_URL = os.getenv("POLYMARKET_API_URL", "https://clob.polymarket.com")
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
REQUEST_TIMEOUT = 20

ORDER_TYPES = {
    "Order": [
        {"name": "maker", "type": "address"},
        {"name": "taker", "type": "address"},
        {"name": "tokenId", "type": "uint256"},
        {"name": "makerAmount", "type": "uint256"},
        {"name": "takerAmount", "type": "uint256"},
        {"name": "side", "type": "uint8"},
        {"name": "feeRateBps", "type": "uint256"},
        {"name": "nonce", "type": "uint256"},
        {"name": "expiration", "type": "uint256"},
    ]
}


def _headers() -> Dict[str, str]:
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    builder_key = os.getenv("POLYMARKET_BUILDER_API_KEY")
    if builder_key:
        headers["Authorization"] = f"Bearer {builder_key}"
    return headers


def _load_web3_and_account() -> Tuple[Web3, Any]:
    load_dotenv()
    private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
    rpc_url = os.getenv("POLYGON_RPC_URL")

    if not private_key or not rpc_url:
        raise ValueError(
            "Missing POLYMARKET_PRIVATE_KEY or POLYGON_RPC_URL in environment."
        )

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise ConnectionError("Failed to connect to POLYGON_RPC_URL.")

    account = w3.eth.account.from_key(private_key)
    return w3, account


def _fetch_market_by_condition_id(condition_id: str) -> Dict[str, Any]:
    resp = requests.get(
        f"{API_BASE_URL}/markets/{condition_id}",
        headers=_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    if resp.status_code == 404:
        raise ValueError(f"No market found for condition_id={condition_id}")
    resp.raise_for_status()

    market = resp.json()
    if (
        not isinstance(market, dict)
        or market.get("condition_id", "").lower() != condition_id.lower()
    ):
        raise ValueError(f"Invalid market payload for condition_id={condition_id}")
    return market


def _pick_token(tokens: list, yes_or_no: int) -> Dict[str, Any]:
    if not isinstance(tokens, list) or len(tokens) < 2:
        raise ValueError("Market does not have at least 2 tokens.")
    if yes_or_no not in (1, 2):
        raise ValueError("yes_or_no must be 1 (first token) or 2 (second token).")
    return tokens[yes_or_no - 1]


def submit_trade(
    condition_id: str,
    amount: float,
    yes_or_no: int,
    price: float,
    post_order: bool = True,
    expiration_seconds: int = 86400,
    fee_rate_bps: int = 0,
    nonce: Optional[int] = None,
) -> Dict[str, Any]:
    if amount <= 0:
        raise ValueError("amount must be > 0")
    if not (0 < price < 1):
        raise ValueError("price must be between 0 and 1")

    w3, account = _load_web3_and_account()
    market = _fetch_market_by_condition_id(condition_id)
    token = _pick_token(market.get("tokens", []), yes_or_no)
    token_id = int(token["token_id"])
    if market.get("closed") or not market.get("accepting_orders"):
        raise ValueError(
            f"Market is not tradeable (closed={market.get('closed')}, "
            f"accepting_orders={market.get('accepting_orders')})."
        )
    market_label = market.get("question") or market.get("market_slug") or condition_id
    print(f"Wallet: {account.address}")
    print(f"Market: {market_label}")

    maker_amount = int(amount * 1_000_000)
    taker_amount = int(maker_amount * price)

    is_neg_risk = bool(market.get("neg_risk", False))

    env_standard = os.getenv("POLYMARKET_EIP712_VERIFIER_STANDARD")
    env_neg_risk = os.getenv("POLYMARKET_EIP712_VERIFIER_NEG_RISK")

    verifying_contract = env_neg_risk if is_neg_risk else env_standard

    domain = {
        "name": os.getenv("POLYMARKET_EIP712_DOMAIN_NAME", "Polymarket CLOB"),
        "version": os.getenv("POLYMARKET_EIP712_DOMAIN_VERSION", "1"),
        "chainId": w3.eth.chain_id,
        "verifyingContract": verifying_contract,
    }

    print(f"Verifier: {verifying_contract} (neg_risk={is_neg_risk})")

    message = {
        "maker": account.address,
        "taker": ZERO_ADDRESS,
        "tokenId": token_id,
        "makerAmount": str(maker_amount),
        "takerAmount": str(taker_amount),
        "side": 1,
        "feeRateBps": str(fee_rate_bps),
        "nonce": int(nonce if nonce is not None else random.randint(1, 10**15)),
        "expiration": str(int(time.time()) + int(expiration_seconds)),
    }

    signed = account.sign_typed_data(
        domain_data=domain,
        message_types={"Order": ORDER_TYPES["Order"]},
        message_data=message,
    )
    signature = signed.signature.hex() if hasattr(signed, "signature") else signed.hex()
    payload: Dict[str, Any] = {**message, "signature": signature}

    if not post_order:
        print("Transaction prepared (dry run).")
        return payload

    resp = requests.post(
        f"{API_BASE_URL}/orders",
        json=payload,
        headers=_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    print("Transaction submitted successfully.")
    return resp.json()


if __name__ == "__main__":
    result = submit_trade(
        condition_id="0xb48621f7eba07b0a3eeabc6afb09ae42490239903997b9d412b0f69aeb040c8b",
        amount=1.0,
        yes_or_no=1,
        price=0.25,
        post_order=False,
    )
    print(result)
