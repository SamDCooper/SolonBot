import datetime
import discord
import logging
import random
import solon

from .cypher import scramble, unscramble

__all__ = []

log = logging.getLogger(__name__)
config = solon.get_config(__name__)

log.info(f"Loading {__name__}")

role_list_name = solon.SerializedList(discord.Role).__name__
int_to_role_name = solon.SerializedDictionary(int, discord.Role).__name__

default_settings = {
    "can_vote": {"value_serialized": "", "type_name": role_list_name},
    "can_delete_quotes": {"value_serialized": "", "type_name": role_list_name},
    "quote_emoji": {"value_serialized": "🗨", "type_name": "Emoji"},
    "added_emoji": {"value_serialized": "👌", "type_name": "Emoji"},
    "fail_emoji": {"value_serialized": "👎", "type_name": "Emoji"},
    "react_threshold": {"value_serialized": "3", "type_name": "int"},
    "thumbnail_url": {"value_serialized": "", "type_name": "str"},

    "award_eligible": {"value_serialized": "", "type_name": "role"},
    "award_ranks": {"value_serialized": "", "type_name": int_to_role_name},
    "award_method": {"value_serialized": "score", "type_name": "str"},
    "award_ranks_exclude": {"value_serialized": "", "type_name": role_list_name}
}


def message_is_by(message, user):
    return message["author_id"] == user.id


class Data:
    def __init__(self):
        self.next_quote_id = 0
        self.messages = []
        self.scoreboard = {}

    def post_init(self):
        if not self.scoreboard:
            for record in self.messages:
                author_id = record["author_id"]
                self.scoreboard[author_id] = self.scoreboard.get(author_id, 0) + 1


@solon.Cog(data_type=Data, default_settings=default_settings)
class Quoting:
    def __init__(self, guild_id, settings, data):
        self.guild_id = guild_id
        self.settings = settings
        self.data = data
        self.counting = {}  # message id -> number of reacts
        self.recorded_messages = []  # list of message ids

        solon.register_scoreboard(self, guild_id, settings)

        self.data.post_init()

    @property
    def scoreboard(self):
        return self.data.scoreboard

    @solon.Command()
    async def quote(self, ctx, user: solon.converter(discord.Member) = None):
        if user is None:
            messages = self.data.messages
        else:
            messages = [msg for msg in self.data.messages if message_is_by(msg, user)]

        num_messages = len(messages)

        if num_messages == 0:
            if user is None:
                await ctx.send("I don't have any quotes stored yet!")
            else:
                await ctx.send("I don't have any quotes stored for that user yet!")
            return

        elif num_messages == 1:
            quote = messages[0]

        else:
            index = random.randint(0, num_messages - 1)
            quote = messages[index]

        await ctx.send(embed=self.create_embed(quote, ctx.guild))

    @solon.Command()
    async def q(self, ctx, quote_code):
        quote_code_unscrambled = unscramble(quote_code, ctx.guild)
        quote = next((q for q in self.data.messages if q["quote_id"] == quote_code_unscrambled), None)
        if not quote:
            await ctx.send(f"{ctx.author.mention} Sorry, I can't find a quote with code {quote_code}.")
            return

        await ctx.send(embed=self.create_embed(quote, ctx.guild))

    @solon.Command()
    async def delete(self, ctx, quote_code):
        quote_code = unscramble(quote_code, ctx.guild)
        quote = next((q for q in self.data.messages if q["quote_id"] == quote_code), None)
        if not quote:
            await ctx.send(f"{ctx.author.mention} Sorry, I can't find a quote with code {quote_code}.")
            return

        if quote["author_id"] != ctx.author.id and not self.authorized_to_delete(ctx.author):
            await ctx.send(f"{ctx.author.mention} Sorry, you don't have permission to remove that quote.")
            return

        self.data.messages.remove(quote)
        await ctx.send(f"{ctx.author.mention} Okay, that quote has been removed.")

    def create_embed(self, quote, guild):
        quote_code = scramble(quote["quote_id"], guild)

        content = quote["content"]
        disclaimer = f"The author of this quote can delete it from the bot's memory with the command `quoting delete {quote_code}`"

        description = f"{content}\n\n{disclaimer}"

        embed = discord.Embed(description=description)

        author = solon.Bot.get_guild(self.guild_id).get_member(quote["author_id"])
        if author:
            author_name = solon.get_name_from_user_id(self.guild_id, quote["author_id"])
            avatar_url = author.avatar_url
        else:
            # use backups
            author_name = quote["author_name"]
            avatar_url = quote["avatar_url"]

        time_as_str = datetime.datetime.utcfromtimestamp(quote["date"]).strftime("%d/%m/%y")
        embed.set_author(name=f"{author_name} ({time_as_str})", icon_url=avatar_url)

        if quote["attachments"]:
            embed.set_image(url=quote["attachments"][0])  # just use first attachment

        thumbnail_url = self.settings["thumbnail_url"]
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)

        return embed

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
        can_vote_roles = self.settings["can_vote"]
        if can_vote_roles is None:
            log.warning(f"Nobody is authorised to vote on {solon.Bot.get_guild(self.guild_id)}.")
            return False

        for role in can_vote_roles:
            if role in user.roles:
                return True

        return False

    def authorized_to_delete(self, user):
        can_delete_roles = self.settings["can_delete_quotes"]
        if can_delete_roles is None:
            return False

        for role in can_delete_roles:
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
            success = self.create_message_record(message)
            if success:
                score = self.data.scoreboard.get(message.author.id, 0)
                self.data.scoreboard[message.author.id] = score + 1
            return success
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

            if message.id not in self.recorded_messages:
                if message.id not in self.counting:
                    log.info(f"Message {message.id} contents are: <{message.content}>")

                added = self.add_vote(message)
                # added ==
                #   None   if we don't add yet,
                #   True   if the adding succeeded, and
                #   False  otherwise.
                if added is not None:
                    if added and self.settings["added_emoji"]:
                        await message.add_reaction(self.settings["added_emoji"].discord_py_emoji)

                    elif not added and self.settings["fail_emoji"]:
                        await message.add_reaction(self.settings["fail_emoji"].discord_py_emoji)

                    self.recorded_messages.append(message.id)

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
