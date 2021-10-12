import discord, asyncio
from discord.ext import commands
from datetime import datetime, timezone
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType

import tools.error as error
import pics.image_links as pics
from tools.string import StringTools
from tools.discord_search import SearchAttributes, SearchTools
from tools.string import StringTools
from tools.embed import Embed, EmbededMessage
import tools.datetime as DateTools
import tools.members as members
from tools.validate import Validate
import tools.channels as ChannelTools
import tools.audit as audit
from database.database import Database
from tools.pagination import Pagination, ButtonedMsg
import pics.image_links as Pics
from tools.abs_func import AbsFunc
from typing import Optional, Union, List, Dict, Callable, Any

MESSAGE_UPDATE_WORD_LIM = 750
EDIT_SEC_WORD_LIM = 170
ACTIVITY_EMBED_FIELD_TITLES = ["\U0001F5A8 Embeds Before", "\U0001F5A8 Embeds After",
                               "\U0001F5A8 Embeds",
                               "\U0001F5D2 The Content of the Message",
                               "\U0001F5D2 The Content of the Message (Message is too long)",
                               "\U0001F5D2 New Content of the Message",
                               "\U0001F5D2 New Content of the Message (Message is too long)",
                               "\U0001F5D2 Old Content of the Message (Message is too long)",
                               "\U0001F5D2 Old Content of the Message"]
ACTIVITY_EMBED_TITLES = ["A Message is Recently Deleted!", "A Message is Recently Editted!"]

DELETE_IGNORE_LST = []

NO_EDIT = 0
BEFORE_EDIT = 1
AFTER_EDIT = 2

MAX_CLEAR = 100

DISCORD_ATTACHMENT_BASE_URL = "https://cdn.discordapp.com/attachments/"


#Finding Emojis
class Add_Emoji:

    #constructor
    def __init__(self, client):
        self.client = client

    #find specific emoji to message
    def find_emoji(self,emoji_name):

        for e in self.client.emojis:
            if (emoji_name == e.name):
                return e





