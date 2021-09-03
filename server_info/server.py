import discord, random, datetime, enum, copy, asyncio
from discord.ext import commands
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType

from tools.discord_search import SearchTools
from database.database import Database
from tools.embed import Embed
from tools.discord_search import SearchAttributes
from tools.data_groups import DataGroups
import pics.image_links as Pics
import tools.members as members
import tools.channels as ChannelTools
from text.bot_texting import Texting
import tools.datetime as DateTime
from tools.string import StringTools
import tools.error as Error
from tools.validate import Validate
from tools.pagination import Pagination
import set_up.prefix as Prefix
from typing import Union, Dict, Optional, Any

intents = discord.Intents()
intents.all()

LOG_REPLACEMENTS = {"doer": "[doer]", "date": "[date]", "channel": "[channel]", "victim": "[victim]", "before_channel": "[before_channel]", "after_channel": "[after_channel]"}

ACTIONS = {discord.ActivityType.unknown: "Unknown", discord.ActivityType.playing: "Playing",
           discord.ActivityType.streaming: "Streaming", discord.ActivityType.listening: "Listening",
           discord.ActivityType.watching: "Watching", discord.ActivityType.competing: "Competing"}

CHANNEL_TYPE = {discord.ChannelType.text: "text", discord.ChannelType.voice: "voice",
                discord.ChannelType.category: "category", discord.ChannelType.stage_voice: "stage voice"}

SPOTIFY_ACTION_BEFORE = "before"
SPOTIFY_ACTION_AFTER = "after"
EVERYONE_ROLE = "everyone"

USER_TYPING = {}
TYPING_DELAY = 60
INVISIBLE_TEXT = "*\U0001F575 __INVISIBLE__ \U0001F575*"
SERVER_INFO_DICT = {}

MEMBERS_PER_PAGE = 20
STATUS_ICONS = {discord.Status.online: "\U0001F7E2", discord.Status.idle: "\U0001F7E1", discord.Status.dnd: "\U0001F534", discord.Status.offline: "\U000026AB", discord.Status.invisible: "\U0001F575"}
BOMB_COUNT = 100


# a class to tell that stores the information about a server
class ServerInfo():
    def __init__(self, approx_active_members: int, invisible_members: int):
        self.approx_active_members = approx_active_members
        self.invisible_members = invisible_members


# MemberActivityInfo: Stores a member and their associated activity
class MemberActivityInfo():
    def __init__(self, member: discord.Member, activity: discord.Status):
        self.member = member
        self.activity = activity


# enum for changing a channel
class ChannelAction(enum.Enum):
    Create = "create"
    Delete = "delete"
    Update = "update"


# enum for the spotify song activity of the user
class SpotifyActivity(enum.Enum):
    Play = "Playing"
    Paused = "Paused"
    Finished = "Finished"
    Skipped = "Skipped"


# enum for member activity status
class MemberActivity(enum.Enum):
    All = "all"
    Online = "online"
    Idle = "idle"
    Dnd = "dnd"
    Offline = "offline"
    Active = "active"
    Invisible = "invisible"


# enum for the identity of the member
class MemberIdentity(enum.Enum):
    Member = "\U0001F973 Members"
    Bot = "\U0001F916 Bots"
    Cute_Girl = "\U0001F497 Cute Girls"


