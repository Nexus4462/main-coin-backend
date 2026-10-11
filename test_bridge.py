import os
import time
import hmac
import hashlib
import uuid
import requests

BASE_URL = os.getenv("BACKEND_URL", "https://main-coin-backend.onrender.com")
SECRET_KEY_STR = os.getenv("HMAC_SECRET", "super_secret_game_server_key_123")
NEXUS_HMAC_SECRET = SECRET_KEY_STR.encode('utf-8')

PLAYER_ID = "salina_pilot_01"

def test_full_bridge():
    print("=" * 50)
    print("   TESTING FASTAPI -> POSTGRESQL -> HEDERA BRIDGE   ")
    print("=" * 50)

    print("\n1. Sending Telemetry Pings to Live Backend...")
    for i in range(1, 6):
        timestamp = int(time.time())
        nonce = uuid.uuid4().hex
        minutes = 30  # Valid 30-minute gameplay session ping

        message = f"{PLAYER_ID}:{minutes}:{timestamp}:{nonce}"
        sig = hmac.new(NEXUS_HMAC_SECRET, message.encode('utf-8'), hashlib.sha256).hexdigest()

        res = requests.post(f"{BASE_URL}/api/v1/telemetry", json={
            "player_id": PLAYER_ID,
            "minutes_played": minutes,
            "timestamp": timestamp,
            "nonce": nonce,
            "signature": sig
        })

        if res.status_code == 200:
            data = res.json()
            minted = data.get('nex_minted') or data.get('earned_nex') or data.get('nex_earned', 0)
            spendable = data.get('total_spendable_nex') or data.get('spendable_nex', 0)
            print(f"   Ping {i}/5 Success! Earned: {minted} NEX | Spendable: {spendable} NEX")
        else:
            print(f"   Ping {i}/5 Failed [{res.status_code}]: {res.text}")

        # Brief delay to prevent nonce/timestamp collision
        time.sleep(0.5)

if __name__ == "__main__":
    test_full_bridge()