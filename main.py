import os
import sqlite3
import logging
import requests
import discord
from discord import app_commands, ui
from discord.ext import commands
from dotenv import load_dotenv
from hiero_sdk_python import (
    Client,
    AccountId,
    PrivateKey,
    TokenId,
    TokenAssociateTransaction,
    TransferTransaction,
    Hbar
)

# -------------------------------------------------------------------
# Setup & Environment Configuration
# -------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ADMIN_CHANNEL_ID = int(os.getenv("ADMIN_CHANNEL_ID", "0"))  # Set your #admin-alerts channel ID
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID", "0"))        # Optional Admin role ID
CURRENT_ENV = os.getenv("HEDERA_NETWORK", "testnet").lower() # 'testnet' or 'mainnet'

OPERATOR_ID = AccountId.from_string(os.getenv("HEDERA_OPERATOR_ID", "0.0.10770972"))
raw_key = os.getenv("HEDERA_OPERATOR_KEY", "").strip().strip('"').strip("'")
OPERATOR_KEY = PrivateKey.from_string(raw_key) if raw_key else None
TOKEN_ID = TokenId.from_string(os.getenv("TOKEN_ID", "0.0.10991235"))

MAX_CLAIM_LIMIT = 500.0  # Max NEX per single claim

# Initialize Hedera Client
if CURRENT_ENV == "mainnet":
    client = Client.for_mainnet()
else:
    client = Client.for_testnet()

client.set_operator(OPERATOR_ID, OPERATOR_KEY)

# Initialize Discord Bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------------------------------------------------------
# Database Initialization (SQLite)
# -------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    
    # Dual-wallet support (Testnet & Mainnet) with UNIQUE constraints
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            discord_id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            testnet_wallet TEXT UNIQUE DEFAULT NULL,
            mainnet_wallet TEXT UNIQUE DEFAULT NULL,
            spendable_nex REAL DEFAULT 0.0,
            total_earned_nex REAL DEFAULT 0.0
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -------------------------------------------------------------------
# Helper Functions & Hedera Utilities
# -------------------------------------------------------------------
def get_user_profile(discord_id: str):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT discord_id, profile_id, testnet_wallet, mainnet_wallet, spendable_nex, total_earned_nex FROM user_profiles WHERE discord_id = ?", (str(discord_id),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "discord_id": row[0],
            "profile_id": row[1],
            "testnet_wallet": row[2],
            "mainnet_wallet": row[3],
            "spendable_nex": row[4],
            "total_earned_nex": row[5]
        }
    return None

def update_user_wallet(discord_id: str, profile_id: str, account_id: str, env: str):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    column = "testnet_wallet" if env == "testnet" else "mainnet_wallet"
    
    cursor.execute("SELECT discord_id FROM user_profiles WHERE discord_id = ?", (str(discord_id),))
    if cursor.fetchone():
        cursor.execute(f"UPDATE user_profiles SET {column} = ? WHERE discord_id = ?", (account_id, str(discord_id)))
    else:
        cursor.execute(f"INSERT INTO user_profiles (discord_id, profile_id, {column}) VALUES (?, ?, ?)", (str(discord_id), profile_id, account_id))
    
    conn.commit()
    conn.close()

def check_token_association(account_id: str, token_id_str: str) -> bool:
    """Checks Hedera Mirror Node API to verify if token is associated."""
    base_url = "https://mainnet-public.mirrornode.hedera.com" if CURRENT_ENV == "mainnet" else "https://testnet.mirrornode.hedera.com"
    url = f"{base_url}/api/v1/accounts/{account_id}/tokens"
    try:
        resp = requests.get(url, params={"token.id": token_id_str, "limit": 1}, timeout=5)
        if resp.status_code == 200:
            tokens = resp.json().get("tokens", [])
            return len(tokens) > 0
    except Exception as e:
        logging.error(f"Mirror node check error: {e}")
    return False

