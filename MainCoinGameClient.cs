using System;
using System.Net.Http;
using System.Text;
using System.Security.Cryptography;
using System.Threading.Tasks;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace MainCoin.SDK
{
    // =========================================================================
    // DATA TRANSFER OBJECTS (DTOs)
    // =========================================================================
    public class TelemetryPayload
    {
        [JsonPropertyName("player_id")]
        public string PlayerId { get; set; }

        [JsonPropertyName("minutes_played")]
        public int MinutesPlayed { get; set; }

        [JsonPropertyName("timestamp")]
        public double Timestamp { get; set; }

        [JsonPropertyName("signature")]
        public string Signature { get; set; }
    }

    public class PlayerStatsResponse
    {
        [JsonPropertyName("player_id")]
        public string PlayerId { get; set; }

        [JsonPropertyName("hours_played")]
        public double HoursPlayed { get; set; }

        [JsonPropertyName("current_level")]
        public int CurrentLevel { get; set; }

        [JsonPropertyName("prestige_level")]
        public int PrestigeLevel { get; set; }

        [JsonPropertyName("spendable_coins")]
        public double SpendableCoins { get; set; }

        [JsonPropertyName("current_earn_rate")]
        public double CurrentEarnRate { get; set; }

        [JsonPropertyName("is_soft_decay_active")]
        public bool IsSoftDecayActive { get; set; }
    }

    public class StorePurchaseResponse
    {
        [JsonPropertyName("status")]
        public string Status { get; set; }

        [JsonPropertyName("item_id")]
        public string ItemId { get; set; }

        [JsonPropertyName("price_paid")]
        public double PricePaid { get; set; }

        [JsonPropertyName("developer_credited")]
        public double DeveloperCredited { get; set; }

        [JsonPropertyName("platform_fee")]
        public double PlatformFee { get; set; }

        [JsonPropertyName("remaining_player_balance")]
        public double RemainingPlayerBalance { get; set; }

        [JsonPropertyName("hedera_tx_id")]
        public string HederaTxId { get; set; }
    }

    public class PrestigeResponse
    {
        [JsonPropertyName("status")]
        public string Status { get; set; }

        [JsonPropertyName("message")]
        public string Message { get; set; }

        [JsonPropertyName("new_prestige_level")]
        public int NewPrestigeLevel { get; set; }

        [JsonPropertyName("burned_coins")]
        public double BurnedCoins { get; set; }

        [JsonPropertyName("new_earn_rate")]
        public double NewEarnRate { get; set; }

        [JsonPropertyName("remaining_coins")]
        public double RemainingCoins { get; set; }

        [JsonPropertyName("hedera_burn_tx_id")]
        public string HederaBurnTxId { get; set; }
    }

    // =========================================================================
    // MAIN COIN GAME CLIENT SDK
    // =========================================================================
    public class MainCoinGameClient
    {
        private readonly string _baseUrl;
        private readonly string _hmacSecret;
        private readonly HttpClient _httpClient;

        public MainCoinGameClient(string baseUrl = "http://127.0.0.1:8000", string hmacSecret = "super_secret_game_server_key_123")
        {
            _baseUrl = baseUrl.TrimEnd('/');
            _hmacSecret = hmacSecret;
            _httpClient = new HttpClient();
        }

        /// <summary>
        /// Generates client-side HMAC-SHA256 signature for telemetry payloads.
        /// </summary>
        private string GenerateHMACSignature(string playerId, int minutesPlayed, double timestamp)
        {
            string payload = $"{playerId}:{minutesPlayed}:{timestamp}";
            byte[] keyBytes = Encoding.UTF8.GetBytes(_hmacSecret);
            byte[] payloadBytes = Encoding.UTF8.GetBytes(payload);

            using (var hmac = new HMACSHA256(keyBytes))
            {
                byte[] hashBytes = hmac.ComputeHash(payloadBytes);
                StringBuilder sb = new StringBuilder();
                foreach (byte b in hashBytes)
                {
                    sb.Append(b.ToString("x2"));
                }
                return sb.ToString();
            }
        }

        /// <summary>
        /// Sends authenticated session telemetry pings to FastAPI backend.
        /// </summary>
        public async Task<bool> SendTelemetryPingAsync(string playerId, int minutesPlayed)
        {
            double timestamp = DateTime.UtcNow.Subtract(new DateTime(1970, 1, 1)).TotalSeconds;
            string signature = GenerateHMACSignature(playerId, minutesPlayed, timestamp);

            var telemetryData = new TelemetryPayload
            {
                PlayerId = playerId,
                MinutesPlayed = minutesPlayed,
                Timestamp = timestamp,
                Signature = signature
            };

            string json = JsonSerializer.Serialize(telemetryData);
            var content = new StringContent(json, Encoding.UTF8, "application/json");

            try
            {
                HttpResponseMessage response = await _httpClient.PostAsync($"{_baseUrl}/api/v1/telemetry", content);
                return response.IsSuccessStatusCode;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[MainCoin SDK Error] Telemetry Ping Failed: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Retrieves real-time player economy profile for HUD display.
        /// </summary>
        public async Task<PlayerStatsResponse> GetPlayerStatsAsync(string playerId)
        {
            try:
            {
                HttpResponseMessage response = await _httpClient.GetAsync($"{_baseUrl}/api/v1/player/{playerId}");
                response.EnsureSuccessStatusCode();
                string json = await response.ContentReadAsStringAsync();
                return JsonSerializer.Deserialize<PlayerStatsResponse>(json);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[MainCoin SDK Error] Get Stats Failed: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Executes cosmetic store item purchase (75% Dev Split & Hedera Transfer).
        /// </summary>
        public async Task<StorePurchaseResponse> BuyStoreItemAsync(string playerId, string itemId, double priceInCoins)
        {
            var payload = new
            {
                player_id = playerId,
                item_id = itemId,
                price_in_coins = priceInCoins
            };

            string json = JsonSerializer.Serialize(payload);
            var content = new StringContent(json, Encoding.UTF8, "application/json");

            try
            {
                HttpResponseMessage response = await _httpClient.PostAsync($"{_baseUrl}/api/v1/store/buy", content);
                response.EnsureSuccessStatusCode();
                string responseJson = await response.ContentReadAsStringAsync();
                return JsonSerializer.Deserialize<StorePurchaseResponse>(responseJson);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[MainCoin SDK Error] Store Purchase Failed: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Executes Level 50 Prestige reset (Charges 2,500 coins & burns 25% on Hedera).
        /// </summary>
        public async Task<PrestigeResponse> ExecutePrestigeAsync(string playerId)
        {
            var payload = new { player_id = playerId };
            string json = JsonSerializer.Serialize(payload);
            var content = new StringContent(json, Encoding.UTF8, "application/json");

            try
            {
                HttpResponseMessage response = await _httpClient.PostAsync($"{_baseUrl}/api/v1/prestige", content);
                response.EnsureSuccessStatusCode();
                string responseJson = await response.ContentReadAsStringAsync();
                return JsonSerializer.Deserialize<PrestigeResponse>(responseJson);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[MainCoin SDK Error] Prestige Execution Failed: {ex.Message}");
                return null;
            }
        }
    }
}