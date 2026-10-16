import os
from hiero_sdk_python import (
    Client,
    AccountId,
    PrivateKey,
    TokenMintTransaction,
    TransferTransaction,
    TokenId,
)

NEX_TOKEN_ID_STR = os.getenv("NEX_NEX_TOKEN_ID", "0.0.10991235")

def get_hedera_client():
    """Initializes and returns the Hedera SDK Client and credentials safely without calling exit()."""
    operator_id_str = os.getenv("HEDERA_OPERATOR_ID")
    operator_key_str = os.getenv("HEDERA_OPERATOR_KEY")

    if not operator_id_str or not operator_key_str:
        raise RuntimeError("CRITICAL ERROR: HEDERA_OPERATOR_ID or HEDERA_OPERATOR_KEY environment variables are missing on Render!")

    operator_id = AccountId.from_string(operator_id_str)
    operator_key = PrivateKey.from_string(operator_key_str)

    client = Client.for_testnet()
    client.set_operator(operator_id, operator_key)
    return client, operator_id, operator_key

def mint_nex_tokens(amount: float):
    """Mints new NEX tokens to the treasury account on Hedera Testnet"""
    client, operator_id, operator_key = get_hedera_client()
    NEX_TOKEN_ID = TokenId.from_string(NEX_TOKEN_ID_STR)
    base_units = int(amount * 10000)  # 4 decimals

    print(f"🔨 Minting {amount} NEX ({base_units} base units) for Token {NEX_TOKEN_ID}...")

    transaction = (
        TokenMintTransaction()
        .set_NEX_TOKEN_ID(NEX_TOKEN_ID)
        .set_amount(base_units)
        .freeze_with(client)
    )

    signed_tx = transaction.sign(operator_key)
    receipt = signed_tx.execute(client)

    new_total = receipt.new_total_supply / 10000
    print(f"\n✅ Mint Successful!")
    print(f"   Status: {receipt.status}")
    print(f"   New Total Supply: {new_total} NEX")
    print(f"   View on Explorer: https://hashscan.io/testnet/token/{NEX_TOKEN_ID}")
    return receipt.status

def transfer_nex_tokens(target_account_id: str, amount: float):
    """Transfers NEX tokens from Treasury to a targeted Hedera account ID"""
    client, operator_id, operator_key = get_hedera_client()
    NEX_TOKEN_ID = TokenId.from_string(NEX_TOKEN_ID_STR)
    recipient = AccountId.from_string(target_account_id)
    base_units = int(amount * 10000)

    print(f"💸 Transferring {amount} NEX to {target_account_id} on Hedera Testnet...")

    transaction = (
        TransferTransaction()
        .add_token_transfer(NEX_TOKEN_ID, operator_id, -base_units)
        .add_token_transfer(NEX_TOKEN_ID, recipient, base_units)
        .freeze_with(client)
    )

    signed_tx = transaction.sign(operator_key)
    receipt = signed_tx.execute(client)

    print(f"✅ Transfer Successful! Status: {receipt.status}")
    return receipt.status

if __name__ == "__main__":
    # Test minting 100 NEX to Treasury when run directly
    mint_nex_tokens(100.0)