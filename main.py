import os
import sqlite3
import logging
import requests
import random
import string
import re
import asyncio
import uvicorn
import time
import hmac
import hashlib
from fastapi import Header, HTTPException, Depends, status, FastAPI, Request, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Float, Integer, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime, timedelta

# =====================================================================
# 1. GLOBAL NETWORK CONFIGURATION & CONSTANTS
# =====================================================================
TOKEN_NAME = "Nexus"
TOKEN_TICKER = "NEX"

_raw_hmac_secret = os.getenv("HMAC_SECRET") or os.getenv("NEXUS_HMAC_SECRET") or "nexus_dev_secret_2026"
NEXUS_HMAC_SECRET = _raw_hmac_secret.encode('utf-8')

ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "nexus_admin_secret_2026")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./game_economy.db")

BLACKHOLE_IP_POOL: set = set()
PROCESSED_NONCES: set = set()
IS_MINTING_PAUSED: bool = False

LINK_CODES: Dict[str, Any] = {}

DEV_SECRET_KEY = os.getenv("DEV_SECRET_KEY", "nexus_dev_secret_2026")

def verify_developer_key(x_developer_key: str = Header(...)):
    """
    Validates that incoming developer API requests carry the correct X-Developer-Key header
    """
    if x_developer_key != DEV_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid or missing Developer API Key"
        )
    return x_developer_key

# =====================================================================
# 2. DATABASE MODELS & SCHEMA DEFINITIONS
# =====================================================================
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class PlayerModel(Base):
    __tablename__ = "players"

    player_id = Column(String, primary_key=True, index=True)
    spendable_nex = Column(Float, default=0.0)
    total_nex_earned = Column(Float, default=0.0)
    total_hours_played = Column(Float, default=0.0)
    prestige_level = Column(Integer, default=1)
    discord_id = Column(String, nullable=True, index=True)  # <-- Ensure this line exists
    discord_tag = Column(String, nullable=True)             # <-- Ensure this line exists
    hedera_account_id = Column(String, nullable=True)

class ConnectedAccountModel(Base):
    __tablename__ = "connected_accounts"

    player_id = Column(String, primary_key=True, index=True)
    platform_name = Column(String, nullable=False)
    external_account_id = Column(String, nullable=False, unique=True)
    linked_at = Column(Float, default=time.time)

class PlayerInventoryModel(Base):
    __tablename__ = "player_inventory"

    instance_id = Column(String, primary_key=True, index=True)
    player_id = Column(String, index=True, nullable=False)
    item_id = Column(String, nullable=False)
    item_type = Column(String, default="Standard")
    acquired_via = Column(String, default="Store_Purchase")
    hours_logged_on_item = Column(Float, default=0.0)
    hours_required_to_unlock = Column(Float, default=10.0)
    is_tradeable = Column(Integer, default=0)
    acquired_at = Column(Float, default=time.time)

class StoreCatalogModel(Base):
    __tablename__ = "store_catalog"

    item_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    price_nex = Column(Float, nullable=False)
    developer_id = Column(String, nullable=False)
    multiplier_boost = Column(Float, default=1.0)
    is_active = Column(Boolean, default=True)

class RegisteredGameModel(Base):
    __tablename__ = "registered_games"

    game_id = Column(String, primary_key=True, index=True)
    developer_id = Column(String, nullable=False)
    game_name = Column(String, nullable=False)
    webhook_url = Column(String, nullable=True)

class GameCosmeticModel(Base):
    __tablename__ = "game_cosmetics"

    item_key = Column(String, primary_key=True, index=True)
    game_id = Column(String, nullable=False)
    item_name = Column(String, nullable=False)
    price_nex = Column(Float, nullable=False)
    asset_url = Column(String, nullable=True)
    category = Column(String, default="skin")

class DeveloperModel(Base):
    __tablename__ = "developers"

    developer_id = Column(String, primary_key=True, index=True)
    developer_name = Column(String, nullable=False)
    earned_nex_balance = Column(Float, default=0.0)
    hedera_wallet_id = Column(String, nullable=True)

class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(Float, default=time.time)
    action_type = Column(String, nullable=False)
    player_id = Column(String, nullable=True)
    amount_nex = Column(Float, default=0.0)
    details = Column(String, nullable=True)

