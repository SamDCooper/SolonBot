import logging

import discord
import solon

__all__ = []

log = logging.getLogger(__name__)
config = solon.get_config(__name__)

log.info(f"Loading {__name__}")

default_settings = {
    "line_format": {"value_serialized": "#{rank} {name}: {score:.0f}", "type_name": "str"},
    "line_format_me": {"value_serialized": "**#{rank} {name}: {score:.0f}**", "type_name": "str"},
    "display_num_ranks": {"value_serialized": "15", "type_name": "int"},
    "my_ranks_buffer": {"value_serialized": "2", "type_name": "int"},
    "thumbnail_url": {"value_serialized": "", "type_name": "str"},
    "hide_absent_users": {"value_serialized": "false", "type_name": "bool"}
}


@solon.Cog(guild_local=True, default_settings=default_settings)
class Scoreboards:
    def __init__(self, guild_id, settings):
        self.settings = settings
        self.guild_id = guild_id

    @solon.Command()
    async def highscores(self, ctx, scoreboard_name):
        identifier = solon.get_identifier(scoreboard_name, ctx.guild.id)
        sb = solon.get_scoreboard_by_identifier(identifier)
        num_to_show = self.settings["display_num_ranks"]
        await self.show_scoreboard(ctx, scoreboard_name, sorted(sb.items(), key=lambda kv: -kv[1]), num_to_show, 0)

    @solon.Command()
    async def lowscores(self, ctx, scoreboard_name):
        identifier = solon.get_identifier(scoreboard_name, ctx.guild.id)
        sb = solon.get_scoreboard_by_identifier(identifier)
        num_to_show = self.settings["display_num_ranks"]
        await self.show_scoreboard(ctx, scoreboard_name, sorted(sb.items(), key=lambda kv: +kv[1]), num_to_show, 0)

    @solon.Command()
    async def score(self, ctx, scoreboard_name: str, user: solon.converter(discord.Member) = None):
        if user is None:
            user = ctx.message.author

        identifier = solon.get_identifier(scoreboard_name, ctx.guild.id)
        sb = solon.get_scoreboard_by_identifier(identifier)
        if user.id not in sb:
            raise solon.CommandError("You aren't ranked yet.")

        buffer = self.settings["my_ranks_buffer"]
        num_to_show = 1 + 2 * buffer
        sorted_scoreboard = sorted(sb.items(), key=lambda kv: -kv[1])

        my_rank = 0
        for user_id, score in sorted_scoreboard:
            if user.id == user_id:
                break
            my_rank = my_rank + 1

        await self.show_scoreboard(ctx, scoreboard_name, sorted_scoreboard, num_to_show, max(my_rank - buffer, 0), user)

    async def show_scoreboard(self, ctx, scoreboard_name, scoreboard_sorted, num_to_show, starting_from,
                              highlight_user=None):
        board_txt = ""

        hide_absent_users = self.settings["hide_absent_users"]
        guild = solon.Bot.get_guild(self.guild_id)

        num_ranks_to_show = num_to_show

        actual_rank = 0
        rank_to_display = starting_from + 1
        while rank_to_display <= starting_from + num_ranks_to_show and rank_to_display - 1 < len(scoreboard_sorted):
            index = actual_rank + starting_from
            if 0 <= index < len(scoreboard_sorted):
                user_id, score = scoreboard_sorted[index]
                hide_user = hide_absent_users and guild.get_member(user_id) is None
                if not hide_user:
                    name = solon.get_name_from_user_id(self.guild_id, user_id)

                    if highlight_user and user_id == highlight_user.id:
                        fmt = self.settings["line_format_me"]
                    else:
                        fmt = self.settings["line_format"]

                    formatted_rank_line = fmt.format(rank=rank_to_display, name=name, score=score)

                    board_txt += formatted_rank_line + "\n"
                    rank_to_display = rank_to_display + 1

            actual_rank = actual_rank + 1

        if board_txt:
            title = f"Leaderboard for {scoreboard_name} on {ctx.guild.name}"

            embed = discord.Embed(title=title, description=board_txt)

            thumbnail_url = self.settings["thumbnail_url"]
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)

            await ctx.send(embed=embed)
        else:
            await ctx.send("Scoreboard is too empty for that right now.")
