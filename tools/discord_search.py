import discord, enum
from discord.ext import commands
from database.database import Database
from tools.embed import Embed
from tools.string import StringTools
from tools.validate import Validate
import tools.error as Error
import tools.members as Members
from typing import Any, Callable, Optional, Dict, Union, List

SEARCH_BY_ID = "id"
SEARCH_BY_NAME = "name"
SEARCH_BY_TAG = "tag"
EVERYONE_ROLE = ["everyone", "@everyone"]


# possible attributes to search by
class SearchAttributes(enum.Enum):
    Name = "name"
    Id = "id"
    DictByVal = "dict by val"

#Useful Tools
class SearchTools(commands.Cog):

    #constructor
    def __init__(self, client: discord.Client):
        self.client = client
        self.embed = Embed(client)
        self.validate = Validate(client)


    # search(self, group, item) Simple search for by first keyword for a
    # particular item in a group
    # note: item could be a 'member', 'server', etc...
    #       group could be a 'member list', 'server list', etc...
    async def search(self, group: Any, item: Any, att: str = SearchAttributes.Name.value,
                     condition: Optional[Callable[[Any, Dict[str, Any]], bool]] = None,
                     condition_kwargs: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        item_found = False;
        founded_item = None;
        for i in group:
            current_item = None
            search = None

            if (att == SearchAttributes.Name.value):
                current_item = i.name.lower()
                search = (current_item.find(item.lower()) == 0)
            elif (att == SearchAttributes.Id.value):
                current_item = i.id
                search = (current_item == item)
            elif (att == SearchAttributes.DictByVal.value):
                current_item = group[i].lower()
                search = (current_item.find(item.lower()) == 0)

            # checks if the item meets the listed condition
            if (condition is None):
                met_condition = True
            else:
                met_condition = condition(i, condition_kwargs)

            if ((search is not None) and search and met_condition):
                founded_item = i;
                item_found = True
                break

        if (item_found):
            return founded_item
        else:
            return None


    # server_search(self, ctx, item) Searches for a particular server
    async def server_search(self, item: Union[int, str], att: str = SearchAttributes.Name.value) -> Optional[discord.Guild]:
        group = self.client.guilds

        if (att == SearchAttributes.Name.value):
            result = await self.search(group, item)
        elif (att == SearchAttributes.Id.value):
            result = await self.search(group, item, att)
        return result

    # member_search(self, ctx, item) Searches for a particular member
    async def member_search(self, item: Union[int, str], server: Optional[discord.Guild] = None,
                            att: str = SearchAttributes.Name.value,
                            condition: Optional[Callable[[Any, Dict[str, Any]], bool]] = None, condition_kwargs: Optional[Dict[str, Any]] = None) -> Optional[discord.Member]:
        if (server is None):
            group = self.client.get_all_members()
        else:
            group = server.members

        if (att == SearchAttributes.Name.value):
            result = await self.search(group, item, condition = condition,
                                       condition_kwargs = condition_kwargs)
        elif (att == SearchAttributes.Id.value):
            result = await self.search(group, item, att, condition = condition,
                                       condition_kwargs = condition_kwargs)

        return result

    # member_search(self, ctx, item) Searches for a particular channel in a
    #   server
    async def channel_search(self, item: Union[int, str], server: Optional[discord.Guild] = None,
                             att: str = SearchAttributes.Name.value) -> discord.abc.GuildChannel:
        if (server is None):
            group = self.client.get_all_channels()
        else:
            group = server.channels

        if (att == SearchAttributes.Name.value):
            result = await self.search(group, item)
        elif (att == SearchAttributes.Id.value):
            result = await self.search(group, item, att)
        return result


    # ch_sev_search(self, ctx, search_channel, search_guild) Searches both the
    #   channel 'search_channel' and the server, 'search_guild'
    async def ch_sev_search(self, ctx: commands.Context, search_channel: Optional[Union[int, str]] = None,
                            search_guild: Optional[Union[int, str]] = None,
                            att: str = SearchAttributes.Name.value) -> Dict[str, Union[Optional[discord.abc.GuildChannel], Optional[discord.Guild]]]:
        channel = None
        server = None
        #get the channel of the command that was sent
        if ((search_channel is None) and (search_guild is None)):
            channel = ctx.message.channel
            server = ctx.message.guild

        elif(search_guild is None):
            server = ctx.message.guild
            if (att == SearchAttributes.Name.value):
                channel = await self.channel_search(search_channel, server)
            elif (att == SearchAttributes.Id.value):
                channel = await self.channel_search(search_channel, server, att = att)
        else:
            if (att == SearchAttributes.Name.value):
                server = await self.server_search(search_guild);
            elif (att == SearchAttributes.Id.value):
                server = await self.server_search(search_guild, att = att)

            #get the channel if the guild is found
            if (server is not None):

                # if no channel is specified for the guild, get the first
                #   text channel available
                if (search_channel is None):
                    #get the list of channels on the server
                    channel_list = server.channels

                    for c in channel_list:
                        if (c.type == discord.ChannelType.text):
                            channel = c
                            break

                else:
                    channel = await self.channel_search(search_channel, server, att = att)

        return {"channel": channel, "server": server}


    # get_server(self, search_guild) Find the available server to the input
    #   string 'search_guild'
    async def get_server(self, ctx: commands.Context, search_guild: str) -> Dict[str, Union[bool, Optional[discord.Guild], Optional[str]]]:
        dm = False
        server = StringTools.convert_none(search_guild)
        server_is_int = None

        # get the guild
        if (server is not None):
            server_is_int = await self.validate.check_integer(ctx, search_guild, "search_guild", verbose = False)
        else:
            server = ctx.guild
            if (server is None):
                dm = True
            return {"dm": dm, "server": server, "guild_search_type": None}

        # determine the type that is being searched
        guild_search_type = SEARCH_BY_ID
        if (server_is_int is None):
            guild_search_type = SEARCH_BY_NAME

        if (server_is_int is not None):
            server = self.client.get_guild(int(server))
            return {"dm": dm, "server": server, "guild_search_type": guild_search_type}
        else:
            server = await self.server_search(server)
            return {"dm": dm, "server": server, "guild_search_type": guild_search_type}


    # get_ch_and_server(self, search_channel, search_guild) Find the available
    #   channel and server to the string input 'search_channel' and 'search_guild'
    async def get_ch_and_server(self, ctx: commands.Context, search_channel: str, search_guild: str) -> Dict[str, Union[bool, Optional[discord.abc.GuildChannel], Optional[discord.Guild], str]]:
        dm = False
        channel = StringTools.convert_none(search_channel)
        server = StringTools.convert_none(search_guild)
        channel_is_int = None
        server_is_int = None

        # check if the search channel or guild are ids
        if (channel is not None):
            channel_is_int = await self.validate.check_integer(ctx, channel, "search_channel", verbose = False)
            channel_is_tag = StringTools.is_tag(channel)

            if (channel_is_tag):
                channel = StringTools.get_tag_id(channel)
                channel_is_int = int(channel)

        if (server is not None):
            server_is_int = await self.validate.check_integer(ctx, search_guild, "search_guild", verbose = False)

        # if both server and channel for the search are specified with at least 1 integer parameter
        if (server is not None and channel is not None and not(channel_is_int is None and server_is_int is None)):
            if (channel_is_int is not None and server_is_int is not None):
                search_result = await self.ch_sev_search(ctx, int(channel), int(server), att = SearchAttributes.Id.value)
                channel = search_result["channel"]
                server = search_result["server"]

            elif (server_is_int is not None):
                server = self.client.get_guild(int(server))

                if (server is not None):
                    channel = await self.channel_search(channel, server = server, att = SearchAttributes.Name.value)
                else:
                    channel = None

            elif (channel_is_int is not None):
                channel = await self.client.fetch_channel(int(channel))

                if (channel is not None and channel.type == discord.ChannelType.text):
                    server = channel.guild
                else:
                    server = None

        # if only server is sepcified with an id parameter
        elif (server is not None and server_is_int is not None):
            search_result = await self.ch_sev_search(ctx, channel, int(server), att = SearchAttributes.Id.value)
            channel = search_result["channel"]
            server = search_result["server"]

        # if only channel is specified with an id parameter
        elif (channel is not None and channel_is_int is not None):
            search_result = await self.ch_sev_search(ctx, int(channel), server, att = SearchAttributes.Id.value)
            channel = search_result["channel"]
            server = search_result["server"]

        else:
            search_result = await self.ch_sev_search(ctx, channel, server)
            channel = search_result["channel"]
            server = search_result["server"]

        # identify whether channel sent is a dm channel
        if (channel is not None and channel.type == discord.ChannelType.private):
            dm = True
            server = "dm"

        # get the type of search for the server and channel
        channel_search_type = SEARCH_BY_ID
        guild_search_type = SEARCH_BY_ID

        if (channel_is_int is None):
            channel_search_type = SEARCH_BY_NAME

        if (server_is_int is None):
            guild_search_type = SEARCH_BY_NAME

        return {"dm": dm, "channel": channel, "server": server, "guild_search_type": guild_search_type, "channel_search_type": channel_search_type}


    # get_member(query) Retrieves a member based off their tag, id, or name
    async def get_member(self, query: str, condition: Optional[Callable[[Any, Dict[str, Any]], bool]] = None, condition_kwargs: Dict[str, Any] = None) -> Dict[str, Union[str, discord.User, discord.Member]]:
        is_nat = await self.validate.check_natural(None, query, "query", verbose = False)
        query_is_tag = StringTools.is_tag(query)
        search_type = SEARCH_BY_NAME

        # search by id
        if (is_nat is not None):
            search_type = SEARCH_BY_ID
            result = self.client.get_user(int(query))
            if (condition is not None and not condition(result, condition_kwargs)):
                result = None
            return {"member_search_type": search_type, "member": result}

        # search by tag
        elif (query_is_tag):
            search_type = SEARCH_BY_TAG
            tag_id = StringTools.get_tag_id(query)
            result = self.client.get_user(int(tag_id))
            if (condition is not None and not condition(result, condition_kwargs)):
                result = None
            return {"member_search_type": search_type, "member": result}

        # search by string
        else:
            result = await self.member_search(query, condition = condition, condition_kwargs = condition_kwargs)

            if (result is None):
                result = await self.search(Members.NICKNAMES, query, att = SearchAttributes.DictByVal.value,
                                           condition = condition, condition_kwargs = condition_kwargs)

                if (result is not None):
                    result = self.client.get_user(result)

            return {"member_search_type": search_type, "member": result}



    # get_recent_audit(guild, condition, action) Gets the most recent action
    #   that meets 'condition' in the audit log
    @classmethod
    async def get_recent_audit(cls, guild: discord.Guild, condition: Optional[Callable[[discord.AuditLogEntry], bool]],
                               action: Optional[discord.AuditLogAction] = None) -> discord.AuditLogEntry:
        result = None

        async for entry in guild.audit_logs(limit=1, action=action):
            if (condition is None):
                valid = entry
            else:
                valid = condition(entry)

            if (valid):
                result = entry
                break

        return result


    # get_announcment_channel(guild) Finds the channel to send announcmenets to
    #   'guild'
    @classmethod
    def get_announcment_channel(cls, guild: discord.Guild) -> discord.TextChannel:
        channel = None
        channel_search_order = [guild.system_channel, guild.public_updates_channel, guild.rules_channel]

        for c in channel_search_order:
            if (c is not None):
                return c

        channel = guild.channels[0]
        return channel


    # get_last_message(self, channel) Retrieves the last existing message from the channel
    async def get_last_message(self, channel: Union[discord.TextChannel, discord.DMChannel]) -> Optional[discord.Message]:
        msg = None

        while True:
            try:
                msg_lst = await channel.history(limit = 1, before = msg).flatten()
                if (msg_lst):
                    msg = msg_lst[0]
            except:
                continue
            else:
                break

        return msg


    # in_server(self, member, kwargs) Determines if 'member' is a part of 'server'
    def in_server(self, member: Union[discord.Member, discord.User], kwargs: Dict[str, Any]) -> bool:
        result = None
        if (isinstance(member, discord.Member)):
            result = (member.guild.id == kwargs["guild"].id)

        # fetch the user by their id

        elif (isinstance(member, discord.User)):
            user_guilds = member.mutual_guilds
            if (kwargs["guild"] in user_guilds):
                result = True
            else:
                result = False
        else:
            user = self.client.get_user(member)
            if (isinstance(user, discord.ClientUser)):
                result = True

            elif (user is None):
                result = False
            else:
                user_guilds = user.mutual_guilds
                if (kwargs["guild"] in user_guilds):
                    result = True
                else:
                    result = False
        return result


    # validate_server(self, ctx, client, error, channel) Determines if
    #   'server' is a server and displays an error if it is not
    # effects: may send an embed
    async def validate_server(self, ctx: commands.Context, error: bool, server: discord.Guild, action: str) -> List[Union[bool, Optional[discord.Guild]]]:
        server = StringTools.convert_none(server)

        if (server is None):
            search_server = ctx.guild

            if (search_server is None):
                dm = True
        else:
            sev_search_results = await self.get_server(ctx, server)
            dm = sev_search_results["dm"]
            search_server = sev_search_results["server"]
            guild_search_type = sev_search_results["guild_search_type"]

        if (search_server is None):
            if (not error):
                if (not dm):
                    embeded_message = Error.display_error(self.client, 4, guild_search_type = guild_search_type, search_guild = server)
                    await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
                else:
                    dm_channel_server = f"Haku's DMs with {Members.convert_name(ctx.author.id, ctx.author)}"
                    embeded_message = Error.display_error(self.client, 9, channel = dm_channel_server, action = action, guild = dm_channel_server)
                    await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
            error = True

        return [error, search_server]


    # validate_channel(self, ctx, client, error, channel) Determines if
    #   'channel' is a channel and displays an error if it is not
    # effects: may send an embed
    async def validate_channel(self, ctx: commands.Context, error: bool, channel: str) -> List[Union[bool, Optional[Union[discord.abc.GuildChannel, discord.abc.PrivateChannel]]]]:
        channel = StringTools.convert_none(channel)

        if (channel is None):
            sending_channel = ctx.channel
        else:
            ch_sev_result = await self.get_ch_and_server(ctx, channel, None)
            sending_channel = ch_sev_result["channel"]
            channel_search_type = ch_sev_result["channel_search_type"]

        if (sending_channel is None):
            if (not error):
                embeded_message = Error.display_error(self.client, 5, channel_search_type = channel_search_type, search_channel = channel)
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
            error = True

        return [error, sending_channel]


    # validate_sev_ch(self, ctx, client, error, channel, server) Determines if
    #   'channel' is a channel and 'server' is a server. Displays an error if
    #   they are not
    # effects: may send an embed
    async def validate_sev_ch(self, ctx: commands.Context, error: bool, channel: str,
                              server: str, action: str = "perform command", allow_dm: bool = True,
                              allow_default: bool = False) -> List[Union[bool, Optional[Union[discord.abc.GuildChannel, discord.abc.PrivateChannel]], Optional[discord.Guild]]]:
        server = StringTools.convert_none(server)
        channel = StringTools.convert_none(channel)

        # check server and channel are valid
        search_server  = None
        search_channel = None
        if (server is not None or channel is not None):
            ch_sev_result = await self.get_ch_and_server(ctx, channel, server)
            search_server = ch_sev_result["server"]
            search_channel = ch_sev_result["channel"]
            channel_search_type = ch_sev_result["channel_search_type"]
            guild_search_type = ch_sev_result["guild_search_type"]

            if (search_server is None):
                if (not error):
                    if (search_channel is not None and server is None and not allow_dm):
                        name = Members.convert_name(ctx.author.id, ctx.author)
                        embeded_message = Error.display_error(self.client, 9, channel = f"Haku's Dms with {name}", action = action, guild = f"Haku's Dms with {name}")
                        await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
                    else:
                        embeded_message = Error.display_error(self.client, 4, guild_search_type = guild_search_type, search_guild = server)
                        await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
                error = True

            if (search_channel is None):
                if (not error):
                    embeded_message = Error.display_error(self.client, 5, search_channel = channel, channel_search_type = channel_search_type)
                    await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
                error = True

            if (not allow_dm and isinstance(search_channel, discord.DMChannel)):
                if (not error):
                    embeded_message = Error.display_error(self.client, 5, search_channel = channel, channel_search_type = channel_search_type)
                    await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
                error = True

        if (allow_default and server is None and channel is None):
            search_server = ctx.guild
            search_channel = ctx.channel

        return [error, search_server, search_channel]


    # validate_member(self, ctx, error, member) Determines if
    #   'member' is a member and displays an error if it is not
    # effects: may send an embed
    async def validate_member(self, ctx: commands.Command, error: bool, member: str,
                              allow_optional: bool = True, condition: Optional[Callable[[Any, Dict[str, Any]], bool]] = None,
                              condition_kwargs: Optional[Dict[str, Any]] = None) -> List[Union[bool, Optional[discord.abc.User]]]:
        member = StringTools.convert_none(member)

        # check if the member is valid
        search_member = None
        if (member is not None or (not allow_optional and member is None)):
            member_result = await self.get_member(member, condition = condition, condition_kwargs = condition_kwargs)
            search_member = member_result["member"]
            member_search_type = member_result["member_search_type"]

            if (search_member is None):
                if (not error):
                    embeded_message = Error.display_error(self.client, 18, member = "member", member_search_type = member_search_type, search_member = member)
                    await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
                error = True

        return [error, search_member]


    # validate_role(self, ctx, error, member) Determines if
    #   'role' is a valid role of 'server'
    # effects: may send an embed
    async def validate_role(self, ctx: commands.Context, error: bool, role: str,
                            server: discord.Guild, param_name: str) -> List[Union[bool, Optional[discord.Role]]]:
        role = StringTools.convert_none(role)
        role_is_tag = StringTools.is_tag(role)
        search_role = None

        if (server is not None):
            if (role_is_tag):
                role_id = StringTools.get_tag_id(role)
                role_is_num = await self.validate.check_natural(ctx, role_id, "role", verbose = False, check_equal = False)
                if (role_is_num):
                    search_role = server.get_role(int(role_id))

            elif (role in EVERYONE_ROLE):
                search_role = role
            else:
                for r in server.roles:
                    if (StringTools.front_substr_match(role, r.name)):
                        search_role = r
                        break

        if (search_role is None):
            if (not error and server is not None):
                embeded_message = Error.display_error(self.client, 10, element = role, group = f"the roles of {server.name}", parameter = param_name)
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
            error = True

        return [error, search_role]
