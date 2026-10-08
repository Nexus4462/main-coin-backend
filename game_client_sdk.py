import hashlib
import hmac
import time
import requests
from typing import Dict, Any, Optional

class MainCoinGameSDK:
    def __init__(self, base_url: str = "http://127.0.0.1:8000", hmac_secret: str = "super_secret_game_server_key_123"):
        self.base_url = base_url.rstrip("/")
        self.hmac_secret = hmac_secret

    def _generate_signature(self, player_id: str, minutes_played: int, timestamp: float) -> str:
        """Generates client-side HMAC-SHA256 signature for telemetry payloads."""
        payload = f"{player_id}:{minutes_played}:{timestamp}"
        return hmac.new(self.hmac_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

    def ping_telemetry(self, player_id: str, minutes_played: int) -> Dict[str, Any]:
        """Sends authenticated gameplay session minutes to the backend server."""
        timestamp = time.time()
        signature = self._generate_signature(player_id, minutes_played, timestamp)

        payload = {
            "player_id": player_id,
            "minutes_played": minutes_played,
            "timestamp": timestamp,
            "signature": signature
        }

        try:
            response = requests.post(f"{self.base_url}/api/v1/telemetry", json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}

    def get_player_data(self, player_id: str) -> Dict[str, Any]:
        """Retrieves real-time player economy profile, decay alerts, and earn rate."""
        try:
            response = requests.get(f"{self.base_url}/api/v1/player/{player_id}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}

    def buy_store_item(self, player_id: str, item_id: str, price_in_coins: float) -> Dict[str, Any]:
        """Executes cosmetic purchase with 75/25 Dev Split & Hedera settlement."""
        payload = {
            "player_id": player_id,
            "item_id": item_id,
            "price_in_coins": price_in_coins
        }

        try:
            response = requests.post(f"{self.base_url}/api/v1/store/buy", json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}

    def trigger_prestige(self, player_id: str) -> Dict[str, Any]:
        """Executes Level 50 Prestige reset, charges 2,500 coins, and triggers Hedera burn."""
        payload = {"player_id": player_id}

        try:
            response = requests.post(f"{self.base_url}/api/v1/prestige", json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}


# --- SIMULATED GAME LOOP EXAMPLE ---
if __name__ == "__main__":
    print("==================================================")
    print("      INITIALIZING GAME CLIENT SDK SESSION        ")
    print("==================================================\n")

    # Initialize Client SDK
    sdk = MainCoinGameSDK()
    player_id = "gamer_tactical_99"

    # 1. Simulate gameplay session (pings every 30 game minutes)
    print("1. [GAME LOOP] Sending telemetry pings from active session...")
    ping_1 = sdk.ping_telemetry(player_id, 30)
    print(f"Ping 1 Result: Credited {ping_1.get('coins_earned')} coins | Total: {ping_1.get('total_spendable_coins')} coins")

    ping_2 = sdk.ping_telemetry(player_id, 30)
    print(f"Ping 2 Result: Credited {ping_2.get('coins_earned')} coins | Total: {ping_2.get('total_spendable_coins')} coins\n")

    # 2. Query player profile for UI rendering
    print("2. [UI HUB] Fetching player stats for HUD overlay...")
    profile = sdk.get_player_data(player_id)
    print(f"Player: {profile.get('player_id')} | Level: {profile.get('current_level')} | Earn Rate: {profile.get('current_earn_rate')} coins/hr")
    print(f"Soft Decay Active: {profile.get('is_soft_decay_active')}\n")

    print("==================================================")
    print("         CLIENT SDK FUNCTIONAL & READY!          ")
    print("==================================================")