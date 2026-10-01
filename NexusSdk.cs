using System;
using System.Text;
using System.Security.Cryptography;
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;
using TMPro;

namespace NexusEngine
{
    // =====================================================================
    // 1. DTO DATA CONTRACTS MATCHING FASTAPI MODELS
    // =====================================================================
    [Serializable]
    public class TelemetryPayload
    {
        public string player_id;
        public int minutes_played;
        public long timestamp;
        public string nonce;
        public string signature;
    }

    [Serializable]
    public class NametagStyle
    {
        public string text_color;
        public string emblem_icon;
        public int prestige_level;
        public string prestige_roman;
        public string prestige_tag;
        public string display_name_formatted;
    }

    [Serializable]
    public class TelemetryResponse
    {
        public string status;
        public string player_id;
        public float nex_earned;
        public float total_spendable_nex;
        public float active_multiplier;
        public NametagStyle nametag_style;
    }

    // =====================================================================
    // 2. CORE NEXUS SDK CLIENT
    // =====================================================================
    public class NexusSdk : MonoBehaviour
    {
        [Header("Backend Configuration")]
        [SerializeField] private string backendUrl = "https://main-coin-backend.onrender.com";
        [SerializeField] private string hmacSecretKey = "dev_secret_key_change_in_production"; // Set in Render Env

        [Header("Active Player Session")]
        [SerializeField] private string currentPlayerId = "player_unity_001";
        [SerializeField] private string currentUsername = "AlphaCommander";

        [Header("UI Binding (Optional)")]
        [SerializeField] private TextMeshProUGUI playerNametagText;
        [SerializeField] private TextMeshProUGUI nexBalanceText;

        private float gameTimeAccumulator = 0f;
        private const float PING_INTERVAL_SECONDS = 300f; // Send telemetry ping every 5 minutes (or adjust as needed)

        private void Start()
        {
            // Initial profile sync on game launch
            StartCoroutine(FetchPlayerProfile(currentPlayerId));

            // Start automated gameplay tracking loop
            StartCoroutine(TelemetryLoop());
        }

        private IEnumerator TelemetryLoop()
        {
            while (true)
            {
                yield return new WaitForSeconds(PING_INTERVAL_SECONDS);

                // Send 5 minutes played (or compute actual elapsed delta)
                yield return StartCoroutine(SendTelemetryPing(currentPlayerId, 5));
            }
        }

        // =====================================================================
        // 3. HMAC-SHA256 SIGNATURE GENERATOR
        // =====================================================================
        private string GenerateHMACSHA256(string rawData, string secretKey)
        {
            byte[] keyBytes = Encoding.UTF8.GetBytes(secretKey);
            byte[] messageBytes = Encoding.UTF8.GetBytes(rawData);

            using (HMACSHA256 hmac = new HMACSHA256(keyBytes))
            {
                byte[] hashBytes = hmac.ComputeHash(messageBytes);
                StringBuilder hex = new StringBuilder(hashBytes.Length * 2);
                foreach (byte b in hashBytes)
                {
                    hex.AppendFormat("{0:x2}", b);
                }
                return hex.ToString();
            }
        }

        // =====================================================================
        // 4. API CALL: SEND HMAC TELEMETRY PING
        // =====================================================================
        public IEnumerator SendTelemetryPing(string playerId, int minutesPlayed)
        {
            string endpoint = $"{backendUrl}/api/v1/telemetry";
            long currentTimestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            string nonce = Guid.NewGuid().ToString("N");

            // Format raw string payload exactly as expected by main.py:
            // f"{player_id}:{minutes_played}:{timestamp}:{nonce}"
            string rawPayloadToSign = $"{playerId}:{minutesPlayed}:{currentTimestamp}:{nonce}";
            string calculatedSignature = GenerateHMACSHA256(rawPayloadToSign, hmacSecretKey);

            TelemetryPayload payload = new TelemetryPayload
            {
                player_id = playerId,
                minutes_played = minutesPlayed,
                timestamp = currentTimestamp,
                nonce = nonce,
                signature = calculatedSignature
            };

            string jsonRequestBody = JsonUtility.ToJson(payload);

            using (UnityWebRequest request = new UnityWebRequest(endpoint, "POST"))
            {
                byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonRequestBody);
                request.uploadHandler = new UploadHandlerRaw(bodyRaw);
                request.downloadHandler = new DownloadHandlerBuffer();
                request.SetRequestHeader("Content-Type", "application/json");

                yield return request.SendWebRequest();

                if (request.result == UnityWebRequest.Result.Success)
                {
                    TelemetryResponse response = JsonUtility.FromJson<TelemetryResponse>(request.downloadHandler.text);
                    Debug.Log($"[NEXUS SDK] Telemetry synced! Earned: {response.nex_earned} NEX. Balance: {response.total_spendable_nex}");

                    // Apply UI Updates
                    UpdatePlayerUI(response.total_spendable_nex, response.nametag_style);
                }
                else
                {
                    Debug.LogError($"[NEXUS SDK] Telemetry Error: {request.error} | Response: {request.downloadHandler.text}");
                }
            }
        }

        // =====================================================================
        // 5. API CALL: FETCH PLAYER PROFILE
        // =====================================================================
        public IEnumerator FetchPlayerProfile(string playerId)
        {
            string endpoint = $"{backendUrl}/api/v1/player/{playerId}";

            using (UnityWebRequest request = UnityWebRequest.Get(endpoint))
            {
                yield return request.SendWebRequest();

                if (request.result == UnityWebRequest.Result.Success)
                {
                    TelemetryResponse profile = JsonUtility.FromJson<TelemetryResponse>(request.downloadHandler.text);
                    UpdatePlayerUI(profile.total_spendable_nex, profile.nametag_style);
                }
            }
        }

        // =====================================================================
        // 6. UI RENDERING & DYNAMIC NAMETAG FORMATTING
        // =====================================================================
        private void UpdatePlayerUI(float nexBalance, NametagStyle nametagStyle)
        {
            if (nexBalanceText != null)
            {
                nexBalanceText.text = $"{nexBalance:N2} NEX";
            }

            if (playerNametagText != null && nametagStyle != null)
            {
                // Reconstruct display format: "⚡ [NEX-II] AlphaCommander" with Rich Text Color
                string formattedText = nametagStyle.display_name_formatted.Replace("{username}", currentUsername);
                
                // Colorize using Unity TextMeshPro Rich Text tags
                playerNametagText.text = $"<color={nametagStyle.text_color}>{formattedText}</color>";
            }
        }
    }
}
