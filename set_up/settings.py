import discord, enum, json, codecs
from discord.ext import commands
from database.database import Database, DbItem
from tools.embed import Embed
from tools.string import StringTools
import tools.channels as ChannelTools
import tools.members as Members
from tools.validate import Validate, DataTypes
from text.bot_texting import Texting
import tools.error as Error
import pics.image_links as Pics
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType
from tools.pagination import Pagination, ButtonedMsg
import tools.datetime as DateTools
from tools.abs_func import AbsFunc
from typing import Union, Dict, List, Any, Optional


# SettingChangeState: State of changing a setting with multiple items
class SettingChangeState(enum.Enum):
    Add = "add"
    Remove = "remove"
    Change = "Change"


# SettingTypes: class for each tree in the settings
class SettingTypes(enum.Enum):
    Server = "server"
    User = "user"
    Music = "music"


# SettingItem: Leafs for the tree in the settings
class SettingItem(DbItem):
    def __init__(self, name, index, table, col, type, description):
        super().__init__(name, index, table, col)
        self.type = type
        self.description = description

    # get_value(settings) Gets the value of a setting
    def get_value(self, settings):
        return settings[self.col]


# SettingCategory: A node in a setting tree that is not a leaf
class SettingCategory():
    def __init__(self, name: str, children):
        self.name = name
        self.children = children


# SettingTree: A tree for a type of settings
class SettingTree():
    def __init__(self, name: str, children: Union[SettingCategory, SettingItem]):
        self.name = name
        self.children = children


SETTING_LST = [SettingItem("prefixes", 2, "Server_Accounts", "prefixes", DataTypes.List, f"The beginning string of a message to indicate an invocation of a command to {Members.BOT_NICKNAMES[1]}"),
               SettingItem("MESSAGE", 4, "Server_Accounts", "track_message", DataTypes.Bool, "Sends an update whenever a message is deleted or editted"),
               SettingItem("ACTIVITY", 3, "Server_Accounts", "track_activity", DataTypes.Bool, "Sends an update ```css\n#1 whenever someone changes their online status\n#2 changes their server nickname\n#3 updates their roles\n#4 changes their current activity\n#5 updates their account (profile pic or name)\n#6 joins/leaves the server```"),
               SettingItem("VOICE", 6, "Server_Accounts", "track_voice", DataTypes.Bool, "Sends an update whenever someone joins/leaves a voice channel"),
               SettingItem("TYPING", 7, "Server_Accounts", "track_typing", DataTypes.Bool, "Sends an update whenever someone is typing"),
               SettingItem("GUILD", 5, "Server_Accounts", "track_guild_update", DataTypes.Bool, "Sends an update whenever someone updates the server or updates the channels in the server"),
               SettingItem("Timezone", 10, "Server_Accounts", "timezone", DataTypes.Str, "Sets all datetime information of the server to the specific timezone. The entries for the timezone are the timezones used in the *pytz* module. You can view the selection for the timezones [here](https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568)"),
               SettingItem("Region", 12, "Server_Accounts", "region", DataTypes.Str, "Sets the region for where the server is located"),
               SettingItem("Sync Time", 13, "Server_Accounts", "sync_time", DataTypes.Bool, "Indicates whether the timezone of the server is synchronized with the selected region of the server"),
               SettingItem("Timezone", 2, "User_Accounts", "timezone", DataTypes.Str, "Sets all datetime information for the user to the specific timezone. The entries for the timezone are the timezones used in the *pytz* module. You can view the selection for the timezones [here](https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568)"),
               SettingItem("Region", 3, "User_Accounts", "region", DataTypes.Str, "Sets the region for where the user is located"),
               SettingItem("Sync Time", 4, "User_Accounts", "sync_time", DataTypes.Bool, "Indicates whether the timezone of the user is synchronized with the selected region of the user"),
               SettingItem("Volume", 2, "Server_Music", "vol", DataTypes.Int, "The volume of the audio being played"),
               SettingItem("Pitch", 3, "Server_Music", "pitch", DataTypes.Str, "The pitch that the audio is being played"),
               SettingItem("Loop", 4, "Server_Music", "loop", DataTypes.Bool, "Indicates whether the server's playlist is being looped"),
               SettingItem("Repeat", 5, "Server_Music", "repeat", DataTypes.Str, "Indicates which song on the server's playlist will be played on repeat"),
               SettingItem("Random", 6, "Server_Music", "random", DataTypes.Bool, "Indicates whether the next songs will be randomly selected not according to the order of the playlist")]


