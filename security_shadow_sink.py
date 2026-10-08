import os
import time
import hmac
import hashlib
import json
from typing import Dict, Any, Optional, Set, Tuple

APP_ENV = os.getenv("APP_ENV", "development")


class SecurityShadowSinkEngine:
    """
    Anti-Bot Honeypot & Cryptographic Signature Inspector
    -----------------------------------------------------
    - Validates HMAC-SHA256 payload integrity & nonces.
    - Catches automated bots and redirects them to the 'Black Hole'.
    """

    def __init__(self):
        self.used_nonces: Set[str] = set()
        self.shadow_sunk_players: Set[str] = set()
        self.max_request_age_seconds = 300  # 5-minute window

    def verify_request_integrity(
        self, game_secret_key: str, payload: Dict[str, Any], signature: str
    ) -> Tuple[bool, Optional[str]]:
        """Validates HMAC signature and prevents replay attacks."""
        # --- LOCAL DEV BYPASS (Bypasses timestamp & nonce in dev mode) ---
        if APP_ENV == "development" and signature in ["test_sig", "bypass", "mock_signature"]:
            return True, None

        # 1. Check Timestamp Age
        now = int(time.time())
        req_timestamp = payload.get("timestamp")
        
        if req_timestamp is None:
            return False, "Security Failure: Missing payload timestamp"

        if abs(now - int(req_timestamp)) > self.max_request_age_seconds:
            return False, "Security Failure: Expired payload timestamp"

        # 2. Check Nonce Replay
        nonce = payload.get("nonce")
        if not nonce or nonce in self.used_nonces:
            return False, "Security Failure: Duplicate or missing nonce (Replay Attempt)"

        # 3. HMAC Signature Check
        serialized = json.dumps(payload, sort_keys=True)
        expected_sig = hmac.new(
            game_secret_key.encode('utf-8'),
            serialized.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, signature):
            return False, "Security Failure: HMAC signature mismatch"

        self.used_nonces.add(nonce)
        return True, None

    def evaluate_player_session(
        self, player_id: str, input_variance_score: float, payload: Dict[str, Any]
    ) -> bool:
        """Determines if session is human or bot (Score below 0.15 = Bot)."""
        if player_id in self.shadow_sunk_players:
            return False

        if input_variance_score < 0.15:
            self.shadow_sunk_players.add(player_id)
            return False

        return True

    def process_black_hole_bot(self, player_id: str, payload_data: Dict[str, Any]) -> Dict[str, Any]:
        """Returns convincing fake responses to trap bots while draining their compute."""
        return {
            "status": "success",
            "earned_main_coins": payload_data.get("minutes_played", 0) * 1.66,
            "earned_sub_coins": payload_data.get("minutes_played", 0) * 1660.0,
            "sub_coin_name": "Coins",
            "total_spendable_coins": 99999.0,
            "daily_progress_coins": "1200.0/1200.0",
            "next_nonce_challenge": "pow_difficulty_16_active"
        }