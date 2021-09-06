import asyncio, discord
from discord.ext import commands
from database.database import Database, DbItem
import tools.members as Members
import tools.error as Error
from typing import List, Optional, Dict, Any, Union

DMCHANNEL = f"{Members.BOT_NICKNAMES[1]}'s DMs with Name"
ACTIVITY_CHANNEL = "ACTIVITY"
CHANNEL_TYPES = [ACTIVITY_CHANNEL]
AC_CHANGE = {}


# ChannelStats: The information regarding a type of channel in the database
class ChannelStats(DbItem):
    def __init__(self, name: str, index: int, col: str):
        super().__init__(name, index, "Server_Accounts", col)


CHANNEL_INFO = {ACTIVITY_CHANNEL: ChannelStats('Activity-Log-\U0001F4D2 \U0000270F', 8, "activity_channel")}


# get_tracked_channel(server_id) Retrieves a list of all channel ids
#   or the id of the channel to the server with the id, 'server_id'
def get_tracked_channel(channel: str, server_id: Optional[int] = None) -> List[int]:
    channel_lst = None
    columns_needed = [f"{channel}"]

    if (server_id is None):
        channel_lst = Database.list_select(f"{channel}", "Server_Accounts")
        return channel_lst
    else:
        channel_lst = Database.list_select(f"{channel}", "Server_Accounts", {"id":f"{server_id}"})

        if (not channel_lst):
            channel = []
        else:
            channel = channel_lst[0]
        return channel


# in_tracked_channel(channel_id, server_id) Determines whether the channel
#   represented by 'channel_id' is a tracked channel
def in_tracked_channel(channel_id: int, channel_name: str, server_id:Optional[int] = None) -> bool:
    if (server_id is None):
        channel_lst = get_tracked_channel(channel_name, server_id)
        return (channel_id in channel_lst)
    else:
        channel = get_tracked_channel(channel_name, server_id)
        return (channel_id == channel)


# get_track_ch_data(client, server_id, channel_stats, columns) Retrieves data
#   about a certain tracked channel
async def get_track_ch_data(client: discord.Client, server_id: int, channel_stats: ChannelStats, columns: Dict[str, int]) -> Dict[str, Any]:
    server_channel_info = Database.in_table(server_id, "id", "Server_Accounts")
    track_enable = None
    activity_channel = None
    server = None
    result = {}

    if (server_channel_info is not None):
        for c in columns:
            result[c] = server_channel_info[0][columns[c]]
        tracked_channel = server_channel_info[0][channel_stats.index]
        server = client.get_guild(server_id)
        result["server"] = server

        try:
            tracked_channel = await client.fetch_channel(tracked_channel)
        except discord.NotFound:
            activity_channel = await update_tracked_channel(client, server, channel_stats, server_channel_info = server_channel_info, channel_exist = False)

    return result


# change_tracked_ch_id(new_channel_id, server_id) Updates the id for the tracked channel
# effects: writes into the database
def change_tracked_ch_id(channel_stats: ChannelStats, new_channel_id: int, server_id: int):
    Database.update({f"{channel_stats.col}": f"{new_channel_id}"}, "Server_Accounts", conditions= {"id":f"{server_id}"})


# update_tracked_channel(client, server) Creates a new channel if the
#   existing channel of the server does not exist
# effects: makes another channel
async def update_tracked_channel(client, server: discord.Guild, channel_stats: ChannelStats,
                                 server_channel_info: Optional[List[List[Any]]] = None,
                                 channel_exist: Optional[bool] = None) -> discord.TextChannel:
    if (server_channel_info is None):
        server_channel_info = Database.in_table(server.id, "id", "Server_Accounts")

    if (server_channel_info is not None):
        server_channel_info = server_channel_info[0]
        if (channel_exist is None):
            activity_channel = client.get_channel(server_channel_info[channel_stats.index])

            if (activity_channel is not None):
                channel_exist = True
            else:
                channel_exist = False

        try:
            AC_CHANGE[server.id]
            new_activity_channel = await client.fetch_channel(server_channel_info[channel_stats.index])

        except KeyError:
            if (not channel_exist):
                new_activity_channel = await server.create_text_channel(channel_stats.name)
                change_tracked_ch_id(channel_stats, new_activity_channel.id, server.id)
            else:
                new_activity_channel = client.get_channel(server_channel_info[channel_stats.index])

        except discord.NotFound:
            if (not channel_exist and AC_CHANGE[server.id] == server_channel_info[channel_stats.index]):
                new_activity_channel = await server.create_text_channel(channel_stats.name)
            elif (not channel_exist):
                new_activity_channel = client.get_channel(AC_CHANGE[server.id])
            else:
                new_activity_channel = client.get_channel(server_channel_info[channel_stats.index])

            if (not channel_exist):
                change_tracked_ch_id(channel_stats, new_activity_channel.id, server.id)

    AC_CHANGE[server.id] = new_activity_channel.id
    return new_activity_channel


