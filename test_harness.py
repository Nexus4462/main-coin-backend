import asyncio
import hmac
import hashlib
import json
import time
import httpx

BACKEND_URL = "https://main-coin-backend.onrender.com"
# Matches _raw_hmac_secret in your backend code
NEXUS_HMAC_SECRET = "nexus_dev_secret_2026".encode('utf-8')

def generate_telemetry_signature(player_id: str, minutes_played: int, timestamp: int, nonce: str) -> str:
    payload = f"{player_id}:{minutes_played}:{timestamp}:{nonce}".encode('utf-8')
    return hmac.new(NEXUS_HMAC_SECRET, payload, hashlib.sha256).hexdigest()

async def simulate_player_session(client: httpx.AsyncClient, player_num: int):
    player_id = f"salina_test_player_{player_num:02d}"
    minutes_played = 30  # Valid duration (1 to 60)
    timestamp = int(time.time())
    # Generate globally unique nonces using player_id and nanoseconds
    nonce = f"nonce_{player_id}_{time.time_ns()}"

    # 1. Generate Valid HMAC Signature
    valid_sig = generate_telemetry_signature(player_id, minutes_played, timestamp, nonce)
    
    valid_payload = {
        "player_id": player_id,
        "minutes_played": minutes_played,
        "timestamp": timestamp,
        "nonce": nonce,
        "signature": valid_sig
    }

    try:
        res = await client.post(f"{BACKEND_URL}/api/v1/telemetry", json=valid_payload)
        if res.status_code == 200:
            data = res.json()
            earned = data.get("nex_earned", 0)
            spendable = data.get("total_spendable_nex", 0)
            mult = data.get("active_multiplier", 1.0)
            print(f"✅ [{player_id}] Earned: {earned:.2f} NEX | Multiplier: {mult}x | Spendable: {spendable:.2f} NEX")
        else:
            print(f"❌ [{player_id}] Valid telemetry failed! Status: {res.status_code} | Detail: {res.text}")
    except Exception as e:
        print(f"⚠️ [{player_id}] Request exception: {e}")

    # 2. Test Security: Invalid HMAC Signature (Distinct nonce to avoid replay trigger)
    bad_nonce = f"bad_nonce_{player_id}_{time.time_ns()}"
    invalid_payload = {
        "player_id": player_id,
        "minutes_played": minutes_played,
        "timestamp": timestamp,
        "nonce": bad_nonce,
        "signature": "corrupted_invalid_signature_string"
    }

    try:
        bad_res = await client.post(f"{BACKEND_URL}/api/v1/telemetry", json=invalid_payload)
        if bad_res.status_code == 401 and "Invalid telemetry cryptographic signature" in bad_res.text:
            print(f"🔒 [{player_id}] Security Check Passed: Invalid signature correctly rejected (401).")
        else:
            print(f"🚨 [{player_id}] SECURITY ALERT: Bad signature return code {bad_res.status_code} | Msg: {bad_res.text}")
    except Exception as e:
        print(f"⚠️ [{player_id}] Invalid signature test error: {e}")

async def main():
    print("🚀 Running Pre-Mainnet Telemetry Harness against Live Backend...")
    start_time = time.time()

    limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
    async with httpx.AsyncClient(timeout=30.0, limits=limits) as client:
        # Run 20 concurrent player sessions
        tasks = [simulate_player_session(client, i) for i in range(1, 21)]
        await asyncio.gather(*tasks)

    elapsed = time.time() - start_time
    print(f"\n✨ Test harness execution finished in {elapsed:.2f} seconds.")

if __name__ == "__main__":
    asyncio.run(main())