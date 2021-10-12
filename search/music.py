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
from typing import Dict, Any, Optional, List, Union, Callable
from text.bot_texting import Texting, DELETE_IGNORE_LST
import tools.dialogue as Dialogue
from tools.pagination import Pagination
from tools.abs_func import AbsFunc
import tools.search_yt as YtSearchTools
import tools.search_sp as SpSearchTools

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

SONG_SEPERATOR = "\n"

PLAYER_OPTION_INDICATORS = {"loop": "\U0001F501", "random": "\U0001F500", "repeat": "\U0001F502"}



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
    def __init__(self, playlist_loop: bool, song_loop: Optional[int], vol: float, speed: float, half_steps: int, random: bool):
        self.playlist_loop = playlist_loop
        self.song_loop = song_loop
        self.jump_loop = False
        self.vol = vol
        self.speed = speed
        self.half_steps = half_steps
        self.random = random


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
    def __init__(self, source: discord.AudioSource, *, data: Dict[str, Any], search_url: str, display_url: str, stream: bool, volume: float = (DEFAULT_VOL / MAX_VOL)):
        super().__init__(source, volume)
        self.data = data
        self.title = StringTools.word_replace(data.get('title'), {"[": "{", "]": "}"})
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.sample_rate = data.get('asr')
        self.search_url = search_url
        self.display_url = display_url
        self.stream = stream
        self.duration = int(data.get('duration'))
        self.duration_left = self.duration
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
        return cls(discord.FFmpegPCMAudio(filename, **new_ffmpeg_options), data=data, search_url = url, display_url = url, stream = stream, volume = options.vol / MAX_VOL)


    # spotify_prepare(url, options, sp_data, loop, stream) Prepares a spotify track
    #   to be played
    @classmethod
    async def spotify_prepare(cls, sp_data: SpSearchTools.SpTrackInfo, options: JukeBoxOptions, loop=None, stream: bool = False):
        song = await cls.prepare_music(sp_data.yt_link, options, loop = loop, stream = stream)
        song.display_url = sp_data.link
        song.title = sp_data.name
        return song


    # fast_prepare(ytdl_source) Prepares a new YTDLSource from an existing source
    @classmethod
    async def fast_prepare(cls, ytdl_source, options: JukeBoxOptions):
        data = ytdl_source.data
        ffmpeg_options = cls.get_ffmpeg_options(data, options)
        filename = data['url'] if ytdl_source.stream else YTDL.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options),
                   data = ytdl_source.data, search_url = ytdl_source.search_url, display_url = ytdl_source.display_url, stream = ytdl_source.stream, volume = ytdl_source.volume)


    # get_end_date() Gets the expected end date for the source
    def get_end_date(self) -> datetime.datetime:
        self.end_date = DateTime.get_current_dt(utc = True) + datetime.timedelta(seconds = self.duration_left)
        return self.end_date


    # reset_dates() Sets end date to none
    def reset_dates(self):
        self.end_date = None
        self.duration_left = self.duration


    # get_duration_left() Gets the duration left in the audio source
    def get_duration_left(self):
        try:
            duration_left = int((self.end_date - DateTime.get_current_dt(utc = True)).total_seconds())
        except:
            duration_left = self.duration_left

        if (duration_left < 0):
            duration_left = 0
        elif (duration_left > self.duration):
            duration_left = self.duration

        self.duration_left = duration_left
        return duration_left


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
        self.player_start_time = None
        self.adding_state = AddSongState.Song
        self.recent_player_msg = None


    # get_default_options(ctx) Gets the default options
    def get_default_options(self) -> JukeBoxOptions:
        return JukeBoxOptions(False, None, DEFAULT_VOL, SPEED["DEFAULT"], DEFAULT_PITCH, False)


    # get_song(index) Gets the song at 'index'
    # requires: 0 <= index < len(self.playlist)
    def get_song(self, index: int) ->  Optional[YTDLSource]:
        if (self.playlist):
            try:
                song = self.playlist[index]
            except:
                song = None

            return song
        else:
            return None


    # set_song(index, value) Sets the song at 'index' to 'value'
    # requires: 0 <= index < len(self.playlist)
    def set_song(self, index: int, value: YTDLSource):
        self.playlist[index] = value


    # get_current_song() Gets the current song in the jukebox
    def get_current_song(self) -> Optional[YTDLSource]:
        return self.get_song(self.current_song_index)


    # get_playlist_len() Gets the length of the playlist
    def get_playlist_len(self) -> int:
        return len(self.playlist)


    # get_repeated_song() Gets the song that is being repeated in the jukebox
    def get_repeated_song(self) -> Optional[YTDLSource]:
        if (self.playlist and self.options.song_loop is not None):
            return self.get_song(self.options.song_loop)
        else:
            return None


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

        if (self.options.song_loop is not None and before_not_empty and pos == self.options.song_loop):
            self.options.song_loop += 1


    #add_song(client, validate, source, pos, playlist_len, condition) Prepares a song or a list of
    #   songs to be added to the playlist
    async def add_song(self, client: discord.Client, validate: ValidateTools.Validate, source: str,
                       pos: int, playlist_len: Optional[int] = None, condition: Optional[List[AddSongState]] = None) -> List[Union[AddSongState, int]]:
        state = AddSongState.Song
        songs_added = 0
        from_list = False

        if (playlist_len is None):
            playlist_len = self.get_playlist_len()

        if (validate.valid_yt_link(source)):
            try:
                prepared_source = await YTDLSource.prepare_music(source, self.options, loop=client.loop, stream=True)
            except:
                state = AddSongState.NotFound

        # prepares source from playlists
        elif (validate.valid_audio_list(source)):
            from_list = True
            self.adding_state = AddSongState.Playlist
            from_spotify = False

            if (validate.valid_yt_playlist_link(source, check_link = False)):
                url_lst = await YtSearchTools.playlist_get_yt_links(client, source)
            else:
                from_spotify = True

                if (validate.valid_sp_album(source, check_link = False)):
                    url_lst = SpSearchTools.album_get_sp_links(source)
                else:
                    url_lst = SpSearchTools.playlist_get_sp_links(source)

            # add the song to the server playlist
            for url in url_lst:
                prepared_source = None

                if (not from_spotify):
                    try:
                        prepared_source = await YTDLSource.prepare_music(url, self.options, loop=client.loop, stream=True)
                    except:
                        pass
                else:
                    song_result = VideosSearch(f"{url.artist}: {url.name}", limit = 1)
                    song_result = song_result.result()["result"]

                    if (song_result):
                        song = song_result[0]
                        url.yt_link = song["link"]

                        try:
                            prepared_source = await YTDLSource.spotify_prepare(url, self.options, loop=client.loop, stream=True)
                        except:
                            pass

                if (prepared_source is not None):
                    self.insert_song(pos, prepared_source, playlist_len)
                    pos += 1
                    songs_added += 1

            if (condition is not None):
                self.adding_state = AddSongState.Song
                condition[0] = AddSongState.Song
                state = AddSongState.Playlist

        else:
            from_spotify = False
            if (validate.valid_sp_track(source)):
                from_spotify = True
                sp_data = SpSearchTools.track_get_link(source)
                source = f"{sp_data.artist}: {sp_data.name}"

            song_result = VideosSearch(source, limit = 1)
            song_result = song_result.result()["result"]

            if (song_result):
                song = song_result[0]
                try:
                    if (from_spotify):
                        sp_data.yt_link = song["link"]
                        prepared_source = await YTDLSource.spotify_prepare(sp_data, self.options, loop=client.loop, stream=True)
                    else:
                        prepared_source = await YTDLSource.prepare_music(song["link"], self.options, loop=self.loop, stream=True)
                except:
                    state = AddSongState.NotFound
            else:
                state = AddSongState.NotFound

        if (not from_list and state == AddSongState.Song):
            self.insert_song(pos, prepared_source, playlist_len)
            songs_added += 1

        return [state, songs_added]


    # lst_add_song(client, validate, source, pos, playlist_len, condition) Prepares list of songs or playlists
    #   to be added to the playlist
    async def lst_add_song(self, client: discord.Client, validate: ValidateTools.Validate, source: str,
                           pos: int, playlist_len: Optional[int] = None, condition: Optional[List[AddSongState]] = None) -> List[Union[AddSongState, int]]:
        state = AddSongState.Song
        songs_added = 0

        source_lst = source.split(SONG_SEPERATOR)
        source_lst_len = len(source_lst)

        for i in range(source_lst_len):
            source_lst[i] = source_lst[i].strip()

            if (source_lst[i] != ""):
                current_condition = None
                if (i == source_lst_len - 1):
                    current_condition = condition

                state, current_songs_added = await self.add_song(client, validate, source_lst[i], pos, condition = current_condition)

                songs_added += current_songs_added

                if (state != AddSongState.NotFound):
                    pos += current_songs_added

        if (songs_added > 1):
            self.adding_state = AddSongState.Song
            condition[0] = AddSongState.Song
            state = AddSongState.Playlist

        return [state, songs_added]


    # remove_song() Removes a song from the playlist
    async def remove_song(self, pos: int, playlist_len: Optional[int] = None) -> SongInfo:
        if (playlist_len is None):
            playlist_len = self.get_playlist_len()

        if (pos < 0):
            pos = 0
        elif(pos >= playlist_len):
            pos = playlist_len - 1

        removed_song = self.get_song(pos)
        removed_source = SongInfo(removed_song.title, removed_song.url, removed_song.duration)
        self.playlist.pop(pos)

        if (pos == self.current_song_index):
            self.current_song_index = self.get_previous_song_index()

        if (self.options.song_loop is not None and pos == self.options.song_loop):
            self.options.song_loop = None
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


    # get_next_song_index() Gets the index for the next song
    def get_next_song_index(self) -> int:
        if (self.options.song_loop is not None and self.current_song_index == self.options.song_loop):
            return self.current_song_index
        else:
            playlist_len = self.get_playlist_len()

            if (self.options.random):
                return random.randrange(0, playlist_len)
            elif (self.current_song_index >= playlist_len - 1 or self.current_song_index < 0):
                return 0
            else:
                return self.current_song_index + 1


    # get_previous_song_index() Gets the index for the previous song
    # requires: 0 <= relative_index < len(self.playlist)
    def get_previous_song_index(self, relative_index: Optional[int] = None) -> int:
        if (relative_index is None):
            index = self.current_song_index
        else:
            index = relative_index

        if (not index):
            return self.get_playlist_len() - 1
        else:
            return index - 1


    # is_last_song() Determines if the current song is the last song being played
    def is_last_song(self) -> bool:
        if (self.options.random):
            return False

        last_index = self.get_playlist_len() - 1
        result = (self.current_song_index == last_index and
                  not self.options.playlist_loop and not self.options.jump_loop and
                  (self.options.song_loop is None or self.options.song_loop != last_index))

        if (self.options.jump_loop):
            self.options.jump_loop = False
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
        self.current_song_index = 0
        self.options.song_loop = None


    # is_playing() Checks if the bot is playing an audio
    def is_playing(self) -> bool:
        return (self.state == VoiceState.Playing or self.state == VoiceState.Paused)


    # change_options() Changes the options for all the songs in the playlist
    async def change_options(self):
        playlist_len = self.get_playlist_len()
        for i in range(playlist_len):
            if (not(self.is_playing() and i == self.current_song_index)):
                current_song = self.get_song(i)
                self.set_song(i, await YTDLSource.fast_prepare(current_song, self.options))


    # reload_song(self) Reloads the song once it is done playing
    # requires: 0 <= song_index < len(self.playlist)
    async def reload_song(self, song_index: int) -> bool:
        success = True
        song = self.get_song(song_index)

        if (song is not None):
            song_url = song.search_url
            try:
                song.read()
            except:
                self.set_song(song_index, await YTDLSource.prepare_music(song_url, self.options, loop=self.loop, stream=True))
        else:
            success = False
        return success


    # reload_current_song(self) Reloads the current song once it is done playing
    async def reload_current_song(self):
        success = await self.reload_song(self.current_song_index)

        if (not success):
            self.current_song_index = self.get_previous_song_index()


    # change_volume(vol) Changes the volume for all songs in the playlist
    # requires: 0 <= vol <= 1
    def change_volume(self, vol):
        for s in self.playlist:
            s.volume = vol


    # get_player_start_time() Changes the time of when the jukebox is updating
    #   the progress bar to a song session
    def get_player_start_time(self) -> datetime.datetime:
        play_date = DateTime.get_current_dt(utc = True)
        self.player_start_time = play_date
        return play_date


    # get_player_opt_indicator(condition, index) Get the option to indicated for
    #   the song player
    def get_player_opt_indicator(self, condition: bool, index: str) -> str:
        result = ""
        if (condition):
            result = PLAYER_OPTION_INDICATORS[index]
        return result


    # get_loop_indicator() Gets the indicator for looping the playlist
    def get_loop_indicator(self) -> str:
        return self.get_player_opt_indicator(self.options.playlist_loop, "loop")


    # get_repeat_loop () Gets the indicator for repeating a song in the playlist
    def get_repeat_indicator(self) -> str:
        return self.get_player_opt_indicator(bool(self.options.song_loop is not None and self.options.song_loop == self.current_song_index), "repeat")


    # get_random_indicator() Gets the indicator for playing songs at random in
    #   in the playlist
    def get_random_indicator(self) -> str:
        return self.get_player_opt_indicator(self.options.random, "random")


    # swap(index_1, index_2) Swaps 2 songs in the playlist
    # requires: 0 <= index_1 <= index_2 < len(self.playlist)
    def swap(self, index_1, index_2):
        temp_song_1 = self.get_song(index_1)
        temp_song_2 = self.get_song(index_2)
        self.set_song(index_1, temp_song_2)
        self.set_song(index_2, temp_song_1)

        if (self.current_song_index == index_1):
            self.current_song_index = index_2
        elif (self.current_song_index == index_2):
            self.current_song_index = index_1

        if (self.options.song_loop is not None):
            if (self.options.song_loop == index_1):
                self.options.song_loop = index_2
            elif (self.options.song_loop == index_2):
                self.options.song_loop = index_1



