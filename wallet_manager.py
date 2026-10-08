# wallet_manager.py
import hashlib
import hmac
import uuid
from typing import Dict, Any, Optional

class ProgressiveWalletManager:
    """
    Handles Instant Day 1 Player Wallets & Hedera Account Mapping
    --------------------------------------------------------------
    - Generates deterministic key pairs from user OAuth IDs (Google/Steam/Discord)
    - Manages Day 1 instant in-game usability (Off-Chain Fast Ledger)
    - Prepares on-chain Hedera Account ID deployment on request
    """

    def __init__(self, master_system_secret: str):
        # System Master Secret used to deterministically derive player keys securely
        self.master_secret = master_system_secret
        
        # User ID -> Wallet Mapping Database
        self.user_wallets: Dict[str, Dict[str, Any]] = {}

    def get_or_create_day_one_wallet(self, user_id: str, auth_provider: str = "google") -> Dict[str, Any]:
        """
        Creates an instant Day 1 wallet mapping in 0 milliseconds.
        Player can immediately earn and spend coins in-game.
        """
        if user_id in self.user_wallets:
            return self.user_wallets[user_id]

        # Generate a secure, deterministic keypair derived from Master Secret + User ID
        # (Allows recovering their wallet via Google/Steam login if they lose their device)
        derived_seed = hmac.new(
            self.master_secret.encode('utf-8'),
            f"{auth_provider}:{user_id}".encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        wallet_data = {
            "user_id": user_id,
            "auth_provider": auth_provider,
            "internal_wallet_id": f"wlt_{uuid.uuid4().hex[:12]}",
            "derived_private_key": derived_seed,  # Used to sign Hedera actions
            "hedera_account_id": None,           # Deployed to Hedera on-chain on demand
            "is_on_chain_deployed": False
        }

        self.user_wallets[user_id] = wallet_data
        return wallet_data

    def deploy_on_chain_account(self, user_id: str, master_treasury_payout_func) -> Dict[str, Any]:
        """
        Triggered when a player opens their Web Dashboard or requests external withdrawal.
        Sponsors the $0.05 Hedera account creation fee from platform treasury.
        """
        wallet = self.user_wallets.get(user_id)
        if not wallet:
            return {"status": "error", "message": "Player wallet not found"}

        if wallet["is_on_chain_deployed"]:
            return {
                "status": "already_deployed",
                "hedera_account_id": wallet["hedera_account_id"]
            }

        # Call Hedera SDK Relayer to create account on Hedera Testnet/Mainnet
        # (Master Treasury pays the ~$0.05 USD creation fee)
        real_hedera_id = master_treasury_payout_func(wallet["derived_private_key"])

        wallet["hedera_account_id"] = real_hedera_id
        wallet["is_on_chain_deployed"] = True

        return {
            "status": "success",
            "hedera_account_id": real_hedera_id,
            "message": "Account successfully activated on Hedera Hashgraph!"
        }


# --- QUICK VERIFICATION DEMO ---
if __name__ == "__main__":
    manager = ProgressiveWalletManager(master_system_secret="super_secret_platform_key_9900")

    print("--- 1. Day 1 Player Joins via Google/Steam ---")
    player_wallet = manager.get_or_create_day_one_wallet(user_id="david_player_77", auth_provider="steam")
    print("Day 1 Internal Wallet Created:", player_wallet["internal_wallet_id"])
    print("Is On-Chain Deployed Yet?:", player_wallet["is_on_chain_deployed"])
    print("Result: Player can earn & spend in-game IMMEDIATELY on Day 1!")

    print("\n--- 2. Player Visits Dashboard Later & Requests On-Chain Activation ---")
    def mock_hedera_creator(private_key_seed):
        # Simulates Hedera AccountCreateTransaction
        return "0.0.849201"

    activation_res = manager.deploy_on_chain_account("david_player_77", mock_hedera_creator)
    print("Dashboard On-Chain Activation:", activation_res)