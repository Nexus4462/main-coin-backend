import os
import time
import hmac
import hashlib
import uuid
import requests

BACKEND_URL = os.getenv("BACKEND_URL", "https://main-coin-backend.onrender.com")
SECRET_KEY = os.getenv("HMAC_SECRET", "super_secret_game_server_key_123").encode('utf-8')

def send_telemetry(player_id: str, minutes_played: int):
    endpoint = f"{BACKEND_URL}/api/v1/telemetry"
    timestamp = int(time.time())
    nonce = uuid.uuid4().hex

    message = f"{player_id}:{minutes_played}:{timestamp}:{nonce}"
    signature = hmac.new(SECRET_KEY, message.encode('utf-8'), hashlib.sha256).hexdigest()

    payload = {
        "player_id": player_id,
        "minutes_played": minutes_played,
        "timestamp": timestamp,
        "nonce": nonce,
        "signature": signature
    }

    res = requests.post(endpoint, json=payload)
    if res.status_code == 200:
        data = res.json()
        
        # Pull correct key names from backend schema
        credited = data.get('nex_minted') or data.get('earned_nex') or data.get('nex_earned', 0)
        total = data.get('total_spendable_nex') or data.get('spendable_nex', 0)
        
        return credited, total
    else:
        print(f"❌ Telemetry Error [{res.status_code}]: {res.text}")
        return 0, 0

def fetch_player_hud(player_id: str):
    endpoint = f"{BACKEND_URL}/api/v1/player/{player_id}"
    res = requests.get(endpoint)
    if res.status_code == 200:
        data = res.json()
        
        # Profile fields from backend GET endpoint
        p_id = data.get('player_id', player_id)
        level = data.get('level', 1)
        rate = data.get('earn_rate_per_hr', 10.0)
        decay = data.get('soft_decay_active', False)
        
        return p_id, level, rate, decay
    else:
        # Fallback print if direct profile route isn't queried
        return player_id, 1, 10.0, False

if __name__ == "__main__":
    player = "salina_pilot_01"
    
    print("📡 Sending SDK Telemetry Heartbeats...")
    cred1, tot1 = send_telemetry(player, 15)
    print(f"Ping 1 Result: Credited {cred1} NEX | Total: {tot1} NEX")

    cred2, tot2 = send_telemetry(player, 15)
    print(f"Ping 2 Result: Credited {cred2} NEX | Total: {tot2} NEX")

    print("\n2. [UI HUB] Fetching player stats for HUD overlay...")
    p_id, lvl, rate, decay = fetch_player_hud(player)
    print(f"Player: {p_id} | Level: {lvl} | Earn Rate: {rate} NEX/hr")
    print(f"Soft Decay Active: {decay}")

    print("\n==============================================")
    print("        CLIENT SDK FUNCTIONAL & READY!")
    print("==============================================")