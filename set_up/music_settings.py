import discord
from discord.ext import commands
from tools.string import StringTools
from set_up.settings import BotSettings, SettingTypes
from database.database import Database


# MusicSettings: settings for server's jukebox
class MusicSettings(BotSettings):
    def __init__(self, client: discord.Client):
        super().__init__(client)
        self.type = SettingTypes.Music


    # default_setting(ctx) Creates the default setting for server settings
    @classmethod
    def default_setting(cls, ctx: commands.Context):
        guild = ctx.guild
        Database.insert({"id":f"{guild.id}", "song_list": f"'{StringTools.NONE}'"}, "Server_Music")