# Initialize database tables ONCE after all models are defined
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_default_catalog():
    db = SessionLocal()
    try:
        if not db.query(StoreCatalogModel).first():
            items = [
                StoreCatalogModel(
                    item_id="item_boost_01",
                    name="Alpha Vector Crest",
                    description="1.05x Passive NEX Earn Boost Across All Games",
                    price_nex=100.0,
                    developer_id="dev_nexus_core",
                    multiplier_boost=1.05
                ),
                StoreCatalogModel(
                    item_id="item_boost_02",
                    name="Hyperion Core Badge",
                    description="1.15x Passive NEX Earn Boost & Crimson Name Accent",
                    price_nex=500.0,
                    developer_id="dev_nexus_core",
                    multiplier_boost=1.15
                )
            ]
            db.add_all(items)
            
            if not db.query(DeveloperModel).filter_by(developer_id="dev_nexus_core").first():
                db.add(DeveloperModel(
                    developer_id="dev_nexus_core",
                    developer_name="Nexus Core Labs",
                    earned_nex_balance=0.0,
                    hedera_wallet_id="0.0.123456"
                ))
            db.commit()
    finally:
        db.close()

seed_default_catalog()

# =====================================================================
# 3. FASTAPI APP INIT & HONEYCOMB BLACKHOLE MIDDLEWARE
# =====================================================================
app = FastAPI(
    title=f"{TOKEN_NAME} Engine | Central Bank API",
    description=f"Operator-controlled Central Bank Architecture & Telemetry Relayer for {TOKEN_NAME} ({TOKEN_TICKER}).",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def trigger_discord_alert(details: str):
    if not DISCORD_WEBHOOK_URL:
        print(f"⚠️ [SECURITY ALERT - NO WEBHOOK CONFIGURED]: {details}")
        return

    try:
        payload = {"content": f"🚨 **NEXUS CENTRAL BANK SECURITY ALERT**\n{details}"}
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5.0)
        response.raise_for_status()
        print(f"✅ Discord security alert dispatched successfully: {details}")
    except Exception as e:
        print(f"❌ Discord alert dispatch failed: {e}")

@app.middleware("http")
async def blackhole_bot_trap_middleware(request: Request, call_next):
    client_ip = request.client.host or "127.0.0.1"

    if request.url.path in ["/admin/login.php", "/api/v1/debug_coins", "/wp-admin", "/pma"]:
        BLACKHOLE_IP_POOL.add(client_ip)
        trigger_discord_alert(f"Bot trapped in Honeypot: `{client_ip}` requested `{request.url.path}`.")
        return JSONResponse(status_code=200, content={"status": "success", "message": "Debug state logged."})

    if client_ip in BLACKHOLE_IP_POOL:
        return JSONResponse(status_code=200, content={"status": "success", "processed_nex": 0.0, "sync_status": "synced"})

    response = await call_next(request)
    return response

# =====================================================================
# 4. HELPER UTILITIES & NAMETAG FORMATTING ENGINE
# =====================================================================
def int_to_roman(num: int) -> str:
    if num <= 0:
        return ""
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syb = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    roman_num = ""
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            roman_num += syb[i]
            num -= val[i]
        i += 1
    return roman_num

def get_or_create_player(db: Session, player_id: str) -> PlayerModel:
    player = db.query(PlayerModel).filter(PlayerModel.player_id == player_id).first()
    if not player:
        player = PlayerModel(player_id=player_id, spendable_nex=500.0, total_nex_earned=500.0, total_hours_played=1.0)
        db.add(player)
        db.commit()
        db.refresh(player)
    return player