TRACK_INFO = {"MESSAGE": SETTING_LST[1],
              "ACTIVITY": SETTING_LST[2],
              "VOICE": SETTING_LST[3],
              "TYPING": SETTING_LST[4],
              "GUILD": SETTING_LST[5],
              "ALL": None}


FULL_SETTINGS = {SettingTypes.Server: SettingTree(SettingTypes.Server.value, [SETTING_LST[0], SettingCategory("Time and Place \U0001F30E \U000023F1", [SETTING_LST[6], SETTING_LST[7], SETTING_LST[8]]),
                                                                              SettingCategory("Activity Moderation \U0001F50D", [TRACK_INFO["MESSAGE"], TRACK_INFO["ACTIVITY"], TRACK_INFO["VOICE"], TRACK_INFO["TYPING"], TRACK_INFO["GUILD"]])]),
                 SettingTypes.User: SettingTree(SettingTypes.User.value, [SettingCategory("Time and Place \U0001F30E \U000023F1", [SETTING_LST[9], SETTING_LST[10], SETTING_LST[11]])]),
                 SettingTypes.Music: SettingTree(SettingTypes.Music.value, [SettingCategory("Sound \U0001F50A", [SETTING_LST[12], SETTING_LST[13]]), SettingCategory("Playlist \U0001F3B6 \U0001F3A7", [SETTING_LST[14], SETTING_LST[15], SETTING_LST[16]])])}


