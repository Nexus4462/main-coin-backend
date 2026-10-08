from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

from main import UniversalCoinEngine

app = FastAPI(
    title="Universal Gaming Token Engine API",
    description="Scalable Cross-Game Micro-Unit Ledger & Hedera HTS Settlement Gateway",
    version="1.0.0"
)

engine = UniversalCoinEngine()


# ==========================================
# REQUEST SCHEMAS
# ==========================================

class TelemetryPingRequest(BaseModel):
    game_id: str = Field(..., example="game_sb_9901")
    player_id: str = Field(..., example="player_david_01")
    minutes_played: float = Field(default=30.0, example=30.0)
    is_active_anti_afk: bool = Field(default=True, example=True)
    input_variance_score: float = Field(default=0.85, ge=0.0, le=1.0, example=0.85)
    ip_address: Optional[str] = Field(default="127.0.0.1", example="127.0.0.1")


class PrestigeRequest(BaseModel):
    player_id: str = Field(..., example="player_david_01")


class CosmeticPurchaseRequest(BaseModel):
    player_id: str = Field(..., example="player_david_01")
    game_id: str = Field(..., example="game_sb_9901")
    price_in_coins: float = Field(..., example=20.0)


class WalletActivationRequest(BaseModel):
    player_id: str = Field(..., example="player_david_01")


# ==========================================
# REST API ENDPOINTS
# ==========================================

@app.get("/")
def health_check():
    """System Health and Global Ledger Summary."""
    return {
        "status": "online",
        "system": "Universal Gaming Token Engine",
        "total_burned_coins": engine._micro_to_coins(engine.total_burned_micro),
        "prize_pool_coins": engine._micro_to_coins(engine.prize_pool_micro),
        "recirculation_pool_coins": engine._micro_to_coins(engine.recirculation_pool_micro)
    }


@app.post("/v1/telemetry/ping")
def record_playtime_ping(
    request_data: TelemetryPingRequest,
    x_signature: str = Header(default="test_sig")
):
    # Fallback to test_sig if header is empty or None
    sig = x_signature if x_signature else "test_sig"
    payload = request_data.dict()

    response = engine.record_playtime_session(
        game_id=request_data.game_id,
        payload=payload,
        signature=sig,
        request_path="/v1/telemetry/ping"
    )

    if response.get("status") == "rejected":
        raise HTTPException(status_code=401, detail=response.get("reason", "Security validation failed"))

    return response


@app.get("/v1/player/balance/{player_id}")
def get_player_balance(player_id: str, game_id: Optional[str] = "game_sb_9901"):
    """Returns spendable Main Coins, game sub-coins, daily progress, and wallet status."""
    engine.register_player(player_id)
    player = engine.players[player_id]

    game = engine.games.get(game_id, engine.games["game_sb_9901"])
    spendable_coins = engine._micro_to_coins(player["spendable_micro"])
    sub_coins = spendable_coins * game["ratio"]

    wallet_data = engine.wallets.user_wallets.get(player_id, {})

    return {
        "player_id": player_id,
        "spendable_main_coins": spendable_coins,
        "sub_coin_display": {
            "amount": round(sub_coins, 2),
            "currency_name": game["sub_coin_name"],
            "symbol": game["symbol"]
        },
        "prestige_level": player["prestige_level"],
        "daily_earned_coins": engine._micro_to_coins(player["daily_earned_micro"]),
        "daily_cap": engine.BASE_DAILY_CAP_COINS * (1.0 + (0.05 * player["prestige_level"])),
        "wallet_info": {
            "internal_id": wallet_data.get("internal_wallet_id"),
            "hedera_account_id": wallet_data.get("hedera_account_id"),
            "is_on_chain": wallet_data.get("is_on_chain_deployed", False)
        }
    }


@app.post("/v1/player/prestige")
def trigger_prestige(request_data: PrestigeRequest):
    res = engine.process_prestige(player_id=request_data.player_id)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res


@app.post("/v1/marketplace/purchase")
def purchase_cosmetic_item(request_data: CosmeticPurchaseRequest):
    res = engine.purchase_cosmetic(
        player_id=request_data.player_id,
        game_id=request_data.game_id,
        price_in_coins=request_data.price_in_coins
    )
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res


@app.post("/v1/wallet/activate_on_chain")
def activate_on_chain_wallet(request_data: WalletActivationRequest):
    """
    On-Chain Wallet Deployment Endpoint
    -----------------------------------
    Calls wallet_manager.py to provision a Hedera Account ID via hedera_relayer.py.
    """
    res = engine.wallets.deploy_on_chain_account(
        user_id=request_data.player_id,
        master_treasury_payout_func=lambda key: engine.hedera.create_on_chain_account(key).get("hedera_account_id")
    )
    return res


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_routes:app", host="127.0.0.1", port=8000, reload=True)