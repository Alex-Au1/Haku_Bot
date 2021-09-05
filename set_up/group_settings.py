import discord
from discord.ext import commands
from set_up.settings import BotSettings, SettingTypes
from database.database import Database, SelectType
from tools.string import StringTools
import tools.channels as ChannelTools
import tools.error as Error
import tools.weather as Weather
import pytz
from typing import Dict


# GroupInfo: Stores specific information about a group
class GroupInfo():
    def __init__(self, object: str, table: str, possess: str):
        self.object = object
        self.table = table
        self.possess = possess


GROUP_DICT = {SettingTypes.Server: GroupInfo(" the server", "Server_Accounts", "the server's"),
              SettingTypes.User: GroupInfo("", "User_Accounts", "your")}


# GroupSettings: settings for servers or private dms
class GroupSettings(BotSettings):
    def __init__(self, client: discord.Client):
        super().__init__(client)


    # get_conditions(category, ctx) Get the specific conditions needed to look
    #   for in the database for a certain table
    def get_conditions(self, category: SettingTypes, ctx: commands.Context) -> Dict[str, str]:
        if (category == SettingTypes.Server):
            conditions = {"id": f"{ctx.guild.id}"}
        elif (category == SettingTypes.User):
            conditions = {"id": f"{ctx.author.id}"}

        return conditions


    # change_timezone(self, ctx, timezone) Changes the server's timezone
    # effects: sends embeds
    #          deletes and edits messages
    async def change_timezone(self, ctx: commands.Context, timezone: str, category: SettingTypes):
        error = False

        if (category == SettingTypes.Server):
            error = await ChannelTools.validate_activity_channel(ctx, error)
        timezone = StringTools.convert_str(timezone)

        if (timezone not in pytz.all_timezones):
            error = True
            embeded_message = Error.display_error(self.client, 10, element = timezone, group = "pytz.all_timezones", parameter = "timezones")
            await ctx.send(embed = embeded_message)

        elif (not error and ((category == SettingTypes.User) or (category == SettingTypes.Server and ctx.guild is not None))):
            table = GROUP_DICT[category].table
            conditions = self.get_conditions(category, ctx)
            group_possess = GROUP_DICT[category].possess
            cap_group_possess = group_possess.capitalize()

            question_message = f"Do you want to change {group_possess} timezone to `{timezone}`?"
            question_title = "Change Timezone?"

            sync = Database.default_select(self.default_setting, SelectType.List, ["sync_time", table], {"conditions": conditions}, [ctx], {})[0]

            fields = None
            if (sync):
                fields = {"Warning \U000026A0": f"*After this change,{group_possess} timezone will stop being synchronized with {group_possess} region and {group_possess} timezone will instead follow the timezone that you selected*"}
            answer = await self.en_question_setting(ctx, question_message, question_title, True, fields = fields)

            if (answer in StringTools.TRUE):
                update_data = {"timezone": f"'{timezone}'"}
                if (sync):
                    update_data["sync_time"] = f"{int(not(sync))}"
                    fields = {"Note \U0001F4DD": f"*{cap_group_possess} timezone stopped synchronizing with {group_possess} region*"}


                Database.update(update_data, table, conditions=conditions)
                answer_message = f"{cap_group_possess} timezone has been updated to `{timezone}`"
                answer_title = "Successfully Changed Timezone"
                await self.en_answer_setting(ctx, answer_message, answer_title, True, fields = fields)


    # change_region(self, ctx, region) Changes the server's region
    # effects: sends embeds
    #          deletes and edits messages
    async def change_region(self, ctx: commands.Context, region: str, category: str):
        error = False
        if (category == SettingTypes.Server):
            error = await ChannelTools.validate_activity_channel(ctx, error)
        region = StringTools.convert_str(region)

        weather_info = await Weather.get_weather(region)

        if (weather_info is None):
            embeded_message = Error.display_error(self.client, 17, member = "region", member_search_type = "search query", search_member = region)
            await ctx.send(embed = embeded_message)

        elif (not error and ((category == SettingTypes.User) or (category == SettingTypes.Server and ctx.guild is not None))):
            object = GROUP_DICT[category].object
            table = GROUP_DICT[category].table
            conditions = self.get_conditions(category, ctx)
            group_possess = GROUP_DICT[category].possess
            cap_group_possess = group_possess.capitalize()

            question = f"Is this the region that you want to set{object}?"
            question_title = "Change Region"
            fields = {"Region \U0001F5FA": f"```bash\n'found region': {weather_info.name}\n\n'latitude': {weather_info.latitude}\n'longitude': {weather_info.longitude}\n```"}
            answer = await self.en_question_setting(ctx, question, question_title, True, fields = fields)

            if (answer in StringTools.TRUE):
                sync = Database.default_select(self.default_setting, SelectType.List, ["sync_time", table], {"conditions": conditions}, [ctx], {})[0]

                update_data = {"region": f"'{weather_info.name}'"}
                if (sync):
                    update_data["timezone"] = f"'{weather_info.tz_offset}'"

                Database.update(update_data, table, conditions=conditions)
                answer_message = f"{cap_group_possess} region has been updated to `{weather_info.name}`"
                answer_title = "Successfully Changed Region"
                await self.en_answer_setting(ctx, answer_message, answer_title, True, fields = fields)


    # sync_time(ctx, category) Changes whether a server synchronizes their
    #   timezone with their region
    # effects: sends embeds
    #          deletes and edits messages
    async def sync_time(self, ctx: commands.Context, category: str):
        error = False
        if (category == SettingTypes.Server):
            error = await ChannelTools.validate_activity_channel(ctx, error)

        if (not error and ((category == SettingTypes.User) or (category == SettingTypes.Server and ctx.guild is not None))):
            columns_needed = ["region", "sync_time"]

            table = GROUP_DICT[category].table
            conditions = self.get_conditions(category, ctx)
            group_possess = GROUP_DICT[category].possess
            cap_group_possess = group_possess.capitalize()

            region_data = Database.default_select(self.default_setting, SelectType.Formatted, [columns_needed, columns_needed, table], {"conditions": conditions}, [ctx], {})[0]
            weather_info = await Weather.get_weather(region_data["region"])

            question = f"Do you want to synchronize {group_possess} timezone to {group_possess} selected region"
            question_title = "Synchronize Time with Region"
            sync = not(bool(region_data["sync_time"]))
            fields = {"Server's Region \U0001F5FA": f"```bash\n'Region': {weather_info.name}\n\n'latitude': {weather_info.latitude}\n'longitude': {weather_info.longitude}\n```"}

            answer = await self.question_setting(ctx, question, question_title, sync, {"synchronize": "unsynchronize", "Synchronize": "Unsynchronize"}, fields = fields)

            if (answer in StringTools.TRUE):
                update_data = {columns_needed[1]: f"{int(sync)}"}
                if (sync):
                    timezone = str(weather_info.tz_offset)
                    update_data["timezone"] = str(weather_info.tz_offset)

                Database.update(update_data, table, conditions=conditions)
                answer_message = f"{cap_group_possess} timezone has been synchronized with {group_possess} region"
                answer_title = "Successfully Synchronized Time with Region"
                await self.answer_setting(ctx, answer_message, answer_title, sync, {"synchronized": "unsynchronized", "Synchronized": "Unsynchronized"}, fields = fields)


    # update_time() Updates the time for timezones with only a time difference
    #   to account for daylight savings
    async def update_time(self):
        found_weather = {}

        table = "Server_Accounts"
        columns_needed = ["id", "timezone", "region"]
        time_data = Database.formatted_select(columns_needed, columns_needed, table, conditions = {"sync_time": "1"})

        for d in time_data:
            try:
                tz_float = float(d["timezone"])
            except:
                pass
            else:
                region = d["region"]
                if (region not in list(found_weather.keys())):
                    found_weather[region] = await Weather.get_weather(region)

                latest_weather = found_weather[region]
                if (latest_weather.tz_offset != tz_float):
                    Database.update({"timezone": f"'{latest_weather.tz_offset}'"}, table, conditions = {"id": f"{d['id']}"})
