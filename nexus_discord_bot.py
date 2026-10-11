import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands
from discord import app_commands
import httpx
from dotenv import load_dotenv

# Load local environment variables from .env file
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
BACKEND_URL = "https://main-coin-backend.onrender.com"

# --- HEALTH CHECK SERVER FOR RENDER PORT BINDING ---
class HealthCheckerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Nexus Discord Bot is running.")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

def run_health_check_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckerHandler)
    server.serve_forever()

# ----------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- PRIVACY COMMAND: Check NEX Balance & Profile ---
@bot.tree.command(name="balance", description="Check your Nexus spendable NEX balance and player profile")
@app_commands.describe(player_id="Your Nexus Player ID (e.g., salina_pilot_01)")
async def check_balance(interaction: discord.Interaction, player_id: str):
    await interaction.response.defer(ephemeral=True)
    
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.get(f"{BACKEND_URL}/api/v1/player/{player_id}")
            
            if res.status_code == 200:
                data = res.json()
                
                # --- EMBLEM & NAMETAG INTEGRATION ---
                nametag_data = data.get("nametag_style", {})
                emblem = nametag_data.get("emblem_icon")
                emblem_prefix = f"{emblem} " if emblem else ""
                
                embed = discord.Embed(
                    title=f"🔒 {emblem_prefix}Private Vault: {player_id}",
                    color=0x00F0FF
                )
                embed.add_field(name="Spendable NEX", value=f"**{data.get('spendable_nex', 0):,} NEX**", inline=True)
                embed.add_field(name="Total Earned", value=f"{data.get('total_nex_earned', 0):,} NEX", inline=True)
                embed.add_field(name="Hours Played", value=f"{data.get('total_hours_played', 0)} hrs", inline=True)
                
                prestige = nametag_data.get('prestige_tag', '[NEX]')
                embed.add_field(name="Prestige Rank", value=f"{prestige}", inline=False)
                embed.set_footer(text="Nexus Central Bank Network • Render Mainnet • Read-Only Encrypted")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Could not fetch profile for `{player_id}`. Status: {res.status_code}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"⚠️ Error connecting to Nexus Central Bank: {e}", ephemeral=True)        

# --- PRIVACY COMMAND: Claim Monthly Reward ---
@bot.tree.command(name="claim-monthly", description="Claim monthly loyalty NEX reward token allowance")
@app_commands.describe(player_id="Your Nexus Player ID")
async def claim_monthly(interaction: discord.Interaction, player_id: str):
    await interaction.response.defer(ephemeral=True)
    
    try:
        await interaction.followup.send(
            f"🎁 **Monthly Loyalty Claim Processed!**\nPlayer `{player_id}` profile active. Use `/balance` to check updated NEX.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"⚠️ Error processing claim: {e}", ephemeral=True)

# --- PRIVACY COMMAND: Link Account ---
@bot.tree.command(name="link", description="Link your game account using a generated code")
@app_commands.describe(code="The link code generated from the backend portal")
async def link(interaction: discord.Interaction, code: str):
    await interaction.response.defer(ephemeral=True)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/api/v1/link/verify",
                json={
                    "discord_id": str(interaction.user.id),
                    "discord_tag": str(interaction.user),
                    "link_code": code
                }
            )
            data = response.json()
            
            if response.status_code == 200 and data.get("status") == "success":
                player_id = data.get("player_id", "Unknown")
                await interaction.followup.send(
                    f"✅ **Account Linked Successfully!**\n"
                    f"• **Player ID:** `{player_id}`\n"
                    f"• **Discord User:** {interaction.user.mention}\n"
                    f"• **Rank:** `NODE`",
                    ephemeral=True
                )
            else:
                detail = data.get("detail", "Invalid or expired link code.")
                await interaction.followup.send(f"❌ **Link Failed:** {detail}", ephemeral=True)
                
    except Exception as e:
        await interaction.followup.send(f"❌ **Connection Error:** {str(e)}", ephemeral=True)

@bot.event
async def on_ready():
    print(f"🤖 Connected as {bot.user.name} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")

if __name__ == "__main__":
    if DISCORD_TOKEN:
        # Start HTTP server on background thread for Render health check
        threading.Thread(target=run_health_check_server, daemon=True).start()
        bot.run(DISCORD_TOKEN)
    else:
        print("⚠️ DISCORD_BOT_TOKEN is missing from environment variables!")