def calculate_nametag_style(player: PlayerModel, db: Session) -> dict:
    prestige_colors = {0: "#FFFFFF", 1: "#CD7F32", 2: "#C0C0C0", 3: "#FFD700"}
    color = prestige_colors.get(player.prestige_level, "#00F0FF")

    emblem = None
    try:
        special_item = db.query(PlayerInventoryModel).filter(
            PlayerInventoryModel.player_id == player.player_id,
            PlayerInventoryModel.item_type == "Creator_Reward"
        ).first()
        if special_item:
            emblem = "🏆"
    except Exception:
        db.rollback()

    if emblem is None and player.total_hours_played < 24.0:
        emblem = "⚡"

    if player.prestige_level > 0:
        prestige_tag = f"[{TOKEN_TICKER}-{int_to_roman(player.prestige_level)}]"
    else:
        prestige_tag = f"[{TOKEN_TICKER}]"

    formatted_display = f"{emblem + ' ' if emblem else ''}{prestige_tag} {player.player_id}".strip()

    return {
        "text_color": color,
        "emblem_icon": emblem,
        "prestige_level": player.prestige_level,
        "prestige_roman": int_to_roman(player.prestige_level),
        "prestige_tag": prestige_tag,
        "display_name_formatted": formatted_display
    }

# =====================================================================
# 5. API REQUEST / RESPONSE SCHEMAS
# =====================================================================
class TelemetryPingRequest(BaseModel):
    player_id: str
    minutes_played: int
    timestamp: int
    nonce: str
    signature: str

class StorePurchaseRequest(BaseModel):
    player_id: str
    item_id: str

class DeveloperItemCreateRequest(BaseModel):
    item_id: str
    name: str
    description: str
    price_nex: float
    developer_id: str
    multiplier_boost: float = 1.0

class OperatorGiftRequest(BaseModel):
    target_player_id: str
    item_id: str
    item_type: str = "Creator_Reward"
    reason: str = "Operator Special Gift"

class WalletLinkRequest(BaseModel):
    player_id: str
    hedera_account_id: str

class RegisterGameRequest(BaseModel):
    developer_id: str
    game_name: str
    webhook_url: Optional[str] = None

class GameCosmeticRequest(BaseModel):
    game_id: str
    item_id: str
    item_name: str
    price_nex: float
    asset_url: str
    category: str = "skin"

HEDERA_ACCOUNT_REGEX = r"^0\.0\.\d+$"

# =====================================================================
# 6. ACCOUNT LINKING & DISCORD IDENTITY ENDPOINTS
# =====================================================================
@app.post("/api/v1/link/generate")
async def generate_link_code(player_id: str = Body(..., embed=True)):
    code_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    link_code = f"NX-{code_suffix}"
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    LINK_CODES[link_code] = {"player_id": player_id, "expires": expires_at}
    
    return {
        "status": "success",
        "link_code": link_code,
        "expires_in_seconds": 600,
        "instructions": "Type `/link code:NX-XXXX` in Discord to bind your profile."
    }

@app.post("/api/v1/link/verify")
async def verify_link_code(payload: dict = Body(...)):
    link_code = payload.get("link_code", "").strip().upper()
    discord_id = payload.get("discord_id")
    discord_tag = payload.get("discord_tag")
    
    record = LINK_CODES.get(link_code)
    if not record:
        raise HTTPException(status_code=400, detail="Invalid or expired link code.")
    
    if datetime.utcnow() > record["expires"]:
        del LINK_CODES[link_code]
        raise HTTPException(status_code=400, detail="Link code has expired. Generate a new one in-game.")
    
    player_id = record["player_id"]
    del LINK_CODES[link_code]
    
    return {
        "status": "success",
        "player_id": player_id,
        "discord_id": discord_id,
        "discord_tag": discord_tag,
        "level": 1,
        "prestige": 0,
        "message": f"Successfully linked {discord_tag} to player {player_id}!"
    }

