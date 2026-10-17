import os
from hiero_sdk_python import (
    Client,
    AccountId,
    PrivateKey,
    TokenMintTransaction,
    TransferTransaction,
    TokenId,
)

def get_token_id_str():
    """Fallback to check multiple potential environment variable keys for Token ID."""
    return (
        os.getenv("TOKEN_ID")
        or os.getenv("NEX_TOKEN_ID")
        or os.getenv("NEX_NEX_TOKEN_ID")
        or "0.0.10991235"
    ).strip().strip('"').strip("'")

def get_hedera_client():
    """Initializes and returns the Hedera SDK Client and credentials safely without calling exit()."""
    # Fallback to handle both OPERATOR_ID and HEDERA_OPERATOR_ID naming conventions
    operator_id_str = (
        os.getenv("OPERATOR_ID") 
        or os.getenv("HEDERA_OPERATOR_ID", "")
    ).strip().strip('"').strip("'")
    
    raw_key = (
        os.getenv("OPERATOR_KEY") 
        or os.getenv("HEDERA_OPERATOR_KEY", "")
    ).strip().strip('"').strip("'")

    if not operator_id_str or not raw_key:
        raise RuntimeError(
            "CRITICAL ERROR: OPERATOR_ID or OPERATOR_KEY environment variables are missing on Render!"
        )

    operator_id = AccountId.from_string(operator_id_str)

    # Force ECDSA SECP256K1 key parsing for account 0.0.10770972
    try:
        operator_key = PrivateKey.from_string_ecdsa(raw_key)
    except Exception:
        try:
            operator_key = PrivateKey.from_string(raw_key)
        except Exception:
            operator_key = PrivateKey.from_string_ed25519(raw_key)

    client = Client.for_testnet()
    client.set_operator(operator_id, operator_key)
    return client, operator_id, operator_key

def mint_nex_tokens(amount: float):
    """Mints new NEX tokens to the treasury account on Hedera Testnet"""
    client, operator_id, operator_key = get_hedera_client()
    nex_token_id_str = get_token_id_str()
    NEX_TOKEN_ID = TokenId.from_string(nex_token_id_str)
    base_units = int(amount * 10000)  # 4 decimals

    print(f"🔨 Minting {amount} NEX ({base_units} base units) for Token {NEX_TOKEN_ID}...")

    transaction = (
        TokenMintTransaction()
        .set_token_id(NEX_TOKEN_ID)
        .set_amount(base_units)
        .freeze_with(client)
    )

    signed_tx = transaction.sign(operator_key)
    response = signed_tx.execute(client)
    receipt = response.get_receipt(client)

    new_total = receipt.new_total_supply / 10000 if receipt.new_total_supply else 0.0
    print(f"\n✅ Mint Successful!")
    print(f"   Status: {receipt.status}")
    print(f"   New Total Supply: {new_total} NEX")
    print(f"   View on Explorer: https://hashscan.io/testnet/token/{NEX_TOKEN_ID}")
    return receipt.status

def transfer_nex_tokens(target_account_id: str, amount: float):
    """Transfers NEX tokens from Treasury to a targeted Hedera account ID"""
    client, operator_id, operator_key = get_hedera_client()
    nex_token_id_str = get_token_id_str()
    NEX_TOKEN_ID = TokenId.from_string(nex_token_id_str)
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
    response = signed_tx.execute(client)
    receipt = response.get_receipt(client)

    print(f"✅ Transfer Successful! Status: {receipt.status}")
    return receipt.status

if __name__ == "__main__":
    # Test minting 100 NEX to Treasury when run directly
    mint_nex_tokens(100.0)