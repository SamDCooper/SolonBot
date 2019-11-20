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

template_settings_type = solon.SerializedDictionary(str, solon.SerializedDictionary(discord.Role,
                                                                                    solon.SerializedDictionary(str,
                                                                                                               bool)))

default_settings = {
    "new_channel_name": {"value_serialized": "new {template} channel", "type_name": "str"},
    "new_channel_category": {"value_serialized": "", "type_name": discord.CategoryChannel.__name__},
    "templates": {"value_serialized": "", "type_name": template_settings_type.__name__}
}


class Data:
    def __init__(self):
        self.templates = {'announcements': {'@everyone': {'send_messages': False},
                                            'moderators': {'send_messages': True}},
                          'general': {},
                          'lobby': {'@everyone': {'read_message_history': True,
                                                  'read_messages': True,
                                                  'send_messages': True},
                                    'access': {'read_messages': False, 'send_messages': False},
                                    'bot': {'send_messages': True},
                                    'moderators': {'send_messages': True},
                                    'muted': {'read_messages': False}},
                          'mods': {'@everyone': {'read_messages': False},
                                   'bot': {'read_messages': True},
                                   'moderators': {'read_messages': True}},
                          'private': {'@everyone': {'read_messages': False},
                                      'bot': {'read_messages': True},
                                      'special access': {'read_messages': True}},
                          'rules': {'@everyone': {'read_message_history': True,
                                                  'read_messages': True,
                                                  'send_messages': False},
                                    'moderators': {'send_messages': True}}}


@solon.Cog(data_type=Data, default_settings=default_settings)
class Template(discord.ext.commands.Cog):
    def __init__(self, guild_id, data, settings):
        self.guild_id = guild_id
        self.settings = settings
        self.data = data

        if not self.settings["templates"]:
            identifier = self.__class__.__name__
            new_templates = template_settings_type()
            for template_name, overwrites in self.data.templates.items():
                overwrites_class = new_templates.value_element_class
                new_templates[template_name] = overwrites_class()
                for role_name, permissions in overwrites.items():
                    permissions_class = overwrites_class.value_element_class
                    role_deser = solon.deserialize(solon.SerializedData(value_serialized=role_name, type_name="role"),
                                                   guild=solon.Bot.get_guild(guild_id))
                    new_templates[template_name][role_deser] = permissions_class()
                    for perm_name, perm_value in permissions.items():
                        new_templates[template_name][role_deser][perm_name] = perm_value
            solon.set_setting_value(identifier, "templates", new_templates)

    def get_permission_overrides_from_template_name(self, template_name):
        overwrites = {role: discord.PermissionOverwrite(**kwargs)
                      for role, kwargs in self.settings["templates"][template_name].items()}
        return overwrites

    @solon.Command(manage_guild=True)
    async def create(self, ctx, template_name: str):
        overrides = self.get_permission_overrides_from_template_name(template_name)
        if overrides is None:
            raise solon.CommandError(f"There is no template with the name {template_name}.")

        channel_name = self.settings["new_channel_name"].format(template=template_name)
        channel = await ctx.guild.create_text_channel(name=channel_name,
                                                      overwrites=overrides,
                                                      category=self.settings["new_channel_category"])
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
        for template_name, template in self.settings["templates"].items():
            formatted += f"{template_name}:\n"
            for role, overrides in template.items():
                formatted += f"  {role}:\n"
                for permission_name, permission_value in overrides.items():
                    formatted += f"    {permission_name}: {permission_value}\n"
            formatted += "\n"

        await ctx.send(f"Available templates on {ctx.guild}:\n```py\n{formatted}```")
