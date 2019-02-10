import datetime
import discord
import logging
import random
import solon

__all__ = []

log = logging.getLogger(__name__)
config = solon.get_config(__name__)

log.info(f"Loading {__name__}")

str_to_emoji_tyoe_name = solon.SerializedDictionary(str, solon.Emoji).__name__

default_settings = {
    "reacts": {"value_serialized": "", "type_name": str_to_emoji_tyoe_name}
}


@solon.Cog(default_settings=default_settings)
class AutoReact:
    def __init__(self, guild_id, settings):
        self.guild_id = guild_id
        self.settings = settings

    @solon.Event()
    async def on_message(self, message):
        reacts = self.settings["reacts"]
        if not reacts:
            return

        for msg_match, emoji in reacts.items():
            if message.content == msg_match:
                await message.add_reaction(emoji.discord_py_emoji)
