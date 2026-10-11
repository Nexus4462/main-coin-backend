import os
from hiero_sdk_python import (
    Client,
    AccountId,
    PrivateKey,
    TokenMintTransaction,
    TokenId,
)

OPERATOR_ID_STR = os.getenv("HEDERA_OPERATOR_ID")
OPERATOR_KEY_STR = os.getenv("HEDERA_OPERATOR_KEY")
TOKEN_ID_STR = os.getenv("NEX_TOKEN_ID", "0.0.10991235")

if not OPERATOR_ID_STR or not OPERATOR_KEY_STR:
    print("❌ ERROR: HEDERA_OPERATOR_ID and HEDERA_OPERATOR_KEY must be set.")
    exit(1)

OPERATOR_ID = AccountId.from_string(OPERATOR_ID_STR)
OPERATOR_KEY = PrivateKey.from_string(OPERATOR_KEY_STR)

client = Client.for_testnet()
client.set_operator(OPERATOR_ID, OPERATOR_KEY)

def mint_nex_tokens(amount: float):
    """Mints new NEX tokens to the treasury account on Hedera Testnet"""
    token_id = TokenId.from_string(TOKEN_ID_STR)
    base_units = int(amount * 10000)  # 4 decimals

    print(f"🔨 Minting {amount} NEX ({base_units} base units) for Token {token_id}...")

    transaction = (
        TokenMintTransaction()
        .set_token_id(token_id)
        .set_amount(base_units)
        .freeze_with(client)
    )

    signed_tx = transaction.sign(OPERATOR_KEY)
    receipt = signed_tx.execute(client)

    new_total = receipt.new_total_supply / 10000
    print(f"\n✅ Mint Successful!")
    print(f"   Status: {receipt.status}")
    print(f"   New Total Supply: {new_total} NEX")
    print(f"   View on Explorer: https://hashscan.io/testnet/token/{token_id}")
    return receipt.status

if __name__ == "__main__":
    # Test minting 100 NEX to Treasury
    mint_nex_tokens(100.0)