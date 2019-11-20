import discord
import logging

from solon import Cog
from solon import Command
from solon import get_config

__all__ = []

log = logging.getLogger(__name__)
config = get_config(__name__)

log.info(f"Loading {__name__}")


@Cog(guild_local=False, guild_only=False)
class Pinging(discord.ext.commands.Cog):
    @Command()
    async def ping(self, ctx):
        await ctx.send("Pong!")
