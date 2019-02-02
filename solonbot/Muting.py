import datetime
import discord
import logging

from solon import Bot
from solon import Cog
from solon import Command
from solon import get_config
from solon import CommandError
from solon import TimedEvent
from solon import timedelta_from_string
from solon import converter
from solon import SerializedList

__all__ = []

log = logging.getLogger(__name__)
config = get_config(__name__)

log.info(f"Loading {__name__}")


class Data:
    def __init__(self):
        self.previous_roles = {}
        self.active_mute_channels = {}
        self.inactive_mute_channels = {}
        self.due_out_times = {}


role_list_name = SerializedList(discord.Role).__name__

default_settings = {
    "mute_role": {"value_serialized": "", "type_name": "role"},
    "create_channel": {"value_serialized": "False", "type_name": "bool"},
    "channel_name": {"value_serialized": "", "type_name": "str"},
    "mute_access_roles": {"value_serialized": "", "type_name": role_list_name},
    "category": {"value_serialized": "", "type_name": "CategoryChannel"}
}


@Cog(default_settings=default_settings, data_type=Data)
class Muting:
    def __init__(self, settings, guild_id, data):
        self.settings = settings
        self.guild_id = guild_id
        self.data = data
        self.clean_up_channels.start(self, timedelta_from_string(config["cleanup_frequency"]))
        self.unmuting_sentry.start(self, timedelta_from_string(config["unmuting_sentry_frequency"]))

    @Command(manage_roles=True)
    async def mute(self, ctx, *, members: converter(SerializedList(discord.Member))):
        mute_role = self.settings["mute_role"]
        if mute_role is None:
            raise CommandError(f"No mute role set.")

        my_highest_role = max(ctx.guild.me.roles)
        for m in members:
            if mute_role in m.roles:
                raise CommandError(f"{m} is already muted.")
            highest_role = max(m.roles)
            if highest_role >= my_highest_role:
                raise CommandError(f"{m} has a higher role than me.")

        for m in members:
            self.data.previous_roles[m.id] = [r.id for r in m.roles[1:]]
            log.info(f"Removing roles {m.roles[1:]} from {m} and adding {mute_role}")
            await m.remove_roles(*m.roles[1:], reason=f"Requested by {ctx.author}")
            await m.add_roles(mute_role)

            create_channel = self.settings["create_channel"]
            channel_name = self.settings["channel_name"]
            if create_channel and channel_name:
                text_channel_options = {
                    "name": channel_name,
                    "overwrites": {  # TODO replace overwrites with a "mute template" channel overwrites template
                        m: discord.PermissionOverwrite(read_messages=True),
                        ctx.guild.roles[0]: discord.PermissionOverwrite(read_messages=False)
                    }
                }
                mute_access_roles = self.settings["mute_access_roles"]
                if mute_access_roles:
                    for role in mute_access_roles:
                        text_channel_options["overwrites"][role] = discord.PermissionOverwrite(read_messages=True)
                category = self.settings["category"]
                if category is not None:
                    text_channel_options["category"] = category

                channel = await ctx.guild.create_text_channel(**text_channel_options)
                self.data.active_mute_channels[m.id] = channel.id

        await ctx.send("Successfully muted: [" + " ".join([str(m) for m in members]) + "]")

    @Command(manage_roles=True)
    async def unmute(self, ctx, *, member: converter(discord.Member)):
        mute_role = self.settings["mute_role"]
        if mute_role is None:
            raise CommandError(f"No mute role set.")

        my_highest_role = max(ctx.guild.me.roles)
        if mute_role not in member.roles:
            raise CommandError(f"{member} is not muted.")
        highest_role = max(member.roles)
        if highest_role > my_highest_role:
            raise CommandError(f"{member} has a higher role than me.")

        if member.id not in self.data.previous_roles:
            raise CommandError(f"I don't have any data on {member}'s previous roles.")

        await self.perform_unmute(member)

        await ctx.send(f"Successfully unmuted: {member}")

    @Command(manage_roles=True)
    async def length(self, ctx, time: str, *, member: converter(discord.Member)):
        mute_role = self.settings["mute_role"]
        if mute_role is None:
            raise CommandError(f"No mute role set.")

        my_highest_role = max(ctx.guild.me.roles)
        if mute_role not in member.roles:
            raise CommandError(f"{member} is not muted.")
        highest_role = max(member.roles)
        if highest_role > my_highest_role:
            raise CommandError(f"{member} has a higher role than me.")

        delta = timedelta_from_string(time)
        now = datetime.datetime.now()
        due_date = now + delta
        self.data.due_out_times[member.id] = due_date.timestamp()

        due_date_str = due_date.strftime("at %H:%M:%S on %a %-d %b")
        await ctx.send(f"{member} will be free {due_date_str}.")

    async def perform_unmute(self, member):
        guild = Bot.get_guild(self.guild_id)

        roles = [guild.get_role(rId) for rId in self.data.previous_roles[member.id] if guild.get_role(rId) is not None]

        await member.remove_roles(*member.roles[1:], reason=f"Unmuting")
        await member.add_roles(*roles)

        if member.id in self.data.active_mute_channels:
            channel_id = self.data.active_mute_channels[member.id]
            channel = guild.get_channel(channel_id)
            if channel:
                await channel.set_permissions(member, overwrite=None, reason="Unmuting")

            self.data.inactive_mute_channels[member.id] = channel_id
            del self.data.active_mute_channels[member.id]

    @TimedEvent()
    async def clean_up_channels(self):
        if len(self.data.inactive_mute_channels) > 0:
            guild = Bot.get_guild(self.guild_id)
            log.info(f"Cleaning up mute channels on {guild}.")
            for channel_id in self.data.inactive_mute_channels.values():
                channel = guild.get_channel(channel_id)
                if channel is not None:
                    await channel.delete(reason=f"Mute is over.")
            self.data.inactive_mute_channels.clear()

    @TimedEvent()
    async def unmuting_sentry(self):
        now = datetime.datetime.now()

        free_members = []
        for member_id, due_out_timestamp in self.data.due_out_times.items():
            out_time = datetime.datetime.utcfromtimestamp(due_out_timestamp)
            if now > out_time:
                guild = Bot.get_guild(self.guild_id)
                member = guild.get_member(member_id)
                if member is not None:
                    log.info(f"Unmuting {member} on {guild}, who was due.")
                    await self.perform_unmute(member)
                free_members.append(member_id)

        for member_id in free_members:
            del self.data.due_out_times[member_id]
