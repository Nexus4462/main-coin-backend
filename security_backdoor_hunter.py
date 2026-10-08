# security_backdoor_hunter.py
import time
import json
import logging
from typing import Dict, Any, Set, List

class BackdoorHunterEngine:
    """
    Deception-Based Threat Hunting & Backdoor Detection Engine
    ----------------------------------------------------------
    - Detects Honey-Token Endpoint probes (Fake Admin Paths)
    - Identifies SDK Key Compromise & Parameter Manipulation
    - Automatically triggers Developer Secret Key Rotations
    """

    def __init__(self):
        # Fake "Backdoor" Endpoints that legitimate SDKs never call
        self.honey_token_paths: Set[str] = {
            "/v1/admin/debug_mint",
            "/v1/developer/override_balance",
            "/v1/internal/bypass_cap"
        }

        # Track compromised Developer Secret Keys
        self.compromised_game_keys: Set[str] = set()
        
        # Real-time Security Incident Logs
        self.security_incidents: List[Dict[str, Any]] = []

    def inspect_request_path(self, request_path: str, client_ip: str, game_id: str) -> bool:
        """
        Checks if an incoming request is probing a Honey-Token path.
        Returns True if SAFE, or False if a BACKDOOR PROBE IS DETECTED.
        """
        if request_path in self.honey_token_paths:
            self._trigger_backdoor_alert(
                threat_type="Honey-Token Probe Detected",
                game_id=game_id,
                client_ip=client_ip,
                details=f"Client attempted to call deceptive path: {request_path}"
            )
            return False  # Trap request instantly
        return True

    def check_parameter_tampering(
        self, 
        game_id: str, 
        payload: Dict[str, Any], 
        is_signature_valid: bool
    ) -> bool:
        """
        Detects if a hacker is attempting to manipulate payload variables 
        or if a developer's secret key has leaked.
        """
        minutes_played = payload.get("minutes_played", 0)
        input_variance = payload.get("input_variance_score", 1.0)

        # Threat Condition 1: Impossible Parameter Values (e.g. >24 hours of play in one ping)
        if minutes_played > 1440 or minutes_played < 0:
            self._trigger_backdoor_alert(
                threat_type="Parameter Manipulation Exploit",
                game_id=game_id,
                client_ip=payload.get("ip_address", "Unknown"),
                details=f"Impossible playtime parameter submitted: {minutes_played} mins"
            )
            return False

        # Threat Condition 2: Invalid HMAC signature with valid structural format
        # Indicates someone is trying to brute-force or guess the SDK signing algorithm
        if not is_signature_valid:
            self._log_suspicious_attempt(game_id, payload)

        return True

    def _trigger_backdoor_alert(self, threat_type: str, game_id: str, client_ip: str, details: str):
        """Logs security breach and revokes/quarantines compromised keys."""
        incident = {
            "timestamp": time.time(),
            "threat_type": threat_type,
            "game_id": game_id,
            "client_ip": client_ip,
            "details": details,
            "action_taken": "Key Flagged for Emergency Rotation & Session Quarantined"
        }
        
        self.security_incidents.append(incident)
        self.compromised_game_keys.add(game_id)
        
        # High-priority alert print (In production, sends PagerDuty / Discord / Webhook alert)
        print(f"\n🚨 [CRITICAL SECURITY ALERT] {threat_type} on Game '{game_id}' from IP '{client_ip}'!")
        print(f"    Details: {details}\n")

    def _log_suspicious_attempt(self, game_id: str, payload: Dict[str, Any]):
        """Tracks failed exploitation attempts to monitor brute-force patterns."""
        self.security_incidents.append({
            "timestamp": time.time(),
            "threat_type": "Signature Brute-Force",
            "game_id": game_id,
            "payload_snippet": payload
        })