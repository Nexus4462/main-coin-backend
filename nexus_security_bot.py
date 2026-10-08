import os
import discord
from discord.ext import commands, tasks
import requests

# Security Bot Credentials & Channel Routing
DISCORD_TOKEN = os.getenv("MTU1NjU3NzYwNTcwNzM2NjQ0MA.GQtkvu.S-s6wr1w-7x1Wjc73a3mLMvkFr8xD42XmHejCM")  # Use your bot token
BACKEND_URL = "https://main-coin-backend.onrender.com"
ADMIN_CHANNEL_ID = 1557639936386277488  # Replace with your copied 18-digit #admin-alerts Channel ID

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Track processed security alerts to prevent duplicate notifications
processed_alert_ids = set()

@bot.event
async def on_ready():
    print(f"🛡️ Security Sentinel online as {bot.user.name} (ID: {bot.user.id})")
    print(f"📢 Monitoring Render backend honeypots -> Routing to Channel ID: {ADMIN_CHANNEL_ID}")
    
    # Start the continuous background polling loop
    if not poll_security_logs.is_running():
        poll_security_logs.start()

# --- BACKGROUND TASK: Poll Backend Honeypots & Security Audit Logs ---
@tasks.loop(seconds=15.0)
async def poll_security_logs():
    channel = bot.get_channel(ADMIN_CHANNEL_ID)
    if not channel:
        print(f"⚠️ Warning: Unable to locate admin channel ID {ADMIN_CHANNEL_ID}. Check channel permissions.")
        return

    try:
        # Request latest security audit events from Render backend
        res = requests.get(f"{BACKEND_URL}/api/v1/admin/security-logs", timeout=10.0)
        
        if res.status_code == 200:
            logs = res.json()
            # If backend returns a list of audit events
            for alert in logs:
                alert_id = alert.get("id") or f"{alert.get('ip')}_{alert.get('timestamp')}"
                
                if alert_id not in processed_alert_ids:
                    processed_alert_ids.add(alert_id)
                    
                    # Construct high-visibility security embed
                    embed = discord.Embed(
                        title="🚨 NEXUS CENTRAL BANK SECURITY ALERT",
                        description=f"**Threat Detected:** {alert.get('event_type', 'Honeypot Triggered')}",
                        color=0xFF0000  # Bright Red
                    )
                    embed.add_field(name="IP Address", value=f"`{alert.get('ip', 'Unknown')}`", inline=True)
                    embed.add_field(name="Requested URI", value=f"`{alert.get('path', '/admin')}`", inline=True)
                    embed.add_field(name="Action Taken", value=f"**{alert.get('action', 'IP Blacklisted')}**", inline=False)
                    embed.set_footer(text="Nexus Automated Sentinel Guard • Render Security Net")
                    
                    await channel.send(embed=embed)
                    
    except Exception as e:
        # Quiet timeout handling for Render cold cycles
        pass

@poll_security_logs.before_loop
async def before_poll():
    await bot.wait_until_ready()

if __name__ == "__main__":
    if DISCORD_TOKEN and DISCORD_TOKEN != "PASTE_YOUR_BOT_TOKEN_HERE":
        bot.run(DISCORD_TOKEN)
    else:
        print("⚠️ Please update DISCORD_TOKEN and ADMIN_CHANNEL_ID before running!")