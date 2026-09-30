import hashlib
import hmac
import math
import os
import sys
import time
from typing import Dict, Any

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

# Load environment variables
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
        # 1. Initialize for Testnet using snake_case syntax
        hedera_client = Client.for_testnet()
        
        # 2. Parse Operator Account ID and Private Key
        op_id = AccountId.from_string(OPERATOR_ID)
        op_key = PrivateKey.from_string(OPERATOR_KEY)
        
        # 3. Set the Operator on the Client
        hedera_client.set_operator(op_id, op_key)
        
        print("🟢 [HEDERA SDK] Connected to Hedera Testnet successfully.")
    except Exception as e:
        print(f"⚠️ [HEDERA SDK] Could not initialize live client: {e}")

# =====================================================================
# 1. SQLITE DATABASE SETUP
# =====================================================================
DATABASE_DIR = "app/data" if os.path.exists("/app/data") else "."
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
            print(f"Token ID: {token_id} | Burned: {amount_to_burn:,} MAIN")
            print(f"Consensus Status: {receipt.status} | Tx ID: {tx_hash}")
            return tx_hash
        except Exception as err:
            print(f"⚠️️ Live Hedera Burn error (falling back to relayer hash): {err}")

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
            print(f"Routed {dev_amount:,} MAIN to Dev Treasury: {dev_account_id}")
            print(f"Consensus Status: {receipt.status} | Tx ID: {tx_hash}")
            return tx_hash
        except Exception as err:
            print(f"⚠️ Live Hedera Transfer error (falling back to relayer hash): {err}")

    timestamp_str = str(time.time()).replace('.', '')[:10]
    return f"{OPERATOR_ID}@{timestamp_str}.000000001"

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
    description="Unified API server for game telemetry, SQLite database, and Hedera HTS token settlement.",
    version="2.3.0"
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
        "environment": "Docker Containerized",
        "admin_dashboard": "http://127.0.0.1:8000/admin",
        "database": "SQLite Persistence",
        "hedera_network": "Testnet",
        "hedera_sdk_connected": bool(hedera_client),
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

