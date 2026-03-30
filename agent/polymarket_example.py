# MarketMind-yHack26/agent/polymarket_example.py
"""
This script demonstrates a more robust way to interact with Polymarket
by using standard, well-maintained Python libraries: `requests` and `web3.py`.

This version is updated to include the use of a Polymarket Builder API Key
for higher rate limits on public data requests.

**Prerequisites:**
1.  Install necessary Python libraries:
    - pip install requests web3 python-dotenv

2.  Create a `.env` file in the same directory (`agent/`) with your credentials:
    ```
    # agent/.env
    POLYMARKET_PRIVATE_KEY="0xYOUR_WALLET_PRIVATE_KEY"
    POLYGON_RPC_URL="https://polygon-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_API_KEY"
    POLYMARKET_BUILDER_API_KEY="YOUR_BUILDER_API_KEY" # Optional, but recommended
    ```
"""

import json
import os

import requests
from dotenv import load_dotenv
from eth_account.messages import encode_defunct
from web3 import Web3

# --- Constants ---
POLYMARKET_API_URL = "https://clob.polymarket.com"


def main():
    """
    Main function to demonstrate Polymarket API interaction using web3.py and requests.
    """
    # --- 1. Load Credentials from .env file ---
    load_dotenv()
    private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
    rpc_url = os.getenv("POLYGON_RPC_URL")
    builder_api_key = os.getenv("POLYMARKET_BUILDER_API_KEY")

    if not private_key or not rpc_url:
        print(
            "ERROR: POLYMARKET_PRIVATE_KEY and POLYGON_RPC_URL must be set in your .env file."
        )
        return
    print("✅ Core credentials loaded successfully.")

    if builder_api_key:
        print("✅ Builder API Key found and loaded.")
    else:
        print(
            "⚠️  Builder API Key not found. Making unauthenticated requests to public API."
        )

    # --- 2. Initialize Web3 and Your Account ---
    try:
        w3_instance = Web3(Web3.HTTPProvider(rpc_url))
        if not w3_instance.is_connected():
            print("❌ Error: Could not connect to the Polygon network via the RPC URL.")
            return

        account = w3_instance.eth.account.from_key(private_key)
        chain_id = w3_instance.eth.chain_id

        print(f"✅ Web3 initialized for chain ID: {chain_id}")
        print(f"👤 Your wallet address: {account.address}")

    except Exception as e:
        print(f"❌ Error initializing Web3 or account: {e}")
        return

    # --- 3. Fetch Public Market Data using Requests ---
    try:
        print("\nFetching active markets via REST API...")

        # Prepare headers for the request. If we have a builder key, use it.
        headers = {}
        if builder_api_key:
            headers["Authorization"] = f"Bearer {builder_api_key}"
            print("   (Using Builder API Key for authentication)")

        response = requests.get(f"{POLYMARKET_API_URL}/markets", headers=headers)
        response.raise_for_status()
        markets = response.json().get("data", [])

        if not markets:
            print("No active markets found.")
            return

        print(f"✅ Found {len(markets)} active markets.")
        example_market = markets[0]

        # --- DEBUG: Print the structure of the first market object ---
        print("\n--- Inspecting First Market Object ---")
        print(json.dumps(example_market, indent=2))
        print("------------------------------------")

        # --- CORRECTED KEY ACCESS ---
        market_question = example_market.get("question", "N/A")
        condition_id = example_market.get("condition_id", "N/A")

        print(f"\nExample Market: '{market_question}'")
        print(f"  - Condition ID: {condition_id}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching markets from API: {e}")
        return
    except (KeyError, IndexError) as e:
        print(
            f"❌ Error parsing market data. API structure may have changed. Error: {e}"
        )
        return

    # --- 4. Demonstrate Signing a Message ---
    print("\n--- Example: Signing a Message (Demonstration) ---")

    try:
        message_text = "This is a test message to prove ownership of my wallet."
        message_to_sign = encode_defunct(text=message_text)
        signed_message = w3_instance.eth.account.sign_message(
            message_to_sign, private_key=account.key
        )

        print(f"✅ Message signed successfully!")
        print(f"  - Original Message: '{message_text}'")
        print(f"  - Signature: {signed_message.signature.hex()}")

        recovered_address = w3_instance.eth.account.recover_message(
            message_to_sign, signature=signed_message.signature
        )
        print(f"\n✅ Verification successful!")
        print(f"  - Recovered Address: {recovered_address}")
        print(f"  - Your Address:      {account.address}")

        if recovered_address.lower() == account.address.lower():
            print("  - Match! The signature is valid.")
        else:
            print("  - Mismatch! The signature is invalid.")

    except Exception as e:
        print(f"❌ Error signing message: {e}")

    print(
        "\nScript finished. This demonstrates fetching data and the core signing mechanic."
    )


if __name__ == "__main__":
    main()
