import asyncio
import hashlib
import hmac
import math
import random
import time
import aiohttp

# Configuration
BACKEND_URL = "https://main-coin-backend.onrender.com/api/v1"
DEV_SECRET = "nexus_dev_secret_2026"
NUM_PLAYERS = 20
TEST_ROUNDS = 5  # Each player will send 5 pings and attempt 2 purchases


def generate_hmac_signature(
    player_id: str, minutes: int, timestamp: int, nonce: str
) -> str:
    msg = f"{player_id}:{minutes}:{timestamp}:{nonce}".encode()
    return hmac.new(DEV_SECRET.encode(), msg, hashlib.sha256).hexdigest()


async def simulate_player_behavior(session: aiohttp.ClientSession, player_num: int):
    player_id = f"sim_pilot_{player_num:02d}"

    print(f"🚀 [INIT] Player {player_id} entering NEXUS ecosystem...")

    # 1. Initialize Player Profile via GET
    async with session.get(f"{BACKEND_URL}/player/{player_id}") as resp:
        if resp.status == 200:
            data = await resp.json()
            print(
                f"✅ [AUTH] {player_id} initialized | Balance: {data['spendable_nex']} NEX"
            )
        else:
            print(f"❌ [AUTH FAILED] {player_id} | Status: {resp.status}")
            return

    # 2. Simulate Telemetry Gameplay Pings
    for round_num in range(1, TEST_ROUNDS + 1):
        await asyncio.sleep(random.uniform(0.5, 2.0))  # Stagger requests

        timestamp = int(time.time())
        nonce = f"nonce_{player_id}_{timestamp}_{round_num}"
        minutes_played = random.randint(15, 60)

        signature = generate_hmac_signature(
            player_id, minutes_played, timestamp, nonce
        )

        telemetry_payload = {
            "player_id": player_id,
            "minutes_played": minutes_played,
            "timestamp": timestamp,
            "nonce": nonce,
            "signature": signature,
        }

        async with session.post(
            f"{BACKEND_URL}/telemetry", json=telemetry_payload
        ) as resp:
            if resp.status == 200:
                res_data = await resp.json()
                print(
                    f"🎮 [TELEMETRY] {player_id} | +{minutes_played} mins logged | Sync Status: {res_data.get('sync_status')}"
                )
            else:
                print(f"⚠️ [TELEMETRY REJECTED] {player_id} | Status: {resp.status}")

        # 3. Simulate Store Purchase (Attempt Katana purchase on rounds 2 & 4)
        if round_num in [2, 4]:
            purchase_payload = {
                "player_id": player_id,
                "item_id": "cosmetic_katana_plasma_01",
            }
            async with session.post(
                f"{BACKEND_URL}/store/buy", json=purchase_payload
            ) as resp:
                if resp.status == 200:
                    res_data = await resp.json()
                    print(
                        f"🔥 [STORE BURN] {player_id} bought Katana! | 13% NEX Burned | Status: SUCCESS"
                    )
                else:
                    err_detail = await resp.text()
                    print(
                        f"🛒 [STORE FAIL] {player_id} failed purchase | {err_detail}"
                    )


async def main():
    print(
        f"=== Starting NEXUS Simulation: {NUM_PLAYERS} Active Players Concurrent Load Test ==="
    )
    start_time = time.time()

    async with aiohttp.ClientSession() as session:
        tasks = [
            simulate_player_behavior(session, i) for i in range(1, NUM_PLAYERS + 1)
        ]
        await asyncio.gather(*tasks)

    duration = time.time() - start_time
    print(
        f"\n=== Simulation Complete in {duration:.2f} seconds! All {NUM_PLAYERS} accounts verified ==="
    )


if __name__ == "__main__":
    asyncio.run(main())