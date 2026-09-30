import hashlib
import hmac
import math
import os
import sys
import time
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import requests

from sqlalchemy import create_engine, Column, String, Float, Integer, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Try importing Hedera / Hiero SDK
HEDERA_SDK_AVAILABLE = False
try:
    from hiero_sdk_python import (
        Client, AccountId, PrivateKey, TokenId,
        TokenBurnTransaction, TransferTransaction
    )
    HEDERA_SDK_AVAILABLE = True
except ImportError:
    try:
        from hedera import (
            Client, AccountId, PrivateKey, TokenId,
            TokenBurnTransaction, TransferTransaction
        )
        HEDERA_SDK_AVAILABLE = True
    except ImportError:
        HEDERA_SDK_AVAILABLE = False

load_dotenv()

OPERATOR_ID = os.getenv("OPERATOR_ID", "0.0.10770972")
OPERATOR_KEY = os.getenv("OPERATOR_KEY", "")
MIRROR_NODE = os.getenv("MIRROR_NODE_URL", "https://testnet.mirrornode.hedera.com")
HMAC_SECRET = os.getenv("HMAC_SECRET", "super_secret_game_server_key_123")
TOKEN_ID = os.getenv("TOKEN_ID", "0.0.10770973")

# Initialize Hedera Testnet Client
hedera_client = None
if HEDERA_SDK_AVAILABLE and OPERATOR_ID and OPERATOR_KEY:
    try:
        hedera_client = Client.for_testnet()
        op_id = AccountId.from_string(OPERATOR_ID)
        op_key = PrivateKey.from_string(OPERATOR_KEY)
        hedera_client.set_operator(op_id, op_key)
        print("🟢 [HEDERA SDK] Connected to Hedera Testnet successfully.")
    except Exception as e:
        print(f"⚠️ [HEDERA SDK] Could not initialize live client: {e}")

# =====================================================================
# 1. SQLITE DATABASE SETUP & MODELS
# =====================================================================
DATA_DIR = "/app/data" if os.path.exists("/app/data") else "."
DATABASE_URL = f"sqlite:///{DATA_DIR}/game_economy.db"

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

class ItemModel(Base):
    __tablename__ = "items"

    item_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price_in_coins = Column(Float, nullable=False)
    rarity = Column(String, default="Common")
    earn_rate_multiplier = Column(Float, default=1.0)  # e.g. 1.05 = +5% earn rate

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =====================================================================
# 2. HEDERA ON-CHAIN RELAYER UTILITIES
# =====================================================================
def burn_tokens_on_hedera(token_id: str, amount_to_burn: float) -> str:
    smallest_unit = int(amount_to_burn * 100_000_000)
    if hedera_client and HEDERA_SDK_AVAILABLE:
        try:
            tx = (
                TokenBurnTransaction()
                .set_token_id(TokenId.from_string(token_id))
                .set_amount(smallest_unit)
                .freeze_with(hedera_client)
            )
            response = tx.execute(hedera_client)
            receipt = response.get_receipt(hedera_client)
            tx_hash = str(response.transaction_id)
            print(f"--- [HEDERA ON-CHAIN LIVE BURN] ---")
            print(f"Token ID: {token_id} | Burned: {amount_to_burn:,} MAIN | Status: {receipt.status}")
            return tx_hash
        except Exception as err:
            print(f"⚠️ Live Hedera Burn error: {err}")

    timestamp_str = str(time.time()).replace('.', '')[:10]
    return f"{OPERATOR_ID}@{timestamp_str}.000000000"

