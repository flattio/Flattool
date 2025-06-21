import discord
from discord.commands import SlashCommandGroup, Option
from discord.ext import commands, tasks
import logging
import database as db


class RoleTracker(commands.Cog):
    """
    A Pycord cog to track members within specific roles and display them in a dynamic embed.
    The embed automatically updates every 60 minutes.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing RoleTracker cog.")
        self.role_embed_message = None
        # Load config from database
        self.config = db.load_config()

    role_tracker_commands = SlashCommandGroup(
        "role_tracker", "Commands related to tracking roles and members."
    )

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info(f"Logged in as {self.bot.user} (ID: {self.bot.user.id})")
        self.logger.info("Starting role embed update task...")
        self.update_role_embed.start()

        if (
            self.config["role_embed_channel_id"]
            and self.config["role_embed_message_id"]
        ):
            try:
                channel = self.bot.get_channel(self.config["role_embed_channel_id"])
                if channel:
                    self.role_embed_message = await channel.fetch_message(
                        self.config["role_embed_message_id"]
                    )
                    self.logger.info(
                        f"Successfully loaded existing role embed message in channel: {channel.name}"
                    )
                else:
                    self.logger.warning(
                        f"Could not find channel with ID {self.config['role_embed_channel_id']}"
                    )
            except discord.NotFound:
                self.logger.warning(
                    f"Existing role embed message with ID {self.config['role_embed_message_id']} not found."
                )
                self.role_embed_message = None
            except discord.Forbidden:
                self.logger.error(
                    f"Bot does not have permissions to access channel or message for ID {self.config['role_embed_channel_id']}."
                )
                self.role_embed_message = None
            except Exception as e:
                self.logger.error(
                    f"An unexpected error occurred while loading existing embed: {e}"
                )
                self.role_embed_message = None

    def build_role_embed(self, guild: discord.Guild) -> discord.Embed:
        embed = discord.Embed(
            title=self.config["embed_title"],
            color=discord.Color.from_rgb(255, 255, 255),
        )
        embed.set_footer(
            text=f"Last updated: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )

        if not self.config["roles_to_track"]:
            trackable_roles = {role.id: role for role in guild.roles if role.members}
            embed.description += "\n\n**Note:** No specific roles are configured for tracking. Displaying all roles with members."
        else:
            trackable_roles = {}
            for role_id in self.config["roles_to_track"]:
                role = guild.get_role(role_id)
                if role:
                    trackable_roles[role.id] = role
                else:
                    embed.add_field(
                        name=f"Role Not Found (ID: {role_id})",
                        value="This role could not be found.",
                        inline=False,
                    )

        if not trackable_roles:
            embed.add_field(
                name="No Trackable Roles",
                value="There are no roles to display or no members in any roles.",
                inline=False,
            )
            return embed

        members_by_highest_role = {role_id: [] for role_id in trackable_roles}

        for member in guild.members:
            member_trackable_roles = [
                role for role in member.roles if role.id in trackable_roles
            ]
            if member_trackable_roles:
                member_trackable_roles.sort(key=lambda r: r.position, reverse=True)
                highest_role = member_trackable_roles[0]
                members_by_highest_role[highest_role.id].append(member.mention)

        sorted_roles = sorted(
            trackable_roles.values(), key=lambda r: r.position, reverse=True
        )

        for role in sorted_roles:
            members = members_by_highest_role.get(role.id, [])
            members.sort()
            if members:
                member_list = "\n".join(members)
                if len(member_list) > 1000:
                    member_list = member_list[:997] + "..."
                embed.add_field(
                    name=f"{role.name} ({len(members)} members)",
                    value=member_list,
                    inline=False,
                )
            else:
                embed.add_field(
                    name=f"{role.name} (0 members)",
                    value="No members in this role (or members are in a higher tracked role).",
                    inline=False,
                )
        return embed

    @role_tracker_commands.command(
        name="set_embed", description="Set up or move the role member tracking embed."
    )
    @commands.has_permissions(manage_roles=True)
    async def set_role_embed(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(
            discord.TextChannel,
            "The channel where the role embed should be sent/updated.",
            required=True,
        ),
    ):
        await ctx.defer(ephemeral=True)
        guild = ctx.guild
        if not guild:
            await ctx.followup.send(
                "This command can only be used in a server (guild).", ephemeral=True
            )
            self.logger.warning("Attempted to use set_embed command outside a guild.")
            return

        try:
            initial_embed = self.build_role_embed(guild)

            if self.role_embed_message:
                try:
                    await self.role_embed_message.delete()
                    self.logger.info(
                        f"Deleted old role embed message (ID: {self.role_embed_message.id}) from channel {self.role_embed_message.channel.name}"
                    )
                except discord.NotFound:
                    self.logger.warning(
                        "Old role embed message not found, perhaps already deleted."
                    )
                except discord.Forbidden:
                    self.logger.warning(
                        "No permissions to delete old role embed message."
                    )
                self.role_embed_message = None

            new_message = await channel.send(embed=initial_embed)
            self.role_embed_message = new_message

            self.config["role_embed_channel_id"] = channel.id
            self.config["role_embed_message_id"] = new_message.id
            db.save_config(self.config)

            await ctx.followup.send(
                f"Role member tracking embed has been set up in {channel.mention}. "
                "It will update every 60 minutes.",
                ephemeral=True,
            )
            self.logger.info(
                f"Role embed set up in channel {channel.name} (ID: {channel.id}). Message ID: {new_message.id}"
            )

        except discord.Forbidden:
            await ctx.followup.send(
                "I don't have permissions to send messages or embed links in that channel.",
                ephemeral=True,
            )
            self.logger.error(
                f"Bot lacks permissions to send messages/embeds in channel {channel.name} (ID: {channel.id})."
            )
        except Exception as e:
            self.logger.error(f"Error setting up role embed: {e}", exc_info=True)
            await ctx.followup.send(
                f"An error occurred while setting up the embed: {e}", ephemeral=True
            )

    @role_tracker_commands.command(
        name="add_role", description="Add a role to be tracked by the embed."
    )
    @commands.has_permissions(manage_roles=True)
    async def add_role_to_track(
        self,
        ctx: discord.ApplicationContext,
        role: Option(discord.Role, "The role to add to the tracker.", required=True),
    ):
        await ctx.defer(ephemeral=True)
        if role.id not in self.config["roles_to_track"]:
            self.config["roles_to_track"].append(role.id)
            db.save_config(self.config)
            await ctx.followup.send(
                f"Role `{role.name}` has been added to the tracker. The embed will update shortly.",
                ephemeral=True,
            )
            self.logger.info(
                f"Added role {role.name} (ID: {role.id}) to tracking list."
            )
            await self._update_embed_now(ctx.guild)
        else:
            await ctx.followup.send(
                f"Role `{role.name}` is already being tracked.", ephemeral=True
            )
            self.logger.info(
                f"Role {role.name} (ID: {role.id}) was already being tracked."
            )

    @role_tracker_commands.command(
        name="remove_role", description="Remove a role from being tracked by the embed."
    )
    @commands.has_permissions(manage_roles=True)
    async def remove_role_from_track(
        self,
        ctx: discord.ApplicationContext,
        role: Option(
            discord.Role, "The role to remove from the tracker.", required=True
        ),
    ):
        await ctx.defer(ephemeral=True)
        if role.id in self.config["roles_to_track"]:
            self.config["roles_to_track"].remove(role.id)
            db.save_config(self.config)
            await ctx.followup.send(
                f"Role `{role.name}` has been removed from the tracker. The embed will update shortly.",
                ephemeral=True,
            )
            self.logger.info(
                f"Removed role {role.name} (ID: {role.id}) from tracking list."
            )
            await self._update_embed_now(ctx.guild)
        else:
            await ctx.followup.send(
                f"Role `{role.name}` was not being tracked.", ephemeral=True
            )
            self.logger.info(
                f"Attempted to remove role {role.name} (ID: {role.id}) which was not tracked."
            )

    @role_tracker_commands.command(
        name="list_tracked_roles", description="List all roles currently being tracked."
    )
    @commands.has_permissions(manage_roles=True)
    async def list_tracked_roles(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)
        if not self.config["roles_to_track"]:
            await ctx.followup.send(
                "No specific roles are currently being tracked. The embed will show all roles with members.",
                ephemeral=True,
            )
            self.logger.info("List tracked roles: No specific roles configured.")
            return

        tracked_role_names = []
        for role_id in self.config["roles_to_track"]:
            role = ctx.guild.get_role(role_id)
            if role:
                tracked_role_names.append(role.name)
            else:
                tracked_role_names.append(f"Unknown Role (ID: {role_id})")

        roles_list_str = "\n".join(tracked_role_names) if tracked_role_names else "None"
        embed = discord.Embed(
            title="Currently Tracked Roles",
            description=f"These roles are specifically being tracked by the role member embed:\n\n{roles_list_str}",
            color=discord.Color.green(),
        )
        await ctx.followup.send(embed=embed, ephemeral=True)
        self.logger.info("Listed tracked roles.")

    @role_tracker_commands.command(
        name="change_title",
        description="Change the title of the role member tracking embed.",
    )
    @commands.has_permissions(manage_roles=True)
    async def change_embed_title(
        self,
        ctx: discord.ApplicationContext,
        new_title: Option(str, "The new title for the role embed.", required=True),
    ):
        await ctx.defer(ephemeral=True)
        self.config["embed_title"] = new_title
        db.save_config(self.config)
        await self._update_embed_now(ctx.guild)
        await ctx.followup.send(
            f"The title of the role member embed has been changed to: `{new_title}`. "
            "The embed should update shortly.",
            ephemeral=True,
        )
        self.logger.info(f"Embed title changed to: '{new_title}'")

    @role_tracker_commands.command(
        name="update_now",
        description="Manually trigger an update of the role member embed.",
    )
    @commands.has_permissions(manage_roles=True)
    async def update_embed_manual(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)
        await self._update_embed_now(ctx.guild)
        self.logger.info(
            "Role member embed update triggered successfully via manual command."
        )
        await ctx.followup.send(
            "Role member embed update triggered successfully.", ephemeral=True
        )

    async def _update_embed_now(self, guild: discord.Guild):
        if not self.role_embed_message:
            self.logger.warning("No role embed message found to update.")
            return

        try:
            updated_embed = self.build_role_embed(guild)
            await self.role_embed_message.edit(embed=updated_embed)
            self.logger.info(
                f"Successfully force-updated role embed in channel {self.role_embed_message.channel.name}"
            )
        except discord.NotFound:
            self.logger.warning(
                "Role embed message not found during manual update. Resetting reference."
            )
            self.role_embed_message = None
            self.config["role_embed_channel_id"] = None
            self.config["role_embed_message_id"] = None
            db.save_config(self.config)
        except discord.Forbidden:
            self.logger.error(
                "No permissions to edit role embed message during manual update."
            )
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred during manual embed update: {e}",
                exc_info=True,
            )

    @tasks.loop(minutes=60)
    async def update_role_embed(self):
        await self.bot.wait_until_ready()

        if (
            not self.role_embed_message
            and self.config["role_embed_channel_id"]
            and self.config["role_embed_message_id"]
        ):
            try:
                channel = self.bot.get_channel(self.config["role_embed_channel_id"])
                if channel:
                    self.role_embed_message = await channel.fetch_message(
                        self.config["role_embed_message_id"]
                    )
                    self.logger.info(
                        f"Re-fetched role embed message for periodic update in channel: {channel.name}"
                    )
                else:
                    self.logger.warning(
                        f"Channel for role embed with ID {self.config['role_embed_channel_id']} not found during periodic update."
                    )
                    return
            except discord.NotFound:
                self.logger.warning(
                    f"Role embed message with ID {self.config['role_embed_message_id']} not found during periodic update. It might have been deleted. Resetting reference."
                )
                self.role_embed_message = None
                self.config["role_embed_channel_id"] = None
                self.config["role_embed_message_id"] = None
                db.save_config(self.config)
                return
            except discord.Forbidden:
                self.logger.error(
                    f"Bot lacks permissions to access channel {self.config['role_embed_channel_id']} for periodic update."
                )
                return
            except Exception as e:
                self.logger.error(
                    f"Error re-fetching role embed message during periodic update: {e}",
                    exc_info=True,
                )
                return

        if self.role_embed_message:
            guild = self.role_embed_message.guild
            if not guild:
                self.logger.warning(
                    "Guild not found for the role embed message. Skipping update."
                )
                return

            try:
                updated_embed = self.build_role_embed(guild)
                await self.role_embed_message.edit(embed=updated_embed)
                self.logger.info(
                    f"Successfully updated role embed in channel {self.role_embed_message.channel.name} at {discord.utils.utcnow()}."
                )
            except discord.NotFound:
                self.logger.warning(
                    "Role embed message not found during periodic update. It might have been deleted. Resetting reference."
                )
                self.role_embed_message = None
                self.config["role_embed_channel_id"] = None
                self.config["role_embed_message_id"] = None
                db.save_config(self.config)
            except discord.Forbidden:
                self.logger.error(
                    "No permissions to edit role embed message during periodic update."
                )
            except Exception as e:
                self.logger.error(
                    f"An unexpected error occurred during periodic embed update: {e}",
                    exc_info=True,
                )
        else:
            self.logger.info(
                "No role embed message available to update. Use /role_tracker set_embed to set it up."
            )

    @update_role_embed.before_loop
    async def before_update_role_embed(self):
        await self.bot.wait_until_ready()
        self.logger.info("Waiting for bot to be ready before starting update loop...")


def setup(bot):
    bot.add_cog(RoleTracker(bot))
    logging.getLogger(__name__).info("RoleTracker cog loaded.")
