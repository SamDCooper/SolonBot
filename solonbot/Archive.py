import logging
import re

import discord

import solon

__all__ = []

log = logging.getLogger(__name__)
config = solon.get_config(__name__)

log.info(f"Loading {__name__}")

role_list = solon.SerializedList(discord.Role)
text_channel_list = solon.SerializedList(discord.TextChannel)

role_list_name = solon.SerializedList(discord.Role).__name__
int_to_role_name = solon.SerializedDictionary(int, discord.Role).__name__

default_settings = {
    "channels": {"value_serialized": "", "type_name": text_channel_list.__name__},
    "archivist_roles": {"value_serialized": "", "type_name": role_list.__name__},
    "blocked_roles": {"value_serialized": "", "type_name": role_list.__name__},
    "require_description": {"value_serialized": "false", "type_name": "bool"},
    "require_embed_links": {"value_serialized": "true", "type_name": "bool"},
    "submission_bump": {"value_serialized": "true", "type_name": "bool"},

    "award_eligible": {"value_serialized": "", "type_name": "role"},
    "award_ranks": {"value_serialized": "", "type_name": int_to_role_name},
    "award_method": {"value_serialized": "score", "type_name": "str"},
    "award_ranks_exclude": {"value_serialized": "", "type_name": role_list_name}
}


def log_malformed(message, why="none specified"):
    log.info(f"{message.author} might have tried to archive in {message.channel} on {message.guild}. "
             f"Reason given: {why}.")
    log.info(f"Message was {message.content} with {len(message.attachments)} attachments.")
    if message.attachments:
        log.info(f"Attachments are {message.attachments}.")


async def parse_archive(message, settings):
    # Parsing
    embedded_url = None

    # Parse message
    content = message.content
    if " " in content:
        channel_link, content_remainder = content.split(" ", 1)
    else:
        channel_link = content
        content_remainder = ""

    if not re.match(r"<#!?([0-9]+)>$", channel_link):
        return None

    # first word must be a channel link
    channel_value_serialized = channel_link

    require_embed_links = settings["require_embed_links"]
    embedded_url = None
    if require_embed_links:
        # Image can either be an attachment
        if message.attachments:
            embedded_url = message.attachments[0].url

        else:
            # Or the last or second word in the message
            if " " in content_remainder:
                content_middle, possible_image_url = content_remainder.rsplit(" ", 1)
                if solon.is_url(possible_image_url):
                    embedded_url = possible_image_url  # we assume its an image, no big deal if it's not
                    content_remainder = content_middle
                else:
                    possible_image_url, content_end = content_remainder.split(" ", 1)
                    if solon.is_url(possible_image_url):
                        embedded_url = possible_image_url
                        content_remainder = content_end
            else:
                # no description given
                if solon.is_url(content_remainder):
                    embedded_url = content_remainder
                    content_remainder = ""

    # With the description being whatever's left, which might be empty
    description = content_remainder

    # Validation
    if not channel_value_serialized:
        # channel must be specified - if we're exiting here
        # it probably means the message wasn't intended to
        # be archived.
        return None

    if require_embed_links and not embedded_url:
        # image required - again, if we're exiting here it's
        # likely that someone is just sending a message
        # consisting of a channel link, and we shouldn't warn
        # them
        log_malformed(message, "no URL")
        return None

    if settings["require_description"] and not description:
        # However, we should warn them when we're requiring a
        # description, because chances are if we've reached
        # this point they are trying to archive, but have
        # neglected a description.
        log_malformed(message, "no description")
        await message.channel.send(f"I can't submit that to the archive without a description.")
        return None

    guild = message.guild
    target_channel_serialized = solon.SerializedData(value_serialized=channel_value_serialized,
                                                     type_name="TextChannel")
    target_channel = solon.deserialize(target_channel_serialized, guild)
    if not target_channel:
        log_malformed(message, f"channel vs='{channel_value_serialized}' doesn't exist.")
        await message.channel.send(f"I don't recognize that channel")
        return None

    channels = settings["channels"]
    if target_channel not in channels:
        log_malformed(message, f"{target_channel} is not an archive channel")
        await message.channel.send(f"{target_channel} is not marked as an archive channel.")
        return None

    # Check the author has permission to add to the archive
    author = message.author
    author_is_archivist = False

    # Must be an archivist
    archivist_roles = settings["archivist_roles"]
    if archivist_roles:
        for role in archivist_roles:
            # Author must have at least one archivist role
            if role in author.roles:
                author_is_archivist = True
                break
    else:
        # Everybody is an archivist if there are no archivist roles.
        author_is_archivist = True

    # Unless they're in the blocked list
    blocked_roles = settings["blocked_roles"]
    if blocked_roles:
        for role in blocked_roles:
            if role in author.roles:
                author_is_archivist = False
                break

    if not author_is_archivist:
        await message.channel.send(f"Sorry, you don't have permission to add to the {message.guild} archive.")
        return None

    return {
        "author": author,
        "description": description,
        "embedded_url": embedded_url,
        "channel": target_channel
    }


