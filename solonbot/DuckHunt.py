import logging
import random
import solon
import discord

__all__ = []

log = logging.getLogger(__name__)
config = solon.get_config(__name__)

log.info(f"Loading {__name__}")

role_list_name = solon.SerializedList(discord.Role).__name__
member_list_name = solon.SerializedList(discord.Member).__name__
channel_list_name = solon.SerializedList(discord.TextChannel).__name__
emoji_to_int_name = solon.SerializedDictionary(solon.Emoji, int).__name__
int_to_role_name = solon.SerializedDictionary(int, discord.Role).__name__

default_settings = {
    "duck_react": {"value_serialized": "🦆", "type_name": "Emoji"},
    "golden_duck_react": {"value_serialized": "", "type_name": "Emoji"},
    "golden_duck_points": {"value_serialized": "3", "type_name": "float"},
    "golden_duck_chance": {"value_serialized": "0.2", "type_name": "float"},
    "can_play": {"value_serialized": "", "type_name": "role"},
    "spawn_rate": {"value_serialized": "0.06", "type_name": "float"},
    "spawn_channels": {"value_serialized": "", "type_name": channel_list_name},
    "hidden_users": {"value_serialized": "", "type_name": member_list_name},

    "award_eligible": {"value_serialized": "", "type_name": "role"},
    "award_ranks": {"value_serialized": "", "type_name": int_to_role_name},
    "award_method": {"value_serialized": "score", "type_name": "str"},
    "award_ranks_exclude": {"value_serialized": "", "type_name": role_list_name}
}


class Data:
    def __init__(self):
        self.scoreboard = {}


@solon.Cog(default_settings=default_settings, data_type=Data)
class DuckHunt:
    def __init__(self, guild_id, settings, data):
        self.chance_spawn_duck.start(self, solon.timedelta_from_string(config["chance_spawn_frequency"]))
        self.spawn_duck = False
        self.data = data
        self.settings = settings
        self.guild_id = guild_id

        self.current_duck = None
        self.current_duck_golden = False

        solon.register_scoreboard(self, guild_id, settings)

    @property
    def scoreboard(self):
        hidden_members = self.settings["hidden_users"]
        return {k: v for k, v in self.data.scoreboard.items() if k not in [user.id for user in hidden_members]}

    @solon.TimedEvent()
    async def chance_spawn_duck(self):
        guild = solon.Bot.get_guild(self.guild_id)

        spawn_rate = self.settings["spawn_rate"]
        spawn_chance = random.random()
        if spawn_chance < spawn_rate:
            if self.current_duck is not None:
                log.info(f"Despawning old duck on {guild}, which was still alive.")
                # credit score to bot user
                me = solon.Bot.user
                score = self.data.scoreboard.get(me.id, 0)
                self.data.scoreboard[me.id] = score + 1

                duck_react = self.settings["duck_react"]
                if duck_react is not None:
                    await self.current_duck.remove_reaction(duck_react.discord_py_emoji, solon.Bot.user)
                self.current_duck = None
                self.current_duck_golden = False
            else:
                log.info(f"Time to spawn a duck on {guild}.")
                self.spawn_duck = True
        else:
            if self.spawn_duck:
                log.info(f"Spawn expired on {guild}.")
                self.spawn_duck = False

    @solon.Event()
    async def on_message(self, message):
        if self.spawn_duck:
            spawn_channels = self.settings["spawn_channels"]
            if spawn_channels is None:
                return
            if message.channel not in spawn_channels:
                return

            self.spawn_duck = False

            duck_react = self.settings["duck_react"]
            if duck_react is None:
                log.warning(f"duckhunt.duck_react is None on guild {message.guild}.")
                return

            golden_duck_react = self.settings["golden_duck_react"]
            self.current_duck_golden = False
            if golden_duck_react is not None:
                golden_duck_chance = self.settings["golden_duck_chance"]
                golden_duck_roll = random.random()
                if golden_duck_roll < golden_duck_chance:
                    self.current_duck_golden = True
                    duck_react = golden_duck_react

            guild = solon.Bot.get_guild(self.guild_id)
            log.info(f"Spawning a duck in {message.channel} on {guild}.")
            if self.current_duck_golden:
                log.info(f"It's a golden duck!")
            await message.add_reaction(duck_react.discord_py_emoji)
            self.current_duck = message

    @solon.Event()
    async def on_reaction_add(self, reaction, user):
        if self.current_duck is not None and reaction.message.id == self.current_duck.id:
            if user.id != solon.Bot.user.id:
                if self.current_duck_golden:
                    duck_react = self.settings["golden_duck_react"]
                else:
                    duck_react = self.settings["duck_react"]

                if duck_react is not None and solon.emoji_equals(reaction.emoji, duck_react):
                    can_play = self.settings["can_play"]
                    if can_play is None or can_play in user.roles:
                        guild = solon.Bot.get_guild(self.guild_id)
                        log.info(f"{user} successfully got the duck on {guild}.")
                        score = self.data.scoreboard.get(user.id, 0)

                        additional = 1 if not self.current_duck_golden else self.settings["golden_duck_points"]
                        self.data.scoreboard[user.id] = score + additional

                        self.current_duck = None
                        await reaction.message.remove_reaction(reaction.emoji, user)
                        await reaction.message.remove_reaction(reaction.emoji, solon.Bot.user)
                        self.current_duck_golden = False
