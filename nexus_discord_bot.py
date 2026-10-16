import os
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI

# Load local environment variables from .env file
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
BACKEND_URL = "https://main-coin-backend.onrender.com"

# --- FASTAPI HEALTH CHECK FOR RENDER PORT BINDING ---
app = FastAPI()

@app.get("/")
async def health_check():
    return {"status": "NEXUS Core Online", "bot_active": True}

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
@bot.tree.command(name="claim-monthly", description="Claim spendable NEX balance on-chain to your linked Hedera wallet")
async def claim_monthly(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    player_id = "salina_pilot_01"

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(f"{BACKEND_URL}/api/v1/player/{player_id}/claim")

        if res.status_code == 200:
            data = res.json()
            amount = data.get("amount")
            wallet = data.get("wallet")
            await interaction.followup.send(
                f"🎉 **Claim Successful!**\n"
                f"Transferred **{amount} NEX** to `{wallet}`!\n"
                f"View on HashScan: https://hashscan.io/testnet/account/{wallet}"
            )
        else:
            try:
                err_detail = res.json().get("detail", res.text)
            except Exception:
                err_detail = f"Server returned status {res.status_code}: {res.text[:200]}"
                
            await interaction.followup.send(f"❌ **Claim Error:** {err_detail}")

    except httpx.TimeoutException:
        await interaction.followup.send("⏰ **Request Timed Out:** The backend or Hedera Testnet node took too long to respond.")
    except Exception as e:
        await interaction.followup.send(f"❌ **Bot Error:** {str(e)}")

# --- PRIVACY COMMAND: Link Account ---
@bot.tree.command(name="link-wallet", description="Link your Hedera Account ID (0.0.XXXXXX) to your NEX profile")
@app_commands.describe(account_id="Your Hedera Account ID (e.g. 0.0.10770972)")
async def link_wallet(interaction: discord.Interaction, account_id: str):
    await interaction.response.defer(ephemeral=True)
    player_id = "salina_pilot_01"  # Matches active profile in nexus-db

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(
                f"{BACKEND_URL}/api/wallet/link",
                json={"player_id": player_id, "hedera_account_id": account_id}
            )

        if res.status_code == 200:
            await interaction.followup.send(
                f"🔗 **Wallet