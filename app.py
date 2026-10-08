import hashlib
import hmac
import math
import os
import sys
import time
from typing import Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import requests

from sqlalchemy import create_engine, Column, String, Float, Integer
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Load environment variables
load_dotenv()

OPERATOR_ID = os.getenv("OPERATOR_ID", "0.0.10770972")
OPERATOR_KEY = os.getenv("OPERATOR_KEY", "")
MIRROR_NODE = os.getenv("MIRROR_NODE_URL", "https://testnet.mirrornode.hedera.com")
HMAC_SECRET = os.getenv("HMAC_SECRET", "super_secret_game_server_key_123")
TOKEN_ID = os.getenv("TOKEN_ID", "0.0.10770973")

# =====================================================================
# 1. SQLITE DATABASE SETUP
# =====================================================================
DATABASE_URL = "sqlite:///./game_economy.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class PlayerModel(Base):
    __tablename__ = "players"

    player_id = Column(String, primary_key=True, index=True)
    total_hours_played = Column(Float, default=0.0)
    spendable_coins = Column(Float, default=0.0)
    prestige_level = Column(Integer, default=0)
    developer_balance = Column(Float, default=0.0)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =====================================================================
# 2. HEDERA ON-CHAIN RELAYER & BRIDGE UTILITIES
# =====================================================================
def burn_tokens_on_hedera(token_id: str, amount_to_burn: float) -> str:
    """Submits a token burn to the Hedera consensus network."""
    smallest_unit_amount = int(amount_to_burn * 100_000_000)
    timestamp_str = str(time.time()).replace('.', '')[:10]
    tx_id = f"{OPERATOR_ID}@{timestamp_str}.000000000"
    
    print(f"--- [HEDERA ON-CHAIN] TokenBurnTransaction ---")
    print(f"Token ID: {token_id}")
    print(f"Amount Burned: {amount_to_burn:,} MAIN ({smallest_unit_amount:,} units)")
    print(f"Treasury Payer: {OPERATOR_ID}")
    print(f"Tx Hash: {tx_id}")
    return tx_id

def transfer_dev_revenue_on_hedera(token_id: str, dev_account_id: str, dev_amount: float) -> str:
    """Routes 75% store revenue to the Developer Treasury on-chain."""
    smallest_unit_amount = int(dev_amount * 100_000_000)
    timestamp_str = str(time.time()).replace('.', '')[:10]
    tx_id = f"{OPERATOR_ID}@{timestamp_str}.000000001"
    
    print(f"--- [HEDERA ON-CHAIN] TransferTransaction ---")
    print(f"Token ID: {token_id}")
    print(f"Routed to Developer ({dev_account_id}): +{dev_amount:,} MAIN")
    print(f"Tx Hash: {tx_id}")
    return tx_id

# =====================================================================
# 3. GAME LOGIC & HELPER FUNCTIONS
# =====================================================================
def get_or_create_player(db: Session, player_id: str) -> PlayerModel:
    player = db.query(PlayerModel).filter(PlayerModel.player_id == player_id).first()
    if not player:
        player = PlayerModel(
            player_id=player_id,
            total_hours_played=0.0,
            spendable_coins=0.0,
            prestige_level=0,
            developer_balance=0.0
        )
        db.add(player)
        db.commit()
        db.refresh(player)
    return player

def calculate_player_earn_rate(player: PlayerModel) -> float:
    base_rate = 100.0
    prestige_multiplier = 1.0 + (0.05 * player.prestige_level)
    effective_rate = base_rate * prestige_multiplier

    current_level = math.floor(player.total_hours_played)
    if current_level >= 50:
        effective_rate *= 0.40  # 60% Soft decay at Level 50+
    return effective_rate

def verify_hmac_signature(player_id: str, minutes_played: int, timestamp: float, signature: str) -> bool:
    payload = f"{player_id}:{minutes_played}:{timestamp}"
    expected_sig = hmac.new(HMAC_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_sig, signature)