# BotSettings: Controls all the settings for the bot
class BotSettings(commands.Cog):

    #constructor
    def __init__(self, client: discord.Client):
        self.client = client
        self.embed = Embed(client)
        self.text = Texting(client)
        self.validate = Validate(client)
        self.settings_per_page = 5
        self.setting_name_limit = 18


    # question_setting(ctx, question, question_title, set_value, values_to_check) Asks the user to
    #   whether they want to do something or not
    # effects: sends embeds
    #          deletes and edits messages
    async def question_setting(self, ctx: commands.Context, question: str, question_title: str,
                               set_value: bool, replace_values: Dict[str, str], fields: Optional[Dict[str, str]] = None) -> str:
        default_pic = {Pics.ImageCategory.Default: 0}
        values_to_check = StringTools.TRUE + StringTools.FALSE

        if (not set_value):
            question = StringTools.word_replace(question, replace_values)
            question_title = StringTools.word_replace(question_title, replace_values)

        question_embed = self.embed.bot_embed(ctx, question, question_title, "yellow", 2, default_pic)
        if (fields is not None):
            question_embed = self.embed.multi_add_section(question_embed, fields)

        question_embed = self.embed.add_section(question_embed, "Yes (y)", "\U0001F44D", True)
        question_embed = self.embed.add_section(question_embed, "No (n)", "\U0001F44E", True)
        return await self.text.continual_ask(ctx, question_embed, values_to_check)


    # answer_setting(ctx, answer_desc, answer_title, set_value, values_to_check) Displays the message
    #   to confirm whether an option has been toggled on or not
    # effects: sends embeds
    async def answer_setting(self, ctx: commands.Context, answer_desc: str, answer_title: str,
                             set_value: str, replace_values: str, fields: Optional[Dict[str, str]] = None):
        default_pic = {Pics.ImageCategory.Default: 0}

        if (not set_value):
            answer_desc = StringTools.word_replace(answer_desc, replace_values)
            answer_title = StringTools.word_replace(answer_title, replace_values)

        answer_embed = self.embed.bot_embed(ctx, answer_desc, answer_title, "light-green", 2, default_pic)
        if (fields is not None):
            answer_embed = self.embed.multi_add_section(answer_embed, fields)

        await ctx.send(embed = answer_embed.embed, file = answer_embed.file)


    # question_setting(ctx, question, question_title, set_value, values_to_check) Asks the user to
    #   enable or disable a setting option
    # effects: sends embeds
    #          deletes and edits messages
    async def en_question_setting(self, ctx: commands.Context, question: str, question_title: str, set_value: bool, fields: Optional[Dict[str, str]] = None) -> str:
        return await self.question_setting(ctx, question, question_title, set_value, {"enable": "disable", "Enable": "Disable"}, fields = fields)


    # answer_setting(ctx, answer_desc, answer_title, set_value, values_to_check) Displays the message
    #   to confirm that the setting option has been enabled or disabled
    # effects: sends embeds
    async def en_answer_setting(self, ctx: commands.Context, answer_desc: str, answer_title: str, set_value: bool, fields: Optional[Dict[str, str]] = None):
        await self.answer_setting(ctx, answer_desc, answer_title, set_value, {"enabled": "disabled", "Enabled": "Disabled"}, fields = fields)


    # default_setting(ctx) Creates the default setting for the setting
    @classmethod
    def default_setting(cls, ctx: commands.Context):
        pass


    # get_setting_categories(node, depth) Gets the number of pages in each setting category
    #   and the total number of items in the certain setting
    def get_setting_categories(self, node: Union[SettingTree, SettingCategory, SettingItem], depth: int) -> Union[int, List[int]]:
        if (node is None or isinstance(node, SettingItem)):
            return 1
        else:
            if (not depth):
                categories = []
            total_items = 0
            children_len = len(node.children)

            # get the other pages from the children
            for i in range(children_len):
                current_pages = self.get_setting_categories(node.children[i], depth + 1)
                total_items += current_pages

                if (not depth):
                    categories.append(current_pages)

            # return the result
            if (not depth):
                return [total_items, categories]
            else:
                return total_items


    # get_setting_page(total_items, categories) Gets the categories to display per
    #   page for the setting
    def get_setting_pages(self, total_items: int, categories: List[int]) -> List[List[int]]:
        no_of_categories = len(categories)
        pages = []

        start_index = 0
        end_index = 0
        current_page_items = 0
        for i in range(no_of_categories):
            current_page_items += categories[i]

            if (current_page_items >= self.settings_per_page):
                end_index = i + 1
                pages.append([start_index, end_index])
                start_index = end_index
                current_page_items = 0

        if (current_page_items):
            end_index = no_of_categories
            pages.append([start_index, end_index])

        return pages


    # format_setting_value(type, value) Format the value for the settings to be displayed
    def format_setting_value(self, type: DataTypes, value: Any) -> str:
        if (type == DataTypes.Bool):
            if (value):
                return "`enabled \U00002714`"
            else:
                return "`disabled \U0000274C`"

        elif (type == DataTypes.List):
            val_lst = StringTools.convert_list(value, allow_optional = True)
            result = ""

            if (val_lst is None):
                return "`not set`"
            val_lst_len = len(val_lst)
            for i in range(val_lst_len):
                if (not i):
                    result += f"`{val_lst[i]}`"
                else:
                    result += f",`{val_lst[i]}`"
            return result

        elif (type == DataTypes.Dict):
            val_dict = StringTools.convert_dict(value, allow_optional = True)
            result = ""

            if (val_dict is None):
                return "`not set`"

            index = 1
            for v in val_dict:
                result += f"{index}) `{v}`:  `{val_dict[v]}`\n"
                index += 1

            return result
        else:
            return f"`{value}`"


    # format_setting_fields(node, page, page_categories, setting_data, fields) Retrieves all the
    #   fields to display in the settings
    def format_setting_fields(self, node: Union[SettingTree, SettingCategory, SettingItem], page: int,
                              page_categories: List[List[int]], setting_data: List[Dict[str, Any]], fields: Dict[str, str]) -> Dict[str, str]:
        if (isinstance(node, SettingItem)):
            title = f"***{StringTools.str_capitalize(node.name.lower())}***"
            value = self.format_setting_value(node.type, setting_data[node.col])
            fields[title] = f"{value}\n\n{node.description}"
            return fields

        elif (isinstance(node, SettingTree)):
            for i in range(page_categories[page - 1][0], page_categories[page - 1][1]):
                fields = self.format_setting_fields(node.children[i], page, page_categories, setting_data, fields)

            return fields

        else:
            title = f"__{node.name.upper()}__"
            value = ""
            for i in node.children:
                current_fields = self.format_setting_fields(i, page, page_categories, setting_data, {})

                for f in current_fields:
                    value += f"\n{f}\n{current_fields[f]}\n"

            fields[title] = value
            return fields


    # generate_setting_pg(page, max_page, kwargs) Generates the page for the settings
    # requires: page >= 1
    #           max_page >= 1
    async def generate_setting_pg(self, page: int, max_page: int, kwargs: Dict[str, Any]):
        message = kwargs["message"]
        title = kwargs["title"]
        thumbnail = kwargs["thumbnail"]
        colour = kwargs["colour"]
        setting_tree = kwargs["setting_tree"]
        setting_data = kwargs["setting_data"]
        page_categories = kwargs["page_categories"]
        ctx = kwargs["ctx"]

        embeded_message = self.embed.context_embed(ctx, message, title, colour, thumbnail = thumbnail)
        fields = self.format_setting_fields(setting_tree, page, page_categories, setting_data, {})
        embeded_message = self.embed.multi_add_section(embeded_message, fields)

        footer_msg = f"\U0001F4C3 pg:  {page} / {max_page}"
        embeded_message = self.embed.add_footer(ctx, embeded_message, footer_msg)

        return embeded_message


    # get_columns_needed(node, columns_needed) Gets all the columns needed to
    #   find in the database
    def get_columns_needed(self, node: Union[SettingTree, SettingCategory, SettingItem], columns_needed: List[str]) -> List[str]:
        if (isinstance(node, SettingItem)):
            columns_needed.append(node.col)
            return columns_needed
        elif (isinstance(node, SettingCategory) or isinstance(node, SettingTree)):
            for c in node.children:
                columns_needed = self.get_columns_needed(c, columns_needed)
            return columns_needed


    # view(ctx, category) Views the settings for a specific setting type
    # effects: sends embeds
    async def view(self, ctx: commands.Context, category: SettingTypes, **kwargs):
        if (category != SettingTypes.Server or (category == SettingTypes.Server and ctx.guild is not None)):
            message = f"Here are the {category.value} settings"
            title = f"{StringTools.str_capitalize(category.value)} Settings"

            if (category == SettingTypes.Server):
                table = "Server_Accounts"
                conditions = {"id": f"{ctx.guild.id}"}
                message += f" for the server, `{ctx.guild.name}`"
                thumbnail = str(ctx.guild.icon_url)
                colour = "light-purple"
                setting_tree = FULL_SETTINGS[SettingTypes.Server]

            elif (category == SettingTypes.User):
                table = "User_Accounts"
                conditions = {"id": f"{ctx.author.id}"}
                message = "Here are your settings"
                thumbnail = str(ctx.author.avatar_url)
                colour = "light-purple"
                setting_tree = FULL_SETTINGS[SettingTypes.User]

            elif (category == SettingTypes.Music):
                table = "Server_Music"
                conditions = {"id": f"{ctx.guild.id}"}
                message = "Here are my performance settings"
                thumbnail = str(ctx.guild.icon_url)
                colour = "light-purple"
                setting_tree = FULL_SETTINGS[SettingTypes.Music]


            columns_needed = self.get_columns_needed(setting_tree, [])
            if (category != SettingTypes.Music):
                setting_data = Database.formatted_select(columns_needed, columns_needed, table, conditions = conditions)

                if (setting_data):
                    setting_data = setting_data[0]
                else:
                    self.default_setting(ctx)
                    setting_data = Database.formatted_select(columns_needed, columns_needed, table, conditions = conditions)[0]

            if (category == SettingTypes.Server or category == SettingTypes.User):
                if (category == SettingTypes.Server):
                    tz_index = 6
                    region_index = 7
                    sync_index = 8
                elif (category == SettingTypes.User):
                    tz_index = 9
                    region_index = 10
                    sync_index = 11

                setting_data[SETTING_LST[tz_index].col] = DateTools.format_timezone(setting_data[SETTING_LST[tz_index].col], setting_data[SETTING_LST[region_index].col], setting_data[SETTING_LST[sync_index].col])

            elif (category == SettingTypes.Music):
                setting_data = {"vol": kwargs["vol"], "pitch": kwargs["pitch"], "loop": kwargs["loop"], "repeat": kwargs["repeat"], "random": kwargs["random"]}

            total_items, categories = self.get_setting_categories(setting_tree, 0)
            page_categories = self.get_setting_pages(total_items, categories)

            page = 1
            max_page = len(page_categories)

            generate_setting_pg_kwargs = {"message": message, "title": title, "thumbnail": thumbnail, "colour": colour, "page_categories": page_categories, "setting_tree": setting_tree, "setting_data": setting_data, "ctx": ctx}
            embeded_message = await self.generate_setting_pg(page, max_page, generate_setting_pg_kwargs)
            paginated_components = Pagination.make_page_buttons(page, max_page)

            generate_page = AbsFunc(self.generate_setting_pg, kwargs = generate_setting_pg_kwargs)
            await Pagination.paginated_send(ctx, self.client, embeded_message, paginated_components, page, max_page, generate_page)
