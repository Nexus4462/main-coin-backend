import requests

BACKEND_URL = "https://main-coin-backend.onrender.com"
DEVELOPER_ID = "studio_cyber_labs"
PLAYER_ID = "salina_pilot_01"
ITEM_ID = "cyber_laser_sword_01"

def test_full_developer_flow():
    print("🛠️ --- TESTING DEVELOPER ITEM PUBLISHING & PURCHASE FLOW --- 🛠️\n")

    # 1. Developer Publishes a New Item
    print(f"1. Developer '{DEVELOPER_ID}' registering item '{ITEM_ID}'...")
    create_item_payload = {
        "item_id": ITEM_ID,
        "name": "Cybernetic Plasma Katana",
        "description": "High-tier energy blade with 1.10x earn boost",
        "price_nex": 4.0,
        "developer_id": DEVELOPER_ID,
        "multiplier_boost": 1.10
    }
    
    dev_res = requests.post(f"{BACKEND_URL}/api/v1/developer/catalog/add", json=create_item_payload)
    if dev_res.status_code == 200:
        print("✅ ITEM PUBLISHED SUCCESSFULLY!")
        print(f"   Response: {dev_res.json()['message']}\n")
    elif dev_res.status_code == 400 and "already registered" in dev_res.text:
        print("ℹ️ Item already exists in catalog. Proceeding to purchase test...\n")
    else:
        print(f"❌ Failed to publish item [{dev_res.status_code}]: {dev_res.text}\n")
        return

    # 2. Player Purchases the Developer's Item
    print(f"2. Player '{PLAYER_ID}' buying '{ITEM_ID}' for 4.0 NEX...")
    buy_payload = {
        "player_id": PLAYER_ID,
        "item_id": ITEM_ID
    }
    
    buy_res = requests.post(f"{BACKEND_URL}/api/v1/store/buy", json=buy_payload)
    if buy_res.status_code == 200:
        print("✅ PURCHASE EXECUTED SUCCESSFULLY!")
        print(f"   Data: {buy_res.json()}\n")
    else:
        print(f"❌ Purchase Failed [{buy_res.status_code}]: {buy_res.text}\n")

if __name__ == "__main__":
    test_full_developer_flow()