import datetime
import discord
import logging
import random
import solon
import pprint

__all__ = []

log = logging.getLogger(__name__)
config = solon.get_config(__name__)

log.info(f"Loading {__name__}")

default_settings = {
    "new_channel_name": {"value_serialized": "new {template} channel", "type_name": "str"},
    "new_channel_category": {"value_serialized": "", "type_name": discord.CategoryChannel.__name__}
}


class Data:
    def __init__(self):
        self.templates = {}


@solon.Cog(data_type=Data, default_settings=default_settings)
class Template:
    def __init__(self, guild_id, data, settings):
        self.guild_id = guild_id
        self.settings = settings
        self.data = data

    def get_permission_overrides_from_template_name(self, template_name):
        template_data = self.data.templates.get(template_name)
        if template_data is not None:
            overwrites = {
                solon.deserialize(serialized_data=solon.SerializedData(value_serialized=k, type_name="role"),
                                  guild=solon.Bot.get_guild(self.guild_id)): discord.PermissionOverwrite(**kwargs)
                for k, kwargs in template_data.items()
            }
            return overwrites
        return None

    @solon.Command(manage_guild=True)
    async def create(self, ctx, template_name: str):
        overrides = self.get_permission_overrides_from_template_name(template_name)
        if overrides is None:
            raise solon.CommandError(f"There is no template with the name {template_name}.")

        channel_name = self.settings["new_channel_name"].format(template=template_name)
        channel = await ctx.guild.create_text_channel(name=channel_name, overwrites=overrides)
        await ctx.send(f"Successfully created {channel.mention} with template {template_name}.")

    @solon.Command(manage_guild=True)
    async def set(self, ctx, channel: solon.converter(discord.TextChannel), template_name: str):
        overrides = self.get_permission_overrides_from_template_name(template_name)
        if overrides is None:
            raise solon.CommandError(f"There is no template with the name {template_name}.")

        for k, v in overrides.items():
            await channel.set_permissions(k, overwrite=v)

        await ctx.send(f"Successfully set {channel} to template {template_name}.")

    @solon.Command(manage_guild=True)
    async def wipe_all_permissions(self, ctx):
        my_highest_role = max(ctx.guild.me.roles)
        for role in ctx.guild.roles:
            if role < my_highest_role:
                await role.edit(permissions=discord.Permissions())
        for channel in ctx.guild.channels:
            for k, v in channel.overwrites:
                await channel.set_permissions(k, overwrite=None)

        await ctx.send("Wiped all channel and role permissions.")

    @solon.Command(manage_guild=True)
    async def list(self, ctx):
        formatted = ""
        for template_name, template in self.data.templates.items():
            formatted += f"{template_name}:\n"
            for role, overrides in template.items():
                formatted += f"  {role}:\n"
                for permission_name, permission_value in overrides.items():
                    formatted += f"    {permission_name}: {permission_value}\n"
            formatted += "\n"

        await ctx.send(f"Available templates on {ctx.guild}:\n```py\n{formatted}```")
