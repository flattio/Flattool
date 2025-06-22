import os
import logging
import discord
from discord.ext import commands
from discord import SlashCommandGroup
from dotenv import load_dotenv
import database as db

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("flatool")

# project modules

load_dotenv()
db.init()

DEBUG_GUILDS = [
    int(os.getenv("DEBUG_GUILDS", 0))
]  # Use environment variable for debug guild ID
ALLOWED_ROLE_IDS = [1121590212011773962, 1091441098330746919, 1376694477233848442]

# bot initialization
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.members = True
bot = commands.Bot(command_prefix="f!", intents=intents, debug_guilds=DEBUG_GUILDS)

# load cogs
cogs_list = ["misc", "roletracker", "counting", "cats"]

for cog in cogs_list:
    try:
        bot.load_extension(f"cogs.{cog}")  # Load each cog from the cogs directory
        logger.info(f"Loaded cog: {cog}")
    except Exception as e:
        logger.error(f"Failed to load cog {cog}: {e}")


# bot startup function
@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}!")
    logger.info(f"debug guilds: {bot.debug_guilds}")
    logger.info("Slash commands should be available in a few minutes.")

    # Set custom status
    try:
        activity = discord.CustomActivity(name="Adding features...")
        await bot.change_presence(status=discord.Status.online, activity=activity)
        logger.info("Status updated successfully")
        await bot.sync_commands(guild_ids=bot.debug_guilds)
        logger.info("Commands synced")

    except Exception as e:
        logger.error(f"Failed to update status: {e}")


# Run the bot
bot.run(os.getenv("BOT_TOKEN"))
