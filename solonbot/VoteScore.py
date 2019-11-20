import discord
import logging

from solon import Bot
from solon import Cog
from solon import emoji_equals
from solon import Event
from solon import get_config
from solon import register_scoreboard
from solon import SerializedList
from solon import SerializedDictionary

__all__ = []

log = logging.getLogger(__name__)
config = get_config(__name__)

log.info(f"Loading {__name__}")

int_to_role_name = SerializedDictionary(int, discord.Role).__name__
role_list_name = SerializedList(discord.Role).__name__

default_settings = {
    "can_vote_roles": {"value_serialized": "", "type_name": role_list_name},
    "up_emoji": {"value_serialized": "⬆", "type_name": "Emoji"},
    "down_emoji": {"value_serialized": "⬇", "type_name": "Emoji"},

    "award_eligible": {"value_serialized": "", "type_name": "role"},
    "award_ranks": {"value_serialized": "", "type_name": int_to_role_name},
    "award_method": {"value_serialized": "score", "type_name": "str"},
    "award_ranks_exclude": {"value_serialized": "", "type_name": role_list_name}
}

int_to_role_name = SerializedDictionary(int, discord.Role).__name__

dummy_default_settings = {
}


class Data:
    def __init__(self):
        self.scoreboard = {}


@Cog(default_settings=default_settings, data_type=Data)
class VoteScore(discord.ext.commands.Cog):
    def __init__(self, guild_id, settings, data):
        self.guild_id = guild_id
        self.settings = settings
        self.data = data

        register_scoreboard(self, guild_id, settings)

    @property
    def scoreboard(self):
        return self.data.scoreboard

    def score(self, author):
        s = self.data.scoreboard.get(author.id)
        if s is None:
            return 0
        return s

    def set_score(self, author, score):
        self.data.scoreboard[author.id] = score

    def authorized_to_vote(self, user):
        can_vote_roles = self.settings["can_vote_roles"]
        if can_vote_roles is None:
            log.warning(f"Nobody is authorised to vote on {Bot.get_guild(self.guild_id)}.")
            return False

        for role in can_vote_roles:
            if role in user.roles:
                return True

        return False

    @Event()
    async def on_reaction_add(self, reaction, user):
        author = reaction.message.author
        if author.bot:
            return

        if author.id == user.id:
            return

        up_emoji = self.settings["up_emoji"]
        down_emoji = self.settings["down_emoji"]

        if up_emoji and emoji_equals(reaction.emoji, up_emoji):
            if self.authorized_to_vote(user):
                log.info(f"{user} added upvote to message by {author} ({reaction.message.id})")
                self.add_vote(author, 1)
            else:
                log.info(f"{user} tried to upvote message by {author}, but did not have permission. "
                         f"({reaction.message.id})")

        elif down_emoji and emoji_equals(reaction.emoji, down_emoji):
            if self.authorized_to_vote(user):
                log.info(f"{user} added downvote to message by {author} ({reaction.message.id})")
                self.add_vote(author, -1)
            else:
                log.info(f"{user} tried to downvote message by {author}, but did not have permission. "
                         f"({reaction.message.id})")

    @Event()
    async def on_reaction_remove(self, reaction, user):
        author = reaction.message.author
        if author.bot:
            return

        if author.id == user.id:
            return

        author = reaction.message.author
        up_emoji = self.settings["up_emoji"]
        down_emoji = self.settings["down_emoji"]

        if up_emoji and emoji_equals(reaction.emoji, up_emoji):
            if self.authorized_to_vote(user):
                log.info(f"{user} removed upvote on message by {author} ({reaction.message.id})")
                self.remove_vote(author, 1)
            else:
                log.info(f"{user} tried to remove upvote on message by {author}, but did not have permission. "
                         f"({reaction.message.id})")

        elif down_emoji and emoji_equals(reaction.emoji, down_emoji):
            if self.authorized_to_vote(user):
                log.info(f"{user} removed downvote on message by {author} ({reaction.message.id})")
                self.remove_vote(author, -1)
            else:
                log.info(f"{user} tried to remove upvote on message by {author}, but did not have permission. "
                         f"({reaction.message.id})")

    def add_vote(self, author, multiplier):
        self.set_score(author, self.score(author) + multiplier)

    def remove_vote(self, author, multiplier):
        self.set_score(author, self.score(author) - multiplier)
