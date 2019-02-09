import logging

import discord
import solon

__all__ = []

log = logging.getLogger(__name__)
config = solon.get_config(__name__)

log.info(f"Loading {__name__}")

role_list_name = solon.SerializedList(discord.Role).__name__

default_settings = {
    "can_quote": {"value_serialized": "", "type_name": role_list_name},
    "quote_emoji": {"value_serialized": "🗨", "type_name": "Emoji"},
    "added_emoji": {"value_serialized": "👌", "type_name": "Emoji"},
    "fail_emoji": {"value_serialized": "👎", "type_name": "Emoji"},
    "react_threshold": {"value_serialized": "3", "type_name": "int"},
}


class Data:
    def __init__(self):
        self.next_quote_id = 0
        self.messages = []


@solon.Cog(data_type=Data, default_settings=default_settings)
class Quoting:
    def __init__(self, guild_id, settings, data):
        self.guild_id = guild_id
        self.settings = settings
        self.data = data
        self.counting = {}  # message id -> number of reacts
        self.recorded_messages = []  # list of message ids

    @solon.Command()
    async def quote(self, ctx, user: solon.converter(discord.Member)):
        await ctx.send("Pong!")

    def create_message_record(self, message):
        if message.content == "" and len(message.attachments) == 0:
            return False

        if message.author.bot:
            return False

        quote_id = self.data.next_quote_id
        self.data.next_quote_id = self.data.next_quote_id + 1

        record = {
            "quote_id": quote_id,
            "author_id": message.author.id,
            "author_name": solon.get_name_from_user_id(message.guild.id, message.author.id),
            "avatar_url": message.author.avatar_url,
            "content": message.content,
            "date": message.created_at.timestamp(),
            "attachments": [att.url for att in message.attachments]
        }
        self.data.messages.append(record)

        log.info(f"Record for message {message.id} created.")
        return True

    def authorized_to_vote(self, user):
        can_vote_roles = self.settings["can_quote"]
        if can_vote_roles is None:
            log.warning(f"Nobody is authorised to vote on {solon.Bot.get_guild(self.guild_id)}.")
            return False

        for role in can_vote_roles:
            if role in user.roles:
                return True

        return False

    def add_vote(self, message):
        if message.id in self.counting:
            self.counting[message.id] = self.counting[message.id] + 1
        else:
            self.counting[message.id] = 1

        react_threshold = self.settings["react_threshold"]
        log.info(f"Vote added on message {message.id}. Now at {self.counting[message.id]}/{react_threshold}.")

        if self.counting[message.id] >= react_threshold:
            return self.create_message_record(message)
        else:
            return None

    def remove_vote(self, message):
        if message.id in self.counting:
            self.counting[message.id] = self.counting[message.id] - 1
            react_threshold = self.settings["react_threshold"]
            log.info(f"Vote removed on message {message.id}. Now at {self.counting[message.id]}/{react_threshold}.")

        elif message.id in self.recorded_messages:
            log.info(f"Cannot remove vote on message {message.id} - it's already been recorded.")

        else:
            log.error(f"Cannot remove vote on message {message.id} - not in counting or recorded_messages lists.")

    @solon.Event()
    async def on_reaction_add(self, reaction, user):
        author = reaction.message.author
        if author.bot:
            return

        if author.id == user.id:
            return

        quote_emoji = self.settings["quote_emoji"]
        message = reaction.message
        if quote_emoji and solon.emoji_equals(reaction.emoji, quote_emoji) and self.authorized_to_vote(user):
            log.info(f"{user} quote voted on message by {author} ({reaction.message.id}).")

            if message.id not in self.counting and message.id not in self.recorded_messages:
                log.info(f"Message {message.id} contents are: <{message.content}>")

            added = self.add_vote(message)
            if added is not None:
                if added and self.settings["added_emoji"]:
                    await message.add_reaction(self.settings["added_emoji"].discord_py_emoji)

                elif not added and self.settings["fail_emoji"]:
                    await message.add_reaction(self.settings["fail_emoji"].discord_py_emoji)

    @solon.Event()
    async def on_reaction_remove(self, reaction, user):
        author = reaction.message.author
        if author.bot:
            return

        if author.id == user.id:
            return

        quote_emoji = self.settings["quote_emoji"]
        if quote_emoji and solon.emoji_equals(reaction.emoji, quote_emoji) and self.authorized_to_vote(user):
            log.info(f"{user} removed quote vote on message by {author} ({reaction.message.id})")
            self.remove_vote(reaction.message)
