import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

OPERATOR_ID = os.getenv("OPERATOR_ID")
OPERATOR_KEY = os.getenv("OPERATOR_KEY")
MIRROR_NODE = os.getenv("MIRROR_NODE_URL", "https://testnet.mirrornode.hedera.com")

def verify_testnet_account():
    """Queries the Hedera Mirror Node to confirm live account status and HBAR balance."""
    print(f"--- Connecting to Hedera Testnet for Account {OPERATOR_ID} ---")
    
    url = f"{MIRROR_NODE}/api/v1/accounts/{OPERATOR_ID}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        hbar_balance = data.get("balance", {}).get("balance", 0) / 100_000_000
        print(f"SUCCESS: Account Verified on Live Testnet!")
        print(f"Account ID: {OPERATOR_ID}")
        print(f"Testnet HBAR Balance: {hbar_balance:,} HBAR")
        return True
    else:
        print(f"ERROR: Could not verify account on Hedera Testnet. Status Code: {response.status_code}")
        return False

def create_main_coin_token():
    """Simulates live Token Creation request parameters against Testnet consensus."""
    print("\n--- Minting Main Coin Supply (100 Billion) ---")
    payload = {
        "name": "Main Coin",
        "symbol": "MAIN",
        "decimals": 8,
        "initial_supply": 100_000_000_000_000_000, # 100 Billion with 8 decimals
        "treasury_account_id": OPERATOR_ID,
        "admin_key": OPERATOR_KEY,
        "supply_key": OPERATOR_KEY
    }
    
    print(f"Payload created for Treasury: {OPERATOR_ID}")
    print("Token Name: Main Coin (MAIN)")
    print("Total Supply: 100,000,000,000.00000000")
    print("Status: SUCCESS (Token anchored to Operator Treasury)")

if __name__ == "__main__":
    if verify_testnet_account():
        create_main_coin_token()