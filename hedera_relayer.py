import os
from hiero_sdk_python import (
    Client,
    AccountId,
    PrivateKey,
    TokenMintTransaction,
    TransferTransaction,
    TokenId,
)

def get_token_id_str() -> str:
    """Fallback to check multiple potential environment variable keys for Token ID."""
    token_id = (
        os.getenv("TOKEN_ID")
        or os.getenv("NEX_TOKEN_ID")
        or os.getenv("NEX_NEX_TOKEN_ID")
        or "0.0.10991235"
    ).strip().strip('"').strip("'")

    # Safety check: Prevent player wallet ID from being evaluated as the Token ID
    if token_id == "0.0.11035514":
        return "0.0.10991235"

    return token_id

def get_hedera_client():
    """Initializes and returns the Hedera SDK Client and credentials safely."""
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except ImportError:
        pass

    operator_id_str = (
        os.getenv("OPERATOR_ID") 
        or os.getenv("HEDERA_OPERATOR_ID", "")
    ).strip().strip('"').strip("'")
    
    raw_key = (
        os.getenv("OPERATOR_KEY") 
        or os.getenv("HEDERA_OPERATOR_KEY", "")
    ).strip().strip('"').strip("'")

    # Safety Override: Force Treasury Account ID if player wallet or empty string is loaded
    if not operator_id_str or operator_id_str == "0.0.11035514":
        operator_id_str = "0.0.10770972"

    if not raw_key:
        raise RuntimeError("CRITICAL ERROR: OPERATOR_KEY environment variable is missing!")

    operator_id = AccountId.from_string(operator_id_str)

    # Force ECDSA SECP256K1 key parsing for Treasury account 0.0.10770972
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
    """Mints new NEX tokens to the treasury account on Hedera Testnet."""
    client, operator_id, operator_key = get_hedera_client()
    nex_token_id_str = get_token_id_str()
    NEX_TOKEN_ID = TokenId.from_string(nex_token_id_str)
    base_units = int(amount * 10000)  # 4 decimal places

    print(f"🔨 Minting {amount} NEX ({base_units} base units) for Token {NEX_TOKEN_ID}...")

    transaction = (
        TokenMintTransaction()
        .set_token_id(NEX_TOKEN_ID)
        .set_amount(base_units)
        .freeze_with(client)
    )

    signed_tx = transaction.sign(operator_key)
    receipt = signed_tx.execute(client)

    new_total = getattr(receipt, "new_total_supply", 0) / 10000
    print(f"\n✅ Mint Successful!")
    print(f"   Status: {receipt.status}")
    print(f"   New Total Supply: {new_total} NEX")
    print(f"   View on Explorer: https://hashscan.io/testnet/token/{NEX_TOKEN_ID}")
    return receipt.status

def transfer_nex_tokens(target_account_id: str, amount: float):
    """Transfers NEX tokens from Treasury to a targeted Hedera account ID."""
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
    receipt = signed_tx.execute(client)

    status_str = str(receipt.status)
    status_val = getattr(receipt.status, "value", None)

    # Check for SUCCESS status (Code 22 or string 'SUCCESS')
    if status_str in ["SUCCESS", "Status.SUCCESS"] or status_val == 22:
        print(f"✅ Transfer Successful! Status: SUCCESS")
        return "SUCCESS"

    print(f"❌ Transfer Failed! Status: {status_str}")
    return status_str