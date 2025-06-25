import discord
from discord.ext import commands
import database as db
import logging
import time
from discord.ext import pages

logger = logging.getLogger(__name__)


def can_receive_rep(member: discord.Member) -> bool:
    """Check if a member can receive reputation.
    Member should have a staff role."""
    staff_role_ids = db.get_staff()
    member_role_ids = [role.id for role in member.roles]
    return any(role_id in staff_role_ids for role_id in member_role_ids)


class Reputation(commands.Cog):
    """Cog for managing user reputation."""

    def __init__(self, bot):
        self.bot = bot

    rep = discord.SlashCommandGroup("rep", "Reputation commands")

    @rep.command(name="give", description="Give reputation to another user.")
    @commands.cooldown(1, 7200, commands.BucketType.user)
    async def give_rep(self, ctx: discord.ApplicationContext, member: discord.Member):
        if member.id == ctx.author.id:
            await ctx.respond("You cannot give reputation to yourself.", ephemeral=True)
            return

        # Check if the recipient can receive reputation
        if not can_receive_rep(member):
            await ctx.respond(
                "Only staff members can receive reputation.", ephemeral=True
            )
            return

        db.update_reputation(member.id, 1)
        new_rank = db.get_rank(member.id)
        new_rep = db.get_reputation(member.id)
        await ctx.respond(
            f"Gave +1 reputation to {member.mention}. They are now rank {new_rank} with {new_rep} rep!"
        )

    @give_rep.error
    async def give_rep_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            retry_timestamp = int(time.time() + error.retry_after)
            await ctx.respond(
                f"You can use this command again <t:{retry_timestamp}:R>.",
                ephemeral=True,
            )
        else:
            logger.error(
                "An error occurred in give_rep command: %s", error, exc_info=True
            )
            await ctx.respond("An error occurred.", ephemeral=True)

    @rep.command(name="take", description="Take reputation from another user.")
    @commands.cooldown(1, 86400, commands.BucketType.user)
    async def take_rep(self, ctx: discord.ApplicationContext, member: discord.Member):
        if member.id == ctx.author.id:
            await ctx.respond(
                "You cannot take reputation from yourself.", ephemeral=True
            )
            return

        # Check if the recipient can receive reputation
        if not can_receive_rep(member):
            await ctx.respond("Only staff members can lose reputation.", ephemeral=True)
            return

        db.update_reputation(member.id, -1)
        new_rank = db.get_rank(member.id)
        new_rep = db.get_reputation(member.id)
        await ctx.respond(
            f"Took -1 reputation from {member.mention}. They are now rank {new_rank} with {new_rep} rep."
        )

    @take_rep.error
    async def take_rep_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            retry_timestamp = int(time.time() + error.retry_after)
            await ctx.respond(
                f"You can use this command again <t:{retry_timestamp}:R>.",
                ephemeral=True,
            )
        else:
            logger.error(
                "An error occurred in take_rep command: %s", error, exc_info=True
            )
            await ctx.respond("An error occurred.", ephemeral=True)

    @rep.command(name="check", description="Check your reputation and rank.")
    async def check_rep(self, ctx: discord.ApplicationContext):
        user_id = ctx.author.id
        rank = db.get_rank(user_id)
        rep = db.get_reputation(user_id)
        embed = discord.Embed(
            title="Your Reputation",
            description=f"Rank: {rank}\nReputation: {rep}",
            color=discord.Color.blue(),
        )
        await ctx.respond(embed=embed)

    @rep.command(name="leaderboard", description="Show the reputation leaderboard.")
    async def rep_leaderboard(self, ctx):
        per_page = 10
        leaderboard = db.get_leaderboard()  # List of (user_id, rep)
        if not leaderboard:
            embed = discord.Embed(
                title="Reputation Leaderboard",
                description="No users found.",
                color=discord.Color.gold(),
            )
            await ctx.respond(embed=embed)
            return

        # Build pages
        page_entries = [
            leaderboard[i : i + per_page] for i in range(0, len(leaderboard), per_page)
        ]
        embeds = []
        for page_num, entries in enumerate(page_entries, start=1):
            embed = discord.Embed(
                title="Reputation Leaderboard",
                color=discord.Color.gold(),
            )
            for idx, (user_id, rep) in enumerate(
                entries, start=(page_num - 1) * per_page + 1
            ):
                user = ctx.guild.get_member(user_id)
                name = user.name if user else f"User ID {user_id}"
                embed.add_field(
                    name=f"#{idx}: {name}",
                    value=f"Reputation: {rep}",
                    inline=False,
                )
            embeds.append(embed)

        paginator = pages.Paginator(
            pages=embeds, show_indicator=True, use_default_buttons=True
        )
        await paginator.respond(ctx.interaction)

    @rep.command(
        name="clear",
        description="Clear the entire reputation list. This action is irreversible.",
    )
    @commands.has_permissions(administrator=True)
    async def clear_reputation(self, ctx: discord.ApplicationContext):
        """Clear the entire reputation list. This action is irreversible."""
        view = discord.ui.View(timeout=30)

        class ConfirmButton(discord.ui.Button):
            def __init__(self):
                super().__init__(style=discord.ButtonStyle.danger, label="Confirm")

            async def callback(self, interaction: discord.Interaction):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("You are not authorized.")
                    return
                view.stop()
                view.value = True
                await interaction.response.edit_message(
                    content="Confirmed. Clearing reputation...", view=None
                )

        class DenyButton(discord.ui.Button):
            def __init__(self):
                super().__init__(style=discord.ButtonStyle.secondary, label="Cancel")

            async def callback(self, interaction: discord.Interaction):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("You are not authorized.")
                    return
                view.stop()
                view.value = False
                await interaction.response.edit_message(content="Cancelled.", view=None)

        view.add_item(ConfirmButton())
        view.add_item(DenyButton())
        view.value = None

        await ctx.respond(
            "Are you sure you want to clear the entire reputation list? This action is **irreversible**.",
            view=view,
        )

        timeout = await view.wait()
        if view.value is not True:
            return
        db.clear_reputation()
        await ctx.respond("The reputation list has been cleared.")


def setup(bot):
    bot.add_cog(Reputation(bot))