class ServerMusic():
    def __init__(self, client):
        self.client = client
        self.embed = Embed(client)
        self.search_tools = SearchTools(client)
        self.validate = ValidateTools.Validate(client)
        self.SONGS_PER_PAGE = 20
        self.SONG_NAME_LIMIT = 30
        self.DURATION_BAR_LEN = 20
        self.READ_PER_SEC = 50
        self.MAX_SKIP_SEC = 300
        self.UPDATE_PLAYER_TIME = 4
        self.JUMP_PLAY_DELAY = 10
        self.PLAYER_DELAY = 5
        self.text = Texting(client)
        self.music_settings = MusicSettings(client)


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
    async def noticeable_msg_send(self, ctx: commands.Context, embeded_message: EmbededMessage, jukebox: JukeBox, delay: int = 0) -> discord.Message:
        if (jukebox.recent_message is None):
            jukebox.recent_message = await ctx.send(embed = embeded_message.embed, file = embeded_message.file, delay = delay)
        else:
            jukebox.recent_message = await self.text.noticeable_edit(ctx, jukebox.recent_message, embeded_message, keep_attachments = False, delay = delay)
        return jukebox.recent_message


    # validate_cond(ctx, jukebox, condition, error_func, verbose, error)
    #   checks 'condition' has been triggered
    async def validate_cond(self, condition: bool, error_func: AbsFunc, verbose: bool = True, error: Optional[bool] = None) -> bool:
        match_cond = False
        if ((error is None or (error is not None and not error)) and condition):
            if (verbose):
                await error_func.async_run()
            match_cond = True
        elif (error is not None and error):
            return error

        return match_cond


    # not_in_voice_channel_action(ctx, jukebox) The resultant action if
    #   the bot is not connected to a voice channel
    async def not_in_voice_channel_action(self, ctx: commands.Context, jukebox: JukeBox):
        jukebox.state = VoiceState.Disconnected
        embeded_message = self.embed.context_embed(ctx, f"I'am currently not in a live concert. Come enjoy seeing me singing live using the command `{Prefix.DEFAULT_PREFIX}join`", "Not in a Live Convert", "red")
        await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # not_in_voice_channel(ctx, jukebox, verbose, error) Determines if the bot is
    #   connected to a voice channel
    # effects: sends an embed
    async def not_in_voice_channel(self, ctx: commands.Context, jukebox: JukeBox, verbose: bool = True, error: Optional[bool] = None) -> bool:
        error_func = AbsFunc(self.not_in_voice_channel_action, [ctx, jukebox])
        return await self.validate_cond(bool(ctx.voice_client is None), error_func, verbose = verbose, error = error)


    # is_playing_action(ctx, jukebox) The resultant action if the bot is
    #   playing a song
    async def is_playing_action(self, ctx: commands.Context, jukebox: JukeBox):
        jukebox.state = VoiceState.Playing
        current_song = jukebox.get_current_song()
        embeded_message = self.embed.context_embed(ctx, f"Right now, I'am in the middle of singing **song #{jukebox.current_song_index + 1}** [{current_song.title}]({current_song.display_url})", "Already Singing a Song", "red")
        await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # is_playing(ctx, jukebox, verbose, error) Checks if the bot is playing an audio file
    # effects: sends an embed
    async def is_playing(self, ctx: commands.Context, jukebox: JukeBox, verbose: bool = True, error: Optional[bool] = None) -> bool:
        error_func = AbsFunc(self.is_playing_action, [ctx, jukebox])
        return await self.validate_cond(bool(ctx.voice_client is not None and ctx.voice_client.is_playing()), error_func, verbose = verbose, error = error)


    # not_playing_action(ctx, jukebox) The resultant action if the bot is
    #   not playing a song
    async def not_playing_action(self, ctx: commands.Context, jukebox: JukeBox):
        embeded_message = self.embed.context_embed(ctx, f"Right now, I'am not on stage singing a song", "Not singing a song", "red")
        await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # not_playing(ctx, jukebox, verbose, error) Checks if the bot is not
    #   playing a song
    async def not_playing(self, ctx: commands.Context, jukebox: JukeBox, verbose: bool = True, error: Optional[bool] = None):
        error_func = AbsFunc(self.not_playing_action, [ctx, jukebox])
        return await self.validate_cond(bool(ctx.voice_client is None or not (ctx.voice_client.is_playing() or ctx.voice_client.is_paused())), error_func, verbose = verbose, error = error)


    # playing_empty_action(ctx, jukebox) The resultant action if the playlist is empty
    #   and the bot is about to play a song
    async def playing_empty_action(self, ctx: commands.Context, jukebox: JukeBox):
        embeded_message = self.embed.context_embed(ctx, "Please give me a song recommendation and I will sing it for you", "No Songs in Playlist", "red")
        await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # playing_empty(ctx, jukebox, verbose, error) Checks if the bot is about to play a song
    #   even though there are no songs in its playlist
    # effects: sends an embed
    async def playing_empty(self, ctx: commands.Context, jukebox: JukeBox, verbose: bool = True, error: Optional[bool] = None) -> bool:
        error_func = AbsFunc(self.playing_empty_action, [ctx, jukebox])
        return await self.validate_cond(bool(jukebox.state == VoiceState.Connected and not jukebox.playlist), error_func, verbose = verbose, error = error)


    # empty_playlist_action(ctx, jukebox) The resultant action if the playlist is empty
    async def empty_playlist_action(self, ctx: commands.Context, jukebox: JukeBox):
        error = True
        embeded_message = Error.display_error(self.client, 19, action = "remove songs", reason = " because there are no songs in the playlist. But you could give her a song recommendation that you want her to sing.")
        await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # empty_playlist(ctx, jukebox, verbose, error) Checks if the playlist in the
    #   jukebox is empty
    # effects: sends an embed
    async def empty_playlist(self, ctx: commands.Context, jukebox: JukeBox, verbose: bool = True, error: Optional[bool] = None) -> bool:
        error_func = AbsFunc(self.playing_empty_action, [ctx, jukebox])
        return await self.validate_cond(bool(not jukebox.get_playlist_len()), error_func, verbose = verbose, error = error)


    # is_playing_current_song(jukebox) Check if the jukebox is currently playing\
    #   the current song
    def is_playing_current_song(self, jukebox: JukeBox, index: int) -> List[Union[bool, str]]:
        currently_playing = False
        question_message = ""
        if (index == jukebox.current_song_index and ((jukebox.state == VoiceState.Playing) or (jukebox.state == VoiceState.Paused))):
            currently_playing = True
            question_message = "**Warning \U000026A0**\nI'am currently in the middle of singing this song\n\n"

        return [currently_playing, question_message]


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
        current_song.reset_dates()
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


            if (ctx.voice_client is not None and (voice_channel is None or voice_channel == ctx.voice_client.channel)):
                embeded_message = self.embed.context_embed(ctx, f"I'am already on stage! Please hear me at `{ctx.voice_client.channel.name}` ({StringTools.format_channel(ctx.voice_client.channel.id)})!", f"{bot_nickname} is Already on Stage", "yellow")
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

            else:
                if (voice_channel is None):
                    await voice.channel.connect()
                    await ctx.voice_client.disconnect()
                    await voice.channel.connect()
                    voice_channel = voice.channel
                else:
                    if (ctx.voice_client is not None):
                        await ctx.voice_client.disconnect()

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

        jukebox.recent_message = None


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
            jukebox.recent_message = None

            try:
                await ctx.voice_client.disconnect()
                jukebox.state = VoiceState.Disconnected
                jukebox.started_playing = False
            except:
                pass


    # view_loading_songs(ctx, jukebox) Slowly updates the songs that are being
    #   loaded into the playlist
    # effects: deletes and edits embeds
    async def view_loading_songs(self, ctx: commands.Context, jukebox: JukeBox, check_func: AbsFunc) -> Optional[discord.Message]:
        embeded_message = self.embed.context_embed(ctx, "Loading these songs may take a while...\n\nMeanwhile, you can view your songs slowly being added here:", "Adding Songs May Take Some Time...", "light-purple")
        loading_msg = await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

        view_page = await self.view(ctx, jukebox = jukebox, check_func = check_func)
        DELETE_IGNORE_LST.append(loading_msg.id)
        await loading_msg.delete()
        return view_page


    # is_lst_adding(current_state, before_state) Checks if the bot is currently
    #   adding songs into its playlist for a certain jukebox
    def is_lst_adding(self, current_state: List[AddSongState], before_state: AddSongState):
        return (before_state == current_state[0])


    # add(ctx, query) Adds a song to the playlist
    async def add(self, ctx: commands.Context, query: str, index: str = StringTools.NONE, jukebox: Optional[JukeBox] = None):
        error = False
        if (jukebox is None):
            jukebox = await self.get_jukebox(ctx)
        playlist_len = jukebox.get_playlist_len()

        query = query.strip()
        error, index = await self.validate.validate_natural(ctx, error, index, "index", allow_optional = True, check_equal = True)

        if (not error):
            if (index is None):
                index = playlist_len + 1
            else:
                error = await self.validate.validate_inbetween(ctx, index, "index", 1, playlist_len, error)

        if (not error):
            no_of_songs = 0
            index -= 1

            if (self.validate.valid_audio_list(query) or query.find(SONG_SEPERATOR) != -1):
                before_no_of_songs = jukebox.get_playlist_len()
                jukebox.adding_state = AddSongState.Playlist
                condition = [jukebox.adding_state]
                check_func = AbsFunc(self.is_lst_adding, args = [condition, AddSongState.Playlist])

                tasks = [self.view_loading_songs(ctx, jukebox, check_func),
                         jukebox.lst_add_song(self.client, self.validate, query, index, playlist_len = playlist_len, condition = condition)]
                done, pending = await asyncio.wait(tasks)
                add_state = AddSongState.Playlist
                no_of_songs = jukebox.get_playlist_len() - before_no_of_songs

            else:
                add_state, no_of_songs = await jukebox.lst_add_song(self.client, self.validate, query, index, playlist_len = playlist_len)

            if (add_state == AddSongState.NotFound):
                embeded_message = Error.display_error(self.client, 18, member = "audio source", member_search_type = "name", search_member = query)
            elif (add_state == AddSongState.Playlist):
                for t in done:
                    if (tasks[0] == t.get_coro()):
                        loading_view_pg = t.result()
                        DELETE_IGNORE_LST.append(loading_view_pg.id)
                        await loading_view_pg.delete()
                embeded_message = self.embed.context_embed(ctx, f"Your selection of **{no_of_songs} songs** have been added to my playlist", f"{Members.DEFAULT_BOT_NAME} Took in Your Selected Playlist", "light-purple")
            else:
                prepared_video = jukebox.get_song(index)
                embeded_message = self.embed.context_embed(ctx, "Your song has been added to my playlist", f"{Members.DEFAULT_BOT_NAME} Took in Your Selected Song", "light-purple")
                embeded_message = self.embed.multi_add_section(embeded_message, {"Title \U0001F3F7": f"**{index + 1}) [{prepared_video.title}]({prepared_video.display_url})**", "Duration \U000023F1": f"`{DateTime.format_time(int(prepared_video.duration))}`"})

            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

            if (add_state == AddSongState.Playlist):
                await self.view(ctx, jukebox = jukebox)


    # remove(ctx, index) Removes a song from the playlist
    async def remove(self, ctx: commands.Context, index: str):
        jukebox = await self.get_jukebox(ctx)
        playlist_len = jukebox.get_playlist_len()
        error = False
        error, index = await self.validate.validate_natural(ctx, error, index, "index", check_equal = True)
        error = await self.empty_playlist(ctx, jukebox, error = error)
        error = await self.validate.validate_inbetween(ctx, index, "index", 1, playlist_len, error)

        if (not error):
            index -= 1
            song = jukebox.get_song(index)
            currently_playing = False

            question_message = ""
            question_title = "Remove Song?"
            position = f"{StringTools.get_lineup_pos(index + 1)}"
            currently_playing, question_message = self.is_playing_current_song(jukebox, index)
            question_message += f"Do you want to remove **the {position} song** from my playlist?"
            response = await self.text.question(ctx, question_message, question_title,
                                                fields = {"Title \U0001F3F7": f"**[{song.title}]({song.display_url})**", "Duration \U000023F1": f"`{DateTime.format_time(song.duration)}`"})

            if (response in StringTools.TRUE):
                if (currently_playing):
                    ctx.voice_client.stop()
                removed_source = await jukebox.remove_song(index, playlist_len)
                await self.text.answer(ctx, f"**The {position} song** in my playlist has been removed", "Song Succesfully Removed", fields = {"Title \U0001F3F7": f"**{index + 1}) [{song.title}]({song.display_url})**", "Duration \U000023F1": f"`{DateTime.format_time(song.duration)}`"})


    # clear(ctx) Clears the playlist
    async def clear(self, ctx: commands.Context):
        jukebox = await self.get_jukebox(ctx)
        error = False
        error = await self.empty_playlist(ctx, jukebox, error = error)

        if (not error):
            question_title = "Clear Playlist?"
            currently_playing, question_message = self.is_playing_current_song(jukebox, jukebox.current_song_index)
            question_message += "Are you sure you want to clear the playlist"
            no_of_cleared_songs = jukebox.get_playlist_len()
            songs_article = StringTools.get_pronouns(no_of_cleared_songs, {-1:'Songs', 1: 'Song'})
            response = await self.text.question(ctx, question_message, question_title, fields = {"No. of Songs in Playlist \U0001F3A4": f"`{songs_article}`"})

            if (response in StringTools.TRUE):
                if (currently_playing):
                    voice = ctx.author.voice
                    await ctx.voice_client.disconnect()
                    jukebox.state = VoiceState.Connected
                    await asyncio.sleep(self.PLAYER_DELAY)
                    await voice.channel.connect()

                jukebox.clear_playlist()
                await self.text.answer(ctx, f"All the songs in my playlist have been cleared", "Playlist Successfully Cleared", fields ={"No. of Songs Cleared \U0001F3A4": f"`{songs_article}`"})


    # format_player_duration(jukebox, current_song) Formats the visualization for
    #   the duration of an audio souce
    def format_player(self, jukebox: JukeBox, current_song: YTDLSource) -> str:
        current_secs = current_song.duration - current_song.duration_left
        current_time = DateTime.format_time(current_secs)
        total_time = DateTime.format_time(current_song.duration)

        play_icon = "\U000023F8"
        if (jukebox.state == VoiceState.Playing):
            play_icon = "\U000025B6"

        duration_bar = ["▬"] * self.DURATION_BAR_LEN
        duration_pos = int((current_secs / current_song.duration) * (len(duration_bar) - 1))

        duration_bar[duration_pos] = "\U0001F7E3"
        duration_bar = "".join(duration_bar)

        loop_indicator = jukebox.get_loop_indicator()
        repeat_indicator = jukebox.get_repeat_indicator()
        random_indicator = jukebox.get_random_indicator()

        duration_bar = f"`{loop_indicator} {play_icon} {duration_bar}  {current_time} / {total_time} {repeat_indicator} {random_indicator}`"
        return duration_bar


    # generate_playlist_pg(current_page, max_page, kwargs) Generates the page for view the playlist
    async def generate_playlist_pg(self, current_page: int, max_page: int, kwargs: Dict[str, Any]) -> EmbededMessage:
        description = kwargs["description"]
        title = kwargs["title"]
        jukebox = kwargs["jukebox"]
        playlist = jukebox.playlist
        current_song_index = jukebox.current_song_index
        song_loop = jukebox.options.song_loop
        ctx = kwargs["ctx"]
        check_func = kwargs["check_func"]

        indices = Pagination.get_indices(current_page, self.SONGS_PER_PAGE, len(playlist))
        start_index = indices["start_index"]
        end_index = indices["end_index"]

        # format the songs in the playlist
        current_song = None
        playlist_msg = ""

        continue_indicator_len = len(StringTools.DEFAULT_CONTINUE_INDICATOR)

        for i in range(start_index, end_index):
            duration = DateTime.format_time(playlist[i].duration)
            link_name = StringTools.limit_str(playlist[i].title, self.SONG_NAME_LIMIT)
            title_len = len(playlist[i].title)

            link = f"[{link_name}]({playlist[i].display_url})"
            song_msg = f"{i + 1}) {link} `{duration}`"

            if (song_loop is not None and i == song_loop):
                song_msg += f" {PLAYER_OPTION_INDICATORS['repeat']}"

            if (i == current_song_index):
                song_msg = f"**{song_msg}**"
                song_msg += " \U0001F530"
            playlist_msg += f"{song_msg}\n"

        if (playlist_msg == ""):
            playlist_msg = "```bash\nThere are no songs in my playlist!\n```"

        embed_description = f"{description}\n\n**Playlist** \U0001F3B5 \U0001F3B6\n{playlist_msg}"

        player_title = "Current Song \U0001F3A4 \U0001F3A7"
        player_message = "`I'am not singing a song right now!\n`"

        if (check_func is None):
            if (jukebox.is_playing()):
                current_song = jukebox.get_current_song()
                if (jukebox.state == VoiceState.Playing):
                    current_song.get_duration_left()

                player_message = f"**{jukebox.current_song_index + 1}) [{current_song.title}]({current_song.display_url})**\n"
                player_message += self.format_player(jukebox, current_song)

            embed_description += f"\n\n**{player_title}**\n{player_message}"

        embeded_message = self.embed.context_embed(ctx, embed_description, f"{Members.DEFAULT_BOT_NAME}'s Playlist in {ctx.guild.name}'", "light-purple")

        footer_msg = f"\U0001F4C3 pg:  {current_page} / {max_page}"
        embeded_message = self.embed.add_footer(ctx, embeded_message, footer_msg)
        return embeded_message


    # view(ctx) Views all the songs in the playlist
    async def view(self, ctx, jukebox: JukeBox = None, check_func: Optional[AbsFunc] = None, description: Optional[str] = None) -> Optional[discord.Message]:
        from_add = True
        if (jukebox is None):
            jukebox = await self.get_jukebox(ctx)
            from_add = False

        if (description is None):
            description = "Here are all the songs in my playlist:"
        title = f"{Members.DEFAULT_BOT_NAME}'s Playlist in {ctx.guild.name}"

        playlist_len = jukebox.get_playlist_len()
        page = Pagination.get_current_page(jukebox.current_song_index, self.SONGS_PER_PAGE)
        max_page = Pagination.get_total_pages(self.SONGS_PER_PAGE, playlist_len)

        generate_playlist_pg_kwargs = {"description": description,  "title": title, "jukebox": jukebox, "ctx": ctx, "check_func": check_func}
        embeded_message = await self.generate_playlist_pg(page, max_page, generate_playlist_pg_kwargs)
        generate_pg = AbsFunc(self.generate_playlist_pg, kwargs = {"kwargs": generate_playlist_pg_kwargs})
        paginated_components = Pagination.make_page_buttons(page, max_page)
        pages = [page]

        if (not from_add and check_func is not None):
            current_song = jukebox.get_current_song()
            play_date = jukebox.get_player_start_time()

            player_msg = await ctx.send(embed = embeded_message.embed, file = embeded_message.file, components = paginated_components)
            jukebox.recent_player_msg = player_msg
            check_func = AbsFunc(self.check_player_update, args = [jukebox, play_date, player_msg, current_song])
            await Pagination.page_react(self.client, player_msg, page, max_page, generate_pg, pages = pages,
                                        update_max_page = True, items_per_page = self.SONGS_PER_PAGE, item_lst = jukebox.playlist,
                                        check_func = check_func, update_items = True, after_react = True)
        elif (check_func is not None):
            return await Pagination.paginated_send(ctx, self.client, embeded_message, paginated_components, page, max_page, generate_pg,
                                                   pages = pages, update_max_page = True, items_per_page = self.SONGS_PER_PAGE, item_lst = jukebox.playlist,
                                                   check_func = check_func, update_items = True)

        else:
            player_msg = await ctx.send(embed = embeded_message.embed, file = embeded_message.file, components = paginated_components)
            jukebox.recent_player_msg = player_msg
            check_func = AbsFunc(self.check_recent_player_msg, args = [jukebox, player_msg])
            await Pagination.page_react(self.client, player_msg, page, max_page, generate_pg, pages = pages,
                                        update_max_page = True, items_per_page = self.SONGS_PER_PAGE, item_lst = jukebox.playlist,
                                        check_func = check_func, update_items = True, after_react = True)
            return player_msg


    #  check_recent_player_msg(jukebox, player_msg) Checks if 'player_msg'
    #   is the message where the progress bar for the player is being updated
    def check_recent_player_msg(self, jukebox: JukeBox, player_msg = discord.Message):
        return (jukebox.recent_player_msg is not None and player_msg.id == jukebox.recent_player_msg.id)


    # check_player_update(jukebox, play_date, player_msg, current_song) Checks if
    #   the progress bar for the player needs to be updated
    def check_player_update(self, jukebox: JukeBox, play_date: datetime.datetime, player_msg: discord.Message, current_song: YTDLSource):
        return (jukebox.player_start_time is not None and play_date == jukebox.player_start_time and
                self.check_recent_player_msg(jukebox, player_msg) and
                current_song is not None and current_song.end_date is not None)


    # update_player(embed_func) Updates the song progress bar when the bot
    async def update_player(self, ctx: commands.Context, jukebox: JukeBox, embed_func: AbsFunc, play_date: datetime.datetime, player_msg: discord.Message, current_song: YTDLSource):
        while (self.check_player_update(jukebox, play_date, player_msg, current_song)):
            await asyncio.sleep(self.UPDATE_PLAYER_TIME)

            if (self.check_player_update(jukebox, play_date, player_msg, current_song)):
                embeded_message = None
                try:
                    current_song.get_duration_left()
                    embeded_message = embed_func.run()
                except:
                    break

                if (embeded_message is not None):
                    try:
                        await player_msg.edit(embed = embeded_message.embed)
                    except:
                        player_msg = await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
                        jukebox.recent_player_msg = player_msg



    # get_resume_embed(jukebox, current_song, message_ptr, image_ptr) Creates the
    #   embed for the resume page
    def get_resume_embed(self, ctx: commands.Context, jukebox: JukeBox, current_song: YTDLSource, message_ptr: List[Optional[str]] = [None],
                         image_ptr: List[int] = [-1], image_cat_ptr: List[Optional[Pics.ImageCategory]] = [None]) -> EmbededMessage:
        if (message_ptr[0] is None):
            everybody = Dialogue.get_dialogue(Dialogue.DialogueCategory.Everybody)
            resume_msg = Dialogue.get_dialogue(Dialogue.DialogueCategory.SongBreakEnd)
            message = f"{everybody}! {resume_msg}\n\nI will now continue singing:\n**[{current_song.title}]({current_song.display_url})**!"
            message_ptr[0] = message
        else:
            message = message_ptr[0]

        title = f"{Members.DEFAULT_BOT_NAME}'s Break is Over"

        if (image_cat_ptr[0] is None):
            img_cat = self.get_random_img_cat([Pics.ImageCategory.Singing, Pics.ImageCategory.Happy])
            image_cat_ptr[0] = img_cat
        else:
            img_cat = image_cat_ptr[0]

        if (image_ptr[0] == -1):
            image_index = random.randrange(0, len(Pics.IMAGE_LIST[img_cat]))
            image_ptr[0] = image_index
        else:
            image_index = image_ptr[0]

        embeded_message = self.embed.context_embed(ctx, message, title, "light-blue", image = {img_cat: image_index})
        player_msg = self.format_player(jukebox, current_song)
        embeded_message.embed.description += f"\n{player_msg}"
        return embeded_message


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
                current_song.get_end_date()
                play_date = jukebox.get_player_start_time()

                message_ptr = [None]
                image_ptr = [-1]
                image_cat_ptr = [None]
                embeded_message = self.get_resume_embed(ctx, jukebox, current_song, message_ptr = message_ptr, image_ptr = image_ptr, image_cat_ptr = image_cat_ptr)
                player_msg = await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
                jukebox.recent_player_msg = player_msg
                jukebox.recent_message = player_msg

                generate_embed = AbsFunc(self.get_resume_embed, args = [ctx, jukebox, current_song], kwargs = {"image_ptr": image_ptr, "message_ptr": message_ptr, "image_cat_ptr": image_cat_ptr})
                await self.update_player(ctx, jukebox, generate_embed, play_date, player_msg, current_song)

            elif (jukebox.state == VoiceState.Connected and not jukebox.playlist):
                embeded_message = self.embed.context_embed(ctx, "Please give me a song recommendation and I will sing it for you", "No Songs in Playlist", "red")
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

            else:
                await self.play(ctx)


    # get_singing_embed(jukebox, player) Gets the embeded message when the bot
    #   is playing audio
    # requires: if image_index is not None, then 0 <= image_index < len(Pics.ImageCategory.Singing)
    def get_singing_embed(self, ctx: commands.Context, jukebox: JukeBox, player: YTDLSource, image_ptr: Optional[List[int]] = None, description_ptr: List[Optional[str]] = [None]) -> EmbededMessage:
        title = f"{Members.DEFAULT_BOT_NAME} is Singing {player.title}!"

        if (description_ptr[0] is None):
            singing_msg = Dialogue.get_dialogue(Dialogue.DialogueCategory.Singing, song = f"**{jukebox.current_song_index + 1}) [{player.title}]({player.display_url})**")
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
            description_ptr[0] = description
        else:
            description = description_ptr[0]

        if (image_ptr is None):
            image_ptr = [-1]
        elif (image_ptr[0] == -1):
            index = random.randrange(0, len(Pics.IMAGE_LIST[Pics.ImageCategory.Singing]))
            image_ptr[0] = index

        embeded_message = self.embed.context_embed(ctx, description, title, "light-purple", image = {Pics.ImageCategory.Singing: image_ptr[0]})
        current_song = jukebox.get_current_song()
        player_msg = self.format_player(jukebox, current_song)
        embeded_message.embed.description += f"\n{player_msg}"
        return embeded_message


    # play_next(ctx, jukebox) Plays the next song in the playlist
    async def play_next(self, ctx: commands.Context, jukebox: JukeBox, current_song: YTDLSource):
        if (ctx.voice_client is not None):
            song_done_msg = Dialogue.get_dialogue(Dialogue.DialogueCategory.SongDone)
            embeded_message = self.embed.context_embed(ctx, song_done_msg, f"{Members.DEFAULT_BOT_NAME} Finished Singing {current_song.title}!", "light-purple")
            current_song.cleanup()
            current_song.reset_dates()

            jukebox.current_song_index = jukebox.get_next_song_index()
            await jukebox.reload_current_song()
            player = jukebox.get_current_song()

            await self.noticeable_msg_send(ctx, embeded_message, jukebox)
            await asyncio.sleep(self.PLAYER_DELAY)


            play_date = jukebox.get_player_start_time()
            player.get_end_date()
            img_index_ptr = [-1]
            description_ptr = [None]
            embeded_message = self.get_singing_embed(ctx, jukebox, player, image_ptr = img_index_ptr, description_ptr = description_ptr)
            player_msg = await self.noticeable_msg_send(ctx, embeded_message, jukebox)

            jukebox.recent_player_msg = player_msg
            ctx.voice_client.play(player, after = lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx, jukebox, player), self.client.loop) if (not jukebox.is_last_song()) else asyncio.run_coroutine_threadsafe(self.end_concert(ctx, jukebox, player), self.client.loop))

            generate_embed = AbsFunc(self.get_singing_embed, args = [ctx, jukebox, player], kwargs = {"image_ptr": img_index_ptr, "description_ptr": description_ptr})
            await self.update_player(ctx, jukebox, generate_embed, play_date, player_msg, player)


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
                tasks = [self.play_song(ctx, jukebox)]
                if (query is not None):
                    tasks.append(self.add(ctx, query, jukebox = jukebox))

                await asyncio.gather(*tasks)


    # play_song(ctx, jukebox) Plays a song on the server's jukebox once
    #   a song is loaded and the jukebox is in the correct state
    async def play_song(self, ctx: commands.Context, jukebox: JukeBox):
        # delay to wait until a song has been added to the playlist
        while (not jukebox.playlist):
            await asyncio.sleep(1)

        await jukebox.reload_current_song()
        player = jukebox.get_current_song()
        player.get_end_date()

        jukebox.state = VoiceState.Playing
        img_index_ptr = [-1]
        description_ptr = [None]
        embeded_message = self.get_singing_embed(ctx, jukebox, player, image_ptr = img_index_ptr, description_ptr = description_ptr)
        player_msg = await self.noticeable_msg_send(ctx, embeded_message, jukebox)
        jukebox.recent_player_msg = player_msg

        play_date = jukebox.get_player_start_time()
        ctx.voice_client.play(player, after = lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx, jukebox, player), self.client.loop) if (not jukebox.is_last_song()) else asyncio.run_coroutine_threadsafe(self.end_concert(ctx, jukebox, player), self.client.loop))

        generate_embed = AbsFunc(self.get_singing_embed, args = [ctx, jukebox, player], kwargs = {"image_ptr": img_index_ptr, "description_ptr": description_ptr})
        await self.update_player(ctx, jukebox, generate_embed, play_date, player_msg, player)


    # skip(ctx) Skips the current song
    async def skip(self, ctx: commands.Context):
        jukebox = await self.get_jukebox(ctx)

        error = await self.not_in_voice_channel(ctx, jukebox)
        error = await self.playing_empty(ctx, jukebox, error = error)

        if (not error):
            ctx.voice_client.stop()


    # jump(ctx, index) Jumps to the another song in the playlist
    async def jump(self, ctx: commands.Context, index: str):
        error = False
        jukebox = await self.get_jukebox(ctx)

        error = await self.playing_empty(ctx, jukebox, error = error)
        error, index = await self.validate.validate_natural(ctx, error, index, "index")

        if (not error):
            error = not (await self.validate.check_inbetween(ctx, index, "index", 1, jukebox.get_playlist_len()))

        if (not error):
            jukebox.options.jump_loop = True

            if (await self.not_playing(ctx, jukebox, error = error)):
                jukebox.current_song_index = index - 1
                await self.play(ctx, jukebox = jukebox)
            else:
                prev_index = jukebox.get_previous_song_index(relative_index = index - 1)
                jukebox.current_song_index = prev_index

                prev_random = jukebox.options.random
                jukebox.options.random = False
                ctx.voice_client.stop()
                await asyncio.sleep(self.JUMP_PLAY_DELAY)
                jukebox.options.random = prev_random


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

                current_song_no = jukebox.current_song_index + 1
                current_song = jukebox.get_current_song()
                current_song.get_duration_left()
                jukebox.get_player_start_time()

                pause_msg = Dialogue.get_dialogue(Dialogue.DialogueCategory.SongBreak)
                embeded_message = self.embed.context_embed(ctx, pause_msg, f"{Members.DEFAULT_BOT_NAME} is Taking a Break", "yellow")

                player_title = "Current Song \U0001F3A4 \U0001F3A7"
                player_message = f"**{current_song_no}) [{current_song.title}]({current_song.display_url})**\n"
                player_message += self.format_player(jukebox, current_song)

                embeded_message = self.embed.add_section(embeded_message, player_title, player_message)

            elif (jukebox_state == VoiceState.Paused):
                embeded_message = self.embed.context_embed(ctx, f"{Members.DEFAULT_BOT_NAME} is currently off the stage during the break", f"{Members.DEFAULT_BOT_NAME} is still on Break", "red")
            elif (jukebox_state == VoiceState.Connected):
                embeded_message = self.embed.context_embed(ctx, f"{Members.DEFAULT_BOT_NAME} is not on stage yet", f"{Members.DEFAULT_BOT_NAME} is not on stage yet", "red")

            if (embeded_message is not None):
                player_msg = await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
                jukebox.recent_player_msg = player_msg


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
            diminished = self.is_interval(hf_distance, PerfectIntervalType.Diminished)
            if (perfect is not None):
                if (perfect.key_distance == OCTAVE):
                    message += "an `octave "
                else:
                    verbose_pos = StringTools.get_lineup_pos(perfect.key_distance)
                    message += f"a `perfect {verbose_pos} "

            elif (diminished is not None):
                verbose_pos = StringTools.get_lineup_pos(diminished.key_distance)
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
        error = await self.validate.validate_inbetween(ctx, half_steps, "half_steps", HALF_STEPS["MIN"], HALF_STEPS["MAX"], error)

        if (not error):
            jukebox = await self.get_jukebox(ctx)
            old_hf = jukebox.options.half_steps
            jukebox.options.half_steps = half_steps
            await jukebox.change_options()

            try:
                current_song = jukebox.get_current_song()
                current_song.change_ffmpeg_options(jukebox.options)
            except:
                pass

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


    # repeat(ctx, index) Enables, disables, or changes the song to be repeated
    async def repeat(self, ctx: commands.Context, index: str):
        error = False
        jukebox = await self.get_jukebox(ctx)
        prev_song_loop = jukebox.options.song_loop
        error, index = await self.validate.validate_natural(ctx, error, index, "index", allow_optional = True, check_equal = True)

        if (index is not None):
            error = await self.validate.validate_inbetween(ctx, index, "index", 1, jukebox.get_playlist_len(), error)
        elif (not error and index is None and prev_song_loop is None):
            error = True
            error_embed = Error.display_error(self.client, 6, correct_type = "integer", type_article = "an", parameter = "index")
            await ctx.send(embed = error_embed.embed, file = error_embed.file)

        if (not error):
            if (index is not None):
                index -= 1
                target_song = jukebox.get_song(index)
            else:
                target_song = jukebox.get_current_song()

            not_current_song = bool(index is not None and index != prev_song_loop)
            embed_title = ""
            embed_description = ""

            if (prev_song_loop is not None):
                embed_title = "Disabled Repeat"
                repeated_song = jukebox.get_repeated_song()
                embed_description += f"I **stopped singing:\n{prev_song_loop + 1}) [{repeated_song.title}]({repeated_song.display_url})\non repeat**"

                if (not_current_song):
                    embed_title = "Changed Repeat"
                    embed_description += "\n\nand "
                    jukebox.options.song_loop = index
                else:
                    jukebox.options.song_loop = None
            else:
                embed_title = "Enabled Repeat"
                jukebox.options.song_loop = index

            if (not (prev_song_loop is not None and not not_current_song)):
                embed_description += f"I will be **singing:\n{index + 1}) [{target_song.title}]({target_song.display_url})**\non repeat"
            embeded_message = self.embed.context_embed(ctx, embed_description, embed_title, "blue-purple")

            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # fast_forward(ctx, duration) Fast forwards into the song
    async def fast_forward(self, ctx: commands.Context, duration: str):
        jukebox = await self.get_jukebox(ctx)

        error = False
        error, duration_diff = await DateTime.validate_time_diff(ctx, self.client, error, duration, "duration", seperator = ":")
        error = await self.not_playing(ctx, jukebox, error = error)

        duration_diff_secs = int(duration_diff.total_seconds())
        error = await self.validate.validate_inbetween(ctx, duration_diff_secs, "duration", 0, self.MAX_SKIP_SEC, error, verbose = False)
        if (error):
            error = True
            embeded_message = Error.display_error(self.client, 20, type_article = "a", correct_type = "duration", scope = "exclusively", left = DateTime.format_time(0), right = DateTime.format_time(self.MAX_SKIP_SEC), parameter = "duration")
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

        if (not error):
            current_song = jukebox.get_current_song()
            current_song.get_duration_left()
            duration_diff_secs = int(duration_diff.total_seconds())
            new_duration_left = current_song.duration_left - duration_diff_secs

            if (new_duration_left <= 0):
                await self.skip(ctx)
            else:
                old_timestamp = current_song.duration - current_song.duration_left
                current_song.duration_left = new_duration_left
                new_timestamp = current_song.duration - current_song.duration_left

                old_timestamp = DateTime.format_time(old_timestamp)
                new_timestamp = DateTime.format_time(new_timestamp)

                formatted_duration_diff = DateTime.format_time(duration_diff_secs, verbose = True)
                current_song.get_end_date()

                if (jukebox.state == VoiceState.Playing):
                    ctx.voice_client.pause()

                no_of_read = duration_diff_secs * self.READ_PER_SEC
                read_per_hf_minute = 30 * self.READ_PER_SEC
                for i in range(no_of_read):
                    if (i % read_per_hf_minute):
                        current_song.read()
                    else:
                        await asyncio.sleep(1)

                if (jukebox.state == VoiceState.Playing):
                    current_song.get_end_date()
                    ctx.voice_client.resume()

                title = f"{Members.DEFAULT_BOT_NAME} has Jumped Ahead in the Song"
                message = f"I skipped ahead by `{formatted_duration_diff}` for **song #{jukebox.current_song_index + 1}: [{current_song.title}]({current_song.display_url})**, jumping from `{old_timestamp}` to `{new_timestamp}`"
                embeded_message = self.embed.context_embed(ctx, message, title, "blue-purple")

                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # swap(ctx, index_1, index_2) Swaps 2 songs in the server's playlist
    async def swap(self, ctx: commands.Context, index_1: str, index_2: str):
        jukebox = await self.get_jukebox(ctx)
        playlist_len = jukebox.get_playlist_len()

        error = False
        error, index_1 = await self.validate.validate_natural(ctx, error, index_1, "index_1", check_equal = True)
        error = await self.validate.validate_inbetween(ctx, index_1, "index_1", 1, playlist_len, error, verbose = True)
        error, index_2 = await self.validate.validate_natural(ctx, error, index_2, "index_2", check_equal = True)
        error = await self.validate.validate_inbetween(ctx, index_2, "index_2", 1, playlist_len, error, verbose = True)

        if (not error):
            if (index_1 == index_2):
                message = "Both of these are the same song, so no swapping needed!"
                title = "Same Song"
                embeded_message = self.embed.context_embed(ctx, message, title, "red")
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

            else:
                index_1 -= 1
                index_2 -= 1
                song_1 = jukebox.get_song(index_1)
                song_2 = jukebox.get_song(index_2)
                jukebox.swap(index_1, index_2)

                message = f"I swapped the position of:\n**{index_1 + 1}) [{song_1.title}]({song_1.display_url})**\nand\n**{index_2 + 1}) [{song_2.title}]({song_2.display_url})**"
                title = "Songs Swapped"
                embeded_message = self.embed.context_embed(ctx, message, title, "blue-purple")
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # shuffle(ctx) Shuffles the server's playlist
    async def shuffle(self, ctx: commands.Context):
        jukebox = await self.get_jukebox(ctx)
        playlist_len = jukebox.get_playlist_len()

        error = False
        error = await self.empty_playlist(ctx, jukebox, error = error)

        if (not error):
            if (playlist_len == 1):
                message = "Are you trying to mock me...? There is only **1 song** in this playlist..."
                title = "No Change to Playlist"
                colour = "yellow"
                image = {Pics.ImageCategory.Disappointed, -1}

                embeded_message = self.embed.context_embed(ctx, message, title, colour, image = image)
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

            else:
                only_swap = False
                description = None
                title = "Playlist Shuffled"

                for i in range(playlist_len - 1, 0, -1):
                    j = random.randrange(0, i + 1)
                    jukebox.swap(i, j)

                    if (not only_swap and i != j):
                        only_swap = True

                if (playlist_len == 2):
                    description = "You know, there are only 2 results for this case:\n```css\n#1 The 2 songs in the playlist are swapped\n#2 The playlist stays the same\n```\n\nWell..., looks like "

                    if (only_swap):
                        title = "Songs Swapped"
                        description += "both songs are now switched"
                    else:
                        title = "Playlist Stayed the Same"
                        description += "your playlist stayed the same"

                elif (not only_swap):
                    title = "Playlist Stayed the Same"
                    description = "By some stroke of luck, looks like your playlist stayed the same..."

                await self.view(ctx, jukebox = jukebox, description = description)


    # setting_view(ctx) Views the settings for the server's jukebox
    async def setting_view(self, ctx: commands.Context):
        jukebox = await self.get_jukebox(ctx)
        vol = jukebox.options.vol

        interval_desc = self.get_relative_interval(jukebox.options.half_steps)
        interval_desc = interval_desc.replace("`", "")
        pitch = f"Played {interval_desc}"
        loop = jukebox.options.playlist_loop
        random = jukebox.options.random

        repeated_song = jukebox.get_repeated_song()

        if (repeated_song is not None):
            repeat = f"{jukebox.options.song_loop + 1}) [{repeated_song.title}]({repeated_song.display_url})"
        else:
            repeat = "`No Songs are Being Repeated at the Moment!`"

        await self.music_settings.view(ctx, self.music_settings.type, vol = vol, pitch = pitch,
                                       loop = loop, repeat = repeat, random = random)


    # random(ctx) Toggles between playing a random song for the next song
    async def random(self, ctx: commands.Context):
        jukebox = await self.get_jukebox(ctx)

        prev_random = jukebox.options.random
        jukebox.options.random = not(prev_random)

        if (prev_random):
            message = "I will now sing the songs according to the order of the playlist"
            title = "Stopped Singing Randomly"
        else:
            message = "I will now sing the songs in any order I want!"
            title = f"{Members.DEFAULT_BOT_NAME} Started Singing in a Random Order"

        embeded_message = self.embed.context_embed(ctx, message, title, "blue-purple")
        await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
