import discord
from discord.ext import commands, tasks
from set_up.settings import SettingTypes, SettingChangeState
from set_up.server_settings import ServerSettings
from set_up.user_settings import UserSettings
import set_up.group_settings as GroupSetup
from tools.embed import Embed
import tools.error as Error
import tools.members as Members
import tools.channels as ChannelTools

# Settings: Controls user and server settings for the bot
class Settings(commands.Cog):
    def __init__(self, client: discord.Client):
        self.client = client
        self.embed = Embed(client)
        self.server_settings = ServerSettings(client)
        self.user_settings = UserSettings(client)
        self.server = GroupSetup.SettingTypes.Server
        self.user = GroupSetup.SettingTypes.User

    # settings(ctx) Set the settings for a certain group
    @commands.group(pass_context=True)
    async def settings(self, ctx: commands.Context):
        if (ctx.invoked_subcommand is None):
            embeded_message = Error.display_error(self.client, 13, command = "settings")
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # settings(ctx) Set the settings for a certain group
    @commands.group(pass_context=True)
    async def settings(self, ctx: commands.Context):
        if (ctx.invoked_subcommand is None):
            embeded_message = Error.display_error(self.client, 13, command = "settings")
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # server(ctx) Set the settings for a server
    @settings.group(pass_context = True)
    async def server(self, ctx: commands.Context):
        if (ctx.invoked_subcommand is None):
            embeded_message = Error.display_error(self.client, 13, command = "settings server")
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

        elif (ctx.guild is None):
            name = Members.convert_name(ctx.author.id, ctx.author)
            dm_channel = ChannelTools.DMCHANNEL.replace("Name", name)
            embeded_message = Error.display_error(self.client, 9, channel = dm_channel, action = "interact with server settings", guild = dm_channel)
            await ctx.send(embed = embeded_message, file = embeded_message.file)


    # track(self, ctx, track_type) Toggles the settings for tracking a 'track_type'
    # effects: sends embeds
    #          deletes and edits messages
    @server.command(name="track", description="toggle the settings for tracking activity, messages, voice, etc...")
    async def track(self, ctx: commands.Context, track_settings: str, set_value: str):
        await self.server_settings.track(ctx, track_settings, set_value)


    # view(ctx, category) Views the server's settings
    # effects: sends embeds
    @server.command(name = "view", description = "Views the server settings of the current server")
    async def server_view(self, ctx: commands.Context):
        await self.server_settings.view(ctx, self.server)


    # set_prefix(ctx, prefixes) Changes the list of prefixes for the server
    # effects: sends embeds
    #          deletes and edits messages
    @server.command(name = "set_prefix", description = "Changes the prefixes for the current server")
    async def set_prefix(self, ctx: commands.Context, prefixes: str):
        await self.server_settings.set_prefixes(ctx, prefixes, SettingChangeState.Change)


    # add_prefix(ctx, prefixes) Adds a prefix to the existing prefixes of the
    #   server
    # effects: sends embeds
    #          deletes and edits messages
    @server.command(name = "add_prefix", description = "Adds a list of prefixes to the existing prefixes of the server")
    async def add_prefix(self, ctx: commands.Context, prefixes: str):
        await self.server_settings.set_prefixes(ctx, prefixes, SettingChangeState.Add)


    # remove_prefix(ctx, prefix_index) Removes a prefix from the existing
    #   prefixes of the server
    # effects: sends embeds
    #          deletes and edits messages
    @server.command(name = "remove_prefix", description = "Removes a prefix from the existing prefixes of the server")
    async def remove_prefix(self, ctx: commands.Context, prefix_index: str):
        await self.server_settings.remove_prefix(ctx, prefix_index)


    # server_set_timezone(ctx, timezone) Sets the timezone for the server
    # effects: sends embeds
    #          deletes and edits messages
    @server.command(name = "set_timezone", description = "Changes the timezone of the server")
    async def server_set_timezone(self, ctx: commands.Context, timezone: str):
        await self.server_settings.change_timezone(ctx, timezone, self.server)


    # server_set_region(ctx, region) Sets the region for the server
    # effects: sends embeds
    #          deletes and edits messages
    @server.command(name = "set_region", description = "Changes the region of the server")
    async def server_set_region(self, ctx: commands.Context, region: str):
        await self.server_settings.change_region(ctx, region, self.server)


    # server_sync_time(ctx) Toggles between synching or unsyching a server's timezone
    #   with their region
    # effects: sends embeds
    #          deletes and edits messages
    @server.command(name = "sync_time", description = "Syncs or unsyncs the time of the server with the selected region of the server")
    async def server_sync_time(self, ctx: commands.Context):
        await self.server_settings.sync_time(ctx, self.server)



    # user(ctx) Set the settings for a user
    @settings.group(pass_context = True)
    async def user(self, ctx: commands.Context):
        if (ctx.invoked_subcommand is None):
            embeded_message = Error.display_error(self.client, 13, command = "settings user")
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # view(ctx, category) Views the server's settings
    # effects: sends embeds
    @user.command(name = "view", description = "Views your settings")
    async def user_view(self, ctx: commands.Context):
        await self.user_settings.view(ctx, self.user)


    # user_set_timezone(ctx, timezone) Sets the timezone for the server
    # effects: sends embeds
    #          deletes and edits messages
    @user.command(name = "set_timezone", description = "Changes your timezone")
    async def user_set_timezone(self, ctx: commands.Context, timezone: str):
        await self.user_settings.change_timezone(ctx, timezone, self.user)


    # user_set_region(ctx, region) Sets the region for the server
    # effects: sends embeds
    #          deletes and edits messages
    @user.command(name = "set_region", description = "Changes your region")
    async def user_set_region(self, ctx: commands.Context, region: str):
        await self.user_settings.change_region(ctx, region, self.user)


    # user_sync_time(ctx) Toggles between synching or unsyching a your timezone
    #   with your region
    # effects: sends embeds
    #          deletes and edits messages
    @user.command(name = "sync_time", description = "Syncs or unsyncs your timezone with your selected region")
    async def user_sync_time(self, ctx: commands.Context):
        await self.user_settings.sync_time(ctx, self.user)


    # update_time() Updates the timezone of groups with timezones synchronized
    #   to their region to account for daylight savings
    @tasks.loop(seconds=43200)
    async def update_time(self):
        await self.server_settings.update_time()



#set up of the cog to the bot
def setup(client):
    client.add_cog(Settings(client))
