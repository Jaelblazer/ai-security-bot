import discord
from discord.ext import commands, tasks
import openai
import os
import json
import logging
import asyncio
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import schedule
import time
import threading

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')

# OpenAI configuration
openai.api_key = os.getenv("OPENROUTER_API_KEY")
openai.api_base = "https://openrouter.ai/api/v1"

def query_openrouter(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="qwen/qwen3-14b:free",
            messages=[{"role": "user", "content": prompt}]
        )
        if isinstance(response, dict) and 'choices' in response and response['choices']:
            return response['choices'][0]['message']['content']
        else:
            print("OpenRouter response missing 'choices':", response)
            return None
    except Exception as e:
        print("OpenRouter error:", e)
        return None

class SecurityMonitor:
    def __init__(self):
        self.threat_feeds = [
            "https://api.github.com/repos/OWASP/CheatSheetSeries/commits",
            "https://api.github.com/repos/OWASP/Top10/commits",
            "https://api.github.com/repos/OWASP/API-Security/commits"
        ]
        self.alert_channels = []
        self.threat_database = []
        
    async def analyze_threat(self, threat_data):
        """Analyze threat data using OpenRouter LLM"""
        try:
            prompt = f"""
            Threat Data: {json.dumps(threat_data, indent=2)}
            Provide response in JSON format:
            {{
                "threat_level": "level",
                "impact": "description",
                "recommendations": ["action1", "action2"],
                "affected_systems": ["system1", "system2"],
                "ai_confidence": 0.95
            }}
            """
            analysis_text = query_openrouter(prompt)
            if analysis_text is not None:
                analysis = json.loads(analysis_text)
                return analysis
            else:
                logger.error("OpenRouter did not return analysis text.")
                return {
                    "threat_level": "Unknown",
                    "impact": "Unable to analyze",
                    "recommendations": ["Review manually"],
                    "affected_systems": ["Unknown"],
                    "ai_confidence": 0.0
                }
        except Exception as e:
            logger.error(f"Error analyzing threat: {e}")
            return {
                "threat_level": "Unknown",
                "impact": "Unable to analyze",
                "recommendations": ["Review manually"],
                "affected_systems": ["Unknown"],
                "ai_confidence": 0.0
            }
    
    async def fetch_threat_intelligence(self):
        """Fetch threat intelligence from various sources"""
        threats = []
        
        for feed in self.threat_feeds:
            try:
                response = requests.get(feed, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        latest = data[0]
                        threat = {
                            "source": feed,
                            "timestamp": datetime.now().isoformat(),
                            "title": latest.get("commit", {}).get("message", "Unknown"),
                            "author": latest.get("commit", {}).get("author", {}).get("name", "Unknown"),
                            "url": latest.get("html_url", ""),
                            "type": "security_update"
                        }
                        threats.append(threat)
                        
            except Exception as e:
                logger.error(f"Error fetching from {feed}: {e}")
                
        return threats
    
    async def send_alert(self, channel_id, threat_data, analysis):
        """Send formatted alert to Discord channel"""
        try:
            channel = bot.get_channel(int(channel_id))
            if isinstance(channel, discord.TextChannel):
                embed = discord.Embed(
                    title=f"🚨 Security Alert - {analysis['threat_level'].upper()}",
                    description=f"**Threat:** {threat_data['title']}",
                    color=self.get_threat_color(analysis['threat_level']),
                    timestamp=datetime.now()
                )
                
                embed.add_field(name="Impact", value=analysis['impact'], inline=False)
                embed.add_field(name="Affected Systems", value=", ".join(analysis['affected_systems']), inline=True)
                embed.add_field(name="AI Confidence", value=f"{analysis['ai_confidence']*100:.1f}%", inline=True)
                
                recommendations = "\n".join([f"• {rec}" for rec in analysis['recommendations']])
                embed.add_field(name="Recommendations", value=recommendations, inline=False)
                
                embed.add_field(name="Source", value=f"[View Details]({threat_data['url']})", inline=True)
                embed.add_field(name="Author", value=threat_data['author'], inline=True)
                
                embed.set_footer(text="AI Security Monitor Bot")
                
                await channel.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    def get_threat_color(self, threat_level):
        """Get Discord embed color based on threat level"""
        colors = {
            "low": 0x00ff00,      # Green
            "medium": 0xffff00,   # Yellow
            "high": 0xff8800,     # Orange
            "critical": 0xff0000   # Red
        }
        return colors.get(threat_level.lower(), 0x808080)  # Gray default

# Initialize security monitor
security_monitor = SecurityMonitor()

@bot.event
async def on_ready():
    print("on_ready event triggered")
    logger.info(f'{bot.user} has connected to Discord!')
    monitor_security.start()

@bot.command(name='setup')
async def setup_monitoring(ctx):
    """Set up security monitoring for this channel"""
    try:
        security_monitor.alert_channels.append(str(ctx.channel.id))
        embed = discord.Embed(
            title="✅ Security Monitoring Setup",
            description="This channel is now configured for security alerts!",
            color=0x00ff00
        )
        embed.add_field(name="Channel ID", value=ctx.channel.id, inline=True)
        embed.add_field(name="Status", value="Active", inline=True)
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error setting up monitoring: {e}")

@bot.command(name='status')
async def check_status(ctx):
    """Check the status of security monitoring"""
    embed = discord.Embed(
        title="🔍 Security Monitor Status",
        color=0x0099ff
    )
    embed.add_field(name="Active Channels", value=len(security_monitor.alert_channels), inline=True)
    embed.add_field(name="Threat Feeds", value=len(security_monitor.threat_feeds), inline=True)
    embed.add_field(name="Bot Status", value="🟢 Online", inline=True)
    await ctx.send(embed=embed)

@bot.command(name='scan')
async def manual_scan(ctx):
    """Manually trigger a security scan"""
    await ctx.send("🔍 Starting manual security scan...")
    
    threats = await security_monitor.fetch_threat_intelligence()
    if threats:
        for threat in threats[:3]:  # Limit to 3 threats for manual scan
            analysis = await security_monitor.analyze_threat(threat)
            await security_monitor.send_alert(str(ctx.channel.id), threat, analysis)
            await asyncio.sleep(2)  # Delay between alerts
    else:
        await ctx.send("✅ No new threats detected in manual scan.")

@tasks.loop(minutes=30)  # Check every 30 minutes
async def monitor_security():
    """Main security monitoring loop"""
    logger.info("Running security monitoring check...")
    
    try:
        threats = await security_monitor.fetch_threat_intelligence()
        
        for threat in threats:
            # Check if this threat is new (simple check - in production, use database)
            if threat not in security_monitor.threat_database:
                security_monitor.threat_database.append(threat)
                
                # Analyze threat with AI
                analysis = await security_monitor.analyze_threat(threat)
                
                # Send alerts to all configured channels
                for channel_id in security_monitor.alert_channels:
                    await security_monitor.send_alert(channel_id, threat, analysis)
                    await asyncio.sleep(1)  # Small delay between channels
                    
    except Exception as e:
        logger.error(f"Error in security monitoring: {e}")

@bot.command(name='help')
async def show_help(ctx):
    """Show available commands"""
    embed = discord.Embed(
        title="🤖 AI Security Monitor Bot - Help",
        description="Available commands:",
        color=0x0099ff
    )
    
    commands_info = [
        ("!setup", "Set up security monitoring for this channel"),
        ("!status", "Check the status of security monitoring"),
        ("!scan", "Manually trigger a security scan"),
        ("!help", "Show this help message")
    ]
    
    for cmd, desc in commands_info:
        embed.add_field(name=cmd, value=desc, inline=False)
    
    embed.set_footer(text="AI Security Monitor Bot - Your 24/7 Security Guardian")
    await ctx.send(embed=embed)

# Run the bot
if __name__ == "__main__":
    print("Starting main block...")
    token = os.getenv('DISCORD_TOKEN')
    print(f"Token is: {token}")
    if not token:
        print("ERROR: DISCORD_TOKEN environment variable is not set.")
    else:
        print("Running bot...")
        bot.run(token) 