async def ensure_treasury_associated():
    """Startup auto-fix: Ensures Treasury (0.0.10770972) is associated on boot."""
    try:
        logging.info(f"Running Treasury association check for {OPERATOR_ID} with Token {TOKEN_ID}...")
        tx = TokenAssociateTransaction().set_account_id(OPERATOR_ID).set_token_ids([TOKEN_ID]).freeze_with(client)
        signed_tx = tx.sign(OPERATOR_KEY)
        receipt = signed_tx.execute(client)
        logging.info(f"✅ Treasury Association Status: {receipt.status}")
    except Exception as e:
        if "184" in str(e) or "TOKEN_ALREADY_ASSOCIATED_TO_ACCOUNT" in str(e):
            logging.info("ℹ️ Treasury account is already associated with token.")
        else:
            logging.warning(f"Treasury association note: {e}")

# -------------------------------------------------------------------
# Discord Interactive Views (Re-link Safety Modals & Buttons)
# -------------------------------------------------------------------
class RelinkReasonModal(ui.Modal, title="Confirm Wallet Re-Link"):
    reason = ui.TextInput(
        label="Reason for wallet change",
        placeholder="e.g., New phone / HashPack account reset",
        required=True,
        max_length=200
    )

    def __init__(self, old_wallet: str, new_wallet: str):
        super().__init__()
        self.old_wallet = old_wallet
        self.new_wallet = new_wallet

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        profile_id = f"user_{user_id[:6]}"
        
        try:
            update_user_wallet(user_id, profile_id, self.new_wallet, CURRENT_ENV)
        except sqlite3.IntegrityError:
            await interaction.response.send_message("❌ Error: This wallet address is already linked to another Discord user!", ephemeral=True)
            return

        # Audit Alert to Private Admin Channel
        if ADMIN_CHANNEL_ID:
            admin_chan = interaction.client.get_channel(ADMIN_CHANNEL_ID)
            if admin_chan:
                embed = discord.Embed(title="⚠️ Wallet Re-Link Executed", color=discord.Color.orange())
                embed.add_field(name="User", value=f"{interaction.user.mention} (`{user_id}`)", inline=False)
                embed.add_field(name="Environment", value=CURRENT_ENV.upper(), inline=True)
                embed.add_field(name="Old Wallet", value=f"`{self.old_wallet}`", inline=True)
                embed.add_field(name="New Wallet", value=f"`{self.new_wallet}`", inline=True)
                embed.add_field(name="Reason", value=f"`{self.reason.value}`", inline=False)
                await admin_chan.send(embed=embed)

        await interaction.response.send_message(f"✅ Wallet re-linked successfully to `{self.new_wallet}` ({CURRENT_ENV.upper()}).", ephemeral=True)

