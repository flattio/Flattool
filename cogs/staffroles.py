import discord
from discord.ext import commands
import logging
import database as db

logger = logging.getLogger(__name__)


class StaffRoles(commands.Cog):
    """Cog for managing staff roles."""

    def __init__(self, bot):
        self.bot = bot

    staff = discord.SlashCommandGroup("staff", "Manage staff roles.")

    @staff.command(name="add", description="Add a role as staff.")
    async def add(self, ctx, role: discord.Role):
        db.add_staff(role.id)
        await ctx.respond(f"{role.mention} added as staff.", ephemeral=True)

    @staff.command(name="remove", description="Remove a role from staff.")
    async def remove(self, ctx, role: discord.Role):
        db.remove_staff(role.id)
        await ctx.respond(f"{role.mention} removed from staff.", ephemeral=True)

    @staff.command(name="list", description="List all staff roles.")
    async def list(self, ctx):
        try:
            role_ids = [role_id for role_id in db.get_staff()]
            if not role_ids:
                await ctx.respond("No staff roles set.", ephemeral=True)
                return
            role_mentions = []
            for role_id in role_ids:
                role = ctx.guild.get_role(role_id)
                if role:
                    role_mentions.append(role.mention)
                else:
                    role_mentions.append(f"`{role_id}` (not found)")
            await ctx.respond(
                "Staff roles:\n" + "\n".join(role_mentions), ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error listing staff roles: {e}", exc_info=True)
            await ctx.respond("Error retrieving staff roles.", ephemeral=True)


def setup(bot):
    bot.add_cog(StaffRoles(bot))
