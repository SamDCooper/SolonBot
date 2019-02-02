import discord
import logging

from solon import Bot
from solon import Cog
from solon import Command
from solon import Event
from solon import get_config
from solon import SerializedList
from solon import CommandError

__all__ = []

# TODO clean up channels which have been deleted from the list and log something out

log = logging.getLogger(__name__)
config = get_config(__name__)

log.info(f"Loading {__name__}")

role_list = SerializedList(discord.Role)

default_settings = {
    "can_create_blog": {"value_serialized": "", "type_name": role_list.__name__},
    "readers": {"value_serialized": "", "type_name": role_list.__name__},
    "writers": {"value_serialized": "", "type_name": role_list.__name__},
    "reacters": {"value_serialized": "", "type_name": role_list.__name__},
    "category": {"value_serialized": "", "type_name": "CategoryChannel"},
}


class BloggingError(CommandError):
    pass


class Data:
    def __init__(self):
        self.blogs = {}  # user_id -> { channel_id }


def set_overwrites_for_roles(roles, overwrites, **kwargs):
    if roles:
        for role in roles:
            if role not in overwrites:
                overwrites[role] = discord.PermissionOverwrite(**kwargs)
            else:
                overwrites[role].update(**kwargs)


@Cog(default_settings=default_settings, data_type=Data)
class Blog:
    def __init__(self, guild_id, settings, data):
        self.guild_id = guild_id
        self.settings = settings
        self.data = data

    def has_blog(self, user):
        channel_id = self.data.blogs.get(user.id, None)
        if channel_id:
            guild = Bot.get_guild(self.guild_id)
            channel = guild.get_channel(channel_id)
            return channel is not None
        return False

    def blog_channel(self, user):
        return self.data.blogs.get(user.id, None)

    @Event()
    async def on_message(self, message):
        if message.channel.id in self.data.blogs.values():
            top_channel = message.channel
            if top_channel.position == 0:
                return

            guild = Bot.get_guild(self.guild_id)

            log.info(f"Reordering blogs on guild {guild}. Setting {top_channel} to top.")

            def order_blog(channel_id):
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

            blogs_ordered = sorted(self.data.blogs.values(), key=order_blog)
            try:
                reason = f"Reordering blogs - new message in {top_channel}."
                for new_position in range(len(blogs_ordered)):
                    channel = guild.get_channel(blogs_ordered[new_position])
                    if channel:
                        if channel.position != new_position:
                            await channel.edit(position=new_position, reason=reason)
                            reason = None

            except discord.Forbidden:
                raise BloggingError("I don't have permission to order channels. I need the Manage Channels permission.")

    @Command()
    async def create(self, ctx):
        can_create_blog = False
        for role in self.settings["can_create_blog"]:
            if role in ctx.author.roles:
                can_create_blog = True
                break

        if not can_create_blog:
            raise BloggingError(f"You don't have permission to do that.")

        if self.has_blog(ctx.author):
            raise BloggingError(f"You already have a blog.")

        # Blog overwrites
        overwrites = {  # TODO replace overwrites with a "blog template" channel overwrites template
            # dont set read_messages to true because we don't want them to have access to their own blog
            # if they wouldn't have access to the others (eg muted)
            ctx.author: discord.PermissionOverwrite(send_messages=True, manage_messages=True, manage_channels=True),
            ctx.guild.roles[0]: discord.PermissionOverwrite(read_messages=False, send_messages=False)
        }
        set_overwrites_for_roles(self.settings["readers"], overwrites, read_messages=True)
        set_overwrites_for_roles(self.settings["writers"], overwrites, read_messages=True, send_messages=True)
        set_overwrites_for_roles(self.settings["reacters"], overwrites, read_messages=True, add_reactions=True)
        if self.settings["reacters"]:
            overwrites[ctx.guild.roles[0]].update(add_reactions=False)

        kwargs = {
            "name": ctx.author.display_name,
            "overwrites": overwrites,
            "reason": "Creating blog"
        }
        category = self.settings["category"]
        if category:
            kwargs["category"] = category

        try:
            new_blog = await ctx.guild.create_text_channel(**kwargs)
            self.data.blogs[ctx.author.id] = new_blog.id
            await ctx.send(f"{ctx.author.mention} Okay, I've created a blog for you at {new_blog.mention}.")

        except discord.Forbidden:
            raise BloggingError("Sorry, I don't have permission to do that. I need the 'manage channels' permission.")

        except discord.HTTPException as e:
            await ctx.send("Sorry, creating the channel failed. It might work if you try again.")
            raise e

        except discord.InvalidArgument as e:
            await ctx.send("Sorry, something went wrong with setting up the permissions.")
            raise e
