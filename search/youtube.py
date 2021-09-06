import discord, urllib, json, aiohttp, enum
from discord.ext import commands, tasks
from tools.string import StringTools
from bs4 import BeautifulSoup
import tools.error as Error
import tools.search_yt as YtSearchTools
import tools.channels as ChannelTools
from youtubesearchpython import *
import tools.datetime as DateTime
from tools.embed import Embed, EmbededMessage
from database.database import Database, SelectType
from tools.discord_search import SearchTools
import pics.image_links as Pics
from text.bot_texting import Texting
from tools.validate import Validate
from tools.pagination import Pagination, ButtonedMsg
from set_up.server_settings import ServerSettings
from set_up.user_settings import UserSettings
from typing import Optional, Union, Dict, Any

YOUTUBE_BASE_VIDEO_URL = 'https://www.youtube.com/watch?v='
YOUTUBE_BASE_CHANNEL_URL = "https://www.youtube.com/channel/"
CHANNEL_VIDEOS = "/videos"
YOUTUBE_BASE_CHANNEL_VIDEOS_URL = YOUTUBE_BASE_CHANNEL_URL + "{id}" + CHANNEL_VIDEOS

KEY_WORDS = {"id": ["\"gridVideoRenderer\":{\"videoId\":\"", "\""],
             "publish_date": ["\"publishedTimeText\":{\"simpleText\":\"", "\"}"],
             "premiere": ["upcomingEventData", ":{"]}


# YtAccount: Class for the context user the bot is dealing with
class YtAccount(enum.Enum):
    Server = "server"
    User = "user"

CHANNEL_LOCATION_INDICES = {YtAccount.Server: "subd_yt_channels", YtAccount.User: "subd_yt_channels"}
CHANNEL_NOTIFY_INDICES = {YtAccount.Server: "notify_yt", YtAccount.User: "notify_yt"}


# YtChannelInfo: Information on the latest video of a channel
class YtChannelInfo():
    def __init__(self, id: str, name: str, latest_video_date: str, publish_date: str, premiere: int):
        self.id = id
        self.name = name
        self.latest_video_id = latest_video_date
        self.publish_date = publish_date
        self.premiere = premiere


LATEST_VIDEOS = {}