class Data:
    def __init__(self):
        self.archive = []
        self.scoreboard = {}

    def post_init(self):
        if not self.scoreboard:
            for record in self.archive:
                author_id = record["author"]
                self.scoreboard[author_id] = self.scoreboard.get(author_id, 0) + 1


@solon.Cog(default_settings=default_settings, data_type=Data)
class Archive:
    def __init__(self, guild_id, settings, data):
        self.settings = settings
        self.guild_id = guild_id
        self.data = data

        self.data.post_init()

        solon.register_scoreboard(self, guild_id, settings)

    @property
    def scoreboard(self):
        return self.data.scoreboard

    @solon.Event()
    async def on_message(self, message):
        if message.author.bot:
            return

        archive = await parse_archive(message, self.settings)
        if archive:
            await self.archive(**archive)

    async def archive(self, author, description, embedded_url, channel):
        author_name = solon.get_name_from_user_id(channel.guild.id, author.id)
        self.data.archive.append({
            "author": author.id,
            "description": description if description is not None else "",
            "embedded_url": embedded_url,
            "channel": channel.id,
            "channel_name": channel.name
        })

        if embedded_url and solon.is_youtube_url(embedded_url):
            youtube_url = embedded_url
            # Have to send this as a separate message, since we can't embed videos in discord.py yet
            await channel.send(youtube_url)
            embedded_url = None

        embed_kwargs = {}
        if description:
            embed_kwargs["description"] = description

        embed = discord.Embed(**embed_kwargs)
        if embedded_url:
            embed.set_image(url=embedded_url)
        embed.set_author(name=author_name, icon_url=author.avatar_url)

        score = self.data.scoreboard.get(author.id, 0)
        self.data.scoreboard[author.id] = score + 1

        await channel.send(embed=embed)

        if self.settings["submission_bump"]:
            await self.bump_channel(channel)

    async def bump_channel(self, top_channel):
        guild = solon.Bot.get_guild(self.guild_id)

        def order_channel(ch):
            channel_id = ch.id
            if channel_id == top_channel.id:
                return 0  # front element

            channel = guild.get_channel(channel_id)
            if not channel:
                return 0xffff  # channel no longer exists, deal with this later

            pivot_position = top_channel.position
            position = channel.position

            if position < pivot_position:
                # if above the old position of the top channel,
                # move channel down by one
                return position + 1
            else:
                # otherwise, dont move channel
                return position

        channels_ordered = sorted(self.settings["channels"], key=order_channel)
        try:
            reason = f"Reordering archive - new message in {top_channel}."
            for new_position in range(len(channels_ordered)):
                channel = channels_ordered[new_position]
                if channel:
                    if channel.position != new_position:
                        await channel.edit(position=new_position, reason=reason)
                        reason = None

        except discord.Forbidden:
            log.warning(f"I don't have permission to order channels on {guild}. I need the Manage Channels permission.")
