import datetime
import discord
import logging
import solon

__all__ = []

log = logging.getLogger(__name__)
config = solon.get_config(__name__)

log.info(f"Loading {__name__}")

int_to_role_name = solon.SerializedDictionary(int, discord.Role).__name__
role_list_name = solon.SerializedList(discord.Role).__name__

default_settings = {
    "ranking_message_delay": {"value_serialized": "1m", "type_name": "timedelta"},
    "decay_interval": {"value_serialized": "1w", "type_name": "timedelta"},
    "depreciation_factor": {"value_serialized": "0.96", "type_name": "float"},

    "award_eligible": {"value_serialized": "", "type_name": "role"},
    "award_ranks": {"value_serialized": "", "type_name": int_to_role_name},
    "award_method": {"value_serialized": "score", "type_name": "str"},
    "award_ranks_exclude": {"value_serialized": "", "type_name": role_list_name}
}


class Data:
    def __init__(self):
        self.scoreboard = {}


@solon.Cog(default_settings=default_settings, data_type=Data)
class Activity(discord.ext.commands.Cog):
    def __init__(self, guild_id, settings, data):
        self.guild_id = guild_id
        self.settings = settings
        self.data = data
        self.last_message_sent = {}

        solon.register_scoreboard(self, guild_id, settings)
        self.depreciate_all_scores.start(self, self.settings["decay_interval"])

    @property
    def scoreboard(self):
        return self.data.scoreboard

    @solon.Event()
    async def on_message(self, message):
        if not message.author.bot:
            author_id = message.author.id
            now = datetime.datetime.utcnow()
            last_message_time = self.get_last_message_sent_time(author_id)
            if now - last_message_time > self.settings["ranking_message_delay"]:
                score = self.data.scoreboard.get(author_id, 0)
                self.data.scoreboard[author_id] = score + 1
                self.last_message_sent[author_id] = now

    @solon.TimedEvent()
    async def depreciate_all_scores(self):
        factor = self.settings["depreciation_factor"]
        for user_id, score in self.data.scoreboard.items():
            self.data.scoreboard[user_id] = factor * score

    def get_last_message_sent_time(self, author_id):
        last_message_sent = self.last_message_sent.get(author_id)
        if last_message_sent is None:
            last_message_sent = datetime.datetime.min
        return last_message_sent