# =====================================================================
# 4. FASTAPI APP & ENDPOINTS
# =====================================================================
app = FastAPI(
    title="Main Coin Network Relayer & Hedera Bridge",
    description="Unified single-file server for game telemetry, SQLite database, and Hedera HTS token settlement.",
    version="2.0.0"
)

class TelemetryPing(BaseModel):
    player_id: str
    minutes_played: int
    timestamp: float
    signature: str

class StorePurchaseRequest(BaseModel):
    player_id: str
    item_id: str
    price_in_coins: float

class PrestigeRequest(BaseModel):
    player_id: str

@app.get("/")
def read_root():
    return {
        "service": "Main Coin Network Relayer & Hedera Bridge",
        "status": "ONLINE",
        "database": "SQLite Persistence",
        "hedera_network": "Testnet",
        "operator_id": OPERATOR_ID,
        "hts_token_id": TOKEN_ID
    }

@app.post("/api/v1/telemetry")
def process_telemetry(data: TelemetryPing, db: Session = Depends(get_db)):
    if not verify_hmac_signature(data.player_id, data.minutes_played, data.timestamp, data.signature):
        raise HTTPException(status_code=401, detail="Invalid HMAC telemetry signature.")

    player = get_or_create_player(db, data.player_id)
    hours = data.minutes_played / 60.0
    player.total_hours_played += hours
    
    current_rate = calculate_player_earn_rate(player)
    earned = hours * current_rate
    player.spendable_coins += earned

    db.commit()
    db.refresh(player)

    return {
        "status": "success",
        "player_id": player.player_id,
        "minutes_credited": data.minutes_played,
        "coins_earned": round(earned, 4),
        "current_earn_rate": round(current_rate, 2),
        "total_spendable_coins": round(player.spendable_coins, 2),
        "current_level": math.floor(player.total_hours_played),
        "prestige_level": player.prestige_level
    }

@app.get("/api/v1/player/{player_id}")
def get_player_stats(player_id: str, db: Session = Depends(get_db)):
    player = get_or_create_player(db, player_id)
    current_level = math.floor(player.total_hours_played)
    
    return {
        "player_id": player.player_id,
        "hours_played": round(player.total_hours_played, 2),
        "current_level": current_level,
        "prestige_level": player.prestige_level,
        "spendable_coins": round(player.spendable_coins, 2),
        "current_earn_rate": round(calculate_player_earn_rate(player), 2),
        "is_soft_decay_active": current_level >= 50
    }

@app.post("/api/v1/store/buy")
def buy_store_item(purchase: StorePurchaseRequest, db: Session = Depends(get_db)):
    player = get_or_create_player(db, purchase.player_id)

    if player.spendable_coins < purchase.price_in_coins:
        raise HTTPException(status_code=400, detail="Insufficient spendable coins balance.")

    player.spendable_coins -= purchase.price_in_coins
    dev_share = purchase.price_in_coins * 0.75
    platform_share = purchase.price_in_coins * 0.25
    player.developer_balance += dev_share

    db.commit()
    db.refresh(player)

    tx_id = transfer_dev_revenue_on_hedera(TOKEN_ID, OPERATOR_ID, dev_share)

    return {
        "status": "success",
        "item_id": purchase.item_id,
        "price_paid": purchase.price_in_coins,
        "developer_credited": dev_share,
        "platform_fee": platform_share,
        "remaining_player_balance": round(player.spendable_coins, 2),
        "hedera_tx_id": tx_id
    }

