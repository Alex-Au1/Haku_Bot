import discord, aiohttp
from youtubesearchpython import SearchVideos
import validators, asyncio, youtube_dl, copy
from bs4 import BeautifulSoup
from typing import List, Union, Any, Dict, List
import tools.validate as ValidateTools
from tools.string import StringTools


#options for downloading the youtube video
ydl_opts = {}

YT_KEYWORDS = {"id_from_playlist": ["\"playlistVideoRenderer\":{\"videoId\":\"", "\""]}


# get_metadata(url) Prepares the metadata for the youtube video by the link
#   'url'
async def get_metadata(url: str) -> Dict[str, Any]:
    url = StringTools.get_link(url)

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        meta = ydl.extract_info(url, download=False)

    meta["duration"] = format_time(meta["duration"])
    return meta


# get_latest_att(script) Get the id or publishing date of the latest youtube video from a channel
def get_latest_att(start: str, script: str, key: str) -> str:
    start += len(YT_KEYWORDS[key][0])
    target_str = script[start:]
    end = target_str.find(YT_KEYWORDS[key][1])
    id = target_str[:end]
    return id


# playlist_get_yt_links(client, url) retrieves a list of youtube video links from
#   youtube playlist
async def playlist_get_yt_links(client: discord.Client, url: str) -> List[str]:
    validate = ValidateTools.Validate(client)
    result = []
    if (validate.valid_yt_playlist_link(url)):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                if r.status == 200:
                    html_text = await r.text()
                    soup = BeautifulSoup(html_text, 'html.parser')
                    script_lst = soup.find_all('script')

                    for s in script_lst:
                        script = str(s)
                        id_index = script.find(YT_KEYWORDS["id_from_playlist"][0])

                        while (id_index != -1):
                            id = get_latest_att(id_index, script, "id_from_playlist")
                            result.append(f"{ValidateTools.YOUTUBE_BASE_VIDEO_URL}{id}")
                            script = script[script.find(id) + len(id):]
                            id_index = script.find(YT_KEYWORDS["id_from_playlist"][0])

                    return result