class ServerUtil(commands.Cog):
    #constructor
    def __init__(self, client: discord.Client):
        self.client = client
        self.database = Database()
        self.searchtools = SearchTools(client)
        self.embed = Embed(client)
        self.text = Texting(client)
        self.validate = Validate(client)


    # is_role(self, member, role) Checks whether 'member' has a certain 'role'
    def is_role(self, member: discord.Member, role: discord.Role) -> bool:
        in_role = True
        if (role != EVERYONE_ROLE):
            in_role = (role in member.roles)
        return in_role


    # check_member_status Checks whether the status of 'member' matches with
    #   'status'
    def check_member_status(self, member: discord.Member, status: discord.Status,
                            role: discord.Role) -> bool:
        in_role = self.is_role(member, role)
        return (member.status == status and in_role)


    # check_member_invisible(member, status, role) Checks whether 'member' is
    #   invisible
    def check_member_invisible(self, member: discord.Member, status: discord.Status,
                               role: discord.Role) -> bool:
        is_invisible = False
        is_offline = self.check_member_status(member, discord.Status.offline, role)
        if (is_offline):
            is_invisible = bool(member.id in list(members.INVISIBLE_MEMBERS.keys()))

        return is_invisible


    # is_active(self, member, role) Determines whether 'member' is active
    def is_active(self, member: discord.Member, role: discord.Role) -> bool:
        return (self.check_member_status(member, discord.Status.online, role) or
                self.check_member_status(member, discord.Status.idle, role) or
                self.check_member_status(member, discord.Status.dnd, role))


    # get_active_members(server) Determines the number of members who are active
    async def get_active_members(self, server: discord.Guild) -> int:
        count = 0
        for m in server.members:
            if (self.is_active(m, EVERYONE_ROLE)):
                count += 1

        return count


    # get_approx_logged_in_members(server) Get the approximate number of member that
    async def get_approx_logged_in_members(self, server: discord.Guild) -> int:
        # create an invite if not created yet
        invite_lst = await server.invites()
        if (not invite_lst):
            for c in server.channels:
                if (type(c) != discord.CategoryChannel):
                    guild_invite = await c.create_invite(temporary = True)
                    break

            invite = await self.client.fetch_invite(guild_invite.id)
        else:
            invite = await self.client.fetch_invite(invite_lst[0].id)

        total_online_members = invite.approximate_presence_count
        return total_online_members


    # on_member_join(self, member) Welcomes a new member to a server
    # effects: sends an embed
    async def on_member_join(self, member: discord.Member):
        #convert name
        name = members.convert_name(member.id, member)

        #embed the message
        embeded_message = self.embed.bot_embed(None, f"\U0001F389 Welcome to the server **{name}**! \U0001F389", None, 0x66FFFF, self.embed.RANDOM_NAME, image = {Pics.ImageCategory.Greet: 0})

        #get the channel to send
        guild = member.guild
        channel = SearchTools.get_announcment_channel(guild)
        await channel.send(embed = embeded_message.embed, file = embeded_message.file)


    # on_member_remove(self, member) Tells when a member leaves a server
    # effects: sends an embed
    async def on_member_remove(self, member : discord.Member):
        #convert name
        name = members.convert_name(member.id, member)

        #embed the message
        image_code = random.randrange(len(Pics.IMAGE_LIST[Pics.ImageCategory.Sad]))
        embeded_message = self.embed.bot_embed(None, f"\U0001F97A Goodbye **{name}** \U0001F97A", None, 0xFF9999, self.embed.RANDOM_NAME, image = {Pics.ImageCategory.Sad: image_code})

        #get the channel to send
        guild = member.guild
        try:
            channel = SearchTools.get_announcment_channel(guild)
            await channel.send(embed = embeded_message.embed, file = embeded_message.file)
        except:
            pass


    # on_guild_join(self, guild) Welcomes everybody when the bot is added to a server
    # effects: sends embeds
    async def on_guild_join(self, guild: discord.Guild):
        server_activity_info = Database.in_table(guild.id, "id", "Server_Accounts")
        channel_list = guild.channels
        channel = None
        for c in channel_list:
            current_channel = c.name.lower()
            if (type(c) is discord.TextChannel):
                channel = c
                break

        welcome_message = f"Hi, my name is {members.BOT_NICKNAMES[1]}. Thank you for welcoming me into the server! I will be in your hands so please take good care of me in the future!"
        welcome_title = "Hello Everybody"

        if (server_activity_info is None):
            welcome_embed = self.embed.bot_embed(None, welcome_message, welcome_title, "pink", 2, {Pics.ImageCategory.Default: 0})
            await channel.send(embed = welcome_embed.embed, file = welcome_embed.file)

            activity_channel_name = 'Activity-Log-\U0001F4D2 \U0000270F'
            word_count_channel_name = "Word-Trigger-Log-\U0001F4D5 \U0001F58A"
            embeded_message = self.embed.bot_embed(None, f"By the way, For now, I will be updating the server's activity in #{activity_channel_name}. You can enable/disable this function anytime using the command `{Prefix.DEFAULT_PREFIX}settings server track`", None, "light-purple", 2, None)
            await self.text.delay_send(channel, 3, embed = embeded_message)
            activity_channel = await guild.create_text_channel(activity_channel_name)
            word_count_channel = await guild.create_text_channel(word_count_channel_name)

            embeded_message = self.embed.bot_embed(None, f"To start off, you can view the list of commands I can do by typing `{Prefix.DEFAULT_PREFIX}help`", None, "light-blue", 2, None)
            await self.text.delay_send(channel, 3, embed = embeded_message)

            embeded_message = self.embed.bot_embed(None, f"\U000026A0 Also **__Please DO NOT Change my nickname yourself! If you want to change my nickname, please consult with me using the command `{Prefix.DEFAULT_PREFIX}your_nickname`__** \U000026A0", None, "red", 2, None)
            await self.text.delay_send(channel, 2, embed = embeded_message)

            self.database.insert({"id":f"{guild.id}", "name":f"'{guild.name}'", "prefixes":f"'{Prefix.DEFAULT_PREFIX}'", "track_activity":f"1", "track_message": f"1","activity_channel":f"{activity_channel.id}",
                                  "word_count_channel":f"{word_count_channel.id}", "timezone": f"'{DateTime.get_timezone(guild)}'", "region": f"'{Weather.get_weather_region(guild)}'"}, "Server_Accounts")

        else:
            welcome_message = StringTools.word_replace(welcome_message, {"welcoming me": "welcoming me back", "hands": "hands again"})
            welcome_embed = self.embed.bot_embed(None, welcome_message, welcome_title, "pink", 2, {Pics.ImageCategory.Default: 0})
            await channel.send(embed = welcome_embed.embed, file = welcome_embed.file)


    # get_updater(self, action) Retrives the most recent update in the audit log
    #   of 'guild' based on 'action'
    async def get_updater(self, guild: discord.Guild, action: discord.AuditLogAction) -> discord.AuditLogEntry:
        update_entry = await SearchTools.get_recent_audit(guild, None, action = action)
        return update_entry


    # activity_eq(act_a, act_b) Compares whether the activities are the same
    def activity_eq(self, act_a: discord.Activity, act_b: discord.Activity) -> bool:
        if (act_a.application_id == act_b.application_id):
            return True
        else:
            return False


    # get_log_date(timezone) Get the current date when logging an activity
    async def get_log_date(self, timezone: str, today: Optional[datetime.datetime] = None) -> Dict[str, str]:
        if (today is None):
            today = DateTime.get_current_dt(utc = True)
        public_today_format = await DateTime.format_date(today, format = DateTime.LONG_FORMAT)
        today_format = await DateTime.format_date(today, format = DateTime.LONG_FORMAT, timezone = timezone)

        return {"today_format": today_format, "public_today_format": public_today_format}


    # log_send(self, message_template, replacements, track_enable, colour, activity_channel, guild, timezone, dates, thumbnail, image)
    #   Formats the message to be embeded and sent to the activity channel
    # effects: sends embeds
    async def log_send(self, message_template: str, replacements: Dict[str, str], track_enable: int,
                       colour: Union[str, int], activity_channel: Optional[int], guild: Union[discord.Guild, str],
                       timezone: str, dates: Optional[Dict[str, str]] = None, thumbnail = None, image = None,
                       fields = {}, footer = {}, first_guild = None, user: Optional[discord.abc.User] = None):
        if (dates is None):
            dates = await self.get_log_date(self, timezone)

        today_format = dates["today_format"]
        public_today_format = dates["public_today_format"]

        replaced_message = StringTools.word_replace(message_template, replacements)
        local_message = replaced_message.replace(LOG_REPLACEMENTS["date"], dates["today_format"])

        embeded_message = self.embed.embed_message(None, local_message, None, colour, None, thumbnail, None, image)

        if (fields):
            embeded_message = self.embed.multi_add_section(embeded_message, fields)

        if (footer):
            footer_items = list(footer.items())
            embeded_message = self.embed.add_footer(None, embeded_message, footer_items[0][0], footer_pic = footer_items[0][1])

        if (embeded_message is not None):
            if (track_enable and activity_channel is not None):
                await ChannelTools.fixed_activity_send(self.client, activity_channel, guild, embed = embeded_message)

            if (first_guild is None or (first_guild is not None and guild == first_guild)):
                try:
                    embeded_message.embed.set_author(name = guild.name, icon_url = guild.icon_url)
                except:
                    guild_name = str(guild)
                    if (user is None):
                        embeded_message.embed.set_author(name = guild_name)
                    else:
                        embeded_message.embed.set_author(name = guild_name, icon_url = user.avatar_url)

                embeded_message.embed.description = replaced_message.replace(LOG_REPLACEMENTS["date"], public_today_format)


    # check_on_phone(member) Checks if a user is on their phone
    def check_on_phone(self, member: discord.Member, past: bool = False) -> str:
        if (member.is_on_mobile()):
            phone_message = f"""\n\n Also, {LOG_REPLACEMENTS['doer']}"""

            if (past):
                phone_message += " was "
            else:
                phone_message += " is "

            phone_message += "on their \U0001F4F1 *phone*"
        else:
            phone_message = ""

        return phone_message


    # check_on_phone_state(member) Checks if a user is on their phone and the relative time they were on their phone
    def check_on_phone_state(self, before: discord.Member, after: discord.Member) -> bool:
        if ((after.is_on_mobile() and before.is_on_mobile()) or after.is_on_mobile()):
            phone_message = self.check_on_phone(after)
        elif (before.is_on_mobile()):
            phone_message = self.check_on_phone(before, past = True)
        else:
            phone_message = ""

        return phone_message


    # format_replacements(doer, channel) Format the replacements for a message template
    async def format_replacements(self, doer: Union[discord.Member, discord.User], channel: Union[discord.abc.GuildChannel, discord.abc.PrivateChannel],
                                  before_channel: Optional[Union[discord.abc.GuildChannel, discord.abc.PrivateChannel]] = None,
                                  after_channel: Optional[Union[discord.abc.GuildChannel, discord.abc.PrivateChannel]] = None,
                                  victim: Optional[Union[discord.Member, discord.User]] = None) -> Dict[str, str]:
        result = {}
        if (doer is not None):
            doer_name = members.convert_name(doer.id, doer)
            result[LOG_REPLACEMENTS["doer"]] = f"**{doer_name}** ({StringTools.format_mention(doer.id)})"

        if (victim is not None):
            victim_name = members.convert_name(victim.id, victim)
            result[LOG_REPLACEMENTS["victim"]] = f"**{victim_name}** ({StringTools.format_mention(victim.id)})"

        if (channel is not None):
            result[LOG_REPLACEMENTS["channel"]] = f"**{channel.name}** ({StringTools.format_channel(channel.id)})"

        if (after_channel is not None):
            result[LOG_REPLACEMENTS["after_channel"]] = f"**{after_channel.name}** ({StringTools.format_channel(after_channel.id)})"

        if (before_channel is not None):
            result[LOG_REPLACEMENTS["before_channel"]] = f"**{before_channel.name}** ({StringTools.format_channel(before_channel.id)})"

        return result


    # format_spotify(self, current_ac, other_ac, name, artist, album, duration, timestamp) Formats the
    #   string display for spotify data
    def format_spotify(self, current_ac: str, other_ac: bool, name: str, artist: str,
                       album: str, duration: int, timestamp: int) -> str:
        name = StringTools.replace_quotes(name)
        artist = StringTools.replace_quotes(artist)
        ablum = StringTools.replace_quotes(album)

        if (timestamp >= duration):
            timestamp = copy.deepcopy(duration)
        elif (timestamp <= 0):
            timestamp = 0

        # get the state of playing the song
        state = SpotifyActivity.Play.value
        if (current_ac == SPOTIFY_ACTION_BEFORE):
            if (timestamp == duration):
                state = SpotifyActivity.Finished.value
            elif (other_ac):
                state = SpotifyActivity.Skipped.value
            else:
                state = SpotifyActivity.Paused.value



        formatted_timestamp = DateTime.format_time(timestamp)
        formatted_duration = DateTime.format_time(duration)

        result = "```bash\n"
        result += f"Name: \"{name}\"\n"
        result += f"Artist: \"{artist}\"\n"
        result += f"Album: \"{album}\"\n"
        result += f"Timestamp: \"{formatted_timestamp} / {formatted_duration}\"\n"
        result += f"State: \"{state}\"\n"
        result += "```"

        return result


    # on_guild_channel_add_delete(channel, action) Notifies when someone adds or deletes
    #   a channel
    # effects: sends an embed
    async def on_guild_channel_add_delete(self, channel: discord.abc.GuildChannel, action: ChannelAction = ChannelAction.Create):
        # get the activity channel
        server_activity_info = await ChannelTools.get_activity_data(self.client, channel.guild.id)
        if (server_activity_info):
            track_enable = server_activity_info["track_guild_update"]
            activity_channel = server_activity_info["activity_channel"]
            server = server_activity_info["server"]
            timezone = server_activity_info["timezone"]

            #get today's date
            dates = await self.get_log_date(timezone)
            embeded_message = None

            # get the person who changed the guild channel
            if (action == ChannelAction.Create):
                guild_change_audit = await SearchTools.get_recent_audit(channel.guild, None, action = discord.AuditLogAction.channel_create)
            elif (action == ChannelAction.Delete):
                guild_change_audit = await SearchTools.get_recent_audit(channel.guild, None, action = discord.AuditLogAction.channel_delete)

            doer = guild_change_audit.user

            # the message
            message = f"{LOG_REPLACEMENTS['doer']} "
            channel_replace = None

            if (action == ChannelAction.Create):
                message += f"created the **{CHANNEL_TYPE[channel.type]} channel** by the name {LOG_REPLACEMENTS['channel']} on "
                colour = 0x006666
                channel_replace = channel
            elif (action == ChannelAction.Delete):
                message += f"deleted the **{CHANNEL_TYPE[channel.type]} channel** by the name **{channel.name}** on "
                colour = 0x800040

            phone_message = self.check_on_phone(doer, past = True)
            replacements = await self.format_replacements(doer, channel_replace)
            message_template = members.notify_invisible(replacements[LOG_REPLACEMENTS["doer"]], doer, doer.status, message + LOG_REPLACEMENTS["date"] + phone_message)

            await self.log_send(message_template, replacements, track_enable, colour, activity_channel, channel.guild, timezone, dates = dates, thumbnail = str(doer.avatar_url))


    # on_guild_channel_update(before, after) Notifies When someone updates a channel
    # effects: sends an embed
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        # get the activity channel
        server_activity_info = await ChannelTools.get_activity_data(self.client, before.guild.id)

        if (server_activity_info):
            track_enable = server_activity_info["track_guild_update"]
            activity_channel = server_activity_info["activity_channel"]
            server = server_activity_info["server"]
            timezone = server_activity_info["timezone"]

            #get today's date
            dates = await self.get_log_date(timezone)
            embeded_message = None

            # get the doer
            guild_change_audit = await SearchTools.get_recent_audit(before.guild, None, action = discord.AuditLogAction.channel_update)
            doer = guild_change_audit.user
            message = f"{LOG_REPLACEMENTS['doer']} "

            # if change the name of the channel
            if (before.name != after.name):
                message += f" changed the name of the **{CHANNEL_TYPE[before.type]} channel** by the name **{before.name}** to {LOG_REPLACEMENTS['channel']}"
                replacements = await self.format_replacements(doer, after)

            # if change the topic of the text channel
            elif (before.type == discord.ChannelType.text and before.topic != after.topic):
                message += f" changed the topic of the **{CHANNEL_TYPE[before.type]} channel** by the name {LOG_REPLACEMENTS['channel']}"
                replacements = await self.format_replacements(doer, before)
            message += f" on "

            fields = {}
            if (before.type == discord.ChannelType.text and before.topic != after.topic):
                old_topic = before.topic
                new_topic = after.topic

                if (old_topic is not None):
                    old_topic = StringTools.word_replace(before.topic, {"`": "'"})

                if (new_topic is not None):
                    new_topic = StringTools.word_replace(after.topic, {"`": "'"})

                fields["\U0001F3F7 Old Topic"] = f"`{old_topic}`"
                fields["\U0001F3F7 New Topic"]  = f"`{new_topic}`"

            phone_message = self.check_on_phone(doer, past = True)
            message_template = members.notify_invisible(replacements[LOG_REPLACEMENTS["doer"]], doer, doer.status, message + LOG_REPLACEMENTS["date"] + phone_message)

            await self.log_send(message_template, replacements, track_enable, "turquoise", activity_channel, before.guild, timezone, dates = dates, thumbnail = str(doer.avatar_url), fields = fields)


    # on_user_update(before, after) Notifies when someone updates their user
    #   account on discord
    # effects: sends an embed
    async def on_user_update(self, before: discord.User, after: discord.User):
        #convert the name
        name = members.convert_name(before.id, before)
        user_guilds = after.mutual_guilds
        embeded_message = None

        try:
            first_guild = after.mutual_guilds[0]
        except:
            first_guild = None

        #check if the user did the action on their phone
        corresponding_member = await self.searchtools.member_search(before.id, att = SearchAttributes.Id.value)

        if (corresponding_member is not None):
            phone_message = self.check_on_phone(corresponding_member, past = True)

        # if changed their profile pic
        if (before.avatar_url != after.avatar_url):
            message = f"""**{name}** changed their profile pic on """
            image = str(after.avatar_url)
            thumbnail = str(before.avatar_url)

            embeded_message = self.embed.embed_message(None, message, None, "turquoise", None, thumbnail, None, image = image)
            embeded_message = self.embed.add_section(embeded_message, "\U0001F5BC New Profile Picture", f"Here is the new profile picture of **{name}**", inline = False)

        # if changed their username
        elif (before.name != after.name):
            new_name = members.convert_name(after.id, after)
            message = f"""**{name}** changed their username to **{new_name}** on """

        if (embeded_message is not None):
            member = None
            for g in user_guilds:
                if (member is None):
                    member = g.get_member(after.id)

                # get the activity channel to send to
                server_activity_info = await ChannelTools.get_activity_data(self.client, g.id)

                if (server_activity_info):
                    track_enable = server_activity_info["track_activity"]
                    activity_channel = server_activity_info["activity_channel"]
                    server = server_activity_info["server"]
                    timezone = server_activity_info["timezone"]

                    #get today's date
                    dates = await self.get_log_date(timezone)
                    today_format = dates["today_format"]
                    public_today_format = dates["public_today_format"]

                    local_message = members.notify_invisible(name, after, member.status, message + today_format + phone_message)
                    if (embeded_message is None):
                        embeded_message = self.embed.embed_message(None, message + today_format + phone_message,
                                                                   None, "turquoise", None, f"<{after.avatar_url}>", None, image = image)
                    else:
                        embeded_message.description = local_message

                    if (track_enable):
                        await ChannelTools.fixed_activity_send(self.client, activity_channel, g, embed = embeded_message)

            embeded_message.embed.set_author(name = first_guild.name, icon_url = first_guild.icon_url)

            embeded_message.description = members.notify_invisible(name, after, member.status,
                                                                   message + public_today_format + phone_message, record = False)


    # is_typing(id) Checks whether a user is already typing a message in a channel
    def is_typing(self, id: int, channel_id: int) -> bool:
        return (id in USER_TYPING and channel_id == USER_TYPING[id])


    # remove_typing(self, id) Remove the flag that the user is typing a message
    async def remove_typing(self, id: int):
        await asyncio.sleep(TYPING_DELAY)
        try:
            USER_TYPING.pop(id)
        except:
            pass


    # on_typing(channel, user, when) When someone is typing in a channel
    async def on_typing(self, channel: discord.abc.Messageable, user: Union[discord.User, discord.Member],
                        when: datetime.datetime):
        already_typing = self.is_typing(user.id, channel.id)

        if (not already_typing):
            USER_TYPING[user.id] = channel.id

            #convert the name
            name = members.convert_name(user.id, user)
            replacements = {}

            # get the activity channel to send to
            if (isinstance(channel, discord.TextChannel)):
                server_activity_info = await ChannelTools.get_activity_data(self.client, channel.guild.id)
            else:
                server_activity_info = []
                channel_name = ChannelTools.DMCHANNEL.replace("Name", name)
                guild = channel_name
                track_enable = True
                activity_channel = None
                timezone = DateTime.TIMEZONES[discord.VoiceRegion.us_east]
                replacements = await self.format_replacements(user, None)
                message = f", {LOG_REPLACEMENTS['doer']} is typing in the channel, **{channel_name}**"

            if (server_activity_info):
                channel_name = channel.name
                guild = channel.guild
                track_enable = server_activity_info["track_typing"]
                activity_channel = server_activity_info["activity_channel"]
                server = server_activity_info["server"]
                timezone = server_activity_info["timezone"]
                replacements = await self.format_replacements(user, channel)
                message = f", {LOG_REPLACEMENTS['doer']} is typing in the channel, {LOG_REPLACEMENTS['channel']}"

            #get today's date
            dates = await self.get_log_date(timezone, today = when)

            try:
                phone_message = self.check_on_phone(user)
            except:
                phone_message = ""

            message_template = f"On {LOG_REPLACEMENTS['date']}" + message + phone_message
            if (isinstance(user, discord.Member)):
                message_template = members.notify_invisible(replacements[LOG_REPLACEMENTS["doer"]],
                                                            user, user.status, message_template)

            await self.log_send(message_template, replacements, track_enable, 0x9999ff,
                                activity_channel, guild, timezone, dates = dates,
                                thumbnail = str(user.avatar_url), user = user)
            await self.remove_typing(user.id)


    # on_voice_state_update(member, before, after) Notifies when someone changes
    #   their voice state
    # effects: sends an embed
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState):
        #convert the name
        name = members.convert_name(member.id, member)

        server_activity_info = await ChannelTools.get_activity_data(self.client, member.guild.id)

        if (server_activity_info):
            track_enable = server_activity_info["track_voice"]
            activity_channel = server_activity_info["activity_channel"]
            server = server_activity_info["server"]
            timezone = server_activity_info["timezone"]

            #get today's date
            dates = await self.get_log_date(timezone)
            replacements = await self.format_replacements(None, None, before_channel = before.channel,
                                                          after_channel = after.channel, victim = member)

            # get the changes in the voice state
            change_message = ""
            footer_message = ""
            message = f", {LOG_REPLACEMENTS['victim']} "
            colour = 0xff5050
            inverse_colour = 0x99cc00
            transition_colour = 0x6666ff
            thumbnail = str(member.avatar_url)

            # switching channels
            if (before.channel != after.channel):
                change_message += "has "
                if (before.channel is not None and after.channel is not None):
                    change_message += f"switched voice channels from {LOG_REPLACEMENTS['before_channel']} to {LOG_REPLACEMENTS['after_channel']}"
                    colour = transition_colour
                elif (before.channel is None):
                    change_message += f"entered the voice channel, {LOG_REPLACEMENTS['after_channel']}"
                    colour = inverse_colour
                elif (after.channel is None):
                    change_message += f"exited the voice channel, {LOG_REPLACEMENTS['before_channel']}"

            # deafening themselves
            if (before.self_deaf != after.self_deaf):
                change_message += f" has "

                if (before.self_deaf):
                    change_message += "un"
                    colour = inverse_colour
                change_message += "deafened themselves"

            # muting someone
            elif (before.deaf != after.deaf):
                audit_entry = await SearchTools.get_recent_audit(member.guild, None, action = discord.AuditLogAction.member_update)
                doer = audit_entry.user
                doer_name = members.convert_name(doer.id, doer)
                replacements.update(await self.format_replacements(doer_name, None))

                footer_message += f"{doer_name} "

                if (doer.id != member.id):
                    change_message += f"is "
                else:
                    change_message += "has "

                if (before.deaf):
                    change_message += f"un"
                    footer_message += "un"
                    colour = inverse_colour

                change_message += "deafened"
                if (doer.id != member.id):
                    footer_message += f"deafened {name}"
                    change_message += f" by {LOG_REPLACEMENTS['doer']}"
                else:
                    change_message += " themselves"
                    footer_message = ""


            # muting themselves
            if (before.self_mute != after.self_mute):
                change_message += f" has "

                if (before.self_mute):
                    change_message += "un"
                    colour = inverse_colour
                change_message += "muted themselves"

            # muting someone
            elif (before.mute != after.mute):
                audit_entry = await SearchTools.get_recent_audit(member.guild, None, action = discord.AuditLogAction.member_update)
                doer = audit_entry.user
                doer_name = members.convert_name(doer.id, doer)
                replacements.update(await self.format_replacements(doer_name, None))

                footer_message += f"{doer_name} "

                if (doer.id != member.id):
                    change_message += "is "
                else:
                    change_message += "has "

                if (before.mute):
                    change_message += f"un"
                    footer_message += "un"
                    colour = inverse_colour

                change_message += "muted"
                if (doer.id != member.id):
                    footer_message += f"muted {name}"
                    change_message += f" by {LOG_REPLACEMENTS['doer']}"
                else:
                    change_message += " themselves"
                    footer_message = ""

            # streaming a video
            if (before.self_stream != after.self_stream):
                change_message += "has "
                if (before.self_stream):
                    change_message += "ended"
                else:
                    change_message += "started"
                    colour = inverse_colour
                change_message += " streaming"

            # broadcasting a video
            if (before.self_video != after.self_video):
                change_message += " has "
                if (before.self_stream):
                    change_message += "ended"
                else:
                    change_message += "started"
                    colour = inverse_colour
                change_message += " broadcasting a video"

            # make the embed
            if (change_message != ""):
                try:
                    temp_doer = replacements[LOG_REPLACEMENTS['doer']]
                except:
                    replacements[LOG_REPLACEMENTS['doer']] = name

                phone_message = self.check_on_phone(member, past = True)
                message_template = members.notify_invisible(name, member, member.status, f"On {LOG_REPLACEMENTS['date']}" + message + change_message + phone_message)

                footer = {}
                if (footer_message != ""):
                    footer[footer_message] = str(doer.avatar_url)

                await self.log_send(message_template, replacements, track_enable, colour, activity_channel, member.guild, timezone, dates = dates, thumbnail = thumbnail, footer = footer)


    # on_member_update(self,before,after) notifies when someone updates their
    #   server profile
    # effects: sends an embed
    async def on_member_update(self,before: discord.Member,after: discord.Member):
        channel = self.client.get_channel(ChannelTools.DEFAULT_GLOBAL_CHANNEL);

        #convert the name
        name = members.convert_name(after.id, after)

        #check whether the member's attributes has been updates
        member_updated = False

        # get the activity channel to send to
        server_activity_info = await ChannelTools.get_activity_data(self.client, after.guild.id)

        if (server_activity_info):
            track_enable = server_activity_info["track_activity"]
            activity_channel = server_activity_info["activity_channel"]
            server = server_activity_info["server"]
            timezone = server_activity_info["timezone"]

            #get today's date
            dates = await self.get_log_date(timezone)
            footer = {}
            image = None
            colour = None

            #get the first guild to send to global channel
            try:
                first_guild = after.mutual_guilds[0]
            except:
                first_guild = after.guild

            #changing nickname
            if (before.nick != after.nick):
                member_updated = True
                first_guild = None
                # get the person who changed the nickname
                name_change_audit = await SearchTools.get_recent_audit(after.guild, None, action = discord.AuditLogAction.member_update)
                doer = name_change_audit.user
                doer_name = members.convert_name(doer.id, doer)
                message = f"{LOG_REPLACEMENTS['doer']} changed the nickname of "

                if (doer.id == after.id):
                    message += "themself"
                else:
                    message += f"{LOG_REPLACEMENTS['victim']}"
                message += f" from **{before.nick}** to **{after.nick}** on "

                phone_message = self.check_on_phone(doer, past = True)
                replacements = await self.format_replacements(doer, None, victim = after)
                message_template = members.notify_invisible(name, before, before.status, message + LOG_REPLACEMENTS["date"] + phone_message)
                footer = {f"Nickname changed by: {doer_name}": str(doer.avatar_url)}
                colour = 0x00ffcc


                #if someone changes the nickname of the bot
                if (before.id == self.client.user.id and after.nick not in members.BOT_NICKNAMES and doer.id != self.client.user.id):
                    await before.edit(nick = members.NICKNAMES[self.client.user.id])

                    #dm the user to not change the bot's nickname
                    embeded_message = self.embed.bot_embed(None, "\U0001F4A2 My name is not a toy for you to play with, baka!! \U0001F624 \U0001F4A2", "\U0001F4A2 MY NICKNAME IS HAKU AND THAT IS FINALL!!! \U0001F4A2", 0xFF0000, 2, image = {Pics.ImageCategory.Disappointed: 1})
                    await doer.send(embed = embeded_message.embed, file = embeded_message.file)

                    #send a message to all channels notifying that a person editted the bot's nickname
                    for c in after.guild.channels:

                        #if the channel is a text channel in the specified guild
                        if (c.type == discord.ChannelType.text and not ChannelTools.in_activity_channel(c.id, server_id = after.guild.id)):

                            for i in range(BOMB_COUNT):
                                text = ["Baka **__name__**!", "**__name__**, Aho!", "**__name__**, hentai!", "**__name__**, ecchi!", "**__name__** bakayaro!", "Ususai **__name__**!", "Kisama **__name__**", "**__name__**, 死ね!"]
                                title_text = ["BAKA name!!!", "AHO name!!!", "ECCHIII name!!!", "HENTAII name!!!", "JIIIIII (ジーッ)...", "Hmmmfff...", "Kisamaa name!!!", "Bakayaro name!!!", "死ね!!!"]
                                img_category = [Pics.ImageCategory.Disappointed, Pics.ImageCategory.Sad]
                                selected_category = img_category[random.randrange(0, len(img_category))]
                                image_no = random.randrange(0, len(Pics.IMAGE_LIST[selected_category]))

                                #emoji at the end of the message
                                emoji_end_list = ["\U0001F4A2", "\U0001F624", "\U0001F621", "\U0001F620", "\U0001F92C", "\U0001F623", "\U0001F616", "\U0001F622"]

                                #message to put into the embed
                                message = text[random.randrange(len(text))]
                                message = message.replace("name", doer_name)

                                #title of the embed
                                title = title_text[random.randrange(len(title_text))]
                                title = title.replace("name", doer_name)

                                #emoji at the end of the message
                                emoji_end = emoji_end_list[random.randrange(len(emoji_end_list))]

                                #embed the message
                                embeded_message = self.embed.bot_embed(None, f"\U0001F4A2 {message} {emoji_end}", f"\U0001F4A2 \U0001F4A2 {title} \U0001F4A2 \U0001F4A2",
                                                                       0xFF9999, self.embed.RANDOM_NAME, image = {selected_category: image_no})
                                await c.send(embed = embeded_message.embed, file = embeded_message.file)


            #changing status
            elif (before.status != after.status):
                member_updated = True
                if (before.status == discord.Status.offline and before.id in list(members.INVISIBLE_MEMBERS.keys())):
                    before_status = INVISIBLE_TEXT
                    members.INVISIBLE_MEMBERS[before.id] -= 1

                    if (not members.INVISIBLE_MEMBERS[before.id]):
                        members.INVISIBLE_MEMBERS.pop(before.id)
                else:
                    before_status = before.status

                # update the number of people who are invisible
                approx_logged_in_members = await self.get_approx_logged_in_members(after.guild)
                active_members = await self.get_active_members(after.guild)
                new_invisible_members = approx_logged_in_members - active_members
                if (new_invisible_members < 0):
                    new_invisible_members = 0

                first_check = False
                try:
                    server_info = SERVER_INFO_DICT[after.guild.id]
                except:
                    server_info = ServerInfo(approx_logged_in_members, new_invisible_members)
                    SERVER_INFO_DICT[after.guild.id] = server_info
                    first_check = True

                #colour for current changed status
                after_status = after.status
                if (after.status == discord.Status.online):
                    colour = 0x00ff00
                elif (after.status == discord.Status.offline):
                    colour = 0x000000

                    if (new_invisible_members > server_info.invisible_members):
                        members.INVISIBLE_MEMBERS[before.id] = len(after.mutual_guilds)
                        after_status = INVISIBLE_TEXT
                        colour = 0x808080

                elif (after.status == discord.Status.idle):
                    colour = 0xffcc00
                elif (after.status == discord.Status.dnd):
                    colour = 0xff3300

                SERVER_INFO_DICT[after.guild.id].invisible_members = new_invisible_members


                message = f"""{LOG_REPLACEMENTS['doer']} went from being **{before_status}** to **{after_status}** on """

                phone_message = self.check_on_phone_state(before, after)
                message_template = message + LOG_REPLACEMENTS["date"] + phone_message
                replacements = await self.format_replacements(after, None)


            #changing roles
            elif (before.roles != after.roles):
                first_guild = None
                member_updated = True
                update_entry = await self.get_updater(before.guild, discord.AuditLogAction.member_role_update)
                doer = update_entry.user
                doer_name = members.convert_name(doer.id, doer)

                before_roles = before.roles[1:]
                after_roles = after.roles[1:]

                changed_roles = DataGroups.set_diff(before_roles, after_roles)
                deleted_roles = changed_roles["a"]
                added_roles = changed_roles["b"]

                if (not deleted_roles and added_roles):
                    message = f"""{LOG_REPLACEMENTS['doer']} gave these roles to {LOG_REPLACEMENTS['victim']} on """
                    colour = 0x009999
                elif (deleted_roles and not added_roles):
                    message = f"""{LOG_REPLACEMENTS['doer']} removed these roles from {LOG_REPLACEMENTS['victim']} on """
                    colour = 0xff0066
                else:
                    message = f"""{LOG_REPLACEMENTS['doer']} updated some roles for {LOG_REPLACEMENTS['victim']} on """
                    colour = 0xCC99FF

                role_message = ""
                if (deleted_roles):
                    role_message += "\n\n**Previous Roles** \U0001F4E4"

                for m in deleted_roles:
                    role_message += f"""\n{m} ({StringTools.format_role_mention(m.id)})"""

                if (added_roles):
                    role_message += "\n\n**New Roles:** \U0001F4E5"

                for m in added_roles:
                    role_message += f"""\n{m} ({StringTools.format_role_mention(m.id)})"""

                footer[f"Roles changed by: {doer_name}"] = str(doer.avatar_url)

                phone_message = self.check_on_phone(doer, past = True)
                replacements = await self.format_replacements(doer, None, victim = after)
                message_template =  members.notify_invisible(replacements[LOG_REPLACEMENTS["doer"]], doer, doer.status, message + LOG_REPLACEMENTS["date"] + phone_message)
                message_template += role_message


            #changing activities
            elif (before.activities != after.activities):
                today = DateTime.get_current_dt(utc = True)

                before_list = set(before.activities)
                after_list = set(after.activities)
                before_display = True;
                after_display = True;
                before_len = 0
                after_len = 0

                #check if the activites do not contain custom statuses
                if before_list:
                    for a in before_list:
                        if (a.type == discord.ActivityType.custom):
                            before_list.remove(a)

                            if (not before_list):
                                before_display = False;
                            break
                else:
                    before_display = False

                if after_list:
                    for a in after_list:
                        if (a.type == discord.ActivityType.custom):
                            after_list.remove(a)

                            if (not after_list):
                                after_display = False
                            break
                else:
                    after_display = False

                changed_activities = DataGroups.lst_diff(before_list, after_list, equal = self.activity_eq)
                before_ac = changed_activities["a"]
                after_ac = changed_activities["b"]

                #check if both lists are emtpy
                if not before_ac:
                    before_display = False

                if not after_ac:
                    after_display = False

                spotify_before = spotify_after = False

                for a in before_ac:
                    if (a.type == discord.ActivityType.listening and a.name == "Spotify"):
                        spotify_before = True
                        spotify_bf_ac = a
                        spotify_bf_alb_image = a.album_cover_url
                        spotify_bf_data = {"name": a.title, "artist": a.artist, "album": a.album,
                                           "duration": int(a.duration.total_seconds()),
                                           "timestamp": int((a.duration - (a.end - today)).total_seconds())}
                    else:
                        spotify_before = False

                for a in after_ac:
                    if (a.type == discord.ActivityType.listening and a.name == "Spotify"):
                        spotify_after = True
                        spotify_af_ac = a
                        spotify_af_alb_image = a.album_cover_url
                        spotify_af_data = {"name": a.title, "artist": a.artist, "album": a.album,
                                           "duration": int(a.duration.total_seconds()),
                                           "timestamp": int((a.duration - (a.end - today)).total_seconds())}

                    else:
                        spotify_after = False

                if (spotify_before):
                    spotify_bf_msg = self.format_spotify(SPOTIFY_ACTION_BEFORE, spotify_after, spotify_bf_data["name"],
                                                         spotify_bf_data["artist"], spotify_bf_data["album"],
                                                         spotify_bf_data["duration"], spotify_bf_data["timestamp"])

                if (spotify_after):
                    spotify_af_msg = self.format_spotify(SPOTIFY_ACTION_AFTER, spotify_before, spotify_af_data["name"],
                                                         spotify_af_data["artist"], spotify_af_data["album"],
                                                         spotify_af_data["duration"], spotify_af_data["timestamp"])

                #message and activities to be listed
                ac_message = ""

                #make the message to be printed
                if(before_display == True):
                    ac_message += f", {LOG_REPLACEMENTS['doer']} has stopped playing:\n"
                    for b in before_ac:
                        ac_message += f"*{b.name}*\n"

                if (before_display):
                    ac_message += "\n"

                if (spotify_before is not None and spotify_before):
                    ac_message += f"{LOG_REPLACEMENTS['doer']} was listening to:\n{spotify_bf_msg}"

                if (spotify_before):
                    ac_message += "\n"

                if (after_display == True):
                    if (ac_message == ""):
                        ac_message += ", "

                    ac_message += f"{LOG_REPLACEMENTS['doer']} has started playing:\n"
                    for a in after_ac:
                        ac_message += f"*{a.name}* \n"

                if (after_display):
                    ac_message += "\n"

                if (spotify_after is not None and spotify_after):
                    ac_message += f"{LOG_REPLACEMENTS['doer']} is listening to:\n{spotify_af_msg}"


                main_action = None
                main_ac_icon = None
                main_ac = None
                main_ac_name = None
                main_ac_image = None

                if (before_display):
                    main_ac = before_ac[0]
                    main_action = ACTIONS[main_ac.type]
                    main_ac_name = main_ac.name

                if (after_display):
                    main_ac = after_ac[0]
                    main_action = ACTIONS[main_ac.type]
                    main_ac_name = main_ac.name

                if (spotify_before or spotify_after):
                    main_action = ACTIONS[discord.ActivityType.listening]
                    main_ac_name = "Spotify"
                    main_ac_icon = StringTools.get_link(Pics.get_image_link(Pics.ImageCategory.Logos, 0))

                    if (spotify_after):
                        main_ac = spotify_af_ac
                        main_ac_image = f"<{spotify_af_alb_image}>"
                    else:
                        main_ac = spotify_bf_ac
                        main_ac_image = f"<{spotify_bf_alb_image}>"

                # get icon if not a spotify activity
                if (not spotify_before and not spotify_after):
                    if (isinstance(main_ac, discord.Activity)):
                        main_ac_icon = main_ac.large_image_url

                        if (main_ac_icon is None):
                            main_ac_icon = main_ac.small_image_url

                #pick the color
                if (before_display == False and after_display == True):
                    colour = 0x99FF33
                elif (before_display == True and after_display == False):
                    colour = 0xFF6600
                else:
                    colour = 0x00FFFF

                phone_message = self.check_on_phone_state(before, after)

                # send the message
                if (after_display == True or before_display == True):
                    member_updated = True
                    replacements = await self.format_replacements(after, None)

                    message_template = members.notify_invisible(replacements[LOG_REPLACEMENTS["doer"]], before, before.status ,f"On {LOG_REPLACEMENTS['date']}" + ac_message + phone_message)
                    footer[f"{main_action}: {main_ac_name}"] = main_ac_icon
                    image = main_ac_image


            if (member_updated):
                await self.log_send(message_template, replacements, track_enable, colour, activity_channel, after.guild, timezone, dates = dates, thumbnail = str(after.avatar_url), image = image, footer = footer, first_guild = first_guild)


    # generate_member_pg(current_page, max_page, kwargs) Generates the
    #   current page for displaying the members in the server
    # requires: page >= 1
    #           max_page_num >= 1
    async def generate_member_pg(self, page: int, max_page_num: int, kwargs: Dict[str, Any]) -> discord.Embed:
        ctx = kwargs["ctx"]
        role_name = kwargs["role_name"]
        member_status = kwargs["member_status"]
        guild = kwargs["guild"]
        author = kwargs["author"]
        identity_lst = kwargs["identity_lst"]

        embed_description = f"Here are all the members of **{role_name}**"
        lower_member_status = member_status.lower()
        if (lower_member_status != MemberActivity.All.value):
            embed_description += f" who are currently **{lower_member_status}**"
        embed_description += f" in the server, **{guild.name}**"

        if (lower_member_status == MemberActivity.Invisible.value or lower_member_status == MemberActivity.All.value or lower_member_status == MemberActivity.Offline.value):
            embed_description += "\n\n**Note \U0001F4DD**"

            if (lower_member_status != MemberActivity.Offline.value):
                embed_description += "\n-*Not all invisible members are necessarily listed below*"
            if (lower_member_status != MemberActivity.Invisible.value):
                embed_description += "\n-*Some offline members may actually be invisible*"

        embeded_message = self.embed.context_embed(ctx, embed_description, "Member Search Results", 0xCC99FF, f"{ctx.guild.icon_url}", name = author)
        embeded_message = self.embed.add_footer(ctx, embeded_message, f"\U0001F4C3 pg:  {page} / {max_page_num}")

        for i in identity_lst:
            mem_count = 0
            message = "```css\n"

            identity_len = len(identity_lst[i])
            if (identity_len):
                indices = Pagination.get_indices(page, MEMBERS_PER_PAGE, identity_len)

                start_index = indices["start_index"]
                end_index = indices["end_index"]
                mem_count = start_index

                for j in range(start_index, end_index):
                    mem_count += 1
                    current_member = identity_lst[i][j]
                    name = members.convert_name(current_member.member.id, current_member.member)
                    message += f"{mem_count}: {STATUS_ICONS[current_member.activity]}  {name}"

                    if (self.client.user is not None and current_member.member.id == self.client.user.id):
                        message += "  <-- BEST GIRL!!! \U0001F970 \U0001F496"
                    message += "\n"
            else:
                message += f"\U0000274C  No {i.value[2:]} Found!\n"

            message += "```"
            embeded_message = self.embed.add_section(embeded_message, i.value, message)

        return embeded_message



    # members(ctx, member_status, member_role, page, server) list members of the server
    async def members(self, ctx: commands.Context, member_status: str = MemberActivity.Active.value,
                      member_role: str = EVERYONE_ROLE, page: str = "1", server: str = StringTools.NONE):
        #author who invoked command
        author = members.convert_name(ctx.author.id, ctx.author)

        #determine if error occured
        error = False

        # validate the data
        error = await ChannelTools.validate_private_channel(ctx, self.client, error, author, "search members")
        error = await ChannelTools.validate_activity_channel(ctx, error)
        error, page = await self.validate.validate_natural(ctx, error, page, "page")
        error, guild = await self.searchtools.validate_server(ctx, error, server, "find members")
        error, role = await self.searchtools.validate_role(ctx, error, member_role, guild, "member_role")

        #list containing all members with the specified status
        status_filter = [];

        #sort by status and role
        if (not error):
            #list all members
            if (member_status.lower() == MemberActivity.All.value):
                status_filter = members.filter(guild.members, self.is_role, desired_role = role)

            #list all the online members
            elif (member_status.lower() == MemberActivity.Online.value):
                status_filter = members.filter(guild.members, self.check_member_status, discord.Status.online, desired_role = role)

            #list all the offline members
            elif (member_status.lower() == MemberActivity.Offline.value):
                status_filter = members.filter(guild.members, self.check_member_status, discord.Status.offline, desired_role = role)

            #list all the idle members
            elif (member_status.lower() == MemberActivity.Idle.value):
                status_filter = members.filter(guild.members, self.check_member_status, discord.Status.idle, desired_role = role)

            #list all the do not disturb members
            elif (member_status.lower() == MemberActivity.Dnd.value):
                status_filter = members.filter(guild.members, self.check_member_status, discord.Status.dnd, desired_role = role)

            #list all the members who are currently active or "online"
            elif (member_status.lower() == MemberActivity.Active.value):
                status_filter = members.filter(guild.members, self.is_active, desired_role = role)

            elif (member_status.lower() == MemberActivity.Invisible.value):
                status_filter = members.filter(guild.members, self.check_member_invisible, discord.Status.offline, desired_role = role)

            else:
                error = True
                embeded_message = Error.display_error(self.client, 10, element = member_status, group = "MemberActivity", parameter = "member_status")
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

        #sort the filtered members by their identity
        identity_lst = {MemberIdentity.Member: [], MemberIdentity.Bot: [], MemberIdentity.Cute_Girl: []}

        invisible_member_ids = list(members.INVISIBLE_MEMBERS.keys())
        for m in status_filter:
            is_invisible = (m.id in invisible_member_ids)
            if (is_invisible):
                activity = discord.Status.invisible
            else:
                activity = m.status

            member_info = MemberActivityInfo(m, activity)

            if (self.client.user is not None and m.id == self.client.user.id):
                identity_lst[MemberIdentity.Cute_Girl].append(member_info)
            elif (m.bot):
                identity_lst[MemberIdentity.Bot].append(member_info)
            else:
                identity_lst[MemberIdentity.Member].append(member_info)

        #get the total page number
        identity_lens = [len(identity_lst[i]) for i in identity_lst]
        max_page_num = Pagination.get_total_pages(MEMBERS_PER_PAGE, DataGroups.get_max(identity_lens))

        if (not error and page > max_page_num):
            error = True
            embeded_message = Error.display_error(self.client, 8, type_article = "an", correct_type = "integer", value = f"{max_page_num}", parameter = "page")
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

        #embed the message
        if (not error):
            role_name = role
            if (not isinstance(role, str)):
                role_name = role.name

            generate_member_pg_kwargs = {"ctx": ctx, "role_name": role, "member_status": member_status, "guild": guild, "author": author, "identity_lst": identity_lst}
            embeded_message = await self.generate_member_pg(page, max_page_num, generate_member_pg_kwargs)
            paginated_components = Pagination.make_page_buttons(page, max_page_num)
            message = await ctx.send(embed = embeded_message.embed, file = embeded_message.file, components = paginated_components)
            await Pagination.page_react(self.client, message, page, max_page_num, self.generate_member_pg, generate_member_pg_kwargs)


    # your_nickname(self, ctx, nickname_no) Changes the bot's nickname
    # effects: sends an embed
    async def your_nickname(self, ctx: commands.Context, nickname_no: str):
        #author who invoked command
        author = members.convert_name(ctx.author.id, ctx.author)

        error = False
        error = await ChannelTools.validate_private_channel(ctx, self.client, error, author, "change my nickname")
        error = await ChannelTools.validate_activity_channel(ctx, error)
        error, nickname_no = await self.validate.validate_natural(ctx, error, nickname_no, "nickname_no", check_equal = True)
        if (not await self.validate.check_inbetween(ctx, nickname_no, "prefix_name", 1, len(members.BOT_NICKNAMES), verbose = (not error))):
            error = True

        if (not error):
            bot_member = await ctx.guild.fetch_member(self.client.user.id)
            changed_nickname = members.BOT_NICKNAMES[nickname_no - 1]
            await bot_member.edit(nick = changed_nickname)
            embeded_message = self.embed.bot_embed(ctx, f"I changed my nickname to `{changed_nickname}`!", "My Nickname Changed", "light-pink", 1, image = {Pics.ImageCategory.Default: 0})
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
