import os
from hiero_sdk_python import (
    Client,
    AccountId,
    PrivateKey,
    TokenCreateTransaction,
    TokenType,
    SupplyType,
)

OPERATOR_ID_STR = os.getenv("HEDERA_OPERATOR_ID")
OPERATOR_KEY_STR = os.getenv("HEDERA_OPERATOR_KEY")

if not OPERATOR_ID_STR or not OPERATOR_KEY_STR:
    print("❌ ERROR: HEDERA_OPERATOR_ID and HEDERA_OPERATOR_KEY must be set.")
    exit(1)

OPERATOR_ID = AccountId.from_string(OPERATOR_ID_STR)
OPERATOR_KEY = PrivateKey.from_string(OPERATOR_KEY_STR)

client = Client.for_testnet()
client.set_operator(OPERATOR_ID, OPERATOR_KEY)

def create_nex_token():
    print(f"🚀 Deploying NEX Token to Hedera Testnet from Account: {OPERATOR_ID}...")
    
    pub_key = OPERATOR_KEY.public_key()

    transaction = (
        TokenCreateTransaction()
        .set_token_name("NEX Token")
        .set_token_symbol("NEX")
        .set_decimals(4)
        .set_initial_supply(0)
        .set_treasury_account_id(OPERATOR_ID)
        .set_admin_key(pub_key)
        .set_supply_key(pub_key)
        .set_token_type(TokenType.FUNGIBLE_COMMON)
        .set_supply_type(SupplyType.FINITE)
        .set_max_supply(100_000_000_000 * 10000)  # 100B fixed cap with 4 decimals
        .freeze_with(client)
    )

    signed_tx = transaction.sign(OPERATOR_KEY)
    receipt = signed_tx.execute(client)
    
    # Convert TokenId object directly to string
    token_id = str(receipt.token_id)
    
    print(f"\n✅ NEX Token Created on Hedera Testnet!")
    print(f"   Token ID: {token_id}")
    print(f"   View on Explorer: https://hashscan.io/testnet/token/{token_id}")
    return token_id

if __name__ == "__main__":
    create_nex_token()