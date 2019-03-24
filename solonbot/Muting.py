import datetime
import discord
import logging
import solon
__all__ = []

log = logging.getLogger(__name__)
config = solon.get_config(__name__)

log.info(f"Loading {__name__}")


class Data:
    def __init__(self):
        self.previous_roles = {}
        self.active_mute_channels = {}
        self.inactive_mute_channels = {}
        self.due_out_times = {}


role_list_name = solon.SerializedList(discord.Role).__name__

default_settings = {
    "mute_role": {"value_serialized": "", "type_name": "role"},
    "create_channel": {"value_serialized": "False", "type_name": "bool"},
    "channel_name": {"value_serialized": "", "type_name": "str"},
    "mute_access_roles": {"value_serialized": "", "type_name": role_list_name},
    "category": {"value_serialized": "", "type_name": "CategoryChannel"}
}


@solon.Cog(default_settings=default_settings, data_type=Data)
class Muting:
    def __init__(self, settings, guild_id, data):
        self.settings = settings
        self.guild_id = guild_id
        self.data = data
        self.clean_up_channels.start(self, solon.timedelta_from_string(config["cleanup_frequency"]))
        self.unmuting_sentry.start(self, solon.timedelta_from_string(config["unmuting_sentry_frequency"]))

    @property
    def guild(self):
        return solon.Bot.get_guild(self.guild_id)

    @solon.Command(manage_roles=True)
    async def mute(self, ctx, *, members: solon.converter(solon.SerializedList(discord.Member))):
        mute_role = self.settings["mute_role"]
        if not mute_role:
            raise solon.CommandError("Mute role not set.")

        for m in members:
            if mute_role in m.roles:
                raise solon.CommandError(f"{m} is already muted.")

        await self.perform_mute(members, ctx.author)

        await ctx.send("Successfully muted: [" + " ".join([str(m) for m in members]) + "]")

    @solon.Event()
    async def on_member_update(self, before, after):
        mute_role = self.settings["mute_role"]
        if mute_role:
            if mute_role in after.roles and mute_role not in before.roles:
                await self.perform_mute([after])

    async def perform_mute(self, members, requested_by=None):
        mute_role = self.settings["mute_role"]
        if mute_role is None:
            raise solon.CommandError(f"No mute role set.")

        guild = self.guild
        my_highest_role = max(guild.me.roles)
        for m in members:
            highest_role = max(m.roles)
            if highest_role >= my_highest_role:
                raise solon.CommandError(f"{m} has a higher role than me.")

        for m in members:
            add_mute_role = mute_role not in m.roles
            previous_roles = m.roles[1:] if add_mute_role else [r for r in m.roles[1:] if r != mute_role]
            
            self.data.previous_roles[m.id] = [r.id for r in previous_roles]
            log.info(f"Removing roles {previous_roles} from {m}" + (" and adding {mute_role}" if add_mute_role else ""))
            await m.remove_roles(*previous_roles, reason=f"Requested by {requested_by}" if requested_by else None)
            if add_mute_role:
                await m.add_roles(mute_role)

            create_channel = self.settings["create_channel"]
            channel_name = self.settings["channel_name"]
            if create_channel and channel_name:
                text_channel_options = {
                    "name": channel_name,
                    "overwrites": {  # TODO replace overwrites with a "mute template" channel overwrites template
                        m: discord.PermissionOverwrite(read_messages=True),
                        guild.roles[0]: discord.PermissionOverwrite(read_messages=False)
                    }
                }
                mute_access_roles = self.settings["mute_access_roles"]
                if mute_access_roles:
                    for role in mute_access_roles:
                        text_channel_options["overwrites"][role] = discord.PermissionOverwrite(read_messages=True)
                category = self.settings["category"]
                if category is not None:
                    text_channel_options["category"] = category

                channel = await guild.create_text_channel(**text_channel_options)
                self.data.active_mute_channels[m.id] = channel.id

    @solon.Command(manage_roles=True)
    async def unmute(self, ctx, *, member: solon.converter(discord.Member)):
        mute_role = self.settings["mute_role"]
        if mute_role is None:
            raise solon.CommandError(f"No mute role set.")

        my_highest_role = max(ctx.guild.me.roles)
        if mute_role not in member.roles:
            raise solon.CommandError(f"{member} is not muted.")
        highest_role = max(member.roles)
        if highest_role > my_highest_role:
            raise solon.CommandError(f"{member} has a higher role than me.")

        if member.id not in self.data.previous_roles:
            raise solon.CommandError(f"I don't have any data on {member}'s previous roles.")

        await self.perform_unmute(member)

        await ctx.send(f"Successfully unmuted: {member}")

    @solon.Command(manage_roles=True)
    async def length(self, ctx, time: str, *, member: solon.converter(discord.Member)):
        mute_role = self.settings["mute_role"]
        if mute_role is None:
            raise solon.CommandError(f"No mute role set.")

        my_highest_role = max(ctx.guild.me.roles)
        if mute_role not in member.roles:
            raise solon.CommandError(f"{member} is not muted.")
        highest_role = max(member.roles)
        if highest_role > my_highest_role:
            raise solon.CommandError(f"{member} has a higher role than me.")

        delta = solon.timedelta_from_string(time)
        now = datetime.datetime.now()
        due_date = now + delta
        self.data.due_out_times[member.id] = due_date.timestamp()

        due_date_str = due_date.strftime("at %H:%M:%S on %a %-d %b")
        await ctx.send(f"{member} will be free {due_date_str}.")

    async def perform_unmute(self, member):
        guild = solon.Bot.get_guild(self.guild_id)

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

    @solon.TimedEvent()
    async def clean_up_channels(self):
        if len(self.data.inactive_mute_channels) > 0:
            guild = solon.Bot.get_guild(self.guild_id)
            log.info(f"Cleaning up mute channels on {guild}.")
            for channel_id in self.data.inactive_mute_channels.values():
                channel = guild.get_channel(channel_id)
                if channel is not None:
                    await channel.delete(reason=f"Mute is over.")
            self.data.inactive_mute_channels.clear()

    @solon.TimedEvent()
    async def unmuting_sentry(self):
        now = datetime.datetime.now()

        free_members = []
        for member_id, due_out_timestamp in self.data.due_out_times.items():
            out_time = datetime.datetime.utcfromtimestamp(due_out_timestamp)
            if now > out_time:
                guild = solon.Bot.get_guild(self.guild_id)
                member = guild.get_member(member_id)
                if member is not None:
                    log.info(f"Unmuting {member} on {guild}, who was due.")
                    await self.perform_unmute(member)
                free_members.append(member_id)

        for member_id in free_members:
            del self.data.due_out_times[member_id]