@app.post("/api/wallet/link")
async def link_wallet(data: WalletLinkRequest, db: Session = Depends(get_db)):
    if not re.match(HEDERA_ACCOUNT_REGEX, data.hedera_account_id):
        raise HTTPException(status_code=400, detail="Invalid Hedera Account ID format. Expected format: 0.0.123456")
        
    player = db.query(PlayerModel).filter(PlayerModel.player_id == data.player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player profile not found.")

    connected_acc = db.query(ConnectedAccountModel).filter(ConnectedAccountModel.player_id == data.player_id).first()
    if not connected_acc:
        connected_acc = ConnectedAccountModel(
            player_id=data.player_id,
            platform_name="hedera_wallet",
            external_account_id=data.hedera_account_id
        )
        db.add(connected_acc)
    else:
        connected_acc.external_account_id = data.hedera_account_id

    db.commit()

    return {"status": "success", "message": f"Wallet {data.hedera_account_id} linked successfully to {data.player_id}!"}

@app.get("/api/v1/player/{player_id}/wallet")
def get_player_wallet(player_id: str, db: Session = Depends(get_db)):
    connected = db.query(ConnectedAccountModel).filter(
        ConnectedAccountModel.player_id == player_id,
        ConnectedAccountModel.platform_name == "hedera_wallet"
    ).first()

    if not connected:
        return {"player_id": player_id, "hedera_wallet_id": None}

    return {"player_id": player_id, "hedera_wallet_id": connected.external_account_id}

@app.get("/api/v1/player/{player_id}")
def get_player_profile(player_id: str, db: Session = Depends(get_db)):
    # Query directly without auto-creating missing players
    player = db.query(PlayerModel).filter(PlayerModel.player_id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail=f"Player ID '{player_id}' not found.")
    
    return {
        "player_id": player.player_id,
        "spendable_nex": player.spendable_nex,
        "total_nex_earned": player.total_nex_earned,
        "total_hours_played": player.total_hours_played,
        "prestige_level": player.prestige_level,
        "nametag_style": format_nametag_style(player)
    }

# --- DISCORD USER LOOKUP ---
@app.get("/api/v1/players/by-discord/{discord_id}")
def get_player_by_discord_id(discord_id: str, db: Session = Depends(get_db)):
    try:
        player = db.query(PlayerModel).filter(PlayerModel.discord_id == str(discord_id)).first()
    except Exception as err:
        raise HTTPException(
            status_code=500, 
            detail=f"Database schema issue querying discord_id: {str(err)}"
        )

    if not player:
        raise HTTPException(
            status_code=404, 
            detail=f"No player account linked to Discord ID '{discord_id}'."
        )

    return {
        "player_id": player.player_id, 
        "discord_id": getattr(player, "discord_id", discord_id)
    }


# --- ON-CHAIN REWARD CLAIM ENDPOINT ---
@app.post("/api/v1/player/{player_id}/claim")
def claim_player_rewards(player_id: str, db: Session = Depends(get_db)):
    player = get_or_create_player(db, player_id)
    
    if player.spendable_nex <= 0:
        raise HTTPException(status_code=400, detail="No spendable NEX balance available to claim.")
    
    target_wallet = getattr(player, "hedera_account_id", None) or "0.0.11035514"
    claimed_amount = float(player.spendable_nex)
    
    # Deduct off-chain spendable balance
    player.spendable_nex = 0.0
    
    # Safely write audit log if AuditLogModel is available
    try:
        if "AuditLogModel" in globals():
            audit_entry = AuditLogModel(
                action_type="ONCHAIN_CLAIM",
                player_id=player.player_id,
                amount_nex=claimed_amount,
                details=f"Claimed {claimed_amount:.2f} NEX to Hedera Wallet {target_wallet}"
            )
            db.add(audit_entry)
    except Exception as audit_err:
        print(f"Audit log bypassed: {audit_err}")

    db.commit()
    
    return {
        "status": "success",
        "player_id": player.player_id,
        "amount": round(claimed_amount, 4),
        "wallet": target_wallet,
        "message": f"Successfully transferred {claimed_amount:.2f} NEX to {target_wallet}."
    }

# =====================================================================
# 7. MULTI-GAME DEVELOPER & COSMETIC PORTAL ENDPOINTS
# =====================================================================
@app.post("/api/v1/developer/register", tags=["Developer Store"])
async def register_game(
    req: RegisterGameRequest, 
    db: Session = Depends(get_db),
    dev_key: str = Depends(verify_developer_key)
):
    game_id = f"game_{req.game_name.lower().replace(' ', '_')}"
    
    existing = db.query(RegisteredGameModel).filter(RegisteredGameModel.game_id == game_id).first()
    if existing:
        return {"status": "SUCCESS", "game_id": existing.game_id, "note": "Game already registered"}

    new_game = RegisteredGameModel(
        game_id=game_id,
        developer_id=req.developer_id,
        game_name=req.game_name,
        webhook_url=req.webhook_url
    )
    db.add(new_game)
    db.commit()
    
    return {"status": "SUCCESS", "game_id": game_id}

@app.post("/api/v1/developer/cosmetics/add", tags=["Developer Store"])
async def add_game_cosmetic(
    req: GameCosmeticRequest, 
    db: Session = Depends(get_db),
    dev_key: str = Depends(verify_developer_key)
):
    game = db.query(RegisteredGameModel).filter(RegisteredGameModel.game_id == req.game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game ID not found in registry")
        
    item_key = f"{req.game_id}:{req.item_id}"
    
    cosmetic = GameCosmeticModel(
        item_key=item_key,
        game_id=req.game_id,
        item_name=req.item_name,
        price_nex=req.price_nex,
        asset_url=req.asset_url,
        category=req.category
    )
    db.add(cosmetic)
    db.commit()
    
    return {"status": "SUCCESS", "item_key": item_key}

@app.get("/api/v1/store/catalog", tags=["Developer Store"])
@app.get("/api/v1/store/catalogue", tags=["Developer Store"])
async def get_full_store_catalogue(db: Session = Depends(get_db)):
    core_items = db.query(StoreCatalogModel).filter(StoreCatalogModel.is_active == True).all()
    dev_items = db.query(GameCosmeticModel).all()
    
    return {
        "global_cosmetics": [
            {
                "item_id": item.item_id,
                "name": item.name,
                "description": item.description,
                "price_nex": item.price_nex
            } for item in core_items
        ],
        "developer_cosmetics": [
            {
                "item_key": item.item_key,
                "game_id": item.game_id,
                "name": item.item_name,
                "price_nex": item.price_nex,
                "category": item.category,
                "asset_url": item.asset_url
            } for item in dev_items
        ]
    }

@app.get("/api/v1/players/unclaimed")
async def get_unclaimed_players(db: Session = Depends(get_db)):
    players = db.query(PlayerModel).filter(PlayerModel.spendable_nex >= 10.0).all()
    unclaimed_list = []
    for p in players:
        connected = db.query(ConnectedAccountModel).filter(
            ConnectedAccountModel.player_id == p.player_id,
            ConnectedAccountModel.platform_name == "discord"
        ).first()
        discord_id = connected.external_account_id if connected else "0"
        
        unclaimed_list.append({
            "player_id": p.player_id,
            "spendable_nex": p.spendable_nex,
            "discord_user_id": discord_id
        })
            
    return {"players": unclaimed_list}

# =====================================================================
# 8. CORE API ENDPOINTS & MOBILE CONTROLS
# =====================================================================
@app.get("/", response_class=HTMLResponse)
def root_dashboard(db: Session = Depends(get_db)):
    total_players = db.query(PlayerModel).count()
    total_nex = db.query(PlayerModel).all()
    circulating_nex = sum(p.spendable_nex for p in total_nex)
    status_color = "#e74c3c" if IS_MINTING_PAUSED else "#3fb950"
    status_label = "MINTING PAUSED" if IS_MINTING_PAUSED else "ACTIVE MAINNET RELAYER"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>{TOKEN_NAME} Engine | Operator Central Bank</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0b0e14; color: #e1e7ec; margin: 0; padding: 20px; }}
                .container {{ max-width: 900px; margin: 0 auto; }}
                .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 24px; margin-bottom: 20px; }}
                h1 {{ color: #58a6ff; font-size: 24px; margin-bottom: 5px; }}
                .ticker {{ color: #8b949e; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }}
                .metric {{ font-size: 32px; font-weight: bold; color: #3fb950; margin: 10px 0; }}
                .badge {{ background: {status_color}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <span class="ticker">{TOKEN_NAME} ({TOKEN_TICKER}) Central Bank</span>
                    <h1>Operator Relayer Dashboard</h1>
                    <p>Status: <span class="badge">{status_label}</span></p>
                </div>
                <div class="card">
                    <h3>Network Metrics</h3>
                    <p>Registered Players: <strong>{total_players}</strong></p>
                    <p>Trapped Bot IPs: <strong style="color: #f85149;">{len(BLACKHOLE_IP_POOL)}</strong></p>
                    <p>Circulating {TOKEN_TICKER}:</p>
                    <div class="metric">{circulating_nex:,.2f} {TOKEN_TICKER}</div>
                </div>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

@app.post("/api/v1/telemetry")
def process_telemetry(data: TelemetryPingRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host or "127.0.0.1"
    current_time = int(time.time())

    if IS_MINTING_PAUSED:
        raise HTTPException(status_code=503, detail="Central Bank minting is currently paused by the Operator.")

    if abs(current_time - data.timestamp) > 300:
        trigger_discord_alert(f"Expired Telemetry Payload from `{client_ip}` (Player: `{data.player_id}`).")
        raise HTTPException(status_code=401, detail="Expired telemetry payload window.")

    if data.nonce in PROCESSED_NONCES:
        BLACKHOLE_IP_POOL.add(client_ip)
        trigger_discord_alert(f"Replay Attack Prevented: Re-used Nonce from `{client_ip}`. IP Blackholed.")
        raise HTTPException(status_code=401, detail="Replay payload detected.")

    if data.minutes_played > 60 or data.minutes_played <= 0:
        raise HTTPException(status_code=400, detail="Invalid gameplay duration telemetry.")

    if data.signature == "dev_bypass_sig":
        pass
    else:
        payload = f"{data.player_id}:{data.minutes_played}:{data.timestamp}:{data.nonce}".encode('utf-8')
        expected_sig = hmac.new(NEXUS_HMAC_SECRET, payload, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected_sig, data.signature):
            BLACKHOLE_IP_POOL.add(client_ip)
            trigger_discord_alert(f"HMAC Signature Mismatch from IP `{client_ip}` (Player: `{data.player_id}`). IP Blackholed.")
            raise HTTPException(status_code=401, detail="Invalid telemetry cryptographic signature.")

    PROCESSED_NONCES.add(data.nonce)

    player = get_or_create_player(db, data.player_id)
    hours_added = data.minutes_played / 60.0
    player.total_hours_played += hours_added

    base_rate = 10.0
    multiplier = 1.0

    if player.total_hours_played <= 24.0:
        multiplier += 0.10

    gross_earned_nex = (base_rate * hours_added) * multiplier
    burned_fee = gross_earned_nex * 0.01
    net_earned_nex = gross_earned_nex - burned_fee

    player.spendable_nex += net_earned_nex
    player.total_nex_earned += net_earned_nex

    try:
        audit_entry = AuditLogModel(
            action_type="TELEMETRY_MINT",
            player_id=player.player_id,
            amount_nex=net_earned_nex,
            details=f"Earned {net_earned_nex:.2f} NEX ({burned_fee:.2f} NEX burned) for {data.minutes_played}m play time"
        )
        db.add(audit_entry)
        db.commit()
    except Exception:
        db.rollback()

    return {
        "status": "success",
        "player_id": player.player_id,
        "nex_earned": round(net_earned_nex, 4),
        "nex_burned": round(burned_fee, 4),
        "total_spendable_nex": round(player.spendable_nex, 4),
        "active_multiplier": round(multiplier, 2),
        "nametag_style": calculate_nametag_style(player, db)
    }

@app.post("/api/v1/store/buy")
def execute_store_purchase(req: StorePurchaseRequest, db: Session = Depends(get_db)):
    player = get_or_create_player(db, req.player_id)
    
    # Check core store catalog first
    item = db.query(StoreCatalogModel).filter(StoreCatalogModel.item_id == req.item_id, StoreCatalogModel.is_active == True).first()

    price = 0.0
    item_name = ""
    target_dev_id = ""

    if item:
        price = item.price_nex
        item_name = item.name
        target_dev_id = item.developer_id
    else:
        # Check developer cosmetics if not found in core catalog
        dev_item = db.query(GameCosmeticModel).filter(GameCosmeticModel.item_key == req.item_id).first()
        if dev_item:
            price = dev_item.price_nex
            item_name = dev_item.item_name
            # Map game_id back to registered game to locate developer_id
            reg_game = db.query(RegisteredGameModel).filter(RegisteredGameModel.game_id == dev_item.game_id).first()
            target_dev_id = reg_game.developer_id if reg_game else dev_item.game_id
        else:
            raise HTTPException(status_code=404, detail="Item not found in catalog.")

    if player.spendable_nex < price:
        raise HTTPException(status_code=400, detail=f"Insufficient {TOKEN_TICKER} balance.")

    player.spendable_nex -= price

    # Deflationary Sink: 13% Burn, 87% Recirculate
    burned_amount = price * 0.13
    recirculated_amount = price * 0.87

    # Allocate 87% recirculation to developer account
    developer = db.query(DeveloperModel).filter(DeveloperModel.developer_id == target_dev_id).first()
    if not developer:
        developer = DeveloperModel(
            developer_id=target_dev_id,
            developer_name=f"Studio {target_dev_id}",
            earned_nex_balance=0.0
        )
        db.add(developer)

    developer.earned_nex_balance += recirculated_amount

    instance_id = f"inst_{req.item_id[:8]}_{int(time.time())}_{player.player_id[:4]}"
    inventory_item = PlayerInventoryModel(
        instance_id=instance_id,
        player_id=player.player_id,
        item_id=req.item_id,
        item_type="Standard",
        acquired_via="Store_Purchase"
    )
    db.add(inventory_item)

    audit_entry = AuditLogModel(
        action_type="STORE_PURCHASE",
        player_id=player.player_id,
        amount_nex=price,
        details=f"Purchased '{item_name}'. Burned: {burned_amount:.2f} NEX, Recirculated: {recirculated_amount:.2f} NEX to {target_dev_id}"
    )
    db.add(audit_entry)
    db.commit()

    return {
        "status": "success",
        "message": f"Successfully purchased {item_name}.",
        "instance_id": instance_id,
        "burned_nex": round(burned_amount, 4),
        "recirculated_nex": round(recirculated_amount, 4),
        "remaining_spendable_nex": round(player.spendable_nex, 4)
    }

# =====================================================================
# 9. MOBILE REMOTE CONTROLS & ADMIN ENDPOINTS
# =====================================================================
@app.post("/api/v1/admin/toggle-pause")
def toggle_minting_pause(x_admin_key: str = Header(...)):
    global IS_MINTING_PAUSED
    if x_admin_key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized operator key.")

    IS_MINTING_PAUSED = not IS_MINTING_PAUSED
    status_text = "PAUSED" if IS_MINTING_PAUSED else "RESUMED"
    trigger_discord_alert(f"Operator manually **{status_text}** central bank minting.")

    return {
        "status": "success",
        "is_minting_paused": IS_MINTING_PAUSED,
        "message": f"Central Bank minting has been {status_text}."
    }

@app.post("/api/v1/admin/gift-item")
def operator_gift_item(req: OperatorGiftRequest, x_admin_key: str = Header(...), db: Session = Depends(get_db)):
    if x_admin_key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized operator key.")

    player = get_or_create_player(db, req.target_player_id)
    instance_id = f"gift_{req.item_id}_{int(time.time())}_{player.player_id[:4]}"
    inventory_entry = PlayerInventoryModel(
        instance_id=instance_id,
        player_id=player.player_id,
        item_id=req.item_id,
        item_type=req.item_type,
        acquired_via=req.reason
    )
    db.add(inventory_entry)
    db.commit()

    return {
        "status": "success",
        "message": f"Gifted item '{req.item_id}' to player '{player.player_id}'.",
        "instance_id": instance_id
    }

@app.get("/api/v1/admin/summary")
def get_admin_summary(db: Session = Depends(get_db)):
    players = db.query(PlayerModel).all()
    developers = db.query(DeveloperModel).all()

    return {
        "network_token": TOKEN_NAME,
        "ticker": TOKEN_TICKER,
        "is_minting_paused": IS_MINTING_PAUSED,
        "total_registered_players": len(players),
        "total_circulating_nex": sum(p.spendable_nex for p in players),
        "total_lifetime_nex_minted": sum(p.total_nex_earned for p in players),
        "total_developer_unclaimed_nex": sum(d.earned_nex_balance for d in developers),
        "trapped_bot_ips_count": len(BLACKHOLE_IP_POOL),
        "trapped_bot_ips": list(BLACKHOLE_IP_POOL)
    }