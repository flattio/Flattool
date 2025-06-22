import discord
from discord.ext import commands
import logging
import random

logger = logging.getLogger(__name__)


class Cats(commands.Cog):
    """Cog for cat-related commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cat_chance = 1

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if "meow" in message.content.lower():
            if random.randint(1, 1000) <= self.cat_chance:
                try:
                    async with self.bot.http._HTTPClient__session.get(
                        "https://api.thecatapi.com/v1/images/search"
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data and "url" in data[0]:
                                await message.reply(data[0]["url"])
                                logger.info("Sent a cat gif.")
                            else:
                                logger.warning(
                                    "Cat API response did not contain a URL."
                                )
                        else:
                            logger.error(f"Cat API returned status code {resp.status}")
                except Exception as e:
                    logger.exception("Exception occurred while fetching cat gif.")
                self.cat_chance = 1
            else:
                self.cat_chance += 1
            logger.info(
                f"Detected 'meow' in message from {message.author}. Cat chance is now {round(self.cat_chance * 0.1, 1)}%"
            )


def setup(bot: commands.Bot):
    bot.add_cog(Cats(bot))
