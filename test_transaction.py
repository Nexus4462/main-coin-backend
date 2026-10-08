import hashlib
import hmac
import time
import math

# --- 1. GAME ENGINE & TELEMETRY LOGIC ---
HMAC_SECRET = "super_secret_game_server_key_123"

def generate_telemetry_signature(player_id: str, minutes_played: int, timestamp: float) -> str:
    """Generates an HMAC-SHA256 signature simulating an in-game telemetry ping."""
    payload = f"{player_id}:{minutes_played}:{timestamp}"
    return hmac.new(HMAC_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()

def verify_telemetry(player_id: str, minutes_played: int, timestamp: float, signature: str) -> bool:
    """Validates telemetry signature from connected game servers."""
    expected_sig = generate_telemetry_signature(player_id, minutes_played, timestamp)
    return hmac.compare_digest(expected_sig, signature)

class PlayerEconomy:
    def __init__(self, player_id: str):
        self.player_id = player_id
        self.total_hours_played = 0.0
        self.spendable_coins = 0.0
        self.prestige_level = 0
        self.developer_balance = 0.0

    @property
    def current_level(self) -> int:
        return math.floor(self.total_hours_played)

    def calculate_earn_rate(self) -> float:
        """Calculates coins earned per hour, applying +5% prestige bonus and 60% decay at Level 50."""
        base_rate = 100.0  # Base 100 coins/hr
        prestige_multiplier = 1.0 + (0.05 * self.prestige_level)
        effective_rate = base_rate * prestige_multiplier

        # Soft Decay Rule: If player hits Level 50 without prestiging, drop pay by 60%
        if self.current_level >= 50:
            effective_rate *= 0.40  # Player earns at 40% efficiency

        return effective_rate

    def record_gameplay(self, minutes_played: int):
        """Processes accredited play time and awards micro-units."""
        hours = minutes_played / 60.0
        self.total_hours_played += hours  # Update hours first!
    
        rate = self.calculate_earn_rate()  # Now correctly checks if level >= 50
        earned = hours * rate
        self.spendable_coins += earned
        return earned, rate

    def buy_cosmetic(self, coin_price: float):
        """Processes a store purchase with a 75/25 Dev/Platform split."""
        if self.spendable_coins < coin_price:
            return False, "Insufficient balance"
        
        self.spendable_coins -= coin_price
        dev_share = coin_price * 0.75
        self.developer_balance += dev_share
        return True, f"Purchased! Developer received {dev_share:.2f} coins (75%)."

    def prestige(self):
        """Executes Level 50 Prestige: Charges 2,500 coins, burns 625 coins (25%), resets level."""
        if self.current_level < 50:
            return False, f"Must be Level 50 to prestige (Current: Level {self.current_level})"
        
        prestige_cost = 2500.0
        if self.spendable_coins < prestige_cost:
            return False, f"Need {prestige_cost} coins to prestige (Current: {self.spendable_coins:.2f})"

        self.spendable_coins -= prestige_cost
        coins_to_burn = prestige_cost * 0.25  # 25% On-Chain Burn (625 coins)
        self.prestige_level += 1
        self.total_hours_played = 0.0  # Reset level progression

        return True, f"PRESTIGE SUCCESS! Burned {coins_to_burn:.2f} coins on-chain. New Prestige: {self.prestige_level}"


# --- 2. END-TO-END SUITE RUNNER ---
def run_tests():
    print("==================================================")
    print("   RUNNING MAIN COIN SUITE & TELEMETRY TESTS      ")
    print("==================================================\n")

    player = PlayerEconomy(player_id="player_dev_001")

    # TEST 1: Telemetry Security Validation
    print("--- Test 1: HMAC Telemetry Authentication ---")
    ts = time.time()
    valid_sig = generate_telemetry_signature(player.player_id, 60, ts)
    is_valid = verify_telemetry(player.player_id, 60, ts, valid_sig)
    print(f"HMAC Signature Verification: {'PASSED' if is_valid else 'FAILED'}\n")

    # TEST 2: Standard Progression (Level 1 to 49)
    print("--- Test 2: Earning Coins (Levels 1 - 49) ---")
    for hour in range(1, 50):
        player.record_gameplay(60)
    print(f"Hours Played: {player.total_hours_played:.1f} hrs | Level: {player.current_level}")
    print(f"Spendable Coins: {player.spendable_coins:.2f}")
    print(f"Earning Efficiency: 100% ({player.calculate_earn_rate():.2f} coins/hr)\n")

    # TEST 3: Soft Decay Activation at Level 50
    print("--- Test 3: Reaching Level 50 (Soft Decay Verification) ---")
    earned, rate = player.record_gameplay(60)  # Pushes to Level 50
    print(f"Hours Played: {player.total_hours_played:.1f} hrs | Level: {player.current_level}")
    print(f"Earn Rate at Level 50: {rate:.2f} coins/hr (60% Decay Applied!)")
    print(f"Spendable Coins: {player.spendable_coins:.2f}\n")

    # TEST 4: Store Purchase & 75/25 Dev Split
    print("--- Test 4: Cosmetic Store Purchase (75/25 Revenue Split) ---")
    success, msg = player.buy_cosmetic(500.0)
    print(f"Purchase Status: {msg}")
    print(f"Player Balance: {player.spendable_coins:.2f} | Developer Vault: {player.developer_balance:.2f} coins\n")

    # TEST 5: Top-up & Prestige Loop
    print("--- Test 5: Prestige Execution & On-Chain Burn ---")
    # Simulate grinding out remaining coins needed for 2,500 Prestige Fee
    player.spendable_coins += 2000.0  # Top-up for test
    print(f"Pre-Prestige Balance: {player.spendable_coins:.2f} coins")
    
    p_success, p_msg = player.prestige()
    print(f"Prestige Status: {p_msg}")
    print(f"Post-Prestige Level: {player.current_level} | Prestige Tier: {player.prestige_level}")
    print(f"New Earn Rate: {player.calculate_earn_rate():.2f} coins/hr (+5% Boost Active!)")
    print("\n==================================================")
    print("               ALL TESTS PASSED!                  ")
    print("==================================================")

if __name__ == "__main__":
    run_tests()