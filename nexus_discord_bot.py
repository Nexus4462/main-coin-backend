import os
import asyncio
import discord
from discord.ext import commands
import discord.ext import commands, tasks
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
                
                # Fetch target wallet ID (default to player wallet)
                wallet_id = data.get("hedera_account_id", "0.0.11035514")
                nex_token_id = "0.0.10991235"
                onchain_balance = 0.0
                
                # Query Hedera Mirror Node for live on-chain token balance
                try:
                    mirror_res = await client.get(
                        f"https://testnet.mirrornode.hedera.com/api/v1/accounts/{wallet_id}/tokens"
                    )
                    if mirror_res.status_code == 200:
                        tokens = mirror_res.json().get("tokens", [])
                        for token in tokens:
                            if token.get("token_id") == nex_token_id:
                                # Divide by 10,000 for 4 decimal places
                                onchain_balance = token.get("balance", 0) / 10000.0
                                break
                except Exception as mirror_err:
                    print(f"Mirror Node query failed: {mirror_err}")

                nametag_data = data.get("nametag_style", {})
                emblem = nametag_data.get("emblem_icon")
                emblem_prefix = f"{emblem} " if emblem else ""
                
                embed = discord.Embed(
                    title=f"🔒 {emblem_prefix}Private Vault: {player_id}",
                    color=0x00F0FF
                )
                
                # Off-Chain Pending / Spendable
                embed.add_field(
                    name="⛏️ Off-Chain Unclaimed", 
                    value=f"**{data.get('spendable_nex', 0):,.2f} NEX**", 
                    inline=True
                )
                
                # Live On-Chain HashPack Wallet Balance
                embed.add_field(
                    name="🔗 On-Chain (HashPack)", 
                    value=f"**{onchain_balance:,.2f} NEX**", 
                    inline=True
                )
                
                embed.add_field(
                    name="🏆 Total Earned", 
                    value=f"{data.get('total_nex_earned', 0):,.2f} NEX", 
                    inline=True
                )
                embed.add_field(
                    name="Hours Played", 
                    value=f"{data.get('total_hours_played', 0)} hrs", 
                    inline=True
                )
                
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
                f"Transferred **{amount:.2f} NEX** to `{wallet}`!\n"
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
                f"🔗 **Wallet Linked Successfully!**\n"
                f"Player: `{player_id}`\n"
                f"Hedera Account: `{account_id}`\n\n"
                f"Make sure account `{account_id}` has associated Token `0.0.10991235` in HashPack or Kabila!"
            )
        else:
            err_msg = res.json().get("detail", "Failed to link wallet.")
            await interaction.followup.send(f"❌ **Error:** {err_msg}")
    except httpx.TimeoutException:
        await interaction.followup.send("⏰ **Request Timed Out:** Backend took too long to respond.")
    except Exception as e:
        await interaction.followup.send(f"❌ **Bot Error:** {str(e)}")

# --- PRIVACY COMMAND: cosmetic catalogue ---

COSMETIC_CATALOGUE = {
    "neon_trail": {"name": "Neon Cyan Glider Trail", "price": 50.0, "emblem": "✨"},
    "apex_badge": {"name": "Apex Pilot Nametag Frame", "price": 150.0, "emblem": "👑"},
    "obsidian_skin": {"name": "Obsidian Mech Armor", "price": 300.0, "emblem": "🛡️"}
}

@bot.tree.command(name="buy-cosmetic", description="Purchase cosmetics using off-chain or on-chain NEX")
@app_commands.describe(
    item_id="Item ID to purchase (e.g., neon_trail, apex_badge, obsidian_skin)",
    player_id="Your Nexus Player ID (e.g., salina_pilot_01)"
)
async def buy_cosmetic(interaction: discord.Interaction, item_id: str, player_id: str):
    await interaction.response.defer(ephemeral=True)
    
    item_id = item_id.lower().strip()
    if item_id not in COSMETIC_CATALOGUE:
        items_list = "\n".join([f"• `{k}` - {v['name']} ({v['price']} NEX)" for k, v in COSMETIC_CATALOGUE.items()])
        await interaction.followup.send(f"❌ Invalid item ID! Available cosmetics:\n{items_list}", ephemeral=True)
        return

    item = COSMETIC_CATALOGUE[item_id]
    
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            payload = {
                "player_id": player_id,
                "item_id": item_id,
                "price": item["price"]
            }
            res = await client.post(f"{BACKEND_URL}/api/v1/store/buy", json=payload)
            
            if res.status_code == 200:
                data = res.json()
                embed = discord.Embed(
                    title=f"🛍️ Purchase Successful: {item['name']}",
                    color=0x00FF88
                )
                embed.add_field(name="Item Acquired", value=f"{item['emblem']} {item['name']}", inline=True)
                embed.add_field(name="Price Paid", value=f"**{item['price']:.2f} NEX**", inline=True)
                embed.add_field(name="Remaining Off-Chain Balance", value=f"{data.get('new_spendable_balance', 0):,.2f} NEX", inline=False)
                embed.set_footer(text="Nexus Store • Deflationary Sink Enabled")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                err_detail = res.json().get("detail", "Transaction failed")
                await interaction.followup.send(f"❌ Purchase failed: {err_detail}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"⚠️ Central Bank connection error: {e}", ephemeral=True)



@bot.event
async def on_ready():
    print(f"🤖 Connected as {bot.user.name} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")

from discord.ext import tasks
import httpx

# 1. Define the 24-hour reminder task
@tasks.loop(hours=24)
async def check_unclaimed_nex_reminder():
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.get(f"{BACKEND_URL}/api/v1/players/unclaimed")
            if res.status_code == 200:
                players = res.json().get("players", [])
                
                # Replace with your actual Discord notification channel ID
                channel = bot.get_channel(1234567890123456789) 
                
                for player in players:
                    unclaimed = player.get("spendable_nex", 0.0)
                    discord_id = player.get("discord_user_id")
                    
                    if unclaimed >= 10.0 and channel:
                        embed = discord.Embed(
                            title="🪙 Daily NEX Vault Alert",
                            description=f"<@{discord_id}>, you have **{unclaimed:,.2f} NEX** waiting in your unclaimed off-chain vault!",
                            color=0xFFD700
                        )
                        embed.add_field(
                            name="Action Required", 
                            value="Run **`/claim-monthly`** to transfer your rewards directly to your HashPack wallet."
                        )
                        embed.set_footer(text="Nexus Central Bank • Automated 24h Reminder Loop")
                        await channel.send(embed=embed)
    except Exception as e:
        print(f"Error in daily claim reminder loop: {e}")

@check_unclaimed_nex_reminder.before_loop
async def before_reminder_loop():
    await bot.wait_until_ready()

# 2. Hook into your existing on_ready event
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} - Nexus Bot ready.")
    
    # Start the task loop when the bot connects to Discord
    if not check_unclaimed_nex_reminder.is_running():
        check_unclaimed_nex_reminder.start()
        print("🚀 Daily NEX unclaimed reminder loop started.")

# --- FASTAPI STARTUP EVENT (LAUNCHES BOT) ---
@app.on_event("startup")
async def startup_event():
    if DISCORD_TOKEN:
        asyncio.create_task(bot.start(DISCORD_TOKEN))
    else:
        print("⚠️ DISCORD_BOT_TOKEN is missing from environment variables!")