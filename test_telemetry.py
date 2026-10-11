import os
import time
import hmac
import hashlib
import uuid
import requests

# Network Configuration
BACKEND_URL = "https://main-coin-backend.onrender.com"

# Fetch HMAC secret from environment or fall back to dev default
SECRET_KEY_STR = os.getenv("HMAC_SECRET", "dev_secret_key_change_in_production")
NEXUS_HMAC_SECRET = SECRET_KEY_STR.encode('utf-8')

def send_test_telemetry(player_id: str, minutes_played: int):
    endpoint = f"{BACKEND_URL}/api/v1/telemetry"
    timestamp = int(time.time())
    nonce = uuid.uuid4().hex

    # 1. Construct payload string
    payload_string = f"{player_id}:{minutes_played}:{timestamp}:{nonce}"

    # 2. Compute HMAC-SHA256 signature
    signature = hmac.new(NEXUS_HMAC_SECRET, payload_string.encode('utf-8'), hashlib.sha256).hexdigest()

    # 3. Build JSON payload
    body = {
        "player_id": player_id,
        "minutes_played": minutes_played,
        "timestamp": timestamp,
        "nonce": nonce,
        "signature": signature
    }

    print(f"📡 Sending HMAC Telemetry Ping for '{player_id}' ({minutes_played} mins)...")
    response = requests.post(endpoint, json=body)

    if response.status_code == 200:
        data = response.json()
        print("✅ SUCCESS!")
        
        # Safe extraction matching backend output schema
        nex_earned = data.get('nex_minted') or data.get('earned_nex') or data.get('nex_earned', 0)
        spendable = data.get('total_spendable_nex') or data.get('spendable_nex', 0)
        multiplier = data.get('active_multiplier', 1.0)
        
        nametag_data = data.get('nametag_style', {})
        display_name = nametag_data.get('display_name_formatted', player_id)

        print(f"   Earned: {nex_earned} NEX")
        print(f"   Spendable Balance: {spendable} NEX")
        print(f"   Active Multiplier: {multiplier}x")
        print(f"   Formatted Nametag: {display_name}")
    else:
        print(f"❌ FAILED [{response.status_code}]: {response.text}")

if __name__ == "__main__":
    send_test_telemetry(player_id="salina_pilot_01", minutes_played=30)