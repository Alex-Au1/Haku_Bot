import discord
from discord.ext import commands, tasks
from search.youtube import YoutubeUtils, YtAccount
import tools.members as Members
import tools.channels as ChannelTools
import tools.error as Error



class Youtube(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.youtube = YoutubeUtils(client)


    # settings(ctx) Set the settings for a certain group
    @commands.group(pass_context=True)
    async def youtube(self, ctx: commands.Context):
        if (ctx.invoked_subcommand is None):
            embeded_message = Error.display_error(self.client, 13, command = "youtube")
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # server(ctx) Set the settings for a server
    @youtube.group(pass_context = True)
    async def server(self, ctx: commands.Context):
        if (ctx.invoked_subcommand is None):
            embeded_message = Error.display_error(self.client, 13, command = "youtube server")
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

        elif (ctx.guild is None):
            name = Members.convert_name(ctx.author.id, ctx.author)
            dm_channel = ChannelTools.DMCHANNEL.replace("Name", name)
            embeded_message = Error.display_error(self.client, 9, channel = dm_channel, action = "perform youtube functions", guild = dm_channel)
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # latest_video(ctx, channel_link) Get the most recent video from a certain youtube channel
    @youtube.command(name="latest_video", description="Retrieves the latest video from a channel")
    async def latest_video(self, ctx: commands.Context, channel: str):
        await self.youtube.latest_video(ctx, channel)


    # add_yt_channel(ctx, channel, sending_channel) Enable video notifications of a youtube channel to the server
    @server.command(name = "add_channel", description = "Allow the server to receive notifications on the latest videos from a youtube channel")
    async def add_yt_channel(self, ctx: commands.Context, channel: str, sending_channel: str):
        await self.youtube.add_yt_channel(ctx, channel, sending_channel, YtAccount.Server)


    # change_yt_channel(ctx, channel_index, sending_channel) Changes the location where the notifications for each video is sent
    @server.command(name = "change_channel", description = "Changes where notifications on the latest videos from a youtube channel are sent to")
    async def change_yt_channel(self, ctx: commands.Context, channel_index: str, sending_channel: str):
        await self.youtube.change_yt_channel(ctx, channel_index, sending_channel)


    # remove_yt_channel(ctx, channel) Disable video notifications of a youtube channel to the server
    @server.command(name = "remove_channel", description = "Allow the server to stop receiving notifications on the latest videos from a youtube channel")
    async def remove_yt_channel(self, ctx: commands.Context, channel_index: str):
        await self.youtube.remove_yt_channel(ctx, channel_index, YtAccount.Server)


    # server_view(ctx) Views all the subscribed channels of the server
    @server.command(name = "view", description = "Views all of the subscribed channels of the server")
    async def server_view(self, ctx: commands.Context):
        await self.youtube.view_subd_channels(ctx, YtAccount.Server)


    # server_notify(ctx) enables/disables all youtube notifications for the server
    @server.command(name = "notifications", description = "Enables/Disables all youtube notifications for the server")
    async def server_notify(self, ctx: commands.Context):
        await self.youtube.enable_notifications(ctx, YtAccount.Server)



    # server(ctx) Set the youtube commands for the user
    @youtube.group(pass_context = True)
    async def user(self, ctx: commands.Context):
        if (ctx.invoked_subcommand is None):
            embeded_message = Error.display_error(self.client, 13, command = "youtube user")
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # add_yt_channel(ctx, channel, sending_channel) Enable video notifications of a youtube channel for the user
    @user.command(name = "add_channel", description = "Allow you to receive notifications on the latest videos from a youtube channel")
    async def user_add_yt_channel(self, ctx: commands.Context, channel: str):
        dm_channel = await ctx.author.create_dm()
        await self.youtube.add_yt_channel(ctx, channel, str(dm_channel.id), YtAccount.User)


    # remove_yt_channel(ctx, channel) Disable video notifications of a youtube channel to the server
    @user.command(name = "remove_channel", description = "Allow you to stop receiving notifications on the latest videos from a youtube channel")
    async def user_remove_yt_channel(self, ctx: commands.Context, channel_index: str):
        await self.youtube.remove_yt_channel(ctx, channel_index, YtAccount.User)


    # server_view(ctx) Views all the subscribed channels of the user
    @user.command(name = "view", description = "Views all of your subscribed channels")
    async def user_view(self, ctx: commands.Context):
        await self.youtube.view_subd_channels(ctx, YtAccount.User)


    # user_notify(ctx) enables/disables all youtube notifications for the server
    @user.command(name = "notifications", description = "Enables/Disables all of your youtube notifications")
    async def user_notify(self, ctx: commands.Context):
        await self.youtube.enable_notifications(ctx, YtAccount.User)



    # channel_updates(self) Get the latest video posted by a channel
    @tasks.loop(seconds=300)
    async def channel_updates(self):
        await self.youtube.channel_updates()




def setup(client):
    client.add_cog(Youtube(client))
