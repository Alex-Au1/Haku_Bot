import discord, enum, json
from discord.ext import commands
from set_up.settings import SettingChangeState, TRACK_INFO, SettingTypes
from set_up.group_settings import GroupSettings
from tools.string import StringTools
from database.database import Database
import set_up.prefix as Prefix
import tools.channels as ChannelTools
import tools.error as Error
from typing import List


# ServerSettings: Controls settings for a server
class ServerSettings(GroupSettings):
    def __init__(self, client: discord.Client):
        super().__init__(client)


    # default_setting(ctx) Creates the default setting for server settings
    @classmethod
    def default_setting(cls, ctx: commands.Context):
        guild = ctx.guild
        Database.insert({"id":f"{guild.id}", "name":f"'{guild.name}'", "prefixes":f"'{Prefix.DEFAULT_PREFIX}'", "track_activity":f"1", "track_message": f"1","activity_channel":f"0",
                         "word_count_channel":f"0", "timezone": f"'UTC'", "region": f"'Greenwich, United Kingdom'"}, "Server_Accounts")


    # track(self, ctx, track_settings) Toggles the settings for tracking a 'track_settings'
    # effects: sends embeds
    #          deletes and edits messages
    async def track(self, ctx: commands.Context, track_settings: str, set_value: str):
        error = False
        error = await ChannelTools.validate_activity_channel(ctx, error)

        if (ctx.message.guild is not None):
            error = False
            track_settings = StringTools.convert_str(track_settings)

            if (track_settings is None or track_settings.upper() not in list(TRACK_INFO.keys())):
                error = True
                embeded_message = Error.display_error(self.client, 10, element = track_settings, group = "TRACK_INFO", parameter = "track_settings")
                await ctx.send(embed = embeded_message)

            track_settings = track_settings.upper()
            error, set_value = await self.validate.validate_bool(ctx, error, set_value, "set_value")

            if (not error):
                server = ctx.message.guild
                server_activity_info = Database.in_table(server.id, "id", "Server_Accounts")

                formatted_track_settings = track_settings.lower()
                question = f"Do you want to me to enable {formatted_track_settings} updates on this server's activity?"
                question_title = f"Enable {formatted_track_settings.capitalize()} Updates?"

                answer = await self.en_question_setting(ctx, question, question_title, set_value)

                answer_desc = f"Successfully enabled {formatted_track_settings} updates"
                answer_title = f"Enabled {formatted_track_settings.capitalize()} Updates"

                # update the values
                if (answer in StringTools.TRUE):
                    if (track_settings == "ALL"):
                        update_values = {}
                        for t in TRACK_INFO:
                            if (t != track_settings):
                                update_values[f"{TRACK_INFO[t].col}"] = f"{int(set_value)}"
                    else:
                        update_values = {f"{TRACK_INFO[track_settings].col}": f"{int(set_value)}"}
                    Database.update(update_values, "Server_Accounts", {"id":f"{server.id}"})
                    await self.en_answer_setting(ctx, answer_desc, answer_title, set_value)


    # format_prefixes(prefixes) Get the formatted prefixes to display on an embed
    def format_prefixes(self, prefixes: List[str]) -> str:
        result = ""
        prefixes_len = len(prefixes)

        for i in range(prefixes_len):
            if (not i):
                result += f"`{prefixes[i]}`"
            elif (i < prefixes_len - 1):
                result += f", `{prefixes[i]}`"
            else:
                result += f" or `{prefixes[i]}`"

        return result


    # set_prefixes(ctx, prefixes) Changes the prefixes for a server
    # effects: sends embeds
    #          deletes and edits messages
    async def set_prefixes(self, ctx: commands.Context, prefixes: str, state: SettingChangeState = SettingChangeState.Add):
        error = False
        error = await ChannelTools.validate_activity_channel(ctx, error)

        prefixes = prefixes.replace(";;", "")
        if (prefixes == "" and state == SettingChangeState.Change):
            prefixes = Prefix.DEFAULT_PREFIX

        prefixes_set = set(StringTools.convert_list(prefixes))
        prefixes = list(prefixes_set)
        input_prefixes = ";".join(prefixes)

        if (ctx.guild is not None and not (state == SettingChangeState.Add and input_prefixes == "") and not error):
            formatted_prefixes = self.format_prefixes(prefixes)

            # ask whether the user want to change the prefix
            if (state == SettingChangeState.Add):
                question_message = "Do you want to add these prefixes to the existing prefixes of the server:\n"
                question_title = "Add Prefixes"
                answer_message = "These prefixes have been added to the existing server prefixes:\n"
                answer_title = "Successfully Added Prefixes"
            elif (state == SettingChangeState.Change):
                question_message = f"Do you want to set the new prefixes for this server to:\n"
                question_title = "Change Prefixes"
                answer_message = "The prefixes to this server have been changed to:\n"
                answer_title = "Successfully Changed Prefixes"

            answer = await self.en_question_setting(ctx, question_message + formatted_prefixes, question_title, True)

            if (answer in StringTools.TRUE):
                if (state == SettingChangeState.Change):
                    Database.update({"prefixes": f"'{input_prefixes}'"}, "Server_Accounts", conditions={"id": f"{ctx.guild.id}"})
                elif (state == SettingChangeState.Add):
                    existing_prefixes = Prefix.get_prefixes(ctx.guild)
                    new_prefixes = existing_prefixes + prefixes
                    new_prefixes_set = set(new_prefixes)
                    new_prefixes_lst = list(new_prefixes_set)
                    new_input_prefixes = ";".join(new_prefixes_lst)
                    Database.update({"prefixes": f"'{new_input_prefixes}'"}, "Server_Accounts", conditions={"id": f"{ctx.guild.id}"})
                await self.en_answer_setting(ctx, answer_message + formatted_prefixes, answer_title, True)


    # remove_prefix(ctx, prefix_index) Removes a specific prefix from the server
    # effects: sends embeds
    #          deletes and edits messages
    async def remove_prefix(self, ctx: commands.Context, prefix_index: str):
        error = False
        error = await ChannelTools.validate_activity_channel(ctx, error)
        error, prefix_index = await self.validate.validate_natural(ctx, error, prefix_index, "prefix_index", check_equal = True)

        existing_prefixes = Database.select(["prefixes"], "Server_Accounts",conditions = {"id": f"{ctx.guild.id}"})[0][0]
        existing_prefixes = StringTools.convert_list(existing_prefixes)
        no_of_prefixes = len(existing_prefixes)

        if (not await self.validate.check_inbetween(ctx, prefix_index, "prefix_name", 1, no_of_prefixes, verbose = (not error))):
            error = True

        if (not error and ctx.guild is not None):
            prefix_index -= 1
            target_prefix = existing_prefixes[prefix_index]
            answer = await self.en_question_setting(ctx, f"Do you want to remove this index from the server?\n`{target_prefix}`", "Remove Index?", True)

            if (answer in StringTools.TRUE):
                existing_prefixes.pop(prefix_index)
                if (not existing_prefixes):
                    existing_prefixes.append(Prefix.DEFAULT_PREFIX)
                input_prefixes = ";".join(existing_prefixes)

                Database.update({"prefixes": f"'{input_prefixes}'"}, "Server_Accounts", conditions={"id": f"{ctx.guild.id}"})
                await self.en_answer_setting(ctx, f"The prefix, `{target_prefix}` ,has been removed from the server", "Successfully Removed Prefix", True)
