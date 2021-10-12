import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import tools.validate as ValidateTools
from typing import List

SPOTIPY_CLIENT_ID='MY_SPOTIFY_CLIENT_ID'
SPOTIPY_CLIENT_SECRET='MY_SPOTIFY_CLIENT_SECRET'
AUTH_MANAGER = SpotifyClientCredentials(client_id = SPOTIPY_CLIENT_ID, client_secret = SPOTIPY_CLIENT_SECRET)
SP = spotipy.Spotify(auth_manager=AUTH_MANAGER)


# SpTrackInfo: stores the information needed from a spotify track
class SpTrackInfo():
    def __init__(self, name: str, link: str, artist: str):
        self.name = name
        self.artist = artist
        self.link = link
        self.yt_link = None


    # get_info(data) Get the information needed for a spotify track
    @classmethod
    def get_info(cls, data: str):
        return cls(data["name"], data["external_urls"]["spotify"], data["artists"][0]["name"])



# playlist_get_sp_links(source) Retrieves all the spotify info to each track
#   in a spotify playlist
def playlist_get_sp_links(source: str) -> List[SpTrackInfo]:
    result = []

    playlist_id = source.replace(ValidateTools.SPOTIFY_BASE_PLAYLIST_URL, "")
    playlist = SP.playlist(playlist_id)
    playlist = playlist['tracks']['items']
    playlist_len = len(playlist)

    for i in range(playlist_len):
        playlist_data = playlist[i]["track"]
        track_info = SpTrackInfo.get_info(playlist_data)
        result.append(track_info)

    return result


# album_get_sp_links(source) Retrieves all the spotify info to each track
#   in a spotify album
def album_get_sp_links(source: str) -> List[SpTrackInfo]:
    result = []
    playlist = SP.album(source)
    playlist = playlist['tracks']['items']
    playlist_len = len(playlist)

    for i in range(playlist_len):
        track_info = SpTrackInfo.get_info(playlist[i])
        result.append(track_info)

    return result


# track_get_link(source) Retrieves the spotify info about a certain spotify track
def track_get_link(source: str) -> SpTrackInfo:
    track = SP.track(source)
    track_info = SpTrackInfo.get_info(track)
    return track_info
