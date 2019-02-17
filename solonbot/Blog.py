import discord
import logging

import solon

__all__ = []

# TODO clean up channels which have been deleted from the list and log something out

log = logging.getLogger(__name__)
config = solon.get_config(__name__)

log.info(f"Loading {__name__}")

role_list_name = solon.SerializedList(discord.Role).__name__
int_to_role_name = solon.SerializedDictionary(int, discord.Role).__name__

default_settings = {
    "can_create_blog": {"value_serialized": "", "type_name": role_list_name},
    "readers": {"value_serialized": "", "type_name": role_list_name},
    "writers": {"value_serialized": "", "type_name": role_list_name},
    "reacters": {"value_serialized": "", "type_name": role_list_name},
    "category": {"value_serialized": "", "type_name": "CategoryChannel"},

    "blogvote_react": {"value_serialized": "", "type_name": "Emoji"},
    "can_blogvote": {"value_serialized": "", "type_name": role_list_name},

    "award_eligible": {"value_serialized": "", "type_name": "role"},
    "award_ranks": {"value_serialized": "", "type_name": int_to_role_name},
    "award_method": {"value_serialized": "score", "type_name": "str"},
    "award_ranks_exclude": {"value_serialized": "", "type_name": role_list_name}
}


class BloggingError(solon.CommandError):
    pass


class Data:
    def __init__(self):
        self.blogs = {}  # user_id -> { channel_id }
        self.scoreboard = {}


def set_overwrites_for_roles(roles, overwrites, **kwargs):
    if roles:
        for role in roles:
            if role not in overwrites:
                overwrites[role] = discord.PermissionOverwrite(**kwargs)
            else:
                overwrites[role].update(**kwargs)


@solon.Cog(default_settings=default_settings, data_type=Data)
class Blog:
    def __init__(self, guild_id, settings, data):
        self.guild_id = guild_id
        self.settings = settings
        self.data = data

        solon.register_scoreboard(self, guild_id, settings)

    @property
    def scoreboard(self):
        return self.data.scoreboard

    def has_blog(self, user):
        channel_id = self.data.blogs.get(user.id, None)
        if channel_id:
            guild = solon.Bot.get_guild(self.guild_id)
            channel = guild.get_channel(channel_id)
            return channel is not None
        return False

    def can_blogvote(self, user):
        if not self.settings["blogvote_react"]:
            return False

        can_vote_roles = self.settings["can_blogvote"]
        if can_vote_roles is None:
            log.warning(f"Nobody is authorised to vote on {solon.Bot.get_guild(self.guild_id)}.")
            return False

        for role in can_vote_roles:
            if role in user.roles:
                return True

        return False

    def blog_channel(self, user):
        return self.data.blogs.get(user.id, None)

    def set_score(self, author, score):
        self.data.scoreboard[author.id] = score

    def score(self, author):
        s = self.data.scoreboard.get(author.id)
        if s is None:
            return 0
        return s

    @solon.Event()
    async def on_reaction_add(self, reaction, user):
        author = reaction.message.author
        if author.bot:
            return

        if author.id == user.id:
            return

        up_emoji = self.settings["blogvote_react"]

        if up_emoji and solon.emoji_equals(reaction.emoji, up_emoji):
            if self.can_blogvote(user):
                blog_id = self.data.blogs.get(author.id, None)
                if blog_id:
                    if blog_id == reaction.message.channel.id:
                        log.info(f"{user} added upvote to message by {author} ({reaction.message.id})")
                        self.set_score(author, self.score(author) + 1)
            else:
                log.info(f"{user} tried to upvote message by {author}, but did not have permission. "
                         f"({reaction.message.id})")

    @solon.Event()
    async def on_reaction_remove(self, reaction, user):
        author = reaction.message.author
        if author.bot:
            return

        if author.id == user.id:
            return

        author = reaction.message.author
        up_emoji = self.settings["blogvote_react"]

        if up_emoji and solon.emoji_equals(reaction.emoji, up_emoji):
            if self.can_blogvote(user):
                blog_id = self.data.blogs.get(author.id, None)
                if blog_id:
                    if blog_id == reaction.message.channel.id:
                        log.info(f"{user} removed upvote on message by {author} ({reaction.message.id})")
                        self.set_score(author, self.score(author) - 1)
            else:
                log.info(f"{user} tried to remove upvote on message by {author}, but did not have permission. "
                         f"({reaction.message.id})")

    @solon.Event()
    async def on_message(self, message):
        if message.channel.id in self.data.blogs.values():
            top_channel = message.channel
            if top_channel.position == 0:
                return

            guild = solon.Bot.get_guild(self.guild_id)

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

    @solon.Command()
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
