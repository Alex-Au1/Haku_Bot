import discord, youtube_dl, enum, random, asyncio, copy, datetime
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from discord.ext import commands
from youtubesearchpython import *
from database.database import Database, SelectType
from tools.string import StringTools
from set_up.music_settings import MusicSettings
import tools.error as Error
from tools.embed import Embed, EmbededMessage
import tools.members as Members
from tools.discord_search import SearchTools
import pics.image_links as Pics
import set_up.prefix as Prefix
import tools.validate as ValidateTools
import tools.datetime as DateTime
from typing import Dict, Any, Optional, List, Union
from text.bot_texting import Texting
import tools.dialogue as Dialogue
from tools.pagination import Pagination
import tools.search_yt as YtSearchTools

MAX_VOL = 100
DEFAULT_VOL = 70

DEFAULT_PITCH = 0
SPEED = {"MIN":0.5, "DEFAULT": 1.0, "MAX": 2.0}
HALF_STEPS = {"MIN": -12.0, "DEFAULT": 0.0, "MAX": 12.0}
HALF_STEPS_PER_OCTAVE = 12
REPLACEMENTS = {"SAMPLE_RATE": "<sample_rate>", "PITCH": "<pitch>",
                "PITCH_SPEED": "<pitch_speed>", "SPEED": "<speed>"}
DEFAULT_BIT_RATE = 48000

TIMEOUT_DURATION = 300
END_CONCERT_CHECK_DELAY = 1


SPOTIPY_CLIENT_ID='3e21f4b851cc4ef48d01a7dc8d561898'
SPOTIPY_CLIENT_SECRET='e30cfda94e8447099607465707363048'
AUTH_MANAGER = SpotifyClientCredentials(client_id = SPOTIPY_CLIENT_ID, client_secret = SPOTIPY_CLIENT_SECRET)
SP = spotipy.Spotify(auth_manager=AUTH_MANAGER)



# AddSongState: Different possiblities when adding a song
class AddSongState(enum.Enum):
    NotFound = 0
    Song = 1
    Playlist = 2


# PerfectIntervalType: The different modes for a perfect interval
class PerfectIntervalType(enum.Enum):
    NotFound = 0
    Diminished = 1
    Perfect = 2


# MusicInterval: Stores information about a certain interval between 2 keys
class MusicInterval():
    def __init__(self, key_distance: int, hf_lowered: Optional[int], hf_norm):
        self.key_distance = key_distance
        self.hf_lowered = hf_lowered
        self.hf_norm = hf_norm


    # in_interval(half_steps) Determines if 'half_steps' fits the indicated interval
    def in_interval(self, half_steps: int) -> PerfectIntervalType:
        is_lowered = (self.hf_lowered is not None and half_steps == self.hf_lowered)
        is_norm = (half_steps == self.hf_norm)

        if (is_lowered):
            return PerfectIntervalType.Diminished
        elif (is_norm):
            return PerfectIntervalType.Perfect
        else:
            return PerfectIntervalType.NotFound

OCTAVE = 8
PERFECT_INTERVALS = {"FOURTH": MusicInterval(4, None, 5),
                     "FIFTH": MusicInterval(5, 6, 7),
                     "OCTAVE": MusicInterval(OCTAVE, None, 12)}

#options for playing the youtube video
YDL_OPTS = {'format': 'bestaudio/best',
            'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0'}

#options for converting audio
FFMPEG_OPTIONS_TEMPLATE = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                          'options': f'-af "asetrate={REPLACEMENTS["SAMPLE_RATE"]}*{REPLACEMENTS["PITCH"]}, atempo={REPLACEMENTS["PITCH_SPEED"]}, atempo={REPLACEMENTS["SPEED"]}" -vn'}

YTDL = youtube_dl.YoutubeDL(YDL_OPTS)
JUKEBOX_DICT = {}


# PlayState: State when using the play option in the jukebox
class PlayState(enum.Enum):
    PlaySong = "play_song"
    AddSong = "add_song"


# VoiceState: Indicate the state of the Jukebox
class VoiceState(enum.Enum):
    Playing = "playing"
    Paused = "paused"
    Connected = "connected"
    Disconnected = "disconnected"


# JukeBoxOptions: Options for a server's jukebox
class JukeBoxOptions():
    def __init__(self, playlist_loop: bool, song_loop: Optional[int], vol: float, speed: float, half_steps: int):
        self.playlist_loop = playlist_loop
        self.song_loop = song_loop
        self.vol = vol
        self.speed = speed
        self.half_steps = half_steps


    #set the volume
    def set_volume(self, volume: int) -> float:
        new_volume = volume / MAX_VOL
        self.vol = volume
        return new_volume


    # get_pitch(self, half_steps) Gets the pitch to set the audio
    def get_pitch(self, half_steps: int) -> float:
        return (2 ** (half_steps / HALF_STEPS_PER_OCTAVE))


    # get_current_pitch(self, half_steps) Gets the current pitch set in the options
    def get_current_pitch(self):
        return self.get_pitch(self.half_steps)


    # get_pitch_speed() Finds the speed to turn the asetrated audio back to normal speed
    def get_pitch_speed(self, pitch: float) -> float:
        return (1 / pitch)


    # get_current_pitch_speed() Finds the speed to turn the asetrated audio
    #   to normal speed based on the current pitch set
    def get_current_pitch_speed(self) -> float:
        return self.get_pitch_speed(self.get_current_pitch())


