import discord, datetime
from discord.ext import commands
from server_info.server import ServerUtil, MemberActivity, EVERYONE_ROLE, ChannelAction
from tools.string import StringTools
from typing import Union

intents = discord.Intents()
intents.all()

# Client Module for Server related Commands
class Server(commands.Cog):
    #constructor
    def __init__(self, client):
        self.client = client
        self.server_util = ServerUtil(client)


    #when someone joins the server
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.server_util.on_member_join(member)


    # when someone updates their account
    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        await self.server_util.on_user_update(before, after)


    #when someone leaves the server
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self.server_util.on_member_remove(member)

    # on_guild_join(guild) Indicates when a new member joins the server
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.server_util.on_guild_join(guild)


    # on_member_update(before, after) Logs when a user updates their status,
    #   roles, nicknames or game/stream activity
    @commands.Cog.listener()
    async def on_member_update(self,before: discord.Member, after: discord.Member):
        await self.server_util.on_member_update(before, after)

    # on_guild_channel_create(channel) Indicates when a new guild channel is
    #   created
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        await self.server_util.on_guild_channel_add_delete(channel, action = ChannelAction.Create)


    # on_guild_channel_delete(channel) Indicates when a guild channel is deleted
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        await self.server_util.on_guild_channel_add_delete(channel, action = ChannelAction.Delete)


    # on_guild_channel_update(channel) Indicates when a guild channel is updated
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        await self.server_util.on_guild_channel_update(before, after)


    # on_typing(channel, user, when) Indicates when someone is typing in a channel
    @commands.Cog.listener()
    async def on_typing(self, channel: discord.abc.Messageable, user: Union[discord.Member, discord.User], when: datetime.datetime):
        await self.server_util.on_typing(channel, user, when)


    # on_voice_state_update(member, before, after) When someone changes their voice state in the server
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        await self.server_util.on_voice_state_update(member, before, after)


    # your_nickname(self, ctx, nickname_no) Changes the bot's nickname in the server
    @commands.command(name="your_nickname")
    async def your_nickname(self, ctx: commands.Context, nickname_no: str):
        await self.server_util.your_nickname(ctx, nickname_no)


    # members(ctx, member_status, member_role, page, server) List the all the
    #   members with the online status 'member_status' and the role 'member_role'
    #   of the server, 'server'
    @commands.command(name="members", description="list the members on the server")
    async def members(self, ctx: commands.Context, member_status: str = MemberActivity.Active.value,
                      member_role: str = EVERYONE_ROLE, page: str = "1", server: str = StringTools.NONE):
        await self.server_util.members(ctx, member_status, member_role, page, server)


#setup the Cog for the bot
def setup(client):
    client.add_cog(Server(client))
