import discord
import logging

from solon import Cog
from solon import Command
from solon import get_config
from solon import get_setting_value
from solon import get_setting_field_names
from solon import set_setting_value
from solon import get_setting_type_name
from solon import get_identifier
from solon import deserialize
from solon import SerializedData
from solon import get_cogs_with_settings

__all__ = []

log = logging.getLogger(__name__)
config = get_config(__name__)

log.info(f"Loading {__name__}")

guild_settings = {
    "use_commands": {"value_serialized": "", "type_name": "role"},
    "name_format_has_nick": {"value_serialized": "{nick} ({name})", "type_name": "str"},
    "name_format_no_nick": {"value_serialized": "{name}", "type_name": "str"},
    "name_decor_absent": {"value_serialized": "{user} (RIP)", "type_name": "str"},
    "name_decor_present": {"value_serialized": "{user}", "type_name": "str"},
    "name_unknown_user": {"value_serialized": "Unknown User {code}", "type_name": "str"},
}


@Cog(default_active=True, default_settings=guild_settings)
class Globals:
    def __init__(self, guild_id, settings):
        pass  # Dummy cog object just for holding settings


@Cog(default_active=True, guild_local=False)
class Settings(discord.ext.commands.Cog):
    @Command(manage_guild=True)
    async def set(self, ctx, variable_name, *, value_serialized):
        guild = ctx.guild
        cog_type_name, field_name = variable_name.split(".", 1)

        identifier = get_identifier(cog_type_name, guild.id)
        field_type_name = get_setting_type_name(identifier, field_name)

        value = deserialize(SerializedData(value_serialized=value_serialized, type_name=field_type_name), guild)
        set_setting_value(identifier, field_name, value)

        value_from_store = get_setting_value(identifier, field_name)

        await ctx.send(f"Successfully set {variable_name} to {value_from_store} ({field_type_name})")

    @Command()
    async def query(self, ctx, variable_name):
        guild = ctx.guild
        cog_type_name, field_name = variable_name.split(".", 1)
        identifier = get_identifier(cog_type_name, guild.id)
        value = get_setting_value(identifier, field_name)

        type_name = get_setting_type_name(identifier, field_name)
        if value is None:
            value_str = "<unset>"
        else:
            value_str = str(value)

        await ctx.send(f"```{variable_name}: {value_str} ({type_name})```")

    @Command(manage_guild=True)
    async def clear(self, ctx, variable_name):
        guild = ctx.guild
        cog_type_name, field_name = variable_name.split(".", 1)

        identifier = get_identifier(cog_type_name, guild.id)
        field_type_name = get_setting_type_name(identifier, field_name)

        set_setting_value(identifier, field_name, None)

        await ctx.send(f"Successfully cleared {variable_name} ({field_type_name})")

    @Command(manage_guild=True)
    async def add(self, ctx, qualified_list_name, *, value_serialized):
        guild = ctx.guild
        cog_type_name, list_name = qualified_list_name.split(".", 1)

        identifier = get_identifier(cog_type_name, guild.id)

        list_in_store = get_setting_value(identifier, list_name)
        value = deserialize(
            SerializedData(value_serialized=value_serialized, type_name=list_in_store.element_type_name), guild)
        list_in_store.append(value)

        await ctx.send(f"Successfully added {value} to {list_name} ({list_in_store.element_type_name})")

    @Command(manage_guild=True)
    async def remove(self, ctx, qualified_list_name, *, value_serialized):
        guild = ctx.guild
        cog_type_name, list_name = qualified_list_name.split(".", 1)

        identifier = get_identifier(cog_type_name, guild.id)

        list_in_store = get_setting_value(identifier, list_name)
        value = deserialize(
            SerializedData(value_serialized=value_serialized, type_name=list_in_store.element_type_name), guild)
        list_in_store.remove(value)

        await ctx.send(f"Successfully removed {value} from {list_name} ({list_in_store.element_type_name})")

    @Command()
    async def list(self, ctx, cog_type_name):
        guild = ctx.guild
        identifier = get_identifier(cog_type_name, guild.id)
        field_names = get_setting_field_names(identifier)

        output = ""
        for field_name in field_names:
            value = get_setting_value(identifier, field_name)
            type_name = get_setting_type_name(identifier, field_name)
            if value is None:
                value_str = "<unset>"
            else:
                value_str = str(value)
            output += f"{field_name}: {value_str} ({type_name})\n"

        await ctx.send(f"Settings for {cog_type_name} on {ctx.guild}:\n```{output}```")

    @Command()
    async def cogs(self, ctx):
        guild = ctx.guild
        cogs = get_cogs_with_settings(guild)
        output = "\n".join(cogs)
        await ctx.send(f"The following cogs have settings available:\n```{output}```")
