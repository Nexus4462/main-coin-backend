import requests

BACKEND_URL = "https://main-coin-backend.onrender.com"
PLAYER_ID = "salina_pilot_01"

def run_store_test():
    print("🛒 --- TESTING STORE PURCHASE & DEVELOPER SPLIT --- 🛒\n")

    # 1. Fetch Store Catalog to get a valid item_id
    print("1. Fetching available store catalog...")
    catalog_res = requests.get(f"{BACKEND_URL}/api/v1/store/catalog")
    
    item_to_buy = None
    if catalog_res.status_code == 200 and catalog_res.json():
        catalog = catalog_res.json()
        print(f"   Found {len(catalog)} item(s) in catalog.")
        item_to_buy = catalog[0].get("item_id")
        print(f"   Selected Item ID: '{item_to_buy}' ({catalog[0].get('item_name')})")
    else:
        # Fallback to default seeded item ID if catalog route varies
        item_to_buy = "item_neon_wrap"
        print(f"   Using default item ID: '{item_to_buy}'")

    print("\n2. Checking starting balance...")
    player_res = requests.get(f"{BACKEND_URL}/api/v1/player/{PLAYER_ID}")
    if player_res.status_code == 200:
        start_balance = player_res.json().get("total_spendable_nex", 0)
        print(f"   Current Balance for '{PLAYER_ID}': {start_balance} NEX\n")

    # 3. Execute Buy
    purchase_payload = {
        "player_id": PLAYER_ID,
        "item_id": item_to_buy
    }

    print(f"3. Sending BUY request to /api/v1/store/buy...")
    buy_res = requests.post(f"{BACKEND_URL}/api/v1/store/buy", json=purchase_payload)

    if buy_res.status_code == 200:
        data = buy_res.json()
        print("\n✅ PURCHASE SUCCESSFUL!")
        print(f"   Response: {data}")
    else:
        print(f"\n❌ Purchase Failed [{buy_res.status_code}]: {buy_res.text}")

if __name__ == "__main__":
    run_store_test()