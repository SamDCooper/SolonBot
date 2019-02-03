import discord
import logging
import solon

__all__ = []

log = logging.getLogger(__name__)
config = solon.get_config(__name__)

log.info(f"Loading {__name__}")

int_to_role_name = solon.SerializedDictionary(int, discord.Role).__name__

default_settings = {
    "award_eligible": {"value_serialized": "", "type_name": "role"},
    "award_ranks": {"value_serialized": "", "type_name": int_to_role_name},
    "award_method": {"value_serialized": "score", "type_name": "str"}
}


class Data:
    def __init__(self):
        self.scoreboard = {}


@solon.Cog(default_settings=default_settings, data_type=Data)
class Activity:
    def __init__(self, guild_id, settings, data):
        self.guild_id = guild_id
        self.settings = settings
        self.data = data

        solon.register_scoreboard(self, guild_id, settings)

    @property
    def scoreboard(self):
        return self.data.scoreboard

    @solon.Event()
    async def on_message(self, message):
        pass