class RelinkConfirmView(ui.View):
    def __init__(self, old_wallet: str, new_wallet: str):
        super().__init__(timeout=60)
        self.old_wallet = old_wallet
        self.new_wallet = new_wallet

    @ui.button(label="Confirm Re-Link", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(RelinkReasonModal(self.old_wallet, self.new_wallet))

    @ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("❌ Re-link request cancelled. Your current wallet remains linked.", ephemeral=True)

# -------------------------------------------------------------------
# Bot Commands
# -------------------------------------------------------------------
@bot.event
async def on_ready():
    logging.info(f"Bot active as {bot.user} ({bot.user.id})")
    
    # Auto-associate Treasury on startup
    await ensure_treasury_associated()
    
    try:
        synced = await bot.tree.sync()
        logging.info(f"Synced {len(synced)} application commands.")
    except Exception as e:
        logging.error(f"Command sync failed: {e}")

@bot.tree.command(name="setup", description="Guide on setting up HashPack to receive NEX tokens")
async def setup(interaction: discord.Interaction):
    net_name = "Testnet" if CURRENT_ENV == "testnet" else "Mainnet"
    
    embed = discord.Embed(title=f"🛠️ Nexus Wallet Setup Guide ({net_name})", color=discord.Color.blue())
    
    if CURRENT_ENV == "testnet":
        embed.add_field(
            name="1. Enable Testnet in HashPack",
            value="Open HashPack -> **Settings** -> **Developer Mode** -> Toggle **Testnet**.",
            inline=False
        )
    else:
        embed.add_field(
            name="1. Standard HashPack Account",
            value="Open HashPack (Mainnet is active by default).",
            inline=False
        )
        
    embed.add_field(
        name="2. Associate NEX Token",
        value=f"In HashPack, tap **Add Token (+)** under Assets and enter:\n`{TOKEN_ID}`",
        inline=False
    )
    embed.add_field(
        name="3. Link Wallet to Discord",
        value="Run `/link-wallet account_id:0.0.XXXXXXX` in this server.",
        inline=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="balance", description="Check your accrued NEX earnings and linked wallet")
async def balance(interaction: discord.Interaction):
    user_data = get_user_profile(str(interaction.user.id))
    
    if not user_data:
        await interaction.response.send_message("❌ Profile not found! Run `/setup` to get started.", ephemeral=True)
        return

    active_wallet = user_data["testnet_wallet"] if CURRENT_ENV == "testnet" else user_data["mainnet_wallet"]
    
    embed = discord.Embed(title="💳 Nexus Player Vault Summary", color=discord.Color.green())
    embed.add_field(name="Profile ID", value=user_data["profile_id"], inline=True)
    embed.add_field(name="Spendable NEX", value=f"{user_data['spendable_nex']:.4f} NEX", inline=True)
    embed.add_field(name="Active Network", value=CURRENT_ENV.upper(), inline=True)
    embed.add_field(name="Linked Wallet", value=f"`{active_wallet or 'None Linked'}`", inline=False)
    embed.set_footer(text=f"Nexus Central Bank • Render {CURRENT_ENV.capitalize()}")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="link-wallet", description="Link your Hedera account ID to your profile")
@app_commands.describe(account_id="Your Hedera Account ID (e.g., 0.0.11035516)")
async def link_wallet(interaction: discord.Interaction, account_id: str):
    account_id = account_id.strip()
    user_id = str(interaction.user.id)
    user_data = get_user_profile(user_id)
    active_wallet = user_data["testnet_wallet"] if (user_data and CURRENT_ENV == "testnet") else (user_data["mainnet_wallet"] if user_data else None)

    # Prompt user with interactive buttons if they are replacing an existing wallet link
    if active_wallet and active_wallet != account_id:
        view = RelinkConfirmView(old_wallet=active_wallet, new_wallet=account_id)
        await interaction.response.send_message(
            f"⚠️ You already have `{active_wallet}` linked to your account. Are you sure you want to replace it with `{account_id}`?",
            view=view,
            ephemeral=True
        )
        return

    profile_id = user_data["profile_id"] if user_data else f"salina_pilot_{user_id[:4]}"
    
    try:
        update_user_wallet(user_id, profile_id, account_id, CURRENT_ENV)
    except sqlite3.IntegrityError:
        await interaction.response.send_message("❌ Error: This wallet address is already linked to another user!", ephemeral=True)
        return

    embed = discord.Embed(title="🔗 Wallet Linked Successfully!", color=discord.Color.blue())
    embed.add_field(name="Player Profile", value=profile_id, inline=True)
    embed.add_field(name="Network Target", value=CURRENT_ENV.upper(), inline=True)
    embed.add_field(name="Hedera Account", value=f"`{account_id}`", inline=False)
    embed.add_field(
        name="Important Note",
        value=f"Ensure `{account_id}` has associated Token `{TOKEN_ID}` in HashPack on **{CURRENT_ENV.upper()}**!",
        inline=False
    )
    embed.set_footer(text=f"Nexus Central Bank Network • Render {CURRENT_ENV.capitalize()}")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="claim-monthly", description="Claim your monthly accrued NEX token distribution")
