import os
import asyncio
import discord
from discord.ext import commands, tasks
from discord import app_commands
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
BACKEND_URL = "https://main-coin-backend.onrender.com"

# FastAPI Health Check for Render Port Binding
app = FastAPI()

@app.get("/")
async def health_check():
    return {"status": "NEXUS Core Online", "bot_active": True}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Helper: Resolve Linked Player ID dynamically
async def get_player_id_from_discord(client: httpx.AsyncClient, discord_id: str) -> str | None:
    try:
        res = await client.get(f"{BACKEND_URL}/api/v1/players/by-discord/{discord_id}")
        if res.status_code == 200:
            return res.json().get("player_id")
    except Exception as e:
        print(f"Error resolving Discord ID: {e}")
    return None

# --- COMMAND: Bind Account via Portal Code ---
@bot.tree.command(name="link", description="Bind your NEX player account using your portal link code")
@app_commands.describe(code="The code generated from the player portal (e.g. NX-UJ0R)")
async def link_code_command(interaction: discord.Interaction, code: str):
    await interaction.response.defer(ephemeral=True)
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(
                f"{BACKEND_URL}/api/v1/link/verify",
                json={
                    "link_code": code.strip().upper(),
                    "discord_id": str(interaction.user.id),
                    "discord_tag": str(interaction.user)
                }
            )
            if res.status_code == 200:
                data = res.json()
                await interaction.followup.send(
                    f"✅ **Account Bound Successfully!**\nDiscord `{interaction.user}` is now linked to Player ID `{data['player_id']}`.",
                    ephemeral=True
                )
            else:
                err = res.json().get("detail", "Failed to verify link code.")
                await interaction.followup.send(f"❌ **Error:** {err}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"⚠️ **Network Error:** {str(e)}", ephemeral=True)

# --- COMMAND: Check NEX Balance & Profile ---
@bot.tree.command(name="balance", description="Check your Nexus spendable NEX balance and player profile")
@app_commands.describe(player_id="Optional: Nexus Player ID. Leave blank if account is linked.")
async def check_balance(interaction: discord.Interaction, player_id: str | None = None):
    await interaction.response.defer(ephemeral=True)
    
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            target_player_id = player_id
            if not target_player_id:
                target_player_id = await get_player_id_from_discord(client, str(interaction.user.id))
                if not target_player_id:
                    await interaction.followup.send(
                        "❌ **Account Not Linked:** Please generate a code in the portal and run `/link` first, or supply a `player_id`.",
                        ephemeral=True
                    )
                    return

            res = await client.get(f"{BACKEND_URL}/api/v1/player/{target_player_id}")
            
            if res.status_code == 200:
                data = res.json()
                wallet_id = data.get("hedera_account_id", "0.0.11035514")
                nex_token_id = "0.0.10991235"
                onchain_balance = 0.0
                
                try:
                    mirror_res = await client.get(
                        f"https://testnet.mirrornode.hedera.com/api/v1/accounts/{wallet_id}/tokens"
                    )
                    if mirror_res.status_code == 200:
                        tokens = mirror_res.json().get("tokens", [])
                        for token in tokens:
                            if token.get("token_id") == nex_token_id:
                                onchain_balance = token.get("balance", 0) / 10000.0
                                break
                except Exception as mirror_err:
                    print(f"Mirror Node query failed: {mirror_err}")

                nametag_data = data.get("nametag_style", {})
                emblem = nametag_data.get("emblem_icon")
                emblem_prefix = f"{emblem} " if emblem else ""
                
                embed = discord.Embed(
                    title=f"🔒 {emblem_prefix}Private Vault: {target_player_id}",
                    color=0x00F0FF
                )
                
                embed.add_field(name="⛏️ Off-Chain Unclaimed", value=f"**{data.get('spendable_nex', 0):,.2f} NEX**", inline=True)
                embed.add_field(name="🔗 On-Chain (HashPack)", value=f"**{onchain_balance:,.2f} NEX**", inline=True)
                embed.add_field(name="🏆 Total Earned", value=f"{data.get('total_nex_earned', 0):,.2f} NEX", inline=True)
                embed.add_field(name="Hours Played", value=f"{data.get('total_hours_played', 0)} hrs", inline=True)
                
                prestige = nametag_data.get('prestige_tag', '[NEX]')
                embed.add_field(name="Prestige Rank", value=f"{prestige}", inline=False)
                embed.set_footer(text="Nexus Central Bank Network • Render Mainnet • Read-Only Encrypted")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Could not fetch profile for `{target_player_id}`. Status: {res.status_code}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"⚠️ Error connecting to Nexus Central Bank: {e}", ephemeral=True)