# YTDLSource(): Prepares youtube videos to be played
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source: discord.AudioSource, *, data: Dict[str, Any], search_url: str, stream: bool, volume: float = (DEFAULT_VOL / MAX_VOL)):
        super().__init__(source, volume)
        self.data = data
        self.title = StringTools.word_replace(data.get('title'), {"[": "{", "]": "}"})
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.sample_rate = data.get('asr')
        self.search_url = search_url
        self.stream = stream
        self.start_date = None
        self.duration = data.get('duration')
        self.end_date = None


    # get_current_options() Retrieves the options for the audio source
    @classmethod
    def get_current_options(cls) -> Dict[str, Any]:
        return {"before_options": cls.before_options, "options": cls.options}


    # get_ffmpeg_options(data) Completes the ffmpeg options for the audio source
    @classmethod
    def get_ffmpeg_options(cls, data: Dict[str, Any], options: JukeBoxOptions) -> Dict[str, Any]:
        new_ffmpeg_options = copy.deepcopy(FFMPEG_OPTIONS_TEMPLATE)

        replacements = {REPLACEMENTS['SAMPLE_RATE']: str(data['asr']),
                        REPLACEMENTS['PITCH']: str(options.get_current_pitch()),
                        REPLACEMENTS['PITCH_SPEED']: str(options.get_current_pitch_speed()),
                        REPLACEMENTS['SPEED']: str(options.speed)}

        new_ffmpeg_options['options'] = StringTools.word_replace(FFMPEG_OPTIONS_TEMPLATE['options'], replacements)
        return new_ffmpeg_options


    # only_ffmpeg_options(data) Retreives only the options for ffmpeg
    @classmethod
    def only_ffmpeg_options(cls, data: Dict[str, Any], options: JukeBoxOptions) -> str:
        new_ffmpeg_options = cls.get_ffmpeg_options(data, options)
        return new_ffmpeg_options['options']


    # change_ffmpeg_options(options) Changes the ffmpeg for the audio source
    def change_ffmpeg_options(self, options: JukeBoxOptions) -> Dict[str, Any]:
        current_options = self.get_current_options
        new_options = self.only_ffmpeg_options(self.data, options)
        self.options = new_options
        return new_options


    #prepares the video url to be played
    @classmethod
    async def prepare_music(cls, url: str, options: JukeBoxOptions, loop=None, stream: bool = False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: YTDL.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else YTDL.prepare_filename(data)
        new_ffmpeg_options = cls.get_ffmpeg_options(data, options)
        return cls(discord.FFmpegPCMAudio(filename, **new_ffmpeg_options), data=data, search_url = url, stream = stream, volume = options.vol / MAX_VOL)


    # fast_prepare(ytdl_source) Prepares a new YTDLSource from an existing source
    @classmethod
    async def fast_prepare(cls, ytdl_source, options: JukeBoxOptions):
        data = ytdl_source.data
        ffmpeg_options = cls.get_ffmpeg_options(data, options)
        filename = data['url'] if ytdl_source.stream else YTDL.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options),
                   data = ytdl_source.data, search_url = ytdl_source.search_url, stream = ytdl_source.stream, volume = ytdl_source.volume)


    # get_start_date() Retrieves the start date of the audio source
    def get_start_date(self) -> datetime.datetime:
        self.start_date = DateTools.get_current_dt(utc = True)
        return self.start_date


    # get_end_date() Gets the expected end date for the source
    def get_end_date(self) -> datetime.datetime:
        self.end_date = self.start_date + datetime.timedelta(seconds = self.duration)
        return self.end_date


    # get_date() Gets the start and end date for an audio source
    def get_dates(self):
        self.get_start_date()
        self.get_end_date()
        return [self.start_date, self.end_date]


# SongInfo: Data for each song
class SongInfo():
    def __init__(self, title, url, duration):
        self.title = title
        self.url = url
        self.duration = duration


