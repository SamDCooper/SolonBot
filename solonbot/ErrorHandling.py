import discord
import logging
import traceback

from discord.ext.commands import CommandNotFound

from solon import Cog
from solon import Event
from solon import Bot
from solon import SocratesRuntimeError
from solon import get_config

__all__ = []

log = logging.getLogger(__name__)
config = get_config(__name__)

log.info(f"Loading {__name__}")


@Cog(guild_local=False, guild_only=False, default_active=True, toggleable=False)
class ErrorHandling:
    @Event()
    async def on_command_error(self, ctx, err):
        excep = err.original if hasattr(err, "original") else err

        tb = "".join(traceback.format_tb(excep.__traceback__))
        log.error(f"Command error from {ctx.author}.\n{tb}{excep.__class__.__name__}: {excep}")
        if ctx.message is not None:
            log.error(f"Message was <{ctx.message.content}>")

        if isinstance(excep, SocratesRuntimeError):
            await ctx.send(f"Error: {excep}")
        elif isinstance(excep, CommandNotFound):
            # do not report command not found errors - could have been talking
            # to a different bot.
            log.info(f"Command not found. {excep}")
            return
        elif isinstance(excep, discord.Forbidden):
            await ctx.send(f"I don't have permission to do that.")
        else:
            if config["dm_owner"]:
                user = Bot.get_user(Bot.owner_id)
                if user is not None:
                    await user.send(
                        f"Unhandled error in command from {ctx.author}.```py\n{tb}{excep.__class__.__name__}: {excep}```")
            await ctx.send("Unknown error.")

    @Event()
    async def on_error(self, event_method, *args, **kwargs):
        user = Bot.get_user(Bot.owner_id)
        if user is not None:
            await user.send(f"Error caught in {event_method} with args {args}, {kwargs}")
