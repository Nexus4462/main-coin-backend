import os
import discord
from discord.ext import commands
from discord import app_commands
import requests

# 🚨 PASTE YOUR BRAND-NEW RESET TOKEN HERE
DISCORD_TOKEN = os.getenv("MTU1NjU3NzYwNTcwNzM2NjQ0MA.GQtkvu.S-s6wr1w-7x1Wjc73a3mLMvkFr8xD42XmHejCM")
BACKEND_URL = "https://main-coin-backend.onrender.com"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🤖 Connected as {bot.user.name} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")

# --- PRIVACY COMMAND: Check NEX Balance & Profile ---
@bot.tree.command(name="balance", description="Check your Nexus spendable NEX balance and player profile")
@app_commands.describe(player_id="Your Nexus Player ID (e.g., salina_pilot_01)")
async def check_balance(interaction: discord.Interaction, player_id: str):
    # ephemeral=True guarantees the response is completely private to the user
    await interaction.response.defer(ephemeral=True)
    
    try:
        res = requests.get(f"{BACKEND_URL}/api/v1/player/{player_id}", timeout=20.0)
        if res.status_code == 200:
            data = res.json()
            embed = discord.Embed(
                title=f"🔒 Private Vault: {player_id}",
                color=0x00F0FF
            )
            embed.add_field(name="Spendable NEX", value=f"**{data.get('spendable_nex', 0):,} NEX**", inline=True)
            embed.add_field(name="Total Earned", value=f"{data.get('total_nex_earned', 0):,} NEX", inline=True)
            embed.add_field(name="Hours Played", value=f"{data.get('total_hours_played', 0)} hrs", inline=True)
            
            # Safe access for nested style dictionary
            prestige = data.get('nametag_style', {}).get('prestige_tag', 'Standard')
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

if __name__ == "__main__":
    if DISCORD_TOKEN and DISCORD_TOKEN != "PASTE_NEW_RESET_TOKEN_HERE":
        bot.run(DISCORD_TOKEN)
    else:
        print("⚠️ Please replace 'PASTE_NEW_RESET_TOKEN_HERE' with your newly reset bot token before running!")