class YoutubeUtils(commands.Cog):
    def __init__(self, client: discord.Client):
        self.client = client
        self.search_tools = SearchTools(client)
        self.embed = Embed(client)
        self.text = Texting(client)
        self.CHANNELS_PER_PAGE = 10
        self.validate  = Validate(client)


    # get_channel_videos_url(channel_name) Get the url to the list of videos of the channel
    def get_channel_videos_url(self, channel_id: str) -> str:
        result = YOUTUBE_BASE_CHANNEL_VIDEOS_URL.replace("{id}", str(channel_id))
        return result


    # get_latest_att(script) Get the id or publishing date of the latest youtube video from a channel
    def get_latest_att(self, start: str, script: str, key: str) -> str:
        start += len(KEY_WORDS[key][0])
        target_str = script[start:]
        end = target_str.find(KEY_WORDS[key][1])
        id = target_str[:end]
        return id


    # get_latest_video_info(channel_link) Gets the id of the latest youtube video
    #   from a certain channel
    async def get_latest_video_info(self, channel_link: str) -> Optional[Dict[str, Union[str, int]]]:
        async with aiohttp.ClientSession() as session:
            async with session.get(channel_link) as r:
                if r.status == 200:
                    html_text = await r.text()
                    soup = BeautifulSoup(html_text, 'html.parser')
                    script_lst = soup.find_all('script')

                    script = None
                    premiere = -1
                    for e in script_lst:
                        script_str = str(e)
                        start_id = script_str.find(KEY_WORDS["id"][0])

                        if (start_id != -1):
                            start_date = script_str.find(KEY_WORDS["publish_date"][0])
                            premiere = script_str.find(KEY_WORDS["premiere"][0])
                            script = script_str
                            break

                    if (script is not None):
                        id = self.get_latest_att(start_id, script, "id")
                        publish_date = self.get_latest_att(start_date, script, "publish_date")

                        if (premiere == -1):
                            premiered_video = False
                        else:
                            premiered_video = True
                        return {"id": id, "publish_date": publish_date, "premiere": int(premiered_video)}

                    elif (channel_link.endswith(CHANNEL_VIDEOS)):
                        print("FAILED TO FIND SEARCH")

                        # find the video in the channel's homepage
                        new_link = channel_link.replace(CHANNEL_VIDEOS, "")
                        result = await self.get_latest_video_info(new_link)

                        if (result is None):
                            return None
                        else:
                            return result

                    return None


    # get_channel_info(channel) Get the info on the latest video of a channel to
    #   be updated to the database
    async def get_channel_info(self, channel: str) -> Optional[YtChannelInfo]:
        channel_id = None
        channel_name = None

        if (YtSearchTools.valid_yt_channel_link(channel)):
            channel = StringTools.get_link(channel)
            channel_id = channel.replace(YOUTUBE_BASE_CHANNEL_URL, "")

            video_pg_url = self.get_channel_videos_url(channel_id)
            search_result = await self.get_latest_video_info(video_pg_url)
            video_id = search_result["id"]
            premiere = search_result["premiere"]

            channel_search = ChannelSearch("", channel_id)
            channel_name = channel_search[0]["channel0"]["title"]

            publish_time = DateTime.get_yt_format_date(search_result["publish_date"])

        else:
            channel_search = ChannelsSearch(channel, limit = 1)
            if (channel_search is not None):
                channel_search_result = channel_search.result()["result"][0]
                channel_id = channel_search_result["id"]
                channel_name = channel_search_result["title"]

                video_pg_url = self.get_channel_videos_url(channel_id)
                search_result = await self.get_latest_video_info(video_pg_url)
                video_id = search_result["id"]
                publish_time = DateTime.get_yt_format_date(search_result["publish_date"])
                premiere = search_result["premiere"]

        if (channel_id is not None):
            return YtChannelInfo(channel_id, channel_name, video_id, publish_time, premiere)
        else:
            return None


    # latest_video(ctx, channel_link) Get the most recent video from a certain youtube channel
    # effects: sends a message
    async def latest_video(self, ctx: commands.Context, channel: str):
        error = False
        # validate the function
        error = await ChannelTools.validate_activity_channel(ctx, error)

        if (not error):
            channel_link = None
            channel_info = await self.get_channel_info(channel)
            if (channel_info is not None):
                id = channel_info.latest_video_id
                video_url = YOUTUBE_BASE_VIDEO_URL + id

                await ctx.send(f"> \n> Here is the latest video from the channel `{channel_info.name}`:\n> \n> {video_url}")

            else:
                embeded_message = Error.display_error(self.client, 17, member = "channel", member_search_type = "name", search_member = channel)
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # add_latest_video(channel_id, channel_name, video_id, publish_time)
    #   Adds the information about a channel and its latest video into the database
    async def add_latest_video(self, channel_id: str, channel_name: str, video_id: str, publish_time: str, premiere: int):
        latest_video_date = await DateTime.format_date(publish_time, format = DateTime.DATABASE_FORMAT, convert = False)
        Database.insert({"id": f"'{channel_id}'", "name": f"'{channel_name}'", "latest_video_id": f"'{video_id}'", "latest_video_date": f"'{latest_video_date}'", "premiere": f"{premiere}"}, "Youtube_Channels")
        LATEST_VIDEOS[channel_id] = YtChannelInfo(channel_id, channel_name, video_id, latest_video_date, premiere)


    # update_latest_video(channel_id, video_id, publish_time)
    #   Updates the information about the latest video of a channel into the
    #   database
    async def update_latest_video(self, channel_id: str, video_id: str, publish_time: str, premiere: int):
        latest_video_date = await DateTime.format_date(publish_time, format = DateTime.DATABASE_FORMAT, convert = False)
        Database.update({"latest_video_id": f"'{video_id}'", "latest_video_date": f"'{latest_video_date}'", "premiere": f"{premiere}"}, "Youtube_Channels", conditions={"id": f"'{channel_id}'"})
        old_data = LATEST_VIDEOS[channel_id]
        LATEST_VIDEOS[channel_id] = YtChannelInfo(channel_id, old_data.name, video_id, latest_video_date, premiere)


    # prepare_latest_videos()
    #   Retrieves the stored information of the latest video on each channel
    #   from the database when the bot loads
    async def prepare_latest_videos(self):
        columns_needed = ["id", "name", "latest_video_id", "latest_video_date", "premiere"]
        channel_videos = Database.formatted_select(columns_needed, columns_needed, "Youtube_Channels")

        for c in channel_videos:
            LATEST_VIDEOS[c["id"]] = YtChannelInfo(c["id"], c["name"], c["latest_video_id"], c["latest_video_date"], c["premiere"])


    # question(ctx, question, question_title, set_value, values_to_check) Asks the user to
    #   enable or disable a certain tracking attribute
    async def question(self, ctx: commands.Context, question: str, question_title: str, set_value: bool, replacements = {"enable": "disable", "Enable": "Disable"}) -> str:
        default_pic = {Pics.ImageCategory.Default: 0}
        values_to_check = StringTools.TRUE + StringTools.FALSE

        if (not set_value):
            question = StringTools.word_replace(question, replacements)
            question_title = StringTools.word_replace(question_title, replacements)

        question_embed = self.embed.bot_embed(ctx, question, question_title, "yellow", 2, default_pic)
        question_embed = self.embed.add_section(question_embed, "Yes (y)", "\U0001F44D", True)
        question_embed = self.embed.add_section(question_embed, "No (n)", "\U0001F44E", True)
        return await self.text.continual_ask(ctx, question_embed, values_to_check)


    # answer(ctx, answer_desc, answer_title, set_value, values_to_check) Displays the message
    #   to confirm that the setting value to a tracking attribute has been changed
    async def answer(self, ctx: commands.Context, answer_desc: str, answer_title: str, set_value: bool, replacements = {"enable": "disable", "Enable": "Disable"}):
        default_pic = {Pics.ImageCategory.Default: 0}

        if (not set_value):
            answer_desc = StringTools.word_replace(answer_desc, replacements)
            answer_title = StringTools.word_replace(answer_title, replacements)
        answer_embed = self.embed.bot_embed(ctx, answer_desc, answer_title, "light-green", 2, default_pic)
        await ctx.send(embed = answer_embed.embed, file = answer_embed.file)


    # add_yt_channel(ctx, channel, sending_channel) Enable video notifications of a youtube channel to the server
    # effects: sends embeds
    #          deletes and edits messages
    async def add_yt_channel(self, ctx: commands.Context, yt_channel: str, sending_channel: str, account_type: YtAccount):
        error = False
        error = await ChannelTools.validate_activity_channel(ctx, error)

        if (account_type == YtAccount.Server):
            error, server, sending_channel = await self.search_tools.validate_sev_ch(ctx, error, sending_channel, str(ctx.guild.id), action = "sending message", allow_dm = False)
        elif (account_type == YtAccount.User):
            sending_channel = self.client.get_channel(int(sending_channel))

        if (ctx.guild is not None and not error):
            channel_info = await self.get_channel_info(yt_channel)

            if (channel_info is not None):
                # determine if the server is already checking on the channel
                subscribed = False

                if (account_type == YtAccount.Server):
                    table = "Server_Accounts"
                    conditions = {"id": f"{ctx.guild.id}"}
                    default_func = ServerSettings.default_setting
                elif (account_type == YtAccount.User):
                    table = "User_Accounts"
                    conditions = {"id": f"{ctx.author.id}"}
                    default_func = UserSettings.default_setting

                subd_yt_channels = Database.default_select(default_func, SelectType.List, [CHANNEL_LOCATION_INDICES[account_type], table], {"conditions": conditions}, [ctx], {})[0]
                subd_yt_channels = StringTools.convert_dict(subd_yt_channels)

                if (subd_yt_channels is not None and channel_info.id in subd_yt_channels):
                    subscribed = True

                elif (subd_yt_channels is None):
                    subd_yt_channels = {}

                # ask the user if they want to enable or disable getting notifications
                if (not subscribed):
                    question_message = f"Do you want to receive notifications on the latest video for the youtube channel, `{channel_info.name}`"

                    if (account_type == YtAccount.Server):
                        question_message += f"in the text channel, `{sending_channel.name}`"
                    question_message += "?"
                    question_title = "Get Latest Videos?"

                    answer = await self.question(ctx, question_message, question_title, True)

                    if (answer in StringTools.TRUE):
                        columns_needed = ["id", "name", "latest_video_id", "latest_video_date"]
                        channel_videos = Database.formatted_select(columns_needed, columns_needed, "Youtube_Channels")

                        channel_dict = {}
                        for c in channel_videos:
                            channel_dict[c["id"]] = c

                        # update the youtube channels being checked
                        if (channel_info.id not in list(channel_dict.keys())):
                            await self.add_latest_video(channel_info.id, channel_info.name, channel_info.latest_video_id, channel_info.publish_date, channel_info.premiere)

                        subd_yt_channels[channel_info.id] = sending_channel.id
                        db_channels = json.dumps(subd_yt_channels)[1:-1]
                        db_channels = db_channels.replace("\"", "")

                        answer_message = f"Notifications to latest videos of `{channel_info.name}` enabled"
                        if (account_type == YtAccount.Server):
                            answer_message += f"to the text channel, `{sending_channel.name}`"

                        answer_title = "Receive Notifications on channel"
                        Database.update({CHANNEL_LOCATION_INDICES[YtAccount.Server]: f"'{db_channels}'"}, table, conditions = conditions)
                        await self.answer(ctx, answer_message, answer_title, True)

                else:
                    found_message = ""

                    if (account_type == YtAccount.Server):
                        found_message += "The Server has"
                    elif (account_type == YtAccount.User):
                        found_message += "You have"
                    found_message += f"already selected to receive notifications from the youtube channel, `{channel_info.name}`"

                    embeded_message = self.embed.bot_embed(ctx, found_message, "Already Receiving Notifications", "yellow", -1, image = {Pics.ImageCategory.Default: 0})
                    await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

            else:
                embeded_message = Error.display_error(self.client, 17, member = "channel", member_search_type = "name or link", search_member = channel)
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # change_yt_channel(ctx, channel_index, sending_channel) Changes the location where the notifications for each video is sent
    # effects: sends embeds
    #          deletes and edits messages
    async def change_yt_channel(self, ctx: commands.Context, channel_index: str, sending_channel: str, account_type: YtAccount):
        error = False
        error = await ChannelTools.validate_activity_channel(ctx, error)
        error, server, sending_channel = await self.search_tools.validate_sev_ch(ctx, error, sending_channel, str(ctx.guild.id), action = "sending message", allow_dm = False, allow_default = False)
        error, channel_index = await self.validate.validate_natural(ctx, error, channel_index, "channel_index")

        if (ctx.guild is not None and not error):
            # determine if the server is already checking on the channel
            subscribed = False
            subd_yt_channels = Database.list_select(CHANNEL_LOCATION_INDICES[YtAccount.Server], "Server_Accounts", conditions = {"id": f"{ctx.guild.id}"})[0]
            subd_yt_channels = StringTools.convert_dict(subd_yt_channels)
            subd_yt_channels_ids = list(subd_yt_channels.keys())

            if (not await self.validate.check_inbetween(ctx, channel_index, "channel_index", 1, len(subd_yt_channels), verbose = (not error))):
                error = True

            if (not error):
                target_channel_id = subd_yt_channels_ids[channel_index - 1]
                target_channel_name = Database.list_select("name", "Youtube_Channels", conditions = {"id": f"'{target_channel_id}'"})[0]
                question_message = f"Do you want to change the location of receiving notifications on the latest videos for the youtube channel, `{target_channel_name}` to the text channel, `#{sending_channel.name}`"
                question_title = f"Change Location of Notifications?"

                answer = await self.question(ctx, question_message, question_title, True)

                if (answer in StringTools.TRUE):
                    subd_yt_channels[target_channel_id] = sending_channel.id
                    db_channels = json.dumps(subd_yt_channels)[1:-1]
                    db_channels = db_channels.replace("\"", "")
                    Database.update({CHANNEL_LOCATION_INDICES[YtAccount.Server]: f"'{db_channels}'"}, "Server_Accounts", conditions = {"id": f"{ctx.guild.id}"})

                    answer_message = f"Notifications to latest videos of `{target_channel_name}` has been redirected to the text channel `#{sending_channel.name}`"
                    answer_title = "Redirected Notifications on Videos"
                    await self.answer(ctx, answer_message, answer_title, True)


    # remove_yt_channel(ctx, channel) Disable video notifications of a youtube channel to the server
    # effects: sends embeds
    #          deletes and edits messages
    async def remove_yt_channel(self, ctx: commands.Context, channel_index: str, account_type: YtAccount):
        error = False
        error = await ChannelTools.validate_activity_channel(ctx, error)
        error, channel_index = await self.validate.validate_natural(ctx, error, channel_index, "channel_index")

        if (ctx.guild is not None and not error):
            # determine if the server is already checking on the channel
            subscribed = False
            if (account_type == YtAccount.Server):
                table = "Server_Accounts"
                conditions = {"id": f"{ctx.guild.id}"}
                default_func = ServerSettings.default_setting
            elif (account_type == YtAccount.User):
                table = "User_Accounts"
                conditions = {"id": f"{ctx.author.id}"}
                default_func = UserSettings.default_setting

            subd_yt_channels = Database.default_select(default_func, SelectType.List, [CHANNEL_LOCATION_INDICES[YtAccount.Server], table], {"conditions": conditions}, [ctx], {})[0]
            subd_yt_channels = StringTools.convert_dict(subd_yt_channels)
            subd_yt_channels_ids = list(subd_yt_channels.keys())

            if (not await self.validate.check_inbetween(ctx, channel_index, "channel_index", 1, len(subd_yt_channels), verbose = (not error))):
                error = True

            if (not error):
                target_channel_id = subd_yt_channels_ids[channel_index - 1]
                target_channel_name = Database.list_select("name", "Youtube_Channels", conditions = {"id": f"'{target_channel_id}'"})[0]
                question_message = f"Do you want to stop receiving notifications of the latest videos for the channel, `{target_channel_name}`"
                question_title = f"Stop Receiving Latest Videos?"

                answer = await self.question(ctx, question_message, question_title, True)

                if (answer in StringTools.TRUE):
                    subd_yt_channels.pop(target_channel_id)

                    if (subd_yt_channels):
                        db_channels = json.dumps(subd_yt_channels)[1:-1]
                        db_channels = db_channels.replace("\"", "")
                    else:
                        db_channels = StringTools.NONE
                    Database.update({CHANNEL_LOCATION_INDICES[account_type]: f"'{db_channels}'"}, table, conditions = conditions)

                    answer_message = f"Notifications to latest videos of `{target_channel_name}` disabled"
                    answer_title = "Stopped Receiving Notifications on channel"
                    await self.answer(ctx, answer_message, answer_title, True)


    # generate_yt_ch_view_pg(current_page, max_page, kwargs) Generates a page to view the subscribed channels
    # requires: current_page >= 1
    #           max_page >= 1
    async def generate_yt_ch_view_pg(self, current_page: int, max_page: int, kwargs: Dict[str, Any]) -> EmbededMessage:
        ctx = kwargs["ctx"]
        yt_channel_name_dict = kwargs["yt_channel_name_dict"]
        yt_channel_name_dict_len = kwargs["yt_channel_name_dict_len"]
        receive_notifications = kwargs["receive_notifications"]
        thumbnail = kwargs["thumbnail"]
        colour = kwargs["colour"]
        account_type = kwargs["account_type"]

        message = "Here are the channels "
        title = f"Subscribed Youtube Channels"

        if (account_type == YtAccount.Server):
            message += f"the server, `{ctx.guild.name}`,"
        elif (account_type == YtAccount.User):
            message += f"that you"

        message += " will receive the latest videos from"

        embeded_message = self.embed.context_embed(ctx, message, title, colour, thumbnail = thumbnail)

        # notifications
        formatted_notifications = ""
        if (receive_notifications):
            formatted_notifications += "`enabled \U00002714`"
        else:
            formatted_notifications += "`disabled \U0000274C`"
        embeded_message = self.embed.add_section(embeded_message, "Notifications \U0001F514", formatted_notifications)

        # subscribed youtube channels
        formatted_yt_channels = ""
        indices = Pagination.get_indices(current_page, self.CHANNELS_PER_PAGE, yt_channel_name_dict_len)
        start_index = indices["start_index"]
        end_index = indices["end_index"]

        yt_channel_key_lst = list(yt_channel_name_dict.keys())
        for i in range(start_index, end_index):
            key = yt_channel_key_lst[i]

            if (account_type == YtAccount.Server):
                formatted_yt_channels += f"#{i + 1}. `{key}` :   {yt_channel_name_dict[key]}\n"
            elif (account_type == YtAccount.User):
                formatted_yt_channels += f"#{i + 1}. `{key}`\n"

        if (formatted_yt_channels == ""):
            formatted_yt_channels = "```\nNo Subscribed Channels\n```"

        embeded_message = self.embed.add_section(embeded_message, "Subscribed Channels \U0001F39E", formatted_yt_channels)
        return embeded_message


    # view_subd_channels(ctx, account_type) Views all the subscribed channels of the server or the user
    # effects: sends an embed
    async def view_subd_channels(self, ctx: commands.Context, account_type: YtAccount):
        error = False
        error = await ChannelTools.validate_activity_channel(ctx, error)

        if (not error and ((account_type == YtAccount.Server and ctx.guild is not None) or account_type == YtAccount.User)):
            colour = "light-purple"
            if (account_type == YtAccount.Server):
                thumbnail = str(ctx.guild.icon_url)
                table = "Server_Accounts"
                conditions = {"id": f"{ctx.guild.id}"}
                default_func = ServerSettings.default_setting
            else:
                thumbnail = str(ctx.author.avatar_url)
                table = "User_Accounts"
                conditions = {"id": f"{ctx.author.id}"}
                default_func = UserSettings.default_setting

            columns_needed = [CHANNEL_LOCATION_INDICES[account_type], CHANNEL_NOTIFY_INDICES[account_type]]
            yt_channel_results = Database.default_select(default_func, SelectType.Formatted, [columns_needed, columns_needed, table], {"conditions": conditions}, [ctx], {})[0]
            yt_channel_dict = StringTools.convert_dict(yt_channel_results[CHANNEL_LOCATION_INDICES[account_type]])

            columns_needed = ["id", "name"]
            channel_map = Database.hash_select(0, columns_needed, columns_needed, "Youtube_Channels")
            yt_channel_name_dict = {}

            for c in yt_channel_dict:
                current_channel = ctx.guild.get_channel(int(yt_channel_dict[c]))
                if (current_channel is None):
                    channel_name = "#deleted-channel"
                else:
                    channel_name = f"`#{current_channel.name}`"

                key = channel_map[c]["name"]
                yt_channel_name_dict[key] = channel_name

            yt_channel_name_dict_len = len(yt_channel_name_dict)
            page = 1
            max_page = Pagination.get_total_pages(self.CHANNELS_PER_PAGE, yt_channel_name_dict_len)

            generate_yt_ch_view_pg_kwargs = {"ctx": ctx, "yt_channel_name_dict": yt_channel_name_dict, "yt_channel_name_dict_len": yt_channel_name_dict_len,
                                             "thumbnail": thumbnail, "colour": colour, "account_type": account_type, "receive_notifications": yt_channel_results[CHANNEL_NOTIFY_INDICES[account_type]]}

            embeded_message = await self.generate_yt_ch_view_pg(page, max_page, generate_yt_ch_view_pg_kwargs)
            paginated_components = Pagination.make_page_buttons(page, max_page)
            await Pagination.paginated_send(ctx, self.client, embeded_message, paginated_components, page, max_page, self.generate_yt_ch_view_pg, generate_yt_ch_view_pg_kwargs)


    # enable_notifications(ctx, account_type) Enables or disables receiving youtube notifications
    async def enable_notifications(self, ctx: commands.Context, account_type: YtAccount):
        if ((account_type == YtAccount.Server and ctx.guild is not None) or account_type == YtAccount.User):
            colour = "light-purple"
            question_message = "Do you want to receive notifications on the newest videos from "
            question_title = "Receive Notifications?"

            if (account_type == YtAccount.Server):
                thumbnail = str(ctx.guild.icon_url)
                table = "Server_Accounts"
                conditions = {"id": f"{ctx.guild.id}"}
                default_func = ServerSettings.default_setting
                question_message += "the server's"
            else:
                thumbnail = str(ctx.author.avatar_url)
                table = "User_Accounts"
                conditions = {"id": f"{ctx.author.id}"}
                default_func = UserSettings.default_setting
                question_message += "your"

            question_message += " subscribed channels"

            notifications = Database.default_select(default_func, SelectType.List, [CHANNEL_NOTIFY_INDICES[account_type], table], {"conditions": conditions}, [ctx], {})[0]
            new_notification = not bool(notifications)
            response = await self.question(ctx, question_message, question_title, new_notification, replacements = {"receive": "stop receiving", "Receive": "Stop Receiving"})

            if (response in StringTools.TRUE):
                Database.update({CHANNEL_NOTIFY_INDICES[account_type]: f"{int(new_notification)}"}, table, conditions = conditions)
                answer_message = f"Notifications to latest videos enabled"

                if (account_type == YtAccount.Server):
                    answer_message += " for the server"
                elif (account_type == YtAccount.User):
                    answer_message += " for you"
                answer_title = "Receiving Notifications on Channel"
                await self.answer(ctx, answer_message, answer_title, new_notification, {"enabled": "disabled", "Receiving": "Stopped Receiving"})


    # channel_updates(self) Get the latest video posted by a channel
    # effects: sends messages
    async def channel_updates(self):
        for c in LATEST_VIDEOS:
            channel_link = self.get_channel_videos_url(LATEST_VIDEOS[c].id)
            search_result = await self.get_latest_video_info(channel_link)
            latest_video_id = search_result["id"]
            latest_premiere = search_result["premiere"]

            if (latest_video_id != LATEST_VIDEOS[c].latest_video_id or (latest_video_id == LATEST_VIDEOS[c].latest_video_id and latest_premiere != LATEST_VIDEOS[c].premiere)):
                print(f"YAYYE AND {latest_video_id} AND {LATEST_VIDEOS[c].latest_video_id}")
                latest_video = LATEST_VIDEOS[c]
                print(f"HERE IS PUBLICSHING DATE: {search_result['publish_date']}")
                latest_publish_date = DateTime.get_yt_format_date(search_result["publish_date"])
                previous_publish_date = DateTime.get_duration(latest_video.publish_date)

                print(f"{latest_publish_date} AND {previous_publish_date} AND {latest_publish_date > previous_publish_date}")
                if (latest_publish_date > previous_publish_date or (latest_premiere != LATEST_VIDEOS[c].premiere)):
                    if (latest_premiere != LATEST_VIDEOS[c].premiere and not latest_premiere):
                        print(f"The premiered video from {latest_video.name} has been uploaded")
                        upload_message = f"The premiered video from `{latest_video.name}` is ready to watch!"
                    elif (latest_premiere):
                        print(f"{latest_video.name} premiered a new video")
                        upload_message = f"`{latest_video.name}` premiered a new video!"
                    else:
                        print(f"{latest_video.name} posted a new video")
                        upload_message = f"`{latest_video.name}` uploaded a new video!"

                    columns_needed = ["id", CHANNEL_LOCATION_INDICES[YtAccount.Server]]
                    notifications_enabled = 1
                    server_subd_lst = Database.hash_select(0, columns_needed, columns_needed, "Server_Accounts", conditions = {str(CHANNEL_NOTIFY_INDICES[YtAccount.Server]): f"{notifications_enabled}"})
                    user_subd_lst = Database.hash_select(0, columns_needed, columns_needed, "User_Accounts", conditions = {str(CHANNEL_NOTIFY_INDICES[YtAccount.User]): f"{notifications_enabled}"})

                    # update the video
                    await self.update_latest_video(c, latest_video_id, latest_publish_date, latest_premiere)
                    new_video_message = f"> \n> {upload_message}\n> \n> {YOUTUBE_BASE_VIDEO_URL + latest_video_id}"

                    # send the notification
                    for s in server_subd_lst:
                        current_server = server_subd_lst[s]
                        if (current_server[CHANNEL_LOCATION_INDICES[YtAccount.Server]] != StringTools.NONE and current_server[CHANNEL_LOCATION_INDICES[YtAccount.Server]].find(latest_video.id) != -1):
                            server = self.client.get_guild(s)
                            server_subd_channels = StringTools.convert_dict(current_server[CHANNEL_LOCATION_INDICES[YtAccount.Server]])
                            if (server is not None):
                                sending_channel_id = server_subd_channels[latest_video.id]
                                sending_channel = server.get_channel(int(sending_channel_id))

                                if (sending_channel is None):
                                    sending_channel = self.search_tools.get_announcment_channel(server)

                                    # update the sending channel next time to be the server's announcement channel
                                    yt_channel_dict = StringTools.convert_dict(current_server[CHANNEL_LOCATION_INDICES[YtAccount.Server]])
                                    yt_channel_dict[latest_video.id] = sending_channel.id

                                    updated_yt_channels = json.dumps(yt_channel_dict)[1:-1]
                                    updated_yt_channels = updated_yt_channels.replace("\"", "")

                                    Database.update({CHANNEL_LOCATION_INDICES[YtAccount.Server]: f"'{updated_yt_channels}'"}, "Server_Accounts", conditions = {"id": f"{server.id}"})

                                await sending_channel.send(new_video_message)

                    for u in user_subd_lst:
                        current_user = user_subd_lst[u]
                        if (current_user[CHANNEL_LOCATION_INDICES[YtAccount.User]] != StringTools.NONE and current_user[CHANNEL_LOCATION_INDICES[YtAccount.User]].find(latest_video.id) != -1):
                            user = self.client.get_user(u)
                            user_subd_channels = StringTools.convert_dict(current_server[CHANNEL_LOCATION_INDICES[YtAccount.User]])

                            if (user is not None):
                                await user.send(new_video_message)

