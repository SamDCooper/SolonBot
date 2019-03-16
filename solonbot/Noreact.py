import discord
import logging
import random
import solon

__all__ = []

log = logging.getLogger(__name__)
config = solon.get_config(__name__)

log.info(f"Loading {__name__}")

member_list_name = solon.SerializedList(discord.Member).__name__

default_settings = {
    "blocked_users": {"value_serialized": "", "type_name": member_list_name},
    "block_chance": {"value_serialized": "1", "type_name": "float"}
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
            block_chance = self.settings["block_chance"]
            block_chance = 1 if block_chance > 1 else 0 if block_chance < 0 else block_chance
            if random.random() < block_chance:
                await reaction.message.remove_reaction(reaction.emoji, user)