#Texting Functions
class Texting(commands.Cog):

    #constructor
    def __init__(self, client: discord.Client):
        self.client = client
        self.searchtools = SearchTools(self.client)
        self.embed = Embed(self.client)
        self.validate = Validate(self.client)


    # get_deleter(self, guild, bulk) Gets the person who deletes the most recent
    #   message in the server
    async def get_deleter(self, guild_id: int, bulk: bool = False) -> Optional[discord.AuditLogEntry]:
        if (bulk):
            action = discord.AuditLogAction.message_bulk_delete
        else:
            action = discord.AuditLogAction.message_delete

        guild = self.client.get_guild(guild_id)

        dm = False
        try:
            entry = await SearchTools.get_recent_audit(guild, None, action)
            entry_time = entry.created_at
            within_time = DateTools.match_date(entry_time)
        except:
            dm = True
            entry = None

        # check if the entry in the audit log is editted
        if (dm or within_time):
            return entry
        else:
            if (bulk):
                before_count = audit.RECENT_AUDITS[guild_id].bulk_del_count
            else:
                before_count = audit.RECENT_AUDITS[guild_id].del_count

            try:
                after_count = entry.extra.count
            except:
                after_count = entry.extra['count']

            if (after_count <= before_count):
                entry = None

            if (bulk):
                audit.RECENT_AUDITS[guild_id].bulk_del_count = after_count
            else:
                audit.RECENT_AUDITS[guild_id].del_count = after_count

            return entry


    # format_msg_update(doer, message, channel, type, msg_type, public, target)
    #   Formats the top portion of the embed whenever a message has been deleted or
    #   editted
    # requires: 'msg_type' is either "embed" or "message"
    #           'type' is either "delete" or "edit"
    async def format_msg_update(self, doer: Optional[discord.abc.User], message: Optional[discord.Message],
                                channel: Union[discord.TextChannel, discord.DMChannel],
                                type: str = "delete", msg_type: str = "embed",
                                public: bool = False,
                                target: Optional[discord.abc.User] = None) -> Union[EmbededMessage, str]:
        doer_id = None
        initiator = None

        if (doer is None and message is None):
            description = "Someone"
        elif (doer is None):
            doer_name = members.convert_name(message.author.id, message.author.name)
            doer_id = message.author.id
            initiator = message.author
            description = f"**{members.convert_name(message.author.id, message.author.name)}**"

            if (msg_type == "embed"):
                description += f" ({StringTools.format_mention(message.author.id)})"

            if (channel.type != discord.ChannelType.private):
                doer_status = message.author.status
        else:
            doer_name = members.convert_name(doer.id, doer)
            doer_id = doer.id
            initiator = doer
            description = f"**{doer_name}**"

            if (msg_type == "embed"):
                description += f" ({StringTools.format_mention(doer.id)})"

            if (channel.type != discord.ChannelType.private):
                doer_status = doer.status

        if (type == "delete" or type == "bulk delete"):
            title = "A Message is Recently Deleted!"
            description += " deleted "
            colour = 0xFF0000
        elif (type == "edit"):
            title = "A Message is Recently Editted!"
            description += " editted "
            colour = 0xFFFF00

        # chekck if someone deleted their own message
        deleted_own = ((doer is not None and message is not None and (doer.id == message.author.id)) or (doer is None and message is not None) or
                       (doer is not None and target is not None and type == "delete" and (doer.id == target.id)) or channel.type == discord.ChannelType.private)

        if ((doer is None and message is None) or deleted_own):
            description += "their own "
        else:
            description += "a "
        description += "message"

        if (public or channel.type == discord.ChannelType.private):
            time_zone = DateTools.TIMEZONES[discord.VoiceRegion.us_east]
        else:
            time_zone = DateTools.db_get_timezone(channel.guild.id)

        if ((target is not None and type == "delete") or message is not None or channel.type == discord.ChannelType.private):
            if (channel.type == discord.ChannelType.private):
                author = channel.recipient

            elif (target is not None):
                author = target
            else:
                author = message.author

            victim_name = members.convert_name(author.id, author.name)
            victim_id = author.id

            if (message is not None):
                utc_datetime = message.created_at
                date = await DateTools.format_date(utc_datetime, timezone = time_zone)

            if (not deleted_own):
                description += f" by **{victim_name}**"

                if (msg_type == "embed"):
                    description += f" ({StringTools.format_mention(victim_id)})"


        if (type == "bulk delete"):
            title = title.replace("!", " During a Bulk Delete!")
            description += "  during a bulk delete"
            colour = 0x8B0000
        description += "!"

        if (doer is None and message is None):
            if (type == "delete"):
                code = 0
            elif (type == "bulk delete"):
                code = 1
            thumbnail = pics.get_image_link(pics.ImageCategory.Deleted, code)
        elif (doer is None):
            thumbnail = f"<{message.author.avatar_url}>"
        else:
            thumbnail = f"<{doer.avatar_url}>"

        # embed the message
        if (msg_type == "embed"):
            if (doer_id is not None and channel.type != discord.ChannelType.private):
                if (doer is None):
                    doer = message.author
                description = members.notify_invisible(doer_name, initiator, doer_status, description)
            embeded_message = self.embed.embed_message(None, description, title, colour, None, thumbnail, None)
        elif (msg_type == "message"):
            result_message = ""
            if (type == "delete"):
                title_emote = "\U0000274C"
            elif (type == "bulk delete"):
                title_emote = "\U000026D4"
            elif (type == "edit"):
                title_emote = "\U0000270F"

            result_message += f"> **__{title_emote} {title} {title_emote}__**\n> \n> {description}\n> \n"

        utc_now = datetime.now(timezone.utc)
        now = await DateTools.format_date(utc_now, timezone = time_zone)

        # get channel where message is deleted/ editted
        channel_sec_title = "\U0001F4C1 Channel Where the Message was "
        action_time_sec_title = "\U0001F4C5 Time of "

        if (type == "delete" or type == "bulk delete"):
            channel_sec_title += "Deleted"
            action_time_sec_title += "Deletion"
        elif (type == "edit"):
            channel_sec_title += "Editted"
            action_time_sec_title += "Edit"

        if (channel.type == discord.ChannelType.private):
            channel_name = ChannelTools.get_dm_channel(members.convert_name(channel.recipient.id, channel.recipient.name))
            channel_link = ""
        else:
            channel_name = channel.name
            channel_link = f" ({StringTools.format_channel(channel.id)})"

        # add footer for the author of the message
        if (message is not None or (target is not None and type == "delete") or channel.type == discord.ChannelType.private):
            if (channel.type == discord.ChannelType.private):
                footer_pic = str(channel.recipient.avatar_url)
            elif (target is not None):
                footer_pic = str(target.avatar_url)
            else:
                footer_pic = str(message.author.avatar_url)

            if (msg_type == "embed"):
                embeded_message = self.embed.add_footer(None, embeded_message, f"Message Written By: {victim_name}", footer_pic = footer_pic)

        if (message is not None):
            section_contents = {"\U0001F4DD Time When the Message was Posted": f"`{date}`",
                                channel_sec_title: f"`{channel_name}`" + channel_link,
                                action_time_sec_title: f"`{now}`"}

            if (type == "edit"):
                section_contents["\U0001F517 Link"] = message.jump_url
        else:
            section_contents = {channel_sec_title: f"`{channel_name}`" + channel_link,
                                action_time_sec_title: f"`{now}`"}

        if (msg_type == "embed"):
            return self.embed.multi_add_section(embeded_message, section_contents)
        elif (msg_type == "message"):
            for s in section_contents:
                result_message += f"> **{s}**\n> "
                result_message += section_contents[s]
                result_message += "\n> \n"

            return result_message


    # list_embed_attach(self, sending_channel, doer, message, channel, type, bf_af, bf_af_lst)
    #   Send messages or embeds of the image/video attachments of the
    #   editted or deleted message
    # required: 'type' is either "delete" or "edit"
    #           'bf_af' is either NO_EDIT, BEFORE_EDIT or AFTER_EDIT
    # effects: sends an embed or a message
    # note: 'bf_af_lst' is a list of content within a message that are not purely strings
    #       (images, videos, embeds, files, etc...)
    async def list_embed_attach(self, sending_channel: Union[discord.TextChannel, discord.DMChannel],
                                doer: Optional[discord.abc.User], message: Optional[discord.Message],
                                channel: Union[discord.TextChannel, discord.DMChannel],
                                type: str = "delete", bf_af: int = NO_EDIT,
                                bf_af_lst: Optional[Union[List[Union[discord.Embed, discord.Sticker]], List[discord.Attachment]]] = None,
                                server: Optional[Union[str, discord.Guild]] = None,
                                public: bool = False, attachments: bool = False) -> Union[discord.TextChannel, discord.DMChannel]:
        if (not attachments and bf_af == NO_EDIT):
            message_embeds = message.embeds + message.stickers
        elif (not attachments):
            message_embeds = bf_af_lst
        elif (bf_af == NO_EDIT):
            message_embeds = message.attachments
        else:
            message_embeds = bf_af_lst

        for e in message_embeds:
            if (not attachments and isinstance(e, discord.Embed)):
                url = e.url
            elif (not attachments):
                url = e.image_url
            else:
                url = e.proxy_url
                backup_url = e.url

            media_title = "\U0001F39E "
            if (bf_af == BEFORE_EDIT):
                media_title += "Removed Media Content"
            elif (bf_af == AFTER_EDIT):
                media_title += "Media Content in New Message"
            else:
                media_title += "Media Content"

            if ((attachments and e.content_type.find("image") != -1) or (not attachments and isinstance(e, discord.Embed) and e.type == "image")):
                embeded_message = await self.format_msg_update(doer, message, channel, type, public = public)
                media_title = media_title.replace("Media", "Image")

                if (server is not None):
                    if (isinstance(server, str)):
                        server_name = server
                        server_icon = doer.avatar_url
                    else:
                        server_name = server.name
                        server_icon = server.icon_url

                    embeded_message.embed.set_author(name = server_name,
                                               icon_url = server_icon)
                elif (isinstance(server, str)):
                    if (doer is not None):
                        icon_url = doer.avatar_url
                    else:
                        current_url = pics.get_image_link(pics.ImageCategory.Unknown, 0)
                        icon_url = current_url[1:-1]

                    embeded_message.set_author(name = server,
                                               icon_url = icon_url)

                try:
                    embeded_message.embed.set_image(url = url)
                    embeded_message = self.embed.add_section(embeded_message, media_title, f"`{url}`")
                except:
                    pass

                sending_channel = await ChannelTools.fixed_activity_send(self.client, sending_channel, sending_channel.guild, embed = embeded_message)
            elif (attachments or isinstance(e, discord.Sticker) or e.type != "rich"):
                sending_message = ""

                if (server is not None and not (isinstance(server, str))):
                    sending_message += f"> \U0001F5A5 **Server:** *{server.name}*\n> \n"
                elif (isinstance(server, str)):
                    sending_message += f"> \U0001F5A5 **Server:** *{server}*\n> \n"

                sending_message += await self.format_msg_update(doer, message, channel, type = type, msg_type = "message", public = public)
                if (attachments):
                    sending_message += f"> \U0001F4D1 **Proxy Url**\n> {url}\n> \n"
                    url = backup_url

                sending_message += f"> **{media_title}**\n> {url}"
                sending_channel = await ChannelTools.fixed_activity_send(self.client, sending_channel, sending_channel.guild, msg = sending_message)

            elif (e.type == "rich"):
                sending_message = ""
                sending_message += await self.format_msg_update(doer, message, channel, type = type, msg_type = "message")
                sending_message += f"> **{media_title}**"
                sending_channel = await ChannelTools.fixed_activity_send(self.client, sending_channel, sending_channel.guild, embed = e, msg = sending_message)

        return sending_channel




    # reduce_long_str(self, str, word_limit) Formats 'str' to only display
    #   characters up to 'word_limit'
    def reduce_long_str(self, str: str, word_limit: int):
        shortend_str = ""
        for i in range(word_limit):
            shortend_str += str[i]
        shortend_str += "...\"\n"
        return shortend_str


    # format_rich_embed(self, e, embed_section_limit) Format the contents of a
    #   rich embeded message to be displayed as a string within an embed
    def format_rich_embed(self, e: discord.Embed, embed_section_limit: int, in_activity: bool = False) -> Dict[str, Union[str, bool]]:
        embed_content = "\n"
        non_empty_embeds = False

        #display the title
        if (not in_activity):
            if (e.title):
                if (not non_empty_embeds):
                    non_empty_embeds = True

                if (len(e.title) <= embed_section_limit):
                    embed_content += f"Title:  \"{discord.utils.remove_markdown(e.title)}\"\n"
                else:
                    embed_content += "Title:  \""
                    embed_content += discord.utils.remove_markdown(self.reduce_long_str(e.title, embed_section_limit))

        if (not in_activity or (in_activity and e.title not in ACTIVITY_EMBED_TITLES)):
            #display the description
            if (e.description):
                if (not non_empty_embeds):
                    non_empty_embeds = True

                if (len(e.description) <= embed_section_limit):
                    embed_content += f"Description:  \"{discord.utils.remove_markdown(e.description)}\"\n"
                else:
                    embed_content += "Description:  \""
                    embed_content += discord.utils.remove_markdown(self.reduce_long_str(e.description, embed_section_limit))

        #display the fields for the embeds
        f_count = 0
        for f in e.fields:
            if (not non_empty_embeds):
                non_empty_embeds = True

            f_count += 1

            if (not in_activity or (in_activity and f.name in ACTIVITY_EMBED_FIELD_TITLES)):
                #title of the field
                if (in_activity or len(f.name) <= embed_section_limit/2):
                    embed_content += f"Field {f_count}: \"{discord.utils.remove_markdown(f.name)}\"\n"
                else:
                    embed_content += f"Field{f_count}: \""
                    embed_content += discord.utils.remove_markdown(self.reduce_long_str(f.name, int(embed_section_limit/2)))

                #content of the field
                if (in_activity or len(f.value) <= embed_section_limit/2):
                    embed_content += f"#{discord.utils.remove_markdown(f.value)}\n"
                else:
                    embed_content += f"#"
                    embed_content += discord.utils.remove_markdown(self.reduce_long_str(f.value, int(embed_section_limit/2)))

                #remove the bash code box for the deleted embed in the activity channel
                if (in_activity and embed_content[1:26] == "Field 4: \"\U0001F5A8 Embeds\"\n#bash"):
                    embed_content = embed_content[26:]

        return {"embed_content": embed_content, "non_empty_embeds": non_empty_embeds}


    # show_deleted_content(self, embeded_message, channel) Inputs the deleted
    #   message into the embed, 'embeded_message'
    def show_deleted_content(self, embeded_message: EmbededMessage, message: discord.Message,
                             channel: Union[discord.TextChannel, discord.DMChannel]) -> discord.Embed:
        #check the message for embeds
        embed_list = message.embeds

        if (len(embed_list) > 0):
            embeds_check = True
            embed_content_title = "\U0001F5A8 Embeds"
            embed_content = "```bash"

            # check if the channel is in the activity channels
            guild = message.guild
            server_id = None
            if (guild is not None):
                server_id = guild.id

            in_activity = ChannelTools.in_activity_channel(channel.id, server_id)

            non_empty_embeds = False
            #display the title
            for e in embed_list:
                #limit for each section content to display for the embed
                embed_section_limit = int((MESSAGE_UPDATE_WORD_LIM - len(message.content))/len(embed_list)/(2 + len(e.fields)))
                embed_format = self.format_rich_embed(e, embed_section_limit, in_activity = in_activity)

                embed_content += embed_format["embed_content"]
                non_empty_embeds = embed_format["non_empty_embeds"]

            embed_content += "```"

            if (non_empty_embeds and embed_format["embed_content"].strip() != ""):
                embeded_message.embed.add_field(name=embed_content_title, value=f"{embed_content}", inline=False)

        else:
            embeds_check = False

        #character limit in displaying the message content
        if(embeds_check):
            content_limit = int(MESSAGE_UPDATE_WORD_LIM / 2)
        else:
            content_limit = MESSAGE_UPDATE_WORD_LIM

        #if the message content is too long to display
        if (len(message.content) > content_limit):
            shortened_message = ""
            shortened_message += discord.utils.remove_markdown(self.reduce_long_str(message.content, content_limit))
            content_title = "\U0001F5D2 The Content of the Message (Message is too long)"
        else:
            shortened_message = discord.utils.remove_markdown(message.content)
            content_title = "\U0001F5D2 The Content of the Message"

        if (shortened_message != ""):
            embeded_message = self.embed.add_section(embeded_message.embed, content_title, f"`{shortened_message}`")
        return embeded_message


    # show_editted_content(self, embeded_message, before, after, channel)
    #   Inputs the editted content to the embed, 'embeded_message'
    def show_editted_content(self, embeded_message: EmbededMessage, before: Optional[discord.Message], after: Optional[discord.Message]) -> discord.Embed:
        if (before is not None):
            #check the before message for embeds
            embed_list = before.embeds

        if (before is not None and len(embed_list) > 0):
            embeds_before_check = True
            embed_content_title = "\U0001F5A8 Embeds Before"
            embed_content = "```bash"
            non_empty_before_eb = False

            #limit for each section content to display for the embed
            embed_section_limit = int(EDIT_SEC_WORD_LIM /len(embed_list)/2)

            #display the title
            for e in embed_list:
                bf_embed_result = self.format_rich_embed(e, embed_section_limit)
                embed_content += bf_embed_result["embed_content"]
                non_empty_before_eb = bf_embed_result["non_empty_embeds"]

            embed_content += "```"

            if (non_empty_before_eb):
                embeded_message.embed.add_field(name=embed_content_title, value=f"{embed_content}", inline=False)

        else:
            embeds_before_check = False

        #check the after message for embeds
        embed_list = after.embeds

        if (len(embed_list) > 0):
            embeds_after_check = True
            embed_content_title = "\U0001F5A8 Embeds After"
            embed_content = "```bash"
            non_empty_after_eb = False

            #limit for each section content to display for the embed
            if (before is not None):
                embed_section_limit = int(EDIT_SEC_WORD_LIM /len(embed_list)/2)
            else:
                embed_section_limit = int((MESSAGE_UPDATE_WORD_LIM / 2) /len(embed_list)/2)

            #display the title
            for e in embed_list:
                af_embed_result = self.format_rich_embed(e, embed_section_limit)
                embed_content += af_embed_result["embed_content"]
                non_empty_after_eb = af_embed_result["non_empty_embeds"]

            embed_content += "```"

            if (non_empty_after_eb):
                embeded_message.embed.add_field(name=embed_content_title, value=f"{embed_content}", inline=False)

        else:
            embeds_after_check = False


        #character limit in displaying the message content
        if (before is not None):
            if(embeds_after_check or embeds_before_check):
                content_limit = 225
            elif (embeds_after_check and embeds_before_check):
                content_limit = 150
            else:
                content_limit = 300
        else:
            if (embeds_after_check):
                content_limit = int(MESSAGE_UPDATE_WORD_LIM / 2)
            else:
                content_limit = MESSAGE_UPDATE_WORD_LIM

        #if the message is too long to display
        if (before is not None):
            if (len(before.content) > content_limit):
                shortened_message = ""
                shortened_message += discord.utils.remove_markdown(self.reduce_long_str(before.content, content_limit))
                content_title = "\U0001F5D2 Old Content of the Message (Message is too long)"
            else:
                shortened_message = discord.utils.remove_markdown(before.content)
                content_title = "\U0001F5D2 Old Content of the Message"

            embeded_message.embed.add_field(name=content_title, value=f"`{shortened_message}`", inline=False)


        #if the message is too long to display
        if (len(after.content) > content_limit):
            shortened_message = ""
            shortened_message += discord.utils.remove_markdown(self.reduce_long_str(after.content, content_limit))
            content_title = "\U0001F5D2 New Content of the Message (Message is too long)"
        else:
            shortened_message = discord.utils.remove_markdown(after.content)
            content_title = "\U0001F5D2 New Content of the Message"

        if (shortened_message != ""):
            embeded_message.embed.add_field(name=content_title, value=f"`{shortened_message}`", inline=False)
        return embeded_message


    # on_raw_message_delete(payload) logs when someone deletes a message
    # effects: sends an embed or message
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        #get the channel where the message was deleted
        channel = await self.client.fetch_channel(payload.channel_id)

        #attempt to get the deleted message from the cache
        catch_message = True
        try:
            message = payload.cached_message
            #convert the name of the author of the message
            name = members.convert_name(message.author.id, message.author)

        except:
            message = None
            catch_message = False

        entry = await self.get_deleter(payload.guild_id)
        doer = None
        target = None
        if (entry is not None):
            doer = entry.user
            target = entry.target
        elif (channel.type == discord.ChannelType.private):
            doer = channel.recipient

        if (payload.message_id not in DELETE_IGNORE_LST):
            embeded_message = await self.format_msg_update(doer, message, channel, target = target)
            public_embeded_message = await self.format_msg_update(doer, message, channel, public = True, target = target)

            if (catch_message):
                embeded_message = self.show_deleted_content(embeded_message, message, channel)
                public_embeded_message = self.show_deleted_content(public_embeded_message, message, channel)


            if (payload.guild_id is not None):
                server_activity_info = await ChannelTools.get_activity_data(self.client, payload.guild_id)
                track_enable = server_activity_info["track_message"]
                activity_channel = server_activity_info["activity_channel"]
                server = server_activity_info["server"]
            else:
                activity_channel = None
                server = None

            if (activity_channel is not None and track_enable):
                activity_channel = await ChannelTools.fixed_activity_send(self.client, activity_channel, server, embed = embeded_message)

                if (message is not None):
                    activity_channel = await self.list_embed_attach(activity_channel, doer, message, channel)
                    activity_channel = await self.list_embed_attach(activity_channel, doer, message, channel, attachments = True)

        else:
            DELETE_IGNORE_LST.remove(payload.message_id)



    # on_raw_bulk_message_delete(payload) logs when someone deletes messages by bulk
    # effects: sends an embed or a message
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):

        #get the channel where the message was deleted
        channel = await self.client.fetch_channel(payload.channel_id)

        #list to see if the individual message is cached
        cache_status_list = []

        cache_message_list = payload.cached_messages
        full_message_list = payload.message_ids
        cached_messages = {}

        for id in full_message_list:
            message = None

            for m in cache_message_list:
                if (id == m.id):
                    message = m
                    break
            cached_messages[id] = message

        doer_retrived = False
        #embed notification for every message deleted
        for m in cached_messages:
            message = cached_messages[m]

            # get the person who is doing the bulk delete
            if (not doer_retrived):
                doer_retrived = True
                entry = await self.get_deleter(payload.guild_id, bulk = True)
                doer = None
                if (entry is not None):
                    if (channel.type == discord.ChannelType.private):
                        doer = channel.recipient
                    else:
                        doer = entry.user

            embeded_message = await self.format_msg_update(doer, message, channel, type = "bulk delete")
            public_embeded_message = await self.format_msg_update(doer, message, channel, type = "bulk delete", public = True)

            if (message is not None):
                embeded_message = self.show_deleted_content(embeded_message, message, channel)
                public_embeded_message = self.show_deleted_content(public_embeded_message, message, channel)

            if (payload.guild_id is not None):
                server_activity_info = await ChannelTools.get_activity_data(self.client, payload.guild_id)
                track_enable = server_activity_info["track_message"]
                activity_channel = server_activity_info["activity_channel"]
                server = server_activity_info["server"]
            else:
                activity_channel = None
                server = None

            if (activity_channel is not None and track_enable):
                activity_channel = await ChannelTools.fixed_activity_send(self.client, activity_channel, server, embed = embeded_message)

                if (message is not None):
                    activity_channel = await self.list_embed_attach(activity_channel, doer, message, channel, type = "delete")
                    activity_channel = await self.list_embed_attach(activity_channel, doer, message, channel, attachments = True)

    # on_raw_message_edit(payload) logs when someone edits any message that is out of the cache
    # effects: sends a message or embed
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        #send a notification only when the editted message is not in the cache
        try:
            message = payload.cached_message
            #convert the name of the author of the message
            name = members.convert_name(message.author.id, message.author)

        except:
            #get the channel where the message was editted
            channel = await self.client.fetch_channel(payload.channel_id)

            #check if the channel is in the activity channels
            in_activity = ChannelTools.in_activity_channel(payload.channel_id, server_id = payload.guild_id)

            #get the editted message
            message = await channel.fetch_message(payload.message_id)

            #delete message if the message is in the activity and the message is not the bot's own messages
            if (in_activity and message.author.id not in members.IGNORED_MEMBERS):
                await message.delete()

            #ignores the bot's own actions if the message is not in the activity channel
            elif (message.author.id not in members.IGNORED_MEMBERS):
                embeded_message = await self.format_msg_update(message.author, message, channel,type = "edit")
                public_embeded_message = await self.format_msg_update(message.author, message, channel,type = "edit", public = True)
                embeded_message = self.show_editted_content(embeded_message, None, message)
                public_embeded_message = self.show_editted_content(public_embeded_message, None, message)

                if (payload.guild_id is not None):
                    server_activity_info = await ChannelTools.get_activity_data(self.client, payload.guild_id)
                    track_enable = server_activity_info["track_message"]
                    activity_channel = server_activity_info["activity_channel"]
                    server = server_activity_info["server"]
                else:
                    activity_channel = None
                    server = None

                if (activity_channel is not None and track_enable):
                    activity_channel = await ChannelTools.fixed_activity_send(self.client, activity_channel, server, embed = embeded_message)
                    activity_channel = await self.list_embed_attach(activity_channel, message.author, message, channel, type = "edit")
                    activity_channel = await self.list_embed_attach(activity_channel, message.author, message, channel, type = "edit", attachments = True)

    # on_message_edit(self, before, after) logs for editted message, if the message is still in the cache
    # effects: sends a message or an embed
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        #get the channel where the message was editted
        channel = await self.client.fetch_channel(after.channel.id)

        #check if the channel is in the activity channels
        in_activity = False

        if (after.channel.type != discord.ChannelType.private):
            in_activity = ChannelTools.in_activity_channel(after.channel.id, server_id = after.guild.id)

        #delete message if the message is in the activity and the message is not the bot's own messages
        if (in_activity and after.author.id not in members.IGNORED_MEMBERS):
            await after.delete()

        #ignores the bot's own actions
        elif ((after.author.id in members.IGNORED_MEMBERS and len(before.embeds) >  len(after.embeds)) or after.author.id not in members.IGNORED_MEMBERS):
            embeded_message = await self.format_msg_update(after.author, after, after.channel, type = "edit")
            public_embeded_message = await self.format_msg_update(after.author, after, after.channel, type = "edit", public = True)
            embeded_message = self.show_editted_content(embeded_message, before, after)
            public_embeded_message = self.show_editted_content(public_embeded_message, before, after)

            if (after.guild is not None):
                server_activity_info = await ChannelTools.get_activity_data(self.client, after.guild.id)
                track_enable = server_activity_info["track_message"]
                activity_channel = server_activity_info["activity_channel"]
                server = server_activity_info["server"]
            else:
                activity_channel = None
                server = None

            if (activity_channel is not None and track_enable):
                activity_channel = await ChannelTools.fixed_activity_send(self.client, activity_channel, server, embed = embeded_message)

            before_embeds = []
            after_embeds_url = []

            for e in after.embeds:
                after_embeds_url.append(e.url)

            for e in before.embeds:
                if (e.url not in after_embeds_url):
                    before_embeds.append(e)

            before_attach = []
            after_attach_url = []

            for a in after.attachments:
                after_attach_url.append(a.proxy_url)

            for a in before.attachments:
                if (a.proxy_url not in after_attach_url):
                    before_attach.append(a)

            if (activity_channel is not None and track_enable):
                activity_channel = await self.list_embed_attach(activity_channel, before.author, before, channel, type = "edit", bf_af = BEFORE_EDIT, bf_af_lst = before_embeds)
                activity_channel = await self.list_embed_attach(activity_channel, before.author, before, channel, type = "edit", bf_af = BEFORE_EDIT, bf_af_lst = before_attach, attachments = True)
                activity_channel = await self.list_embed_attach(activity_channel, after.author, after, channel, type = "edit", bf_af = AFTER_EDIT, bf_af_lst = after.embeds)
                activity_channel = await self.list_embed_attach(activity_channel, after.author, after, channel, type = "edit", bf_af = AFTER_EDIT, bf_af_lst = after.attachments, attachments = True)


    # on_message(message) Deletes the message if the message is in a
    #   server's activity channel
    # effects: may delete a message
    async def on_message(self, message: discord.Message):
        guild = message.guild

        if (guild is not None):
            in_activity = ChannelTools.in_activity_channel(message.channel.id, guild.id)

            if (message.author.id not in members.IGNORED_MEMBERS and in_activity):
                await message.delete()


    # user_embed(ctx, description, title, colour, display_thumbnail, thumbnail, image, search_channel, search_guild)
    #   converts user's messages to embeded messages
    # effects: sends an embed and deletes message
    async def user_embed(self, ctx: commands.Context, description: str, title: str,
                         colour: str, thumbnail: str, image: str, search_channel: str = StringTools.NONE,
                         search_guild: str = StringTools.NONE):

        error = False
        error = await ChannelTools.validate_activity_channel(ctx, error)
        error, thumbnail = await self.validate.validate_embed_image(ctx, error, thumbnail, "thumbnail")
        error, image = await self.validate.validate_embed_image(ctx, error, image, "image")
        error, search_guild, search_channel = await self.searchtools.validate_sev_ch(ctx, error, search_channel, search_guild, action = "send embed",
                                                                                allow_dm = True, allow_default = True)

        if (not error):
            description = StringTools.convert_str(description)
            title = StringTools.convert_str(title)

            #delete the message that invoked the command
            try:
                await ctx.message.delete()
            except:
                pass

            embeded_message = self.embed.embed_message(ctx, description, title, colour, ctx.message.author.name, thumbnail, Embed.EMBED_IMG_SELF, image)
            await search_channel.send(embed = embeded_message.embed, file = embeded_message.file)

            
    # hello(ctx) greets the user with hello
    # effects: sends an embed
    async def hello(self, ctx: commands.Context):
        error = False
        error = await ChannelTools.validate_activity_channel(ctx, error)

        if (not error):
            #convert names
            name = members.convert_name(ctx.message.author.id, ctx.message.author);

            image = pics.get_image_link(pics.ImageCategory.Greet, 0)
            embeded_message = self.embed.embed_message(ctx, f'Yahello {name}! \U0001F496 \U0001F497', "Haku says:", 0xD9B3FF, ctx.message.author.name, None, Embed.EMBED_IMG_BOT, image)
            #display the embeded message
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)



    # clear(self, ctx, no_of_messages, no_from_last_message, search_channel)
    #   deletes a number of messages
    # effects: sends an embed and deletes messages
    async def clear(self, ctx: commands.Context, no_of_messages: str, no_from_last_message: str = "0", search_channel: str = StringTools.NONE):
        author = members.convert_name(ctx.author.id, ctx.author)

        error = False
        error = await ChannelTools.validate_activity_channel(ctx, error)
        error = await ChannelTools.validate_private_channel(ctx, self.client, error, author, "clear messages")
        error, no_of_messages = await self.validate.validate_natural(ctx, error, no_of_messages, "no_of_messages", allow_optional = False, check_equal = True)
        error, last_message_index = await self.validate.validate_natural(ctx, error, no_from_last_message, "no_from_last_message", allow_optional = False, check_equal = True)
        error, channel = await self.searchtools.validate_channel(ctx, error, search_channel)

        # check if the message are in between 0 to 100
        error = await self.validate.validate_inbetween(ctx, no_of_messages, "no_of_messages", 1, MAX_CLEAR, error, verbose = True, check_equal = True)
        error = await self.validate.validate_inbetween(ctx, last_message_index, "no_from_last_message", 0, MAX_CLEAR, error, verbose = True, check_equal = True)

        if (not error):
            #generate a password for the function
            password = StringTools.generate_password()
            embeded_message = self.embed.bot_embed(ctx, f"To confirm your action to clear the selected messages, please enter the code:\n \n   ```fix\n{password}\n``` \n\n to the ***channel that you invoked the `$clear` command***",
                                                   "Confirmation to Clear Messages", "yellow", 0, {pics.ImageCategory.Default: 0})

            await ctx.author.send(embed = embeded_message.embed, file = embeded_message.file)
            invoked_command = ctx.message
            await ctx.message.delete(delay = 2)

            #get the last message
            if (last_message_index > 0):
                if (channel == ctx.message.channel):
                    last_message_index += 1

                last_messages = await channel.history(limit=last_message_index).flatten()
                before_msg = last_messages[last_message_index - 1]
            else:
                before_msg = None

            #ask the user for password before deleting messsages
            thumbnail = pics.get_image_link(pics.ImageCategory.Unknown, 0)

            def check(m):
                return m.content == password

            msg = await self.client.wait_for('message', check=check)
            await msg.delete()

            #deletes the messages
            if (before_msg is not None):
                await channel.purge(limit=no_of_messages, before = before_msg)
            else:
                await channel.purge(limit=no_of_messages)


    # is_discord_attachment(attachment) Determines if 'attachment' is a url
    #   to a discord attachment
    def is_discord_attachment(self, attachment: Any):
        return (isinstance(attachment, str) and attachment.startswith(DISCORD_ATTACHMENT_BASE_URL))


    # noticeable_edit(self, ctx, last_message, embeded_message, action) Edits or
    #   deletes the message if the message is the most recent in the channel
    # requires: 'action' is either "edit" or "delete"
    #           'delay' >= 0
    # effects: may edit, delete or send an embed
    async def noticeable_edit(self, ctx: commands.Context, last_message: discord.Message,
                              embeded_message: EmbededMessage, action: str = "edit", keep_attachments: bool = True, delay: int = 0) -> Optional[discord.Message]:
        recent_message = await self.searchtools.get_last_message(ctx.channel)
        if (recent_message is not None and recent_message.id == last_message.id):
            if (delay):
                asyncio.sleep(delay)

            if (action == "edit"):
                print(bool(recent_message.attachments))
                if (recent_message.embeds and recent_message.embeds[0].image != discord.Embed.Empty):
                    print(recent_message.embeds[0].image.url)
                print()
                if (embeded_message.file is None and
                    ((not recent_message.attachments and
                      not (recent_message.embeds and self.is_discord_attachment(recent_message.embeds[0].image.url))) or
                     keep_attachments)):
                    await recent_message.edit(embed = embeded_message.embed)
                    return recent_message
                else:
                    DELETE_IGNORE_LST.append(recent_message.id)
                    await recent_message.delete()
                    new_message = await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
                    return new_message
            elif (action == "delete"):
                try:
                    DELETE_IGNORE_LST.append(recent_message.id)
                    await recent_message.delete()
                except:
                    pass
                return None

        elif (action == "edit"):
            channel = last_message.channel
            return_msg = await channel.send(embed = embeded_message.embed, file = embeded_message.file)
            return return_msg


    # continual_ask(self, ctx, question_embed, value_to_check)continuously asks
    #   the user until the correct value is reached
    # requires: 'values_to_check' is not empty
    # effects: deletes messages and sends embeds
    async def continual_ask(self, ctx: commands.Context, question_embed: EmbededMessage,
                            values_to_check: List[str], send_question: bool = True) -> str:
        if (send_question):
            quest_msg = await ctx.message.channel.send(embed = question_embed.embed, file = question_embed.file)

        def check(m):
            return (m.content and (m.author.id == ctx.author.id))

        err_description = "Please type in either: "
        for i in range(len(values_to_check)):
            err_description += f"`{values_to_check[i]}`"
            if (i == (len(values_to_check) - 2)):
                err_description += " or "
            elif (i < (len(values_to_check) - 2)):
                err_description += ", "

        msg = await self.client.wait_for('message', check=check)
        question_content = question_embed.embed.description

        embeded_message = self.embed.bot_embed(ctx, f"For the statement:\n```\n{question_content}\n```\n\n{err_description}", "Invalid Input", "red", 2, {pics.ImageCategory.Default: 0})

        direction_msg = None
        while (msg.content.lower() not in values_to_check):
            await self.noticeable_edit(ctx, msg, embeded_message, action = "delete")

            if (direction_msg is not None):
                direction_msg = await self.noticeable_edit(ctx, direction_msg, embeded_message, action = "edit")
            else:
                direction_msg = await ctx.channel.send(embed = embeded_message.embed, file = embeded_message.file)
            msg = await self.client.wait_for('message', check=check)

        # delete all the messages
        try:
            await msg.delete()
            if (direction_msg is not None):
                await direction_msg.delete()

            if (send_question):
                await quest_msg.delete()
        except:
            pass

        return msg.content


    # question(ctx, question, question_title, set_value, values_to_check) Asks the user to
    #   enable or disable a certain tracking attribute
    async def question(self, ctx: commands.Context, question: str, question_title: str, set_value: bool = True, replacements = {"enable": "disable", "Enable": "Disable"}, fields: Dict[str, str] = {}) -> str:
        default_pic = {Pics.ImageCategory.Default: 0}
        values_to_check = StringTools.TRUE + StringTools.FALSE

        if (not set_value):
            question = StringTools.word_replace(question, replacements)
            question_title = StringTools.word_replace(question_title, replacements)

        question_embed = self.embed.bot_embed(ctx, question, question_title, "yellow", 2, default_pic)
        question_embed = self.embed.multi_add_section(question_embed, fields)
        question_embed = self.embed.add_section(question_embed, "Yes (y)", "\U0001F44D", True)
        question_embed = self.embed.add_section(question_embed, "No (n)", "\U0001F44E", True)
        return await self.continual_ask(ctx, question_embed, values_to_check)


    # answer(ctx, answer_desc, answer_title, set_value, values_to_check) Displays the message
    #   to confirm that the setting value to a tracking attribute has been changed
    async def answer(self, ctx: commands.Context, answer_desc: str, answer_title: str, set_value: bool = True, replacements = {"enable": "disable", "Enable": "Disable"}, fields: Dict[str, str] = {}):
        default_pic = {Pics.ImageCategory.Default: 0}

        if (not set_value):
            answer_desc = StringTools.word_replace(answer_desc, replacements)
            answer_title = StringTools.word_replace(answer_title, replacements)
        answer_embed = self.embed.bot_embed(ctx, answer_desc, answer_title, "light-green", 2, default_pic)
        answer_embed = self.embed.multi_add_section(answer_embed, fields)
        await ctx.send(embed = answer_embed.embed, file = answer_embed.file)


    # paginated_continual_ask(self, ctx, current_page, max_page, generate_pg, generate_pg_kwargs, values_to_check) Continuosly asks
    #   the user until the correct value is reached for paginated embeds
    #   for the question
    # requires: 1 <= max_page
    #           1 <= current_page
    # effects: sends messages and deletes message
    async def paginated_continual_ask(self, ctx: commands.Context, current_page: int,
                                      max_page: int, generate_pg: AbsFunc, values_to_check: List[str],
                                      delete_question: bool = True) -> str:
        embeded_message = await generate_pg.async_run(pre_args = [current_page, max_page])
        paginated_components = Pagination.make_page_buttons(current_page, max_page)
        sent_message = await ctx.send(embed = embeded_message.embed, file = embeded_message.file, components = paginated_components)

        done, pending = await asyncio.wait([self.continual_ask(ctx, embeded_message, values_to_check, send_question = False),
                                            Pagination.page_react(self.client, sent_message, current_page, max_page, generate_pg)],
                                           return_when=asyncio.FIRST_COMPLETED)
        for t in done:
            result = t.result()

        # if the function for reacting to the buttons of the paginated
        #   embed ended before the result for the choice is picked
        if (result is None):
            done, pending = await asyncio.wait(pending)
            for t in done:
                result = t.result()

        await sent_message.delete()
        return result


    # announcment(self, ctx, embeded_message, condition, condition_kwargs) Sends
    #   an announcement embed to all servers
    # requires: 1 <= max_page
    #           1 <= current_page
    # effects: sends messages
    async def announcment(self, ctx: commands.Context, embeded_message: EmbededMessage,
                          condition: Optional[Callable[discord.Guild, bool]] = None, condition_kwargs: Dict[str, Any] = {}):
        for g in self.client.guilds:
            if (condition is None or (condition is not None and condition(g, condition_kwargs))):
                announcement_channel = self.searchtools.get_announcment_channel(g)
                await announcement_channel.send(embed = embeded_message.embed, file = embeded_message.file)


    # paginated_announcement(self, ctx, msg_lst, current_page, max_page, generate_pg,
    #                        generate_pg_kwargs, pin, condition, condition_kwargs)
    # Sends a paginated announcement to all guilds
    # requires: 1 <= max_page
    #           1 <= current_page
    #           'paginated_components' is not empty
    # effects: sends messages
    async def paginated_announcement(self, ctx: commands.Context, msg_lst: List[ButtonedMsg],
                                     current_page: int, max_page: int, embeded_message: EmbededMessage,
                                     generate_pg: AbsFunc, paginated_components: List[List[Button]], pin: bool = False,
                                     condition: Optional[Callable[discord.Guild, bool]] = None, condition_kwargs: Dict[str, Any] = {}):
        for g in self.client.guilds:
            if (condition is None or (condition is not None and condition(g, condition_kwargs))):
                announcement_channel = self.searchtools.get_announcment_channel(g)
                temp_message = await announcement_channel.send(embed = embeded_message.embed, file = embeded_message.file, components = paginated_components)
                if (pin):
                    await temp_message.pin()
                msg_lst.append(ButtonedMsg(temp_message, current_page, max_page))

        # delete the pin
        if (pin):
            for m in msg_lst:
                await m.message.channel.purge(limit=1)
        await Pagination.multi_page_react(self.client, msg_lst, generate_pg)


    # delay_send(cls, ctx, time, embed) Send an message with a delay
    # effects: sends messages
    @classmethod
    async def delay_send(cls, ctx: commands.Context, time: float, embed: Optional[EmbededMessage] = None):
        await asyncio.sleep(time)
        msg = await ctx.send(embed = embed.embed, file = embed.file)
