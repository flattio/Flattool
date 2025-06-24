import discord
from discord.ext import commands
from discord.ext.commands import Greedy
from discord.ext import tasks


class Misc(commands.Cog):  # create a class for our cog that inherits from commands.Cog
    # this class is used to create a cog, which is a module that can be added to the bot

    def __init__(self, bot):
        self.bot = bot

    @commands.has_permissions(administrator=True)
    @commands.slash_command(
        name="say",
        description="Send a message to a specified channel as the bot.",
    )
    async def say(
        self,
        ctx: discord.ApplicationContext,
        message: str,
        channel: discord.Option(discord.TextChannel, "Channel to send the message to"),
    ):
        await channel.send(message)
        await ctx.respond(f"Message sent to {channel.mention}.", ephemeral=True)

    @commands.slash_command(
        name="ping",
        description="Check the bot's latency.",
    )
    async def ping(self, ctx: discord.ApplicationContext):
        latency = round(self.bot.latency * 1000)
        await ctx.respond(f"Pong! 🏓 Latency: {latency}ms")


def setup(bot):  # this is called by Pycord to setup the cog
    bot.add_cog(Misc(bot))
