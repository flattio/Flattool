import os
import discord
from discord.ext import commands
# from discord import app_commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GUILD_ID = int(os.getenv('GUILD_ID'))  # Convert to int
ALLOWED_ROLE_IDS = [1121590212011773962, 1091441098330746919, 1376694477233848442]

# Initialize the bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
bot = commands.Bot(command_prefix="f!", intents=intents)

# Slash Commands

# @app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.slash_command(name="ping", description="Get bot response time")
async def ping(ctx: discord.ApplicationContext):
    ping = round(bot.latency * 1000)
    await ctx.respond(f"Pong! Latency is {ping}ms.")

@bot.slash_command(
    name="say",
    description="Send a message to a specified channel as the bot"
)
async def say(
    ctx: discord.ApplicationContext,
    channel: discord.Option(discord.TextChannel, "Channel to send the message to"),
    message: discord.Option(str, "Message to send")
):
    # Check if the user has one of the allowed roles
    if any(role.id in ALLOWED_ROLE_IDS for role in ctx.author.roles):
        await channel.send(message)
        await ctx.respond("Message sent!", ephemeral=True)
    else:
        await ctx.respond("You do not have permission to use this command.", ephemeral=True)


# Add these prefix commands below the existing slash commands
@bot.command()
async def ping(ctx):
    ping = round(bot.latency * 1000)
    await ctx.send(f"Pong! Latency is {ping}ms.")

@bot.command()
async def say(ctx, channel: discord.TextChannel, *, message: str):
    if any(role.id in ALLOWED_ROLE_IDS for role in ctx.author.roles):
        await channel.send(message)
        await ctx.send("Message sent!")
    else:
        await ctx.send("You do not have permission to use this command.")

@bot.command()
async def hello(ctx):
    await ctx.send('Hello! This is a prefix command.')

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")
    print(f"Guild ID: {GUILD_ID}")
    print("Slash commands should be available in a few minutes.")
    
    # Set custom status with no preset prefix
    try:
        activity = discord.CustomActivity(name="Adding features...")
        await bot.change_presence(status=discord.Status.online, activity=activity)
        print("Status updated successfully")
    except Exception as e:
        print(f"Failed to update status: {e}")

# Run the bot
bot.run(os.getenv('DISCORD_TOKEN'))

