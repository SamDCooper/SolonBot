import discord
import logging

from solon import Cog
from solon import Event
from solon import get_config
from solon import SocratesRuntimeError

__all__ = []

log = logging.getLogger(__name__)
config = get_config(__name__)

log.info(f"Loading {__name__}")

default_settings = {
    "channel": {"value_serialized": "", "type_name": "textchannel"},
    "message": {"value_serialized": "hey {mention}, welcome to {server}!", "type_name": "str"},
    "image_url": {"value_serialized": "", "type_name": "str"}
}


class WelcomeError(SocratesRuntimeError):
    pass


@Cog(default_settings=default_settings)
class Welcome:
    def __init__(self, guild_id, settings):
        self.guild_id = guild_id
        self.settings = settings

    @Event()
    async def on_member_join(self, member):
        if member.bot:
            return

        channel = self.settings["channel"]
        if not channel:
            raise WelcomeError(f"Can't send welcome message on guild {member.guild} - no welcome channel set.")

        message_fmt = self.settings["message"]
        if not message_fmt:
            raise WelcomeError(f"Can't send welcome message on guild {member.guild} - no welcome message set.")
        message = message_fmt.format(**self.message_params(member))
        await channel.send(message)

        image_url = self.settings["image_url"]
        if image_url:
            embed = discord.Embed()
            embed.set_image(url=image_url)
            await channel.send(embed=embed)

    def message_params(self, member):
        return {
            "mention": member.mention,
            "user": member.display_name,
            "server": member.guild.name
        }
