import discord
from discord.ext import commands
from search.music import ServerMusic
import tools.members as Members
import tools.error as Error
from tools.string import StringTools


class Music(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.server_music = ServerMusic(client)


    # settings(ctx) Set the settings for a certain group
    @commands.group(pass_context=True)
    async def music(self, ctx: commands.Context):
        if (ctx.invoked_subcommand is None):
            embeded_message = Error.display_error(self.client, 13, command = "music")
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # join(ctx, voice_channel) Lets the bot join a voice channel
    @music.command(name="join", description=f"Allows me to join a voice channel")
    async def join(self, ctx: commands.Context, voice_channel: str = StringTools.NONE):
        await self.server_music.join(ctx, voice_channel)


    # leave(ctx) Lets the bot leave a voice channel
    @music.command(name="leave", description=f"Allows me to leave a voice channel")
    async def leave(self, ctx: commands.Context):
        await self.server_music.leave(ctx)


    # add(ctx, index) Adds a song to the playlist
    @music.command(name="add", description=f"Adds a song to my playlist in the server")
    async def add(self, ctx: commands.Context, query: str, index: str = StringTools.NONE):
        await self.server_music.add(ctx, query, index)


    # remove(ctx, index) Removes a song from the playlist
    @music.command(name="remove", description=f"Removes a song from my playlist in the server")
    async def remove(self, ctx: commands.Context, index: str = StringTools.NONE):
        await self.server_music.remove(ctx, index)


    # remove(ctx, index) Removes a song from the playlist
    @music.command(name="clear", description=f"Clears the server's playlist")
    async def clear(self, ctx: commands.Context):
        await self.server_music.clear(ctx)


    # view(ctx) Looks at the playlist
    @music.command(name="view", description=f"Look at my playlist in the server")
    async def view(self, ctx: commands.Context):
        await self.server_music.view(ctx)


    # play(ctx, query) Plays a song
    @music.command(name="play", description=f"Plays a song in the server")
    async def play(self, ctx: commands.Context, query: str = StringTools.NONE):
        await self.server_music.play(ctx, query)


    # jump(ctx, index) Jumps to a particular song
    @music.command(name="jump", description=f"Jumps to a particular song")
    async def jump(self, ctx: commands.Context, index: str):
        await self.server_music.jump(ctx, index)


    # skip(ctx) Skips to the next song in the playlist
    @music.command(name="skip", description=f"Skips to the next song in the server")
    async def skip(self, ctx: commands.Context):
        await self.server_music.skip(ctx)


    # resume(ctx) resumes a paused song
    @music.command(name="resume", description=f"Resumes a paused song")
    async def resume(self, ctx: commands.Context):
        await self.server_music.resume(ctx)


    # pause(ctx) resumes a paused song
    @music.command(name="pause", description=f"Pauses a song that is playing")
    async def pause(self, ctx: commands.Context):
        await self.server_music.pause(ctx)


    # vol(ctx, str) Changes the volume of the server's jukebox
    @music.command(name="vol", description=f"Changes the volume of the server's jukebox")
    async def vol(self, ctx: commands.Context, volume: str):
        await self.server_music.vol(ctx, volume)


    # tempo(ctx, speed) Changes the volume of the server's jukebox
    @music.command(name="tempo", description=f"Changes the speed songs are played on the server's jukebox")
    async def tempo(self, ctx: commands.Context, speed: str):
        await self.server_music.tempo(ctx, speed)


    # vol(ctx, str) Changes the volume of the server's jukebox
    @music.command(name="pitch", description=f"Changes the pitch at which songs are played on the server's jukebox")
    async def pitch(self, ctx: commands.Context, half_steps: str):
        await self.server_music.pitch(ctx, half_steps)


    # vol(ctx, str) Changes the volume of the server's jukebox
    @music.command(name="loop", description=f"Toggles between enabling/disabling the server's loop on its playlist")
    async def loop(self, ctx: commands.Context):
        await self.server_music.loop(ctx)


    # repeat(ctx, index) Changes the song that will be repeated in the server
    @music.command(name="repeat", description=f"Changes the song being repeated for the server")
    async def repeat(self, ctx: commands.Context, index = StringTools.NONE):
        await self.server_music.repeat(ctx, index)


    # fast_forward(ctx, duration) Fast forwards into the server's current song being played
    @music.command(name = "fast_forward", description = f"Fast forwards the current song being played on the server")
    async def fast_forward(self, ctx: commands.Context, duration: str):
        await self.server_music.fast_forward(ctx, duration)


    # swap(ctx, index_1, index_2) Swaps the position of 2 songs in the server's playlist
    @music.command(name = "swap", description = f"Swaps 2 songs in the server's playlist")
    async def swap(self, ctx: commands.Context, index_1: str, index_2: str):
        await self.server_music.swap(ctx, index_1, index_2)


    # shuffle(ctx) Randomly shuffles the server's playlist
    @music.command(name = "shuffle", description = f"Randomly shuffles the server's playlist")
    async def shuffle(self, ctx):
        await self.server_music.shuffle(ctx)


    # setting_view(ctx) Views the server's settings for their jukebox
    @music.command(name = "setting_view", description = f"Views the settings to the server's jukebox")
    async def setting_view(self, ctx):
        await self.server_music.setting_view(ctx)


    # random(ctx) Randomly selects a song to be played next
    @music.command(name = "random", description = f"Toggles the option to randomly select the next songs to be played")
    async def random(self, ctx):
        await self.server_music.random(ctx)



def setup(client):
    client.add_cog(Music(client))
