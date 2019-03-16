import discord
import logging
import solon

__all__ = []

log = logging.getLogger(__name__)
config = solon.get_config(__name__)

log.info(f"Loading {__name__}")

member_list_name = solon.SerializedList(discord.Member).__name__

default_settings = {
    "blocked_users": {"value_serialized": "", "type_name": member_list_name}
}


@solon.Cog(default_settings=default_settings)
class NoReact:
    def __init__(self, guild_id, settings):
        self.guild_id = guild_id
        self.settings = settings

    @solon.Event()
    async def on_reaction_add(self, reaction, user):
        blocked_users = self.settings["blocked_users"]
        if not blocked_users:
            return

        if user in blocked_users:
            await reaction.message.remove_reaction(reaction.emoji, user)
