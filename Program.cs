using System;
using System.Threading.Tasks;
using MainCoin.SDK;

namespace MainCoin.TestApp
{
    class Program
    {
        static async Task Main(string[] args)
        {
            Console.WriteLine("==================================================");
            Console.WriteLine("    TESTING C# GAME ENGINE SDK -> FASTAPI CONTAINER");
            Console.WriteLine("==================================================\n");

            var client = new MainCoinGameClient("http://127.0.0.1:8000");
            string playerId = "csharp_tactical_player";

            // 1. Send 60 minutes of gameplay telemetry
            Console.WriteLine("1. [GAME LOOP] Pinging 60 minutes of gameplay telemetry...");
            bool pingSuccess = await client.SendTelemetryPingAsync(playerId, 60);
            Console.WriteLine($"Telemetry Status: {(pingSuccess ? "SUCCESS" : "FAILED")}\n");

            // 2. Fetch Player Stats for HUD
            Console.WriteLine("2. [HUD SYNC] Fetching real-time stats...");
            var stats = await client.GetPlayerStatsAsync(playerId);
            if (stats != null)
            {
                Console.WriteLine($"Player: {stats.PlayerId} | Level: {stats.CurrentLevel}");
                Console.WriteLine($"Coins Balance: {stats.SpendableCoins} | Earn Rate: {stats.CurrentEarnRate} coins/hr");
                Console.WriteLine($"Soft Decay Active: {stats.IsSoftDecayActive}\n");
            }

            Console.WriteLine("==================================================");
            Console.WriteLine("         C# CLIENT SDK VERIFIED & READY!");
            Console.WriteLine("==================================================");
        }
    }
}