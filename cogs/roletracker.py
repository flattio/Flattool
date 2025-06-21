import discord
from discord.commands import SlashCommandGroup, Option
from discord.ext import commands, tasks
import logging  # Import the logging library

# Set up basic logging configuration
# This will output logs to the console. For production, you might want to log to a file.
# logging.basicConfig(
#     level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
# )

# You might want to store these in a database or a persistent file for a production bot
# so that the bot remembers the embed's location across restarts.
# For this example, they will be in-memory and reset if the bot restarts.
CONFIG = {
    "role_embed_channel_id": None,
    "role_embed_message_id": None,
    "roles_to_track": [],  # Example: [123456789012345678, 234567890123456789] (Role IDs)
    "embed_title": "Role Member Tracker",  # New: Default title for the embed
}


class RoleTracker(commands.Cog):
    """
    A Pycord cog to track members within specific roles and display them in a dynamic embed.
    The embed automatically updates every 60 minutes.
    """

    def __init__(self, bot):
        self.bot = bot
        # Initialize a logger specifically for this cog
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing RoleTracker cog.")
        # This will hold the actual discord.Message object of the embed we are tracking
        self.role_embed_message = None

    # Slash command group for role tracking commands
    role_tracker_commands = SlashCommandGroup(
        "role_tracker", "Commands related to tracking roles and members."
    )

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Event listener that runs when the bot is fully ready.
        It starts the role embed update task.
        """
        self.logger.info(f"Logged in as {self.bot.user} (ID: {self.bot.user.id})")
        self.logger.info("Starting role embed update task...")
        self.update_role_embed.start()  # Start the background task

        # Attempt to retrieve the message if IDs are known from a previous session (if persistent storage was used)
        if CONFIG["role_embed_channel_id"] and CONFIG["role_embed_message_id"]:
            try:
                channel = self.bot.get_channel(CONFIG["role_embed_channel_id"])
                if channel:
                    self.role_embed_message = await channel.fetch_message(
                        CONFIG["role_embed_message_id"]
                    )
                    self.logger.info(
                        f"Successfully loaded existing role embed message in channel: {channel.name}"
                    )
                else:
                    self.logger.warning(
                        f"Could not find channel with ID {CONFIG['role_embed_channel_id']}"
                    )
            except discord.NotFound:
                self.logger.warning(
                    f"Existing role embed message with ID {CONFIG['role_embed_message_id']} not found."
                )
                self.role_embed_message = None
            except discord.Forbidden:
                self.logger.error(
                    f"Bot does not have permissions to access channel or message for ID {CONFIG['role_embed_channel_id']}."
                )
                self.role_embed_message = None
            except Exception as e:
                self.logger.error(
                    f"An unexpected error occurred while loading existing embed: {e}"
                )
                self.role_embed_message = None

    def build_role_embed(self, guild: discord.Guild) -> discord.Embed:
        """
        Constructs the Discord embed showing roles and their members.
        This function dynamically generates the content based on current guild data.
        Members with multiple tracked roles will only appear under their highest role.
        """
        embed = discord.Embed(
            title=CONFIG["embed_title"],  # Use the title from CONFIG
            description="This embed lists members currently assigned to specific roles. "
            "Members holding multiple tracked roles are listed under their highest role.",
            color=discord.Color.blue(),
        )
        embed.set_footer(
            text=f"Last updated: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )

        # Determine the set of roles we care about
        # If roles_to_track is empty, we consider all roles with members as "tracked"
        if not CONFIG["roles_to_track"]:
            trackable_roles = {role.id: role for role in guild.roles if role.members}
            embed.description += "\n\n**Note:** No specific roles are configured for tracking. Displaying all roles with members."
        else:
            trackable_roles = {}
            for role_id in CONFIG["roles_to_track"]:
                role = guild.get_role(role_id)
                if role:
                    trackable_roles[role.id] = role
                else:
                    # Only add field if a specific tracked role is not found
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

        # Dictionary to store members grouped by their highest role
        members_by_highest_role = {role_id: [] for role_id in trackable_roles}

        # Iterate through all members in the guild
        for member in guild.members:
            # Find all roles the member has that are in our trackable_roles set
            member_trackable_roles = [
                role for role in member.roles if role.id in trackable_roles
            ]

            if member_trackable_roles:
                # Sort these roles by position (highest position first)
                member_trackable_roles.sort(key=lambda r: r.position, reverse=True)
                highest_role = member_trackable_roles[0]
                # Changed from member.display_name to member.mention
                members_by_highest_role[highest_role.id].append(member.mention)

        # Now, build the embed fields based on our grouped members
        # Sort roles by position for consistent display
        sorted_roles = sorted(
            trackable_roles.values(), key=lambda r: r.position, reverse=True
        )

        for role in sorted_roles:
            members = members_by_highest_role.get(role.id, [])
            # Sort members alphabetically for consistent display (by their mention string)
            members.sort()

            if members:
                member_list = "\n".join(members)
                # Ensure field value does not exceed Discord's 1024 character limit
                # Mentions are shorter than display names, but still good to check
                if len(member_list) > 1000:  # Approximate check before truncation
                    member_list = member_list[:997] + "..."  # Truncate and add ellipsis
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
    @commands.has_permissions(
        manage_roles=True
    )  # Require manage_roles permission to use this command
    async def set_role_embed(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(
            discord.TextChannel,
            "The channel where the role embed should be sent/updated.",
            required=True,
        ),
    ):
        """
        Sets up the initial role tracking embed in the specified channel.
        If an embed already exists, it will be updated and moved to the new channel.
        """
        await ctx.defer(ephemeral=True)  # Acknowledge the command immediately

        # Get the guild from the context
        guild = ctx.guild
        if not guild:
            await ctx.followup.send(
                "This command can only be used in a server (guild).", ephemeral=True
            )
            self.logger.warning("Attempted to use set_embed command outside a guild.")
            return

        try:
            # Build the initial embed
            initial_embed = self.build_role_embed(guild)

            if self.role_embed_message:
                # If an existing message is being tracked, delete it from its old location
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
                self.role_embed_message = None  # Clear the reference

            # Send the new embed message to the specified channel
            new_message = await channel.send(embed=initial_embed)
            self.role_embed_message = new_message

            # Store the channel and message IDs
            CONFIG["role_embed_channel_id"] = channel.id
            CONFIG["role_embed_message_id"] = new_message.id

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
            self.logger.error(
                f"Error setting up role embed: {e}", exc_info=True
            )  # exc_info=True prints traceback
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
        """Adds a role to the list of roles to be tracked."""
        await ctx.defer(ephemeral=True)
        if role.id not in CONFIG["roles_to_track"]:
            CONFIG["roles_to_track"].append(role.id)
            await ctx.followup.send(
                f"Role `{role.name}` has been added to the tracker. The embed will update shortly.",
                ephemeral=True,
            )
            self.logger.info(
                f"Added role {role.name} (ID: {role.id}) to tracking list."
            )
            # Immediately update the embed after adding a role
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
        """Removes a role from the list of roles to be tracked."""
        await ctx.defer(ephemeral=True)
        if role.id in CONFIG["roles_to_track"]:
            CONFIG["roles_to_track"].remove(role.id)
            await ctx.followup.send(
                f"Role `{role.name}` has been removed from the tracker. The embed will update shortly.",
                ephemeral=True,
            )
            self.logger.info(
                f"Removed role {role.name} (ID: {role.id}) from tracking list."
            )
            # Immediately update the embed after removing a role
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
        """Lists all roles currently configured for tracking."""
        await ctx.defer(ephemeral=True)
        if not CONFIG["roles_to_track"]:
            await ctx.followup.send(
                "No specific roles are currently being tracked. The embed will show all roles with members.",
                ephemeral=True,
            )
            self.logger.info("List tracked roles: No specific roles configured.")
            return

        tracked_role_names = []
        for role_id in CONFIG["roles_to_track"]:
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
        """
        Changes the title of the role member tracking embed.
        """
        await ctx.defer(ephemeral=True)
        CONFIG["embed_title"] = new_title  # Update the title in CONFIG
        await self._update_embed_now(
            ctx.guild
        )  # Trigger an immediate update to reflect the change

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
        """Manually triggers an update of the role member embed."""
        await ctx.defer(ephemeral=True)
        await self._update_embed_now(ctx.guild)
        self.logger.info(
            "Role member embed update triggered successfully via manual command."
        )
        await ctx.followup.send(
            "Role member embed update triggered successfully.", ephemeral=True
        )

    async def _update_embed_now(self, guild: discord.Guild):
        """Helper to force an embed update immediately."""
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
            CONFIG["role_embed_channel_id"] = None
            CONFIG["role_embed_message_id"] = None
        except discord.Forbidden:
            self.logger.error(
                "No permissions to edit role embed message during manual update."
            )
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred during manual embed update: {e}",
                exc_info=True,
            )

    @tasks.loop(minutes=60)  # Runs every 60 minutes
    async def update_role_embed(self):
        """
        Background task that updates the role member embed periodically.
        """
        await self.bot.wait_until_ready()  # Ensure the bot is ready before doing anything

        if (
            not self.role_embed_message
            and CONFIG["role_embed_channel_id"]
            and CONFIG["role_embed_message_id"]
        ):
            # If bot restarted or message reference was lost, try to fetch it again
            try:
                channel = self.bot.get_channel(CONFIG["role_embed_channel_id"])
                if channel:
                    self.role_embed_message = await channel.fetch_message(
                        CONFIG["role_embed_message_id"]
                    )
                    self.logger.info(
                        f"Re-fetched role embed message for periodic update in channel: {channel.name}"
                    )
                else:
                    self.logger.warning(
                        f"Channel for role embed with ID {CONFIG['role_embed_channel_id']} not found during periodic update."
                    )
                    return  # Can't update without the channel
            except discord.NotFound:
                self.logger.warning(
                    f"Role embed message with ID {CONFIG['role_embed_message_id']} not found during periodic update. It might have been deleted. Resetting reference."
                )
                self.role_embed_message = None
                CONFIG["role_embed_channel_id"] = None
                CONFIG["role_embed_message_id"] = None
                return
            except discord.Forbidden:
                self.logger.error(
                    f"Bot lacks permissions to access channel {CONFIG['role_embed_channel_id']} for periodic update."
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
                CONFIG["role_embed_channel_id"] = None
                CONFIG["role_embed_message_id"] = None
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
        """Waits until the bot is ready before starting the loop."""
        await self.bot.wait_until_ready()
        self.logger.info("Waiting for bot to be ready before starting update loop...")


def setup(bot):
    """
    The setup function for the cog. This is called by the bot to load the cog.
    """
    bot.add_cog(RoleTracker(bot))
    logging.getLogger(__name__).info("RoleTracker cog loaded.")
