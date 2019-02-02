import logging

from solon import Cog
from solon import Command
from solon import get_config
from solon import get_identifier
from solon import get_scoreboard_by_identifier
from solon import get_name_from_user_id
from solon import CommandError

__all__ = []

log = logging.getLogger(__name__)
config = get_config(__name__)

log.info(f"Loading {__name__}")

default_settings = {
    "line_format": {"value_serialized": "#{rank} {name}: {score:.2f}", "type_name": "str"},
    "line_format_me": {"value_serialized": "**#{rank} {name}: {score:.2f}**", "type_name": "str"},
    "display_num_ranks": {"value_serialized": "15", "type_name": "int"},
    "my_ranks_buffer": {"value_serialized": "2", "type_name": "int"}
}


@Cog(guild_local=True, default_settings=default_settings)
class Scoreboards:
    def __init__(self, guild_id, settings):
        self.settings = settings
        self.guild_id = guild_id

    @Command()
    async def highscores(self, ctx, scoreboard_name):
        identifier = get_identifier(scoreboard_name, ctx.guild.id)
        sb = get_scoreboard_by_identifier(identifier)
        num_to_show = self.settings["display_num_ranks"]
        await self.show_scoreboard(ctx, sorted(sb.items(), key=lambda kv: -kv[1]), num_to_show, 0)

    @Command()
    async def lowscores(self, ctx, scoreboard_name):
        identifier = get_identifier(scoreboard_name, ctx.guild.id)
        sb = get_scoreboard_by_identifier(identifier)
        num_to_show = self.settings["display_num_ranks"]
        await self.show_scoreboard(ctx, sorted(sb.items(), key=lambda kv: +kv[1]), num_to_show, 0)

    @Command()
    async def score(self, ctx, scoreboard_name):
        identifier = get_identifier(scoreboard_name, ctx.guild.id)
        sb = get_scoreboard_by_identifier(identifier)
        if ctx.message.author.id not in sb:
            raise CommandError("You aren't ranked yet.")

        buffer = self.settings["my_ranks_buffer"]
        num_to_show = 1 + 2 * buffer
        sorted_scoreboard = sorted(sb.items(), key=lambda kv: -kv[1])

        my_rank = 0
        for user_id, score in sorted_scoreboard:
            if ctx.message.author.id == user_id:
                break
            my_rank = my_rank + 1

        await self.show_scoreboard(ctx, sorted_scoreboard, num_to_show, my_rank - buffer)

    async def show_scoreboard(self, ctx, scoreboard_sorted, num_to_show, starting_from):
        board_txt = ""

        num_ranks_to_show = num_to_show
        for rank in range(0, num_ranks_to_show):
            index = rank + starting_from
            if 0 <= index < len(scoreboard_sorted):
                user_id, score = scoreboard_sorted[index]
                name = get_name_from_user_id(self.guild_id, user_id)

                if user_id == ctx.message.author.id:
                    fmt = self.settings["line_format_me"]
                else:
                    fmt = self.settings["line_format"]

                formatted_rank_line = fmt.format(rank=index + 1, name=name, score=score)
                board_txt += formatted_rank_line + "\n"
        if board_txt:
            await ctx.send(board_txt)
        else:
            await ctx.send("Scoreboard is too empty for that right now.")