class JukeBox():
    def __init__(self, ctx: commands.Context, client: discord.Client):
        self.id = ctx.guild.id
        self.name = ctx.guild.name
        self.options = self.get_default_options()
        self.playlist = []
        self.current_song_index = 0
        self.state = self.get_state(ctx)
        self.loop = client.loop
        self.started_playing = False
        self.recent_message = None
        self.adding_state = AddSongState.Song


    # get_default_options(ctx) Gets the default options
    def get_default_options(self) -> JukeBoxOptions:
        return JukeBoxOptions(False, None, DEFAULT_VOL, SPEED["DEFAULT"], DEFAULT_PITCH)


    # get_current_song() Gets the current song in the jukebox
    def get_current_song(self) -> YTDLSource:
        return self.playlist[self.current_song_index]


    # insert_song(pos, prepared_source) Inserts a song into the playlist
    def insert_song(self, pos: int, prepared_source: YTDLSource, playlist_len: int):
        before_not_empty = bool(self.playlist)
        if (pos <= 0):
            self.playlist.insert(0, prepared_source)
        elif(pos >= playlist_len):
            self.playlist.append(prepared_source)
        else:
            self.playlist.insert(pos, prepared_source)

        if (before_not_empty and pos == self.current_song_index):
            self.current_song_index += 1


    #add_song(validate, source, pos, playlist_len) Prepares a song or a list of
    #   songs to be added to the playlist
    async def add_song(self, client: discord.Client, validate: ValidateTools.Validate, source: str,
                       pos: int, playlist_len: Optional[int] = None, condition: Optional[List[AddSongState]] = None) -> List[Union[AddSongState, int]]:
        state = AddSongState.Song
        songs_added = 0

        if (playlist_len is None):
            playlist_len = len(self.playlist)

        if (validate.valid_yt_link(source)):
            prepared_source = await YTDLSource.prepare_music(source, self.options, loop=client.loop, stream=True)

        elif (validate.valid_yt_playlist_link(source)):
            self.adding_state = AddSongState.Playlist
            url_lst = await YtSearchTools.playlist_get_yt_links(client, source)

            for url in url_lst:
                try:
                    prepared_source = await YTDLSource.prepare_music(url, self.options, loop=client.loop, stream=True)
                    self.insert_song(pos, prepared_source, playlist_len)
                    pos += 1
                    songs_added += 1
                except:
                    pass

            self.adding_state = AddSongState.Song
            condition[0] = AddSongState.Song
            print(f"STATE CHANGE TO {AddSongState.Song.value}")
            state = AddSongState.Playlist

        else:
            song_result = VideosSearch(source, limit = 1)
            song_result = song_result.result()["result"]

            if (song_result):
                song = song_result[0]
                prepared_source = await YTDLSource.prepare_music(song["link"], self.options, loop=self.loop, stream=True)
            else:
                state = AddSongState.NotFound

        if (state == AddSongState.Song):
            self.insert_song(pos, prepared_source, playlist_len)
            songs_added += 1

        return [state, songs_added]


    # remove_song() Removes a song from the playlist
    async def remove_song(self, pos: int, playlist_len: Optional[int] = None) -> SongInfo:
        if (playlist_len is None):
            playlist_len = len(self.playlist)

        if (pos < 0):
            pos = 0
        elif(pos >= playlist_len):
            pos = playlist_len - 1

        removed_song = self.playlist[pos]
        removed_source = SongInfo(removed_song.title, removed_song.url, removed_song.duration)
        self.playlist.pop(pos)
        return removed_source


    # get_playlist(ctx) Get the list of searches of songs for the playlist of
    #   the server
    async def get_playlist(self, ctx: commands.Context, client: discord.Client, validate: ValidateTools.Validate):
        columns_needed = ["song_list"]
        music_info = Database.default_select(MusicSettings.default_setting, SelectType.Formatted, [columns_needed, columns_needed, "Server_Music"],
                                             {"conditions": {"id": f"{ctx.guild.id}"}}, [ctx], {})
        music_info = music_info[0]
        music_list = StringTools.convert_list(music_info[columns_needed[0]])

        for s in music_list:
            pos = self.current_song_index + 1
            await self.add_song(client, validate, s, pos)


    # get_state(ctx) Gets the state of the Jukebox
    def get_state(self, ctx: commands.Context):
        if (ctx.voice_client is None):
            return VoiceState.Disconnected
        elif (ctx.voice_client.is_paused()):
            return VoiceState.Paused
        elif (ctx.voice_client.is_playing()):
            return VoiceState.Playing
        else:
            return VoiceState.Connected


    # get_next_song_index() Gets the index for the nextsong
    def get_next_song_index(self) -> int:
        if (self.options.song_loop is not None and self.current_song_index == self.options.song_loop):
            return self.current_song_index
        else:
            playlist_len = len(self.playlist)

            if (self.current_song_index >= playlist_len - 1 or self.current_song_index < 0):
                return 0
            else:
                return self.current_song_index + 1


    # is_last_song() Determines if the current song is the last song being played
    def is_last_song(self) -> bool:
        last_index = len(self.playlist) - 1
        result = (self.current_song_index == last_index and
                  not self.options.playlist_loop and
                  (self.options.song_loop is None or self.options.song_loop != last_index))
        return result


    # continual_check_connected() Continuosly checks whether the jukeboxes' state
    #   changes from being connected to another state
    async def continual_check_exit(self):
        if (self.state == VoiceState.Connected):
            while(True):
                await asyncio.sleep(END_CONCERT_CHECK_DELAY)
                if (self.state != VoiceState.Connected):
                    break

    # clear_playlist() Clears the playlist for the jukebox
    def clear_playlist(self):
        self.playlist = []


    # is_playing() Checks if the bot is playing an audio
    def is_playing(self) -> bool:
        return (self.state == VoiceState.Playing or self.state == VoiceState.Paused)


    # change_options() Changes the options for all the songs in the playlist
    async def change_options(self):
        playlist_len = len(self.playlist)
        for i in range(playlist_len):
            if (not(self.is_playing() and i == self.current_song_index)):
                current_song = self.playlist[i]
                self.playlist[i] =  await YTDLSource.fast_prepare(current_song, self.options)


    # reload_song(self) Reloads the song once it is done playing
    # requires: 0 <= song_index < len(self.playlist)
    async def reload_song(self, song_index: int):
        song = self.playlist[song_index]
        song_url = song.search_url
        try:
            song.read()
        except:
            self.playlist[song_index] = await YTDLSource.prepare_music(song_url, self.options, loop=self.loop, stream=True)


    # reload_current_song(self) Reloads the current song once it is done playing
    async def reload_current_song(self):
        await self.reload_song(self.current_song_index)


    # change_volume(vol) Changes the volume for all songs in the playlist
    # requires: 0 <= vol <= 1
    def change_volume(self, vol):
        for s in self.playlist:
            s.volume = vol