# fixed_channel_send(client, channel, server, channel_type, channel_stats, embed) Sends a message to a channel
#   remembered by the bot
# effects: sends a message and may make another channel
async def fixed_channel_send(client, channel: Union[discord.TextChannel, int], server: discord.Guild,
                             channel_type: str, channel_stats:ChannelStats ,
                             embed: Optional[discord.Embed] = None, msg: Optional[str] = None) -> discord.TextChannel:
    try:
        await channel.send(content = msg, embed = embed)
        new_channel = channel
    except (discord.HTTPException, AttributeError) as e:
        if (channel_type in CHANNEL_TYPES):
            new_channel = await update_tracked_channel(client, server, channel_stats)

        await new_channel.send(content = msg, embed = embed)
    return new_channel


# in_activity_channel(channel_id, server_id) Determines whether the activity channel
#   represented by 'channel_id' is an activity channel
def in_activity_channel(channel_id: int, server_id: Optional[int] = None) -> bool:
    return (in_tracked_channel(channel_id, CHANNEL_INFO[ACTIVITY_CHANNEL].col, server_id))


# get_track_ch_data(client, server_id) Retrieves data about a certain activity channel
async def get_activity_data(client: discord.Client, server_id: int) -> Dict[str, Any]:
    result = await get_track_ch_data(client, server_id, CHANNEL_INFO[ACTIVITY_CHANNEL],
                                    {"activity_channel": CHANNEL_INFO[ACTIVITY_CHANNEL].index, "track_activity": 3, "track_message": 4, "track_guild_update": 5, "track_voice": 6, "track_typing": 7, "timezone": 10})

    if (result):
        result["activity_channel"] = client.get_channel(result["activity_channel"])
    return result


# update_tracked_channel(client, server) Creates a new activity channel if the
#   existing channel of the server does not exist
# effects: may create a channel
async def update_activity_channel(client, server: discord.Guild, server_channel_info: Optional[ChannelStats] = None,
                                  channel_exist: Optional[bool] = None) -> discord.TextChannel:
    return await update_tracked_channel(client, server, CHANNEL_INFO[ACTIVITY_CHANNEL], server_channel_info, channel_exist)


# fixed_activity_send(client, channel, server, channel_type, embed) Sends a message to an activity channel
#   remembered by the bot
async def fixed_activity_send(client: discord.Client, channel: Union[discord.TextChannel, int], server: discord.Guild,
                              embed: Optional[discord.Embed] = None, msg: Optional[str] = None) -> discord.TextChannel:
    return await fixed_channel_send(client, channel, server, ACTIVITY_CHANNEL, CHANNEL_INFO[ACTIVITY_CHANNEL], embed, msg)


# get_dm_channel(name) Retrieves the name of the dm channel of a certain member
def get_dm_channel(name: str) -> str:
    return DMCHANNEL.replace("Name", name)


# validate_activity_channel(ctx, error) Disables the function if a command is
#   invoked in an activity channel
async def validate_activity_channel(ctx: commands.Context, error: bool) -> bool:
    if (not error and ctx.guild is not None and in_activity_channel(ctx.channel.id, server_id = ctx.guild.id)):
        error = True

    return error


# validate_private_channel(ctx, client, error, name, action) Checks whether the
#   invoked command is in a private channel
# effects: may send an embed
async def validate_private_channel(ctx: commands.Context, client: discord.Client,
                                    error: bool, name: str, action: str) -> bool:
    if (not error and ctx.guild is None):
        dm_channel = get_dm_channel(name)
        embeded_message = Error.display_error(client, 9, channel = dm_channel, action = action, guild = dm_channel)
        await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
        error = True

    return error