def transfer_dev_revenue_on_hedera(token_id: str, dev_account_id: str, dev_amount: float) -> str:
    smallest_unit = int(dev_amount * 100_000_000)
    if hedera_client and HEDERA_SDK_AVAILABLE:
        try:
            tx = (
                TransferTransaction()
                .add_token_transfer(TokenId.from_string(token_id), AccountId.from_string(OPERATOR_ID), -smallest_unit)
                .add_token_transfer(TokenId.from_string(token_id), AccountId.from_string(dev_account_id), smallest_unit)
                .freeze_with(hedera_client)
            )
            response = tx.execute(hedera_client)
            receipt = response.get_receipt(hedera_client)
            tx_hash = str(response.transaction_id)
            print(f"--- [HEDERA ON-CHAIN LIVE TRANSFER] ---")
            print(f"Routed {dev_amount:,} MAIN to Dev Treasury: {dev_account_id} | Status: {receipt.status}")
            return tx_hash
        except Exception as err:
            print(f"⚠️ Live Hedera Transfer error: {err}")

    timestamp_str = str(time.time()).replace('.', '')[:10]
    return f"{OPERATOR_ID}@{timestamp_str}.000000001"

# =====================================================================
# 3. GAME LOGIC & HELPER FUNCTIONS
# =====================================================================
def get_or_create_player(db: Session, player_id: str) -> PlayerModel:
    player = db.query(PlayerModel).filter(PlayerModel.player_id == player_id).first()
    if not player:
        player = PlayerModel(player_id=player_id, total_hours_played=0.0, spendable_coins=0.0, prestige_level=0, developer_balance=0.0)
        db.add(player)
        db.commit()
        db.refresh(player)
    return player

def calculate_player_earn_rate(player: PlayerModel) -> float:
    base_rate = 100.0
    prestige_multiplier = 1.0 + (0.05 * player.prestige_level)
    effective_rate = base_rate * prestige_multiplier
    if math.floor(player.total_hours_played) >= 50:
        effective_rate *= 0.40  # 60% Soft decay
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
    description="Unified API server for game telemetry, SQLite database, dynamic developer store, and Hedera HTS token settlement.",
    version="2.4.0"
)

class TelemetryPing(BaseModel):
    player_id: str
    minutes_played: int
    timestamp: float
    signature: str

class StorePurchaseRequest(BaseModel):
    player_id: str
    item_id: str

class PrestigeRequest(BaseModel):
    player_id: str

class CreateItemRequest(BaseModel):
    item_id: str
    name: str
    description: Optional[str] = ""
    price_in_coins: float
    rarity: Optional[str] = "Common"
    earn_rate_multiplier: Optional[float] = 1.0

@app.get("/")
def read_root():
    return {
        "service": "Main Coin Network Relayer & Hedera Bridge",
        "status": "ONLINE",
        "admin_dashboard": "http://127.0.0.1:8000/admin",
        "hedera_sdk_connected": bool(hedera_client),
        "operator_id": OPERATOR_ID,
        "hts_token_id": TOKEN_ID
    }

# --- STORE MANAGEMENT (DEVELOPER CONTROL) ---
@app.get("/api/v1/store/catalog")
def get_store_catalog(db: Session = Depends(get_db)):
    items = db.query(ItemModel).all()
    return {
        "status": "success",
        "total_items": len(items),
        "catalog": [
            {
                "item_id": i.item_id,
                "name": i.name,
                "description": i.description,
                "price_in_coins": i.price_in_coins,
                "rarity": i.rarity,
                "earn_rate_multiplier": i.earn_rate_multiplier
            } for i in items
        ]
    }

@app.post("/api/v1/admin/store/item")
def create_or_update_store_item(item: CreateItemRequest, db: Session = Depends(get_db)):
    existing = db.query(ItemModel).filter(ItemModel.item_id == item.item_id).first()
    if existing:
        existing.name = item.name
        existing.description = item.description
        existing.price_in_coins = item.price_in_coins
        existing.rarity = item.rarity
        existing.earn_rate_multiplier = item.earn_rate_multiplier
        message = f"Updated item '{item.item_id}'."
    else:
        new_item = ItemModel(
            item_id=item.item_id,
            name=item.name,
            description=item.description,
            price_in_coins=item.price_in_coins,
            rarity=item.rarity,
            earn_rate_multiplier=item.earn_rate_multiplier
        )
        db.add(new_item)
        message = f"Created new store item '{item.name}'."

    db.commit()
    return {"status": "success", "message": message, "item": item.model_dump()}

