import time
import hmac
import hashlib
import uuid
import requests

# Network Configuration
BACKEND_URL = "https://main-coin-backend.onrender.com"
NEXUS_HMAC_SECRET = b"dev_secret_key_change_in_production"  # Must match Render Env Variable

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
        print(f"   Earned: {data['nex_earned']} NEX")
        print(f"   Spendable Balance: {data['total_spendable_nex']} NEX")
        print(f"   Active Multiplier: {data['active_multiplier']}x")
        print(f"   Formatted Nametag: {data['nametag_style']['display_name_formatted']}")
    else:
        print(f"❌ FAILED [{response.status_code}]: {response.text}")

if __name__ == "__main__":
    # Test Player 1
    send_test_telemetry(player_id="salina_pilot_01", minutes_played=30)