import logging

from solon import Cog
from solon import Command
from solon import save_all
from solon import save_interval
from solon import TimedEvent

__all__ = []

log = logging.getLogger(__name__)

log.info(f"Loading {__name__}")


@Cog(default_active=True, guild_local=False, guild_only=False, toggleable=False)
class Database:
    def __init__(self):
        self.timed_save.start(self, save_interval)

    @Command(is_owner=True)
    async def save(self, ctx):
        save_all()
        await ctx.send("Saved.")

    @TimedEvent()
    async def timed_save(self):
        log.info("Scheduled timed save.")
        save_all()