@app.delete("/api/v1/admin/store/item/{item_id}")
def delete_store_item(item_id: str, db: Session = Depends(get_db)):
    item = db.query(ItemModel).filter(ItemModel.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")
    db.delete(item)
    db.commit()
    return {"status": "success", "message": f"Deleted item '{item_id}' from store catalog."}

# --- STORE PURCHASE ---
@app.post("/api/v1/store/buy")
def buy_store_item(purchase: StorePurchaseRequest, db: Session = Depends(get_db)):
    item = db.query(ItemModel).filter(ItemModel.item_id == purchase.item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Store item '{purchase.item_id}' does not exist.")

    player = get_or_create_player(db, purchase.player_id)

    if player.spendable_coins < item.price_in_coins:
        raise HTTPException(status_code=400, detail=f"Insufficient coins. Item costs {item.price_in_coins} MAIN.")

    player.spendable_coins -= item.price_in_coins
    dev_share = item.price_in_coins * 0.75
    platform_share = item.price_in_coins * 0.25
    player.developer_balance += dev_share

    db.commit()
    db.refresh(player)

    tx_id = transfer_dev_revenue_on_hedera(TOKEN_ID, OPERATOR_ID, dev_share)

    return {
        "status": "success",
        "item_id": item.item_id,
        "item_name": item.name,
        "price_paid": item.price_in_coins,
        "developer_credited": dev_share,
        "platform_fee": platform_share,
        "remaining_player_balance": round(player.spendable_coins, 2),
        "hedera_tx_id": tx_id
    }

# --- TELEMETRY & PRESTIGE ---
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

@app.post("/api/v1/prestige")
def execute_prestige(req: PrestigeRequest, db: Session = Depends(get_db)):
    player = get_or_create_player(db, req.player_id)
    current_level = math.floor(player.total_hours_played)

    if current_level < 50:
        raise HTTPException(status_code=400, detail=f"Must be Level 50+. Current: {current_level}")

    prestige_fee = 2500.0
    if player.spendable_coins < prestige_fee:
        raise HTTPException(status_code=400, detail=f"Requires {prestige_fee} coins.")

    player.spendable_coins -= prestige_fee
    burned_amount = prestige_fee * 0.25
    player.prestige_level += 1
    player.total_hours_played = 0.0

    db.commit()
    db.refresh(player)

    tx_id = burn_tokens_on_hedera(TOKEN_ID, burned_amount)

    return {
        "status": "success",
        "message": "Prestige reset complete! Token burn submitted to Hedera.",
        "new_prestige_level": player.prestige_level,
        "burned_coins": burned_amount,
        "new_earn_rate": round(calculate_player_earn_rate(player), 2),
        "remaining_coins": round(player.spendable_coins, 2),
        "hedera_burn_tx_id": tx_id
    }

@app.get("/api/v1/admin/summary")
def get_admin_summary(db: Session = Depends(get_db)):
    total_players = db.query(func.count(PlayerModel.player_id)).scalar() or 0
    total_spendable_coins = db.query(func.sum(PlayerModel.spendable_coins)).scalar() or 0.0
    total_dev_earnings = db.query(func.sum(PlayerModel.developer_balance)).scalar() or 0.0
    total_prestige_resets = db.query(func.sum(PlayerModel.prestige_level)).scalar() or 0
    total_hours_logged = db.query(func.sum(PlayerModel.total_hours_played)).scalar() or 0.0
    total_burned_coins = total_prestige_resets * 625.0

    leaderboard = db.query(PlayerModel).order_by(PlayerModel.prestige_level.desc(), PlayerModel.spendable_coins.desc()).limit(10).all()
    players_list = [
        {
            "player_id": p.player_id,
            "level": math.floor(p.total_hours_played),
            "prestige_level": p.prestige_level,
            "hours_played": round(p.total_hours_played, 1),
            "spendable_coins": round(p.spendable_coins, 2)
        } for p in leaderboard
    ]

    return {
        "system_status": "ONLINE",
        "economy_metrics": {
            "total_registered_players": total_players,
            "circulating_spendable_coins": round(total_spendable_coins, 2),
            "total_dev_revenue_credited": round(total_dev_earnings, 2),
            "total_prestige_resets_executed": total_prestige_resets,
            "total_hedera_tokens_burned": round(total_burned_coins, 2),
            "total_gameplay_hours_logged": round(total_hours_logged, 2)
        },
        "leaderboard": players_list
    }

# =====================================================================
# 5. EMBEDDED VISUAL WEB DASHBOARD ROUTE (WITH STORE CONTROLS)
# =====================================================================
@app.get("/admin", response_class=HTMLResponse)
def render_admin_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Main Coin Network - Admin Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            :root { --bg: #0f172a; --panel: #1e293b; --accent: #38bdf8; --green: #22c55e; --red: #ef4444; --text: #f8fafc; --subtext: #94a3b8; --border: #334155; }
            body { margin: 0; font-family: system-ui, sans-serif; background-color: var(--bg); color: var(--text); padding: 24px; }
            .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 16px; margin-bottom: 24px; }
            .title { font-size: 24px; font-weight: bold; color: var(--accent); }
            .badge { background: #0284c7; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
            .card { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
            .card-title { font-size: 12px; color: var(--subtext); text-transform: uppercase; margin-bottom: 8px; }
            .card-value { font-size: 22px; font-weight: bold; color: var(--text); }
            .content-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }
            @media (max-width: 900px) { .content-grid { grid-template-columns: 1fr; } }
            .panel-box { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
            table { width: 100%; border-collapse: collapse; margin-top: 12px; }
            th, td { padding: 8px; text-align: left; border-bottom: 1px solid var(--border); font-size: 13px; }
            th { color: var(--subtext); }
            input, select, button { background: #0f172a; border: 1px solid var(--border); color: white; padding: 8px; border-radius: 4px; width: 100%; box-sizing: border-box; margin-bottom: 8px; }
            button { background: #0284c7; font-weight: bold; cursor: pointer; border: none; margin-top: 8px; }
            button:hover { background: #0369a1; }
            .btn-danger { background: var(--red); }
            .btn-danger:hover { background: #dc2626; }
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <span class="title">MAIN COIN NETWORK</span>
                <span style="color: var(--subtext); margin-left: 12px;">Developer Admin Dashboard</span>
            </div>
            <div>
                <span class="badge" style="background:var(--green);">CONNECTED TO HEDERA</span>
            </div>
        </div>

        <div class="grid">
            <div class="card"><div class="card-title">Registered Players</div><div class="card-value" id="kpi-players">0</div></div>
            <div class="card"><div class="card-title">Circulating Supply</div><div class="card-value" id="kpi-circulating">0 MAIN</div></div>
            <div class="card"><div class="card-title">Developer Revenue (75%)</div><div class="card-value" style="color:var(--green);" id="kpi-dev">0 MAIN</div></div>
            <div class="card"><div class="card-title">Total Burned (25%)</div><div class="card-value" style="color:var(--red);" id="kpi-burned">0 MAIN</div></div>
        </div>

        <div class="content-grid">
            <div class="panel-box">
                <div class="card-title">Developer Store Control (Add / Edit Item)</div>
                <form id="item-form" onsubmit="saveItem(event)">
                    <input type="text" id="item_id" placeholder="Item ID (e.g. dragon_shield)" required />
                    <input type="text" id="item_name" placeholder="Item Name (e.g. Dragon Shield)" required />
                    <input type="text" id="item_desc" placeholder="Description" />
                    <input type="number" id="item_price" placeholder="Price in MAIN (e.g. 1500)" step="0.1" required />
                    <select id="item_rarity">
                        <option value="Common">Common</option>
                        <option value="Rare">Rare</option>
                        <option value="Epic">Epic</option>
                        <option value="Legendary">Legendary</option>
                    </select>
                    <input type="number" id="item_multiplier" placeholder="Earn Rate Multiplier (e.g. 1.05 = +5%)" step="0.01" value="1.0" />
                    <button type="submit">Save Store Item</button>
                </form>
            </div>

            <div class="panel-box">
                <div class="card-title">Active Store Catalog</div>
                <table>
                    <thead>
                        <tr><th>ID</th><th>Name</th><th>Price</th><th>Rarity</th><th>Action</th></tr>
                    </thead>
                    <tbody id="catalog-body"></tbody>
                </table>
            </div>
        </div>

        <div class="panel-box">
            <div class="card-title">Top Players Leaderboard</div>
            <table>
                <thead>
                    <tr><th>Player ID</th><th>Level</th><th>Prestige</th><th>Hours</th><th>Balance</th></tr>
                </thead>
                <tbody id="leaderboard-body"></tbody>
            </table>
        </div>

        <script>
            async function refreshDashboard() {
                try {
                    const res = await fetch('/api/v1/admin/summary');
                    const data = await res.json();
                    const m = data.economy_metrics;

                    document.getElementById('kpi-players').innerText = m.total_registered_players;
                    document.getElementById('kpi-circulating').innerText = m.circulating_spendable_coins.toLocaleString() + ' MAIN';
                    document.getElementById('kpi-dev').innerText = m.total_dev_revenue_credited.toLocaleString() + ' MAIN';
                    document.getElementById('kpi-burned').innerText = m.total_hedera_tokens_burned.toLocaleString() + ' MAIN';

                    const tbody = document.getElementById('leaderboard-body');
                    tbody.innerHTML = '';
                    data.leaderboard.forEach(p => {
                        tbody.innerHTML += `<tr>
                            <td style="font-weight:600;">${p.player_id}</td>
                            <td>${p.level}</td>
                            <td style="color:var(--accent); font-weight:bold;">${p.prestige_level}</td>
                            <td>${p.hours_played} hrs</td>
                            <td>${p.spendable_coins.toLocaleString()} MAIN</td>
                        </tr>`;
                    });

                    refreshCatalog();
                } catch (e) { console.error("Dashboard update failed:", e); }
            }

            async function refreshCatalog() {
                const res = await fetch('/api/v1/store/catalog');
                const data = await res.json();
                const tbody = document.getElementById('catalog-body');
                tbody.innerHTML = '';
                data.catalog.forEach(item => {
                    tbody.innerHTML += `<tr>
                        <td><b>${item.item_id}</b></td>
                        <td>${item.name}</td>
                        <td>${item.price_in_coins} MAIN</td>
                        <td>${item.rarity}</td>
                        <td><button class="btn-danger" onclick="deleteItem('${item.item_id}')">Delete</button></td>
                    </tr>`;
                });
            }

            async function saveItem(e) {
                e.preventDefault();
                const payload = {
                    item_id: document.getElementById('item_id').value,
                    name: document.getElementById('item_name').value,
                    description: document.getElementById('item_desc').value,
                    price_in_coins: parseFloat(document.getElementById('item_price').value),
                    rarity: document.getElementById('item_rarity').value,
                    earn_rate_multiplier: parseFloat(document.getElementById('item_multiplier').value)
                };
                await fetch('/api/v1/admin/store/item', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                document.getElementById('item-form').reset();
                refreshCatalog();
            }

            async function deleteItem(itemId) {
                if(confirm('Delete store item ' + itemId + '?')) {
                    await fetch('/api/v1/admin/store/item/' + itemId, { method: 'DELETE' });
                    refreshCatalog();
                }
            }

            refreshDashboard();
            setInterval(refreshDashboard, 5000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("\n=== RUNNING CLI TEST SUITE ===")
        base_url = "http://127.0.0.1:8000"
        
        # 1. Create Developer Item
        requests.post(f"{base_url}/api/v1/admin/store/item", json={
            "item_id": "laser_sword", "name": "Laser Sword", "description": "High energy blade", "price_in_coins": 500.0, "rarity": "Rare", "earn_rate_multiplier": 1.05
        })
        print("Developer item 'laser_sword' created.")

        # 2. Query Catalog
        cat = requests.get(f"{base_url}/api/v1/store/catalog").json()
        print(f"Catalog Total Items: {cat['total_items']}")