class ServerMusic():
    def __init__(self, client):
        self.client = client
        self.embed = Embed(client)
        self.search_tools = SearchTools(client)
        self.validate = ValidateTools.Validate(client)
        self.SONGS_PER_PAGE = 20
        self.SONG_NAME_LIMIT = 30
        self.text = Texting(client)


    # get_jukebox: Gets a server's jukebox
    async def get_jukebox(self, ctx: commands.Context):
        try:
            jukebox = JUKEBOX_DICT[ctx.guild.id]
        except:
            jukebox = JukeBox(ctx, self.client)
            await jukebox.get_playlist(ctx, self.client, self.validate)
            JUKEBOX_DICT[ctx.guild.id] = jukebox
        return jukebox


    # noticeable_msg_send(embeded_message) Edits the message when the last message
    #   is a recorded message by the bot
    # effects: sends and edits embeds
    async def noticeable_msg_send(self, ctx: commands.Context, embeded_message: EmbededMessage, jukebox: JukeBox, delay: int = 0):
        if (jukebox.recent_message is None):
            jukebox.recent_message = await ctx.send(embed = embeded_message.embed, file = embeded_message.file, delay = delay)
        else:
            jukebox.recent_message = await self.text.noticeable_edit(ctx, jukebox.recent_message, embeded_message, keep_attachments = False, delay = delay)


    # not_in_voice_channel(ctx, jukebox, verbose, error) Determines if the bot is
    #   connected to a voice channel
    # effects: sends an embed
    async def not_in_voice_channel(self, ctx: commands.Context, jukebox: JukeBox, verbose: bool = True, error: Optional[bool] = None) -> bool:
        not_in_channel = False
        if ((error is None or (error is not None and not error)) and ctx.voice_client is None):
            if (verbose):
                jukebox.state = VoiceState.Disconnected
                embeded_message = self.embed.context_embed(ctx, f"I'am currently not in a live concert. Come enjoy seeing me singing live using the command `{Prefix.DEFAULT_PREFIX}join`", "Not in a Live Convert", "red")
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
            not_in_channel = True
        elif (error is not None and error):
            return error

        return not_in_channel


    # is_playing(ctx, jukebox, verbose, error) Checks if the bot is playing an audio file
    # effects: sends an embed
    async def is_playing(self, ctx: commands.Context, jukebox: JukeBox, verbose: bool = True, error: Optional[bool] = None) -> bool:
        playing = False
        if ((error is None or (error is not None and not error)) and ctx.voice_client is not None and ctx.voice_client.is_playing()):
            if (verbose):
                jukebox.state = VoiceState.Playing
                current_song = jukebox.get_current_song()
                embeded_message = self.embed.context_embed(ctx, f"Right now, I'am in the middle of singing **song #{jukebox.current_song_index + 1}** [{current_song.title}]({current_song.search_url})", "Already Singing a Song", "red")
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
            playing = True
        elif (error is not None and error):
            return error

        return playing


    # playing_empty(ctx, jukebox, verbose, error) Checks if the bot is about to play a song
    #   even though there are no songs in its playlist
    # effects: sends an embed
    async def playing_empty(self, ctx: commands.Context, jukebox: JukeBox, verbose: bool = True, error: Optional[bool] = None) -> bool:
        empty_playing = False

        if ((error is None or (error is not None and not error)) and jukebox.state == VoiceState.Connected and not jukebox.playlist):
            embeded_message = self.embed.context_embed(ctx, "Please give me a song recommendation and I will sing it for you", "No Songs in Playlist", "red")
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
            empty_playing = True
        elif (error is not None and error):
            return error

        return empty_playing


    # get_random_img_cat(img_cat_lst) Gets a random image category
    def get_random_img_cat(self, img_cat_lst: List[Pics.ImageCategory]) -> Pics.ImageCategory:
        return img_cat_lst[random.randrange(0, len(img_cat_lst))]


    # end_song_embed(ctx, current_song) Makes the embed format for ending the playing of
    #   a jukeboxes' playlist
    def end_song_embed(self, ctx: commands.Context, current_song: YTDLSource) -> EmbededMessage:
        song_done_msg = Dialogue.get_dialogue(Dialogue.DialogueCategory.SongDone)
        embeded_message = self.embed.context_embed(ctx, song_done_msg, f"{Members.DEFAULT_BOT_NAME} Finished Singing {current_song.title}!", "light-purple")
        return embeded_message

    # leave_concert_embed(ctx) Makes tghe embed format when the bot leaves a voice channel
    def leave_concert_embed(self, ctx: commands.Context, voice_channel: discord.abc.Connectable, auto_leave = False) -> EmbededMessage:
        title = f"{Members.DEFAULT_BOT_NAME}'s Concert has Just Finished"
        message = f"Minaa! Thank you for coming to my concert at `{voice_channel.name}`({StringTools.format_channel(voice_channel.id)})! Hope you will come again!"
        colour = "light-red"
        image = image = {Pics.ImageCategory.Happy: -1}
        if (not auto_leave):
            embeded_message = self.embed.context_embed(ctx, message, title, colour, image = image)
        else:
            embeded_message = self.embed.bot_embed(ctx, message, title, colour, 1, image = image)
        return embeded_message

    # end_conert(ctx, jukebox, current_song) indicates the end of a playing session
    async def end_concert(self, ctx: commands.Context, jukebox: JukeBox, current_song: YTDLSource):
        jukebox.state = VoiceState.Connected
        jukebox.current_song_index = jukebox.get_next_song_index()
        embeded_message = self.end_song_embed(ctx, current_song)
        current_song.cleanup()
        await self.noticeable_msg_send(ctx, embeded_message, jukebox)
        await self.check_to_end(ctx, jukebox)


    # check_to_end(ctx, jukebox) Checks whether to discard all jukebox data for the server
    async def check_to_end(self, ctx: commands.Context, jukebox: JukeBox):
        try:
            await asyncio.wait_for(jukebox.continual_check_exit(), timeout=TIMEOUT_DURATION)
        except asyncio.TimeoutError:
            await self.jukebox_end(ctx, jukebox)


    # join(ctx, voice_channel) Joins a voice Channel
    async def join(self, ctx: commands.Context, voice_channel: str = StringTools.NONE, jukebox: Optional[JukeBox] = None):
        error = False
        voice = ctx.author.voice

        voice_channel = StringTools.convert_str(voice_channel)
        if (voice_channel is None and voice is None):
            error = True
            embeded_message = self.embed.error_embed(f"Either join a voice channel and invoke the command `{Prefix.DEFAULT_PREFIX}join` again or specify a voice channel in the parameter `voice_channel` for me to sing at",
                                                      "No Voice Channel Specificed")
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

        elif (voice_channel is not None):
            error, voice_channel = await self.search_tools.validate_channel(ctx, error, voice_channel)

            if (not isinstance(voice_channel, discord.abc.Connectable)):
                error = True
                embeded_message = Error.display_error(self.client, 6, type_article = "a", correct_type = "voice channel", parameter = "voice_channel")
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

        if (not error):
            from_playing = True
            if (jukebox is None):
                from_playing = False
                jukebox = await self.get_jukebox(ctx)

            bot_nickname = Members.get_bot_nickname()

            if (voice_channel is None):
                await voice.channel.connect()
                await ctx.voice_client.disconnect()
                await voice.channel.connect()
                voice_channel = voice.channel
            else:
                await voice_channel.connect()
                await ctx.voice_client.disconnect()
                await voice_channel.connect()

            jukebox.state = VoiceState.Connected
            message = f"{bot_nickname} is about to come on stage at `{voice_channel.name}` ({StringTools.format_channel(voice_channel.id)})!"

            embeded_message = self.embed.context_embed(ctx, f"{bot_nickname} is about to come on stage at `{voice_channel.name}` ({StringTools.format_channel(voice_channel.id)})!", f"{bot_nickname} is About to Appear on Stage!", "pink")
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

            if (not from_playing):
                await self.check_to_end(ctx, jukebox)


    # leave(ctx) Leaves the voice channel
    async def leave(self, ctx):
        jukebox = await self.get_jukebox(ctx)
        try:
            voice_channel = ctx.voice_client.channel
            await ctx.voice_client.disconnect()
            embeded_message = self.leave_concert_embed(ctx, voice_channel)
            jukebox.state = VoiceState.Disconnected
        except:
            await self.not_in_voice_channel(ctx, jukebox)
        else:
            await self.noticeable_msg_send(ctx, embeded_message, jukebox)


    # jukebox_end(ctx, jukebox) Leave the voice channel and clear the server's playlist
    #   When nobody is playing anything on the bot and the bot is in a voice chanel
    async def jukebox_end(self, ctx: commands.Context, jukebox: JukeBox):
        if (jukebox.state == VoiceState.Connected):
            voice_channel = ctx.voice_client.channel
            field_message = "To save my energy, since nobody is requesting me to sing a song, I left the concert "
            if (jukebox.started_playing):
                embeded_message = self.leave_concert_embed(ctx, voice_channel)
            else:
                embeded_message = self.embed.bot_embed(ctx, "Sniff, Nobody wants to listen to my concert, so I decided to leave \U0001F625", "Haku Cancelled the Concert", "dark-purple", 1, image = {Pics.ImageCategory.Sad: -1})
                field_message += f"at `{voice_channel.name}`({StringTools.format_channel(voice_channel.id)}) "

            field_message += "and cleared the server's playlist"
            embeded_message = self.embed.add_section(embeded_message, "Note \U0001F4DD", field_message)
            embeded_message.embed.set_author(name = f"Sad {Members.DEFAULT_BOT_NAME}", url = self.embed.ADD_BOT_URL, icon_url = str(self.client.user.avatar_url))
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

            jukebox.clear_playlist()

            try:
                await ctx.voice_client.disconnect()
                jukebox.state = VoiceState.Disconnected
                jukebox.started_playing = False
            except:
                pass


    # view_loading_songs(ctx, jukebox) Slowly updates the songs that are being
    #   loaded into the playlist
    async def view_loading_songs(self, ctx: commands.Context, jukebox: JukeBox, condition: List[AddSongState]):
        embeded_message = self.embed.context_embed(ctx, "Loading these songs may take a while...\n\nMeanwhile, you can view your songs slowly being added here:", "Adding Songs May Take Some Time...", "light-purple")
        await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
        await self.view(ctx, jukebox = jukebox, condition = condition)


    # add(ctx, query) Adds a song to the playlist
    async def add(self, ctx: commands.Context, query: str, index: str = StringTools.NONE, jukebox: Optional[JukeBox] = None):
        error = False
        if (jukebox is None):
            jukebox = await self.get_jukebox(ctx)
        playlist_len = len(jukebox.playlist)

        error, index = await self.validate.validate_natural(ctx, error, index, "index", allow_optional = True, check_equal = True)

        if (not error):
            if (index is None):
                index = playlist_len + 1
            else:
                error = await self.validate.validate_inbetween(ctx, index, "index", 1, playlist_len, error)

        if (not error):
            no_of_songs = 0
            index -= 1

            if (self.validate.valid_yt_playlist_link(query)):
                before_no_of_songs = len(jukebox.playlist)
                jukebox.adding_state = AddSongState.Playlist
                condition = [jukebox.adding_state]
                print(f"CHECK: {condition} AND {jukebox.adding_state.value}")
                await asyncio.wait([jukebox.add_song(self.client, self.validate, query, index, playlist_len = playlist_len, condition = condition),
                                    self.view_loading_songs(ctx, jukebox, condition)])
                add_state = AddSongState.Playlist
                no_of_songs = len(jukebox.playlist) - before_no_of_songs
            else:
                add_state, no_of_songs = await jukebox.add_song(self.client, self.validate, query, index, playlist_len = playlist_len)

            if (add_state == AddSongState.NotFound):
                embeded_message = Error.display_error(self.client, 18, member = "audio source", member_search_type = "name", search_member = query)
            elif (add_state == AddSongState.Playlist):
                embeded_message = self.embed.context_embed(ctx, f"Your selection of **{no_of_songs} songs** have been added to my playlist", f"{Members.DEFAULT_BOT_NAME} Took in Your Selected Playlist", "light-purple")
            else:
                prepared_video = jukebox.playlist[index]
                embeded_message = self.embed.context_embed(ctx, "Your song has been added to my playlist", f"{Members.DEFAULT_BOT_NAME} Took in Your Selected Song", "light-purple")
                embeded_message = self.embed.multi_add_section(embeded_message, {"Title \U0001F3F7": f"[{prepared_video.title}]({prepared_video.search_url})", "Duration \U000023F1": f"`{DateTime.format_time(prepared_video.duration)}`"})

            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # remove(ctx, index) Removes a song from the playlist
    async def remove(self, ctx: commands.Context, index: str):
        jukebox = await self.get_jukebox(ctx)
        playlist_len = len(jukebox.playlist)
        error = False
        error, index = await self.validate.validate_natural(ctx, error, index, "index", check_equal = True)

        if (not playlist_len and not error):
            error = True
            embeded_message = Error.display_error(self.client, 19, action = "remove songs", reason = " because there are no songs in the playlist")
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

        if (not error):
            error = await self.validate.validate_inbetween(ctx, index, "index", 1, playlist_len, error)

        if (not error):
            index -= 1
            song = jukebox.playlist[index]
            currently_playing = False

            question_message = ""
            question_title = "Remove Song?"
            position = f"{StringTools.get_lineup_pos(index + 1)}"
            if (index == jukebox.current_song_index and ((jukebox.state == VoiceState.Playing) or (jukebox.state == VoiceState.Paused))):
                currently_playing = True
                question_message = "**Warning \U000026A0**\nI'am currently in the middle of singing this song\n\n"
            question_message += f"Do you want to remove **the {position} song** from my playlist?"
            response = await self.text.question(ctx, question_message, question_title, replacements = {"receive": "stop receiving", "Receive": "Stop Receiving"},
                                                fields = {"Title \U0001F3F7": f"[{song.title}]({song.search_url})", "Duration \U000023F1": f"`{DateTime.format_time(song.duration)}`"})

            if (response in StringTools.TRUE):
                if (currently_playing):
                    ctx.voice_client.stop()
                removed_source = await jukebox.remove_song(index, playlist_len)
                await self.text.answer(ctx, f"**The {position} song** in my playlist has been removed", "Song Succesfully Removed", fields = {"Title \U0001F3F7": f"[{song.title}]({song.search_url})", "Duration \U000023F1": f"`{DateTime.format_time(song.duration)}`"})


    # generate_playlist_pg(current_page, max_page, kwargs) Generates the page for view the playlist
    async def generate_playlist_pg(self, current_page: int, max_page: int, kwargs: Dict[str, Any]) -> EmbededMessage:
        description = kwargs["description"]
        title = kwargs["title"]
        playlist = kwargs["playlist"]
        current_song_index = kwargs["current_song_index"]
        song_loop = kwargs["song_loop"]
        ctx = kwargs["ctx"]

        indices = Pagination.get_indices(current_page, self.SONGS_PER_PAGE, len(playlist))
        start_index = indices["start_index"]
        end_index = indices["end_index"]

        playlist_msg = ""
        for i in range(start_index, end_index):
            duration = DateTime.format_time(playlist[i].duration)
            link_name = StringTools.limit_str(playlist[i].title, self.SONG_NAME_LIMIT)
            link = f"[{link_name}]({playlist[i].search_url})"
            playlist_msg += f"{i + 1}) {link}   {duration}"

            if (song_loop is not None and i == song_loop):
                playlist_msg += " \U0001F502"

            if (i == current_song_index):
                playlist_msg += " \U0001F530"
            playlist_msg += "\n"

        if (playlist_msg == ""):
            playlist_msg = "```bash\nThere are no songs in my playlist!\n```"
        embeded_message = self.embed.context_embed(ctx, f"{description}\n\n**Playlist** \U0001F3B5 \U0001F3B6\n{playlist_msg}", f"{Members.DEFAULT_BOT_NAME}'s Playlist in {ctx.guild.name}'", "light-purple")

        footer_msg = f"\U0001F4C3 pg:  {current_page} / {max_page}"
        embeded_message = self.embed.add_footer(ctx, embeded_message, footer_msg)
        return embeded_message


    # view(ctx) Views all the songs in the playlist
    async def view(self, ctx, jukebox: JukeBox = None, condition: List[AddSongState] = None):
        from_add = True
        if (jukebox is None):
            jukebox = await self.get_jukebox(ctx)
            from_add = False

        description = "Here are all the songs in my playlist:"
        title = f"{Members.DEFAULT_BOT_NAME}'s Playlist in {ctx.guild.name}"

        playlist_len = len(jukebox.playlist)
        page = Pagination.get_current_page(jukebox.current_song_index, self.SONGS_PER_PAGE)
        max_page = Pagination.get_total_pages(self.SONGS_PER_PAGE, playlist_len)

        generate_playlist_pg_kwargs = {"description": description,  "title": title, "playlist": jukebox.playlist,
                                       "current_song_index": jukebox.current_song_index, "song_loop": jukebox.options.song_loop, "ctx": ctx}
        embeded_message = await self.generate_playlist_pg(page, max_page, generate_playlist_pg_kwargs)
        paginated_components = Pagination.make_page_buttons(page, max_page)

        if (not from_add):
            await Pagination.paginated_send(ctx, self.client, embeded_message, paginated_components, page, max_page, self.generate_playlist_pg, generate_playlist_pg_kwargs)
        else:
            pages = [page]
            await Pagination.paginated_send(ctx, self.client, embeded_message, paginated_components, page, max_page, self.generate_playlist_pg, generate_playlist_pg_kwargs,
                                            pages = pages, update_max_page = True, items_per_page = self.SONGS_PER_PAGE, item_lst = jukebox.playlist, condition_left = condition,
                                            condition_right = AddSongState.Playlist, update_items = True)


    # resume(ctx, jukebox) Resumes playing the jukebox
    async def resume(self, ctx: commands.Context, jukebox: Optional[JukeBox] = None):
        error = False
        if (jukebox is None):
            jukebox = await self.get_jukebox(ctx)

        error = await self.not_in_voice_channel(ctx, jukebox)
        error = await self.is_playing(ctx, jukebox, error = error)
        error = await self.playing_empty(ctx, jukebox, error = error)

        if (not error):
            if (jukebox.state == VoiceState.Paused):
                ctx.voice_client.resume()
                jukebox.state = VoiceState.Playing
                current_song = jukebox.get_current_song()

                everybody = Dialogue.get_dialogue(Dialogue.DialogueCategory.Everybody)
                resume_msg = Dialogue.get_dialogue(Dialogue.DialogueCategory.SongBreakEnd)
                message = f"{everybody}! {resume_msg}\n\nI will now continue singing:\n[{current_song.title}]({current_song.search_url})!"
                title = f"{Members.DEFAULT_BOT_NAME}'s Break is Over"

                img_cat = self.get_random_img_cat([Pics.ImageCategory.Singing, Pics.ImageCategory.Happy])
                embeded_message = self.embed.context_embed(ctx, message, title, "light-blue", image = {img_cat: -1})
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

            elif (jukebox.state == VoiceState.Connected and not jukebox.playlist):
                embeded_message = self.embed.context_embed(ctx, "Please give me a song recommendation and I will sing it for you", "No Songs in Playlist", "red")
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

            else:
                await self.play(ctx)


    # get_singing_embed(jukebox, player) Gets the embeded message when the bot
    #   is playing audio
    def get_singing_embed(self, ctx: commands.Context, jukebox: JukeBox, player: YTDLSource) -> EmbededMessage:
        title = f"{Members.DEFAULT_BOT_NAME} is Singing {player.title}!"
        singing_msg = Dialogue.get_dialogue(Dialogue.DialogueCategory.Singing, song = f"{jukebox.current_song_index + 1}) [{player.title}]({player.search_url})")
        everybody = Dialogue.get_dialogue(Dialogue.DialogueCategory.Everybody)

        description = ""
        if (not jukebox.started_playing):
            jukebox.started_playing = True
            welcome_msg = Dialogue.get_dialogue(Dialogue.DialogueCategory.ConcertWelcome)
            song_order_msg = Dialogue.get_dialogue(Dialogue.DialogueCategory.FirstSong)
            description = f"{everybody}! {welcome_msg}\n\n"
        elif (jukebox.is_last_song()):
            song_order_msg = Dialogue.get_dialogue(Dialogue.DialogueCategory.LastSong)
            description = f"{everybody}! "
        else:
            song_order_msg = Dialogue.get_dialogue(Dialogue.DialogueCategory.NextSong)

        description += f"{song_order_msg}{singing_msg}"
        embeded_message = self.embed.context_embed(ctx, description, title, "light-purple", image = {Pics.ImageCategory.Singing: -1})
        return embeded_message


    # play_next(ctx, jukebox) Plays the next song in the playlist
    async def play_next(self, ctx: commands.Context, jukebox: JukeBox, current_song: YTDLSource):
        if (ctx.voice_client is not None):
            song_done_msg = Dialogue.get_dialogue(Dialogue.DialogueCategory.SongDone)
            embeded_message = self.embed.context_embed(ctx, song_done_msg, f"{Members.DEFAULT_BOT_NAME} Finished Singing {current_song.title}!", "light-purple")
            current_song.cleanup()
            await self.noticeable_msg_send(ctx, embeded_message, jukebox)

            jukebox.current_song_index = jukebox.get_next_song_index()
            await jukebox.reload_current_song()
            player = jukebox.get_current_song()

            embeded_message = self.get_singing_embed(ctx, jukebox, player)
            await self.noticeable_msg_send(ctx, embeded_message, jukebox)
            ctx.voice_client.play(player, after = lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx, jukebox, player), self.client.loop) if (not jukebox.is_last_song()) else asyncio.run_coroutine_threadsafe(self.end_concert(ctx, jukebox, player), self.client.loop))


    # play(ctx, query, jukebox) Plays a song
    async def play(self, ctx: commands.Context, query: str = StringTools.NONE, jukebox: Optional[JukeBox] = None):
        error = False
        state = PlayState.PlaySong

        query = StringTools.convert_str(query)
        if (jukebox is None):
            jukebox = await self.get_jukebox(ctx)

        if (not jukebox.playlist and query is None):
            embeded_message = Error.display_error(self.client, 15, correct_type = "audio source", parameter = "query")
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
            error = True

        elif (jukebox.playlist and query is not None):
            state = PlayState.AddSong

        if (not error):
            jukebox_state = jukebox.state

            if (jukebox_state == VoiceState.Paused):
                await self.resume(ctx, jukebox)
            elif (jukebox_state == VoiceState.Disconnected):
                embeded_message = self.embed.context_embed(ctx, f"\U0001F4A2 {Dialogue.get_dialogue(Dialogue.DialogueCategory.SongEnterEmbarassed)} \U0001F4A2 \n\n Pleasse, give me a moment...",
                                                           f"{Members.DEFAULT_BOT_NAME} is not Ready Yet!", "red", image = {Pics.ImageCategory.Embarassed: -1})
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file, delete_after = 5)
                await self.join(ctx, jukebox = jukebox)

                if (jukebox.state != VoiceState.Disconnected):
                    await self.play(ctx, query, jukebox = jukebox)
            elif (jukebox_state == VoiceState.Playing and query is not None):
                await self.add(ctx, query, jukebox = jukebox)

            elif(not(await self.is_playing(ctx, jukebox))):
                if (query is not None):
                    await self.add(ctx, query, jukebox = jukebox)

                await jukebox.reload_current_song()
                player = jukebox.get_current_song()
                jukebox.state = VoiceState.Playing
                embeded_message = self.get_singing_embed(ctx, jukebox, player)
                await self.noticeable_msg_send(ctx, embeded_message, jukebox)
                ctx.voice_client.play(player, after = lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx, jukebox, player), self.client.loop) if (not jukebox.is_last_song()) else asyncio.run_coroutine_threadsafe(self.end_concert(ctx, jukebox, player), self.client.loop))


    # skip(ctx) Skips the current song
    async def skip(self, ctx: commands.Context):
        jukebox = await self.get_jukebox(ctx)

        error = await self.not_in_voice_channel(ctx, jukebox)
        error = await self.playing_empty(ctx, jukebox, error = error)

        if (not error):
            current_song = jukebox.get_current_song()
            ctx.voice_client.stop()


    # pause(ctx) Pauses a song
    async def pause(self, ctx: commands.Context):
        jukebox = await self.get_jukebox(ctx)
        error = await self.not_in_voice_channel(ctx, jukebox)

        if (not error):
            jukebox_state = jukebox.state
            embeded_message  = None

            if (jukebox_state == VoiceState.Playing):
                ctx.voice_client.pause()
                jukebox.state = VoiceState.Paused
                pause_msg = Dialogue.get_dialogue(Dialogue.DialogueCategory.SongBreak)
                embeded_message = self.embed.context_embed(ctx, pause_msg, f"{Members.DEFAULT_BOT_NAME} is Taking a Break", "yellow")

            elif (jukebox_state == VoiceState.Paused):
                embeded_message = self.embed.context_embed(ctx, f"{Members.DEFAULT_BOT_NAME} is currently off the stage during the break", f"{Members.DEFAULT_BOT_NAME} is still on Break", "red")
            elif (jukebox_state == VoiceState.Connected):
                embeded_message = self.embed.context_embed(ctx, f"{Members.DEFAULT_BOT_NAME} is not on stage yet", f"{Members.DEFAULT_BOT_NAME} is not on stage yet", "red")

            if (embeded_message is not None):
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # singing_msg_action(jukebox) Get the prefix part of the message when changing a
    #   certain music setting
    def singing_msg_action(self, jukebox: JukeBox, old_value: int, new_value: int) -> str:
        if (old_value == new_value):
            message = "I'am already singing "
        else:
            message = "I will be singing "

        return message

    # vol(ctx, volume) Changes the volume for the bot
    async def vol(self, ctx: commands.Context, volume: str):
        error = False
        error, volume = await self.validate.validate_natural(ctx, error, volume, "volume", check_equal = True)

        if (not error):
            error = await self.validate.validate_inbetween(ctx, volume, "volume", 0, MAX_VOL, error)

        if (not error):
            jukebox = await self.get_jukebox(ctx)
            old_volume = jukebox.options.vol
            new_set_volume = jukebox.options.set_volume(volume)
            jukebox.change_volume(new_set_volume)

            message = ""
            title = f"{Members.DEFAULT_BOT_NAME} "
            colour = "blue-purple"
            image = None
            message = self.singing_msg_action(jukebox, old_volume, volume)

            if (old_volume == volume):
                title += "Already "
                colour = "yellow"

            if (volume == MAX_VOL):
                message += "as loud as possible!"
                title += " is Singing Her Hardest"
            elif (not volume and old_volume != volume):
                message = "Ok... I will be quiet..."
                title += "Reluctently Muted Themselves"
                image = {Pics.ImageCategory.Sad: -1}
            elif (not volume):
                message = "You *really* don't want to hear a **cute girl** singing for you, do you..."
                title += " Muted Themselves"
                image = {Pics.ImageCategory.Sad: -1}
            else:
                message += f"at volume `{volume}`"

                if (old_volume != volume):
                    title += "Changed Their Volume"
                else:
                    title += " is Singing at this Volume"
            embeded_message = self.embed.context_embed(ctx, message, title, colour, image = image)
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # tempo(ctx, speed) Changes the speed of the played audio
    async def tempo(self, ctx: commands.Context, speed: str):
        error = False
        error, speed = await self.validate.validate_float(ctx, error, speed, "speed")

        if (not error):
            error = await self.validate.validate_inbetween(ctx, speed, "speed", SPEED["MIN"], SPEED["MAX"], error)

        if (not error):
            jukebox = await self.get_jukebox(ctx)
            old_speed = jukebox.options.speed
            jukebox.options.speed = speed
            await jukebox.change_options()

            title = f"{Members.DEFAULT_BOT_NAME} "
            colour = "blue-purple"
            message = self.singing_msg_action(jukebox, old_speed, speed)

            if (speed == old_speed):
                title += "Already is Singing at this Tempo"
                colour = "yellow"
            else:
                title += " Changed their Tempo"

            if (speed == SPEED["MAX"]):
                message += "as fast as possible!"
            elif (speed == SPEED["MIN"]):
                message += "as slow as possible!"
            else:
                message += f"at `{speed * 100}%` of normal speed"

            embeded_message = self.embed.context_embed(ctx, message, title, colour)
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # is_interval(half_steps, type) Determines if 'half_steps' is the indicated interval
    #   based on 'type'
    def is_interval(self, half_steps: int, type: PerfectIntervalType) -> MusicInterval:
        result = None
        for i in PERFECT_INTERVALS:
            if (PERFECT_INTERVALS[i].in_interval(half_steps) == type):
                result = PERFECT_INTERVALS[i]
                break

        return result


    # get_relative_interval(half_steps) Get the relative interval for the pitch of the audio
    def get_relative_interval(self, half_steps: int) -> str:
        message = ""
        if (not half_steps):
            return "in the original key"
        else:
            if (half_steps > 0):
                relative_distance = "above"
            else:
                relative_distance = "below"

            hf_distance = abs(half_steps)
            perfect = self.is_interval(hf_distance, PerfectIntervalType.Perfect)
            diminished = self.is_interval(hf_distance, PerfectIntervalType.Perfect)
            if (perfect is not None):
                if (perfect.key_distance == OCTAVE):
                    message += "an `octave "
                else:
                    verbose_pos = StringTools.get_lineup_pos(perfect.key_distance)
                    message += f"a `perfect {verbose_pos} "

            elif (diminished is not None):
                verbose_pos = StringTools.get_lineup_pos(perfect.key_distance)
                message += f"a `diminished {verbose_pos} "

            else:
                major = "`major"
                minor = "`minor"
                interval, interval_type = divmod(hf_distance, 2)
                verbose_interval_type = ""

                if ((half_steps < PERFECT_INTERVALS["FOURTH"].hf_norm and not interval_type) or
                    (half_steps > PERFECT_INTERVALS["FOURTH"].hf_norm and interval_type)):
                    interval += 1
                    verbose_interval_type = major
                else:
                    interval += 2
                    verbose_interval_type = minor

                verbose_pos = StringTools.get_lineup_pos(interval)

                message += f"a {verbose_interval_type} {verbose_pos} "

            message += f"{relative_distance} the original key`"
            return message


    # pitch(ctx, half_steps) Change the pitch for the audio
    async def pitch(self, ctx: commands.Context, half_steps: str):
        error = False
        error, half_steps = await self.validate.validate_integer(ctx, error, half_steps, "half_steps")

        if (not error):
            error = await self.validate.validate_inbetween(ctx, half_steps, "half_steps", HALF_STEPS["MIN"], HALF_STEPS["MAX"], error)

        if (not error):
            jukebox = await self.get_jukebox(ctx)
            old_hf = jukebox.options.half_steps
            jukebox.options.half_steps = half_steps
            await jukebox.change_options()

            try:
                current_song = jukebox.get_current_song()
            except:
                pass
            else:
                current_song.change_ffmpeg_options(jukebox.options)

            title = f"{Members.DEFAULT_BOT_NAME} "
            colour = "blue-purple"

            message = self.singing_msg_action(jukebox, old_hf, half_steps)
            if (old_hf != half_steps):
                message += self.get_relative_interval(half_steps)
                title += "Changed their Pitch"
            else:
                message += "at this pitch"
                colour = "yellow"
                title += "is Already Singing at this Pitch"

            embeded_message = self.embed.context_embed(ctx, message, title, colour)
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # loop(ctx) Toggles between enable/disable the playlist's loop
    async def loop(self, ctx: commands.Context):
        jukebox = await self.get_jukebox(ctx)
        jukebox.options.playlist_loop = not(jukebox.options.playlist_loop)
        colour = "blue-purple"
        message = "I will "
        title = f"{Members.DEFAULT_BOT_NAME} "

        if (jukebox.options.playlist_loop):
            title = "Enabled "
        else:
            message += "not "
            title = "Disabled "
        message += "be singing in a loop"
        title += "Looping"

        embeded_message = self.embed.context_embed(ctx, message, title, colour)
        await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
