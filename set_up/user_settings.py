import discord, enum
from discord.ext import commands
from set_up.settings import SettingChangeState, TRACK_INFO, SettingTypes
from set_up.group_settings import GroupSettings
from database.database import Database
from tools.embed import Embed
from tools.string import StringTools


# UserSettings: Controls the settings for a user
class UserSettings(GroupSettings):
    def __init__(self, client: discord.Client):
        super().__init__(client)


    # default_setting(ctx) Creates the default setting for user settings
    @classmethod
    def default_setting(cls, ctx: commands.Context):
        Database.insert({"id": f"{ctx.author.id}", "name": f"'{ctx.author.name}'", "timezone": "'UTC'", "region": "'Greenwich, United Kingdom'", "sync_time": "0", "subd_yt_channels": f"'{StringTools.NONE}'"}, "User_Accounts")