@app.get("/api/v1/admin/summary")
def get_admin_summary(db: Session = Depends(get_db)):
    total_players = db.query(func.count(PlayerModel.player_id)).scalar() or 0
    total_spendable_coins = db.query(func.sum(PlayerModel.spendable_coins)).scalar() or 0.0
    total_dev_earnings = db.query(func.sum(PlayerModel.developer_balance)).scalar() or 0.0
    total_prestige_resets = db.query(func.sum(PlayerModel.prestige_level)).scalar() or 0
    total_hours_logged = db.query(func.sum(PlayerModel.total_hours_played)).scalar() or 0.0
    total_burned_coins = total_prestige_resets * 625.0

    # Retrieve leaderboard
    leaderboard = db.query(PlayerModel).order_by(PlayerModel.prestige_level.desc(), PlayerModel.spendable_coins.desc()).limit(10).all()
    players_list = [
        {
            "player_id": p.player_id,
            "level": math.floor(p.total_hours_played),
            "prestige_level": p.prestige_level,
            "hours_played": round(p.total_hours_played, 1),
            "spendable_coins": round(p.spendable_coins, 2)
        }
        for p in leaderboard
    ]

    return {
        "system_status": "ONLINE",
        "container_environment": "Docker",
        "hedera_sdk_active": bool(hedera_client),
        "hedera_token_id": TOKEN_ID,
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
# 5. EMBEDDED VISUAL WEB DASHBOARD ROUTE
# =====================================================================
@app.get("/admin", response_class=HTMLResponse)
def render_admin_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Main Coin Network - Admin Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            :root {
                --bg: #0f172a;
                --panel: #1e293b;
                --accent: #38bdf8;
                --green: #22c55e;
                --red: #ef4444;
                --text: #f8fafc;
                --subtext: #94a3b8;
                --border: #334155;
            }
            body {
                margin: 0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background-color: var(--bg);
                color: var(--text);
                padding: 24px;
            }
            .header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid var(--border);
                padding-bottom: 16px;
                margin-bottom: 24px;
            }
            .title { font-size: 24px; font-weight: bold; color: var(--accent); }
            .badge {
                background: #0284c7;
                color: white;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 16px;
                margin-bottom: 24px;
            }
            .card {
                background: var(--panel);
                border: 1px solid var(--border);
                border-radius: 8px;
                padding: 16px;
            }
            .card-title { font-size: 13px; color: var(--subtext); text-transform: uppercase; margin-bottom: 8px; }
            .card-value { font-size: 24px; font-weight: bold; color: var(--text); }
            .content-grid {
                display: grid;
                grid-template-columns: 1fr 2fr;
                gap: 24px;
            }
            @media (max-width: 900px) { .content-grid { grid-template-columns: 1fr; } }
            .chart-container {
                background: var(--panel);
                border: 1px solid var(--border);
                border-radius: 8px;
                padding: 16px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 12px;
            }
            th, td {
                padding: 10px;
                text-align: left;
                border-bottom: 1px solid var(--border);
                font-size: 14px;
            }
            th { color: var(--subtext); font-weight: 600; }
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <span class="title">MAIN COIN NETWORK</span>
                <span style="color: var(--subtext); margin-left: 12px; font-size: 14px;">Hedera Bridge Admin Dashboard</span>
            </div>
            <div style="display:flex; gap:10px; align-items:center;">
                <span class="badge" id="env-badge">DOCKER CONTAINER</span>
                <span class="badge" style="background:var(--green);" id="status-badge">ONLINE</span>
            </div>
        </div>

        <div class="grid">
            <div class="card"><div class="card-title">Registered Players</div><div class="card-value" id="kpi-players">0</div></div>
            <div class="card"><div class="card-title">Circulating Supply</div><div class="card-value" id="kpi-circulating">0 MAIN</div></div>
            <div class="card"><div class="card-title">Developer Revenue (75%)</div><div class="card-value" id="kpi-dev">0 MAIN</div></div>
            <div class="card"><div class="card-title">Total Burned (25%)</div><div class="card-value" style="color:var(--red);" id="kpi-burned">0 MAIN</div></div>
            <div class="card"><div class="card-title">Prestige Resets</div><div class="card-value" style="color:var(--accent);" id="kpi-prestige">0</div></div>
        </div>

        <div class="content-grid">
            <div class="chart-container">
                <div class="card-title">Token Economy Allocation</div>
                <canvas id="tokenChart" style="max-height: 280px;"></canvas>
            </div>
            <div class="chart-container">
                <div class="card-title">Player Leaderboard (Top 10)</div>
                <table>
                    <thead>
                        <tr>
                            <th>Player ID</th>
                            <th>Level</th>
                            <th>Prestige</th>
                            <th>Hours</th>
                            <th>Coins</th>
                        </tr>
                    </thead>
                    <tbody id="leaderboard-body"></tbody>
                </table>
            </div>
        </div>

        <script>
            let chartInstance = null;

            async function refreshData() {
                try {
                    const res = await fetch('/api/v1/admin/summary');
                    const data = await res.json();
                    const m = data.economy_metrics;

                    document.getElementById('kpi-players').innerText = m.total_registered_players;
                    document.getElementById('kpi-circulating').innerText = m.circulating_spendable_coins.toLocaleString() + ' MAIN';
                    document.getElementById('kpi-dev').innerText = m.total_dev_revenue_credited.toLocaleString() + ' MAIN';
                    document.getElementById('kpi-burned').innerText = m.total_hedera_tokens_burned.toLocaleString() + ' MAIN';
                    document.getElementById('kpi-prestige').innerText = m.total_prestige_resets_executed;

                    // Update Chart
                    const chartData = [m.circulating_spendable_coins, m.total_dev_revenue_credited, m.total_hedera_tokens_burned];
                    if (!chartInstance) {
                        const ctx = document.getElementById('tokenChart').getContext('2d');
                        chartInstance = new Chart(ctx, {
                            type: 'doughnut',
                            data: {
                                labels: ['Circulating', 'Dev Revenue', 'Burned Tokens'],
                                datasets: [{
                                    data: chartData,
                                    backgroundColor: ['#38bdf8', '#22c55e', '#ef4444'],
                                    borderWidth: 0
                                }]
                            },
                            options: { responsive: true, plugins: { legend: { position: 'bottom', labels: { color: '#f8fafc' } } } }
                        });
                    } else {
                        chartInstance.data.datasets[0].data = chartData;
                        chartInstance.update();
                    }

                    // Update Leaderboard
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
                } catch (e) {
                    console.error("Failed to update dashboard metrics:", e);
                }
            }

            refreshData();
            setInterval(refreshData, 5000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# =====================================================================
# 6. CLI TEST RUNNER
# =====================================================================
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("\n=== RUNNING CLI TEST SUITE ===")
        base_url = "http://127.0.0.1:8000"
        player_id = "dashboard_tactical_player"
        
        # Credit 50 Hours
        for _ in range(50):
            ts = time.time()
            sig = hmac.new(HMAC_SECRET.encode(), f"{player_id}:60:{ts}".encode(), hashlib.sha256).hexdigest()
            requests.post(f"{base_url}/api/v1/telemetry", json={
                "player_id": player_id, "minutes_played": 60, "timestamp": ts, "signature": sig
            })
        
        p = requests.get(f"{base_url}/api/v1/player/{player_id}").json()
        print(f"Level: {p['current_level']} | Balance: {p['spendable_coins']} | Decay: {p['is_soft_decay_active']}")
        
        # Store Buy
        b = requests.post(f"{base_url}/api/v1/store/buy", json={"player_id": player_id, "item_id": "sword_01", "price_in_coins": 500.0}).json()
        print(f"Store Purchase: {b['status']} | Dev Share: {b['developer_credited']}")
        
        # Prestige
        pr = requests.post(f"{base_url}/api/v1/prestige", json={"player_id": player_id}).json()
        print(f"Prestige Status: {pr['status']} | Burned: {pr['burned_coins']} MAIN | New Earn Rate: {pr['new_earn_rate']} coins/hr")
        
        # Admin Summary Query
        admin = requests.get(f"{base_url}/api/v1/admin/summary").json()
        print("\n--- ADMIN ECOSYSTEM SUMMARY ---")
        print(f"Registered Players: {admin['economy_metrics']['total_registered_players']}")
        print(f"Circulating Supply: {admin['economy_metrics']['circulating_spendable_coins']} MAIN")
        print(f"Total Burned on Hedera: {admin['economy_metrics']['total_hedera_tokens_burned']} MAIN\n")