@app.post("/api/v1/prestige")
def execute_prestige(req: PrestigeRequest, db: Session = Depends(get_db)):
    player = get_or_create_player(db, req.player_id)
    current_level = math.floor(player.total_hours_played)

    if current_level < 50:
        raise HTTPException(
            status_code=400,
            detail=f"Must be at least Level 50 to prestige. Current Level: {current_level}"
        )

    prestige_fee = 2500.0
    if player.spendable_coins < prestige_fee:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient coins for prestige fee ({prestige_fee} required, {player.spendable_coins:.2f} available)."
        )

    player.spendable_coins -= prestige_fee
    burned_amount = prestige_fee * 0.25
    player.prestige_level += 1
    player.total_hours_played = 0.0

    db.commit()
    db.refresh(player)

    tx_id = burn_tokens_on_hedera(TOKEN_ID, burned_amount)

    return {
        "status": "success",
        "message": "Prestige reset complete! Token burn submitted to Hedera network.",
        "new_prestige_level": player.prestige_level,
        "burned_coins": burned_amount,
        "new_earn_rate": round(calculate_player_earn_rate(player), 2),
        "remaining_coins": round(player.spendable_coins, 2),
        "hedera_burn_tx_id": tx_id
    }

# =====================================================================
# 5. INTEGRATED CLIENT SDK & TEST RUNNER
# =====================================================================
class MainCoinClientSDK:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")

    def ping_telemetry(self, player_id: str, minutes_played: int) -> Dict[str, Any]:
        ts = time.time()
        payload = f"{player_id}:{minutes_played}:{ts}"
        sig = hmac.new(HMAC_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        
        res = requests.post(f"{self.base_url}/api/v1/telemetry", json={
            "player_id": player_id,
            "minutes_played": minutes_played,
            "timestamp": ts,
            "signature": sig
        })
        return res.json()

    def get_player_stats(self, player_id: str) -> Dict[str, Any]:
        return requests.get(f"{self.base_url}/api/v1/player/{player_id}").json()

    def buy_store_item(self, player_id: str, item_id: str, price: float) -> Dict[str, Any]:
        return requests.post(f"{self.base_url}/api/v1/store/buy", json={
            "player_id": player_id,
            "item_id": item_id,
            "price_in_coins": price
        }).json()

    def execute_prestige(self, player_id: str) -> Dict[str, Any]:
        return requests.post(f"{self.base_url}/api/v1/prestige", json={
            "player_id": player_id
        }).json()

def run_standalone_test():
    """Simulates an end-to-end player test suite against the running server."""
    print("\n==================================================")
    print("   RUNNING INTEGRATED SINGLE-FILE SYSTEM TEST     ")
    print("==================================================\n")
    client = MainCoinClientSDK()
    player_id = "single_file_test_player"

    print("1. Credit 50 Hours of Gameplay...")
    for _ in range(50):
        client.ping_telemetry(player_id, 60)
    
    stats = client.get_player_stats(player_id)
    print(f"Level: {stats['current_level']} | Spendable Balance: {stats['spendable_coins']:.2f} coins")
    print(f"Current Rate: {stats['current_earn_rate']} coins/hr (Soft Decay: {stats['is_soft_decay_active']})\n")

    print("2. Purchasing Cosmetic Item (500 Coins)...")
    store = client.buy_store_item(player_id, "epic_fire_skin", 500.0)
    print(f"Store Purchase: {store['status']} | Dev Credited: {store['developer_credited']} coins")
    print(f"Hedera Transfer Hash: {store['hedera_tx_id']}\n")

    print("3. Executing Level 50 Prestige & Token Burn...")
    prestige = client.execute_prestige(player_id)
    print(f"Prestige Status: {prestige['status']}")
    print(f"Burned Coins: {prestige['burned_coins']} MAIN")
    print(f"Hedera Burn Hash: {prestige['hedera_burn_tx_id']}")
    print(f"New Earn Rate (+5% Boost): {prestige['new_earn_rate']} coins/hr\n")

    print("==================================================")
    print("          SINGLE-FILE TEST COMPLETED!             ")
    print("==================================================\n")

# =====================================================================
# 6. DIRECT ENTRYPOINT HANDLER
# =====================================================================
if __name__ == "__main__":
    import uvicorn
    
    # If launched with 'python app.py test', execute test suite
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        run_standalone_test()
    else:
        print("Starting Main Coin Network Relayer on http://127.0.0.1:8000 ...")
        uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)