# --- COMMAND: Claim Monthly Reward ---
@bot.tree.command(name="claim-monthly", description="Claim spendable NEX balance on-chain to your linked Hedera wallet")
async def claim_monthly(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    async with httpx.AsyncClient(timeout=20.0) as client:
        player_id = await get_player_id_from_discord(client, str(interaction.user.id))
        
        if not player_id:
            await interaction.followup.send(
                "❌ **Account Not Linked:** Please generate a link code in the portal and run `/link` first!", 
                ephemeral=True
            )
            return

        try:
            res = await client.post(f"{BACKEND_URL}/api/v1/player/{player_id}/claim")

            if res.status_code == 200:
                data = res.json()
                amount = data.get("amount", 0.0)
                wallet = data.get("wallet", "N/A")
                await interaction.followup.send(
                    f"🎉 **Claim Successful!**\n"
                    f"Transferred **{amount:.2f} NEX** for player `{player_id}` to `{wallet}`!\n"
                    f"View on HashScan: https://hashscan.io/testnet/account/{wallet}",
                    ephemeral=True
                )
            else:
                try:
                    err_detail = res.json().get("detail", res.text)
                except Exception:
                    err_detail = f"Server returned status {res.status_code}: {res.text[:200]}"
                await interaction.followup.send(f"❌ **Claim Error:** {err_detail}", ephemeral=True)

        except httpx.TimeoutException:
            await interaction.followup.send("⏰ **Request Timed Out:** Backend took too long to respond.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ **Bot Error:** {str(e)}", ephemeral=True)

# --- COMMAND: Link Wallet ---
@bot.tree.command(name="link-wallet", description="Link your Hedera Account ID (0.0.XXXXXX) to your NEX profile")
@app_commands.describe(account_id="Your Hedera Account ID (e.g. 0.0.10770972)")
async def link_wallet(interaction: discord.Interaction, account_id: str):
    await interaction.response.defer(ephemeral=True)

    async with httpx.AsyncClient(timeout=20.0) as client:
        player_id = await get_player_id_from_discord(client, str(interaction.user.id))
        
        if not player_id:
            await interaction.followup.send(
                "❌ **Account Not Linked:** Please generate a link code in the portal and run `/link` first!", 
                ephemeral=True
            )
            return

        try:
            res = await client.post(
                f"{BACKEND_URL}/api/wallet/link",
                json={"player_id": player_id, "hedera_account_id": account_id}
            )

            if res.status_code == 200:
                await interaction.followup.send(
                    f"🔗 **Wallet Linked Successfully!**\n"
                    f"Player: `{player_id}`\n"
                    f"Hedera Account: `{account_id}`\n\n"
                    f"Make sure account `{account_id}` has associated Token `0.0.10991235` in HashPack or Kabila!",
                    ephemeral=True
                )
            else:
                err_msg = res.json().get("detail", "Failed to link wallet.")
                await interaction.followup.send(f"❌ **Error:** {err_msg}", ephemeral=True)
        except httpx.TimeoutException:
            await interaction.followup.send("⏰ **Request Timed Out:** Backend took too long to respond.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ **Bot Error:** {str(e)}", ephemeral=True)
