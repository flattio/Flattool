import logging
import discord
from discord.ext import commands
import database as db  # Make sure this import path matches your project structure

logger = logging.getLogger(__name__)


class Counting(commands.Cog):
    """A cog for a counting channel."""

    def __init__(self, bot):
        self.bot = bot
        counting_info = db.get_counting_row()
        if counting_info is not None:
            self.counting_channel_id, self.count_value = db.get_counting_row()
        else:
            self.counting_channel_id = None
            self.count_value = None
        logger.info(
            "Counting cog initialized with channel_id=%s, count_value=%s",
            self.counting_channel_id,
            self.count_value,
        )

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("%s cog loaded.", self.__class__.__name__)
        print(f"{self.__class__.__name__} cog loaded.")

    @commands.has_permissions(manage_guild=True)
    @commands.slash_command(name="setchannel")
    async def set_counting_channel(
        self, ctx, channel: discord.TextChannel, starting_count: int
    ):
        db.create_counting_row(channel.id, starting_count)
        self.counting_channel_id, self.count_value = db.get_counting_row()
        logger.info(
            "Counting channel set to %s and counter set to %d by %s",
            channel.id,
            starting_count,
            ctx.author,
        )
        await ctx.respond(
            f"Counting channel set to {channel.mention} and counter set to {starting_count}.",
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.channel.id != self.counting_channel_id:
            return

        try:
            number = int(message.content.strip())
        except ValueError:
            logger.warning(
                "Non-integer message deleted in counting channel by %s: %s",
                message.author,
                message.content,
            )
            await message.delete()
            return

        if number != self.count_value + 1:
            logger.warning(
                "Incorrect count by %s: %s (expected %d)",
                message.author,
                message.content,
                self.count_value + 1,
            )
            await message.delete()
            return

        self.count_value = number
        db.update_counting_value(number)

        logger.info("Count updated to %d by %s", number, message.author)


def setup(bot: commands.Bot):
    bot.add_cog(Counting(bot))
