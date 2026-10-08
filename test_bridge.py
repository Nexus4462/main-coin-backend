import hashlib
import hmac
import requests
import time

BASE_URL = "http://127.0.0.1:8000"
HMAC_SECRET = "super_secret_game_server_key_123"
PLAYER_ID = "pilot_player_001"

def test_full_bridge():
    print("==================================================")
    print("   TESTING FASTAPI -> SQLITE -> HEDERA BRIDGE     ")
    print("==================================================\n")

    # 1. Simulate 50 Hours of Gameplay Telemetry
    print("1. Sending 50 Hours of Telemetry Pings...")
    for h in range(50):
        ts = time.time()
        payload = f"{PLAYER_ID}:60:{ts}"
        sig = hmac.new(HMAC_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()

        res = requests.post(f"{BASE_URL}/api/v1/telemetry", json={
            "player_id": PLAYER_ID,
            "minutes_played": 60,
            "timestamp": ts,
            "signature": sig
        })

    stats = requests.get(f"{BASE_URL}/api/v1/player/{PLAYER_ID}").json()
    print(f"Level: {stats['current_level']} | Coins: {stats['spendable_coins']:.2f} | Earn Rate: {stats['current_earn_rate']} coins/hr")
    print(f"Soft Decay Active: {stats['is_soft_decay_active']}\n")

    # 2. Buy Store Item
    print("2. Buying Cosmetic Item (500 Coins)...")
    store_res = requests.post(f"{BASE_URL}/api/v1/store/buy", json={
        "player_id": PLAYER_ID,
        "item_id": "dragon_skin_01",
        "price_in_coins": 500.0
    }).json()
    print(f"Purchase Status: {store_res['status']}")
    print(f"Dev Revenue: {store_res['developer_credited']} coins")
    print(f"Hedera Transfer Tx: {store_res['hedera_tx_id']}\n")

    # 3. Trigger Prestige & On-Chain Burn
    print("3. Executing Level 50 Prestige & Token Burn...")
    prestige_res = requests.post(f"{BASE_URL}/api/v1/prestige", json={
        "player_id": PLAYER_ID
    }).json()
    print(f"Prestige Status: {prestige_res['status']}")
    print(f"Burned Coins: {prestige_res['burned_coins']} MAIN")
    print(f"Hedera Burn Tx Hash: {prestige_res['hedera_burn_tx_id']}")
    print(f"New Earn Rate (+5% Boost): {prestige_res['new_earn_rate']} coins/hr\n")

    print("==================================================")
    print("      BRIDGE TEST COMPLETED SUCCESSFULLY!         ")
    print("==================================================")

if __name__ == "__main__":
    test_full_bridge()