async def claim_monthly(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    user_id = str(interaction.user.id)
    user_data = get_user_profile(user_id)

    if not user_data:
        await interaction.followup.send("❌ Profile not found. Please run `/setup` first.", ephemeral=True)
        return

    target_wallet = user_data["testnet_wallet"] if CURRENT_ENV == "testnet" else user_data["mainnet_wallet"]
    spendable = user_data["spendable_nex"]

    if not target_wallet:
        await interaction.followup.send(f"❌ You have not linked a {CURRENT_ENV.upper()} wallet! Run `/link-wallet` first.", ephemeral=True)
        return

    if spendable <= 0:
        await interaction.followup.send("❌ You have no spendable NEX tokens to claim right now.", ephemeral=True)
        return

    if spendable > MAX_CLAIM_LIMIT:
        await interaction.followup.send(f"⚠️ Claim exceeds safety threshold ({MAX_CLAIM_LIMIT} NEX max). Contact an admin.", ephemeral=True)
        return

    # Mirror Node Pre-check for Token Association
    if not check_token_association(target_wallet, str(TOKEN_ID)):
        await interaction.followup.send(
            f"❌ **Token Not Associated!**\nYour wallet `{target_wallet}` has not added NEX (`{TOKEN_ID}`) under Assets in HashPack on **{CURRENT_ENV.upper()}**.",
            ephemeral=True
        )
        return

    # Execute On-Chain HTS Transfer
    try:
        recipient_id = AccountId.from_string(target_wallet)
        
        # Convert float NEX tokens to integer base units (assuming 4 decimal places)
        token_amount = int(spendable * 10000)

        tx = (
            TransferTransaction()
            .add_token_transfer(TOKEN_ID, OPERATOR_ID, -token_amount)
            .add_token_transfer(TOKEN_ID, recipient_id, token_amount)
            .freeze_with(client)
        )
        signed_tx = tx.sign(OPERATOR_KEY)
        receipt = signed_tx.execute(client)
        tx_id = signed_tx.transaction_id.to_string()

        # Update DB: Zero out spendable balance
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE user_profiles SET spendable_nex = 0.0 WHERE discord_id = ?", (user_id,))
        conn.commit()
        conn.close()

        # Public / Ephemeral User Success Response
        embed = discord.Embed(title="✅ NEX Settlement Complete!", color=discord.Color.green())
        embed.add_field(name="Amount Claimed", value=f"{spendable:.4f} NEX", inline=True)
        embed.add_field(name="Destination Wallet", value=f"`{target_wallet}`", inline=True)
        embed.add_field(name="Status", value=str(receipt.status), inline=False)
        embed.set_footer(text=f"Nexus Central Bank Network • Render {CURRENT_ENV.capitalize()}")
        await interaction.followup.send(embed=embed, ephemeral=True)

        # Audit Log to Private Admin Channel
        if ADMIN_CHANNEL_ID:
            admin_chan = interaction.client.get_channel(ADMIN_CHANNEL_ID)
            if admin_chan:
                log_embed = discord.Embed(title="💸 NEX Claim Settled", color=discord.Color.gold())
                log_embed.add_field(name="User", value=f"{interaction.user.mention} (`{user_id}`)", inline=True)
                log_embed.add_field(name="Amount", value=f"{spendable:.4f} NEX", inline=True)
                log_embed.add_field(name="Wallet", value=f"`{target_wallet}` ({CURRENT_ENV.upper()})", inline=False)
                log_embed.add_field(
                    name="HashScan Link",
                    value=f"[View Explorer](https://hashscan.io/{CURRENT_ENV}/transaction/{tx_id})",
                    inline=False
                )
                await admin_chan.send(embed=log_embed)

    except Exception as e:
        logging.error(f"Claim transfer error: {e}")
        await interaction.followup.send(f"❌ **Claim Error:** Hedera transfer rejected with error: `{e}`", ephemeral=True)

# -------------------------------------------------------------------
# Run Bot Application
# -------------------------------------------------------------------
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
