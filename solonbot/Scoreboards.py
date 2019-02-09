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
    "thumbnail_url": {"value_serialized": "", "type_name": "str"}
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
    async def score(self, ctx, scoreboard_name):
        identifier = solon.get_identifier(scoreboard_name, ctx.guild.id)
        sb = solon.get_scoreboard_by_identifier(identifier)
        if ctx.message.author.id not in sb:
            raise solon.CommandError("You aren't ranked yet.")

        buffer = self.settings["my_ranks_buffer"]
        num_to_show = 1 + 2 * buffer
        sorted_scoreboard = sorted(sb.items(), key=lambda kv: -kv[1])

        my_rank = 0
        for user_id, score in sorted_scoreboard:
            if ctx.message.author.id == user_id:
                break
            my_rank = my_rank + 1

        await self.show_scoreboard(ctx, scoreboard_name, sorted_scoreboard, num_to_show, my_rank - buffer)

    async def show_scoreboard(self, ctx, scoreboard_name, scoreboard_sorted, num_to_show, starting_from):
        board_txt = ""

        num_ranks_to_show = num_to_show
        for rank in range(0, num_ranks_to_show):
            index = rank + starting_from
            if 0 <= index < len(scoreboard_sorted):
                user_id, score = scoreboard_sorted[index]
                name = solon.get_name_from_user_id(self.guild_id, user_id)

                if user_id == ctx.message.author.id:
                    fmt = self.settings["line_format_me"]
                else:
                    fmt = self.settings["line_format"]

                formatted_rank_line = fmt.format(rank=index + 1, name=name, score=score)
                board_txt += formatted_rank_line + "\n"
        if board_txt:
            title = f"Leaderboard for {scoreboard_name} on {ctx.guild.name}"

            embed = discord.Embed(title=title, description=board_txt)

            thumbnail_url = self.settings["thumbnail_url"]
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)

            await ctx.send(embed=embed)
        else:
            await ctx.send("Scoreboard is too empty for that right now.")
