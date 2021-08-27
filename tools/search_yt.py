from youtubesearchpython import SearchVideos
import validators, asyncio, youtube_dl, copy
from typing import List, Union, Any, Dict


#options for downloading the youtube video
ydl_opts = {}


'''
search_youtube_video(search_query) Produces a list of the video attributes
   based off the search, `search_query`
'''
def youtube_search(no_of_searches: int, search_query: str) -> List[List[Union[str, List[str]]]]:
    search = SearchVideos(search_query, offset = 1, mode = "json", max_results = int(no_of_searches))
    results = search.result()

    #list containing all the result contents
    video = results.split("\n")

    #list of attributes for the Video
    video_attributes=[]

    #get only the video attributes seperated by {} brackets
    video = video[2:-2]

    #strip whitespaces infront and behind each element
    for i in range(len(video)):
        video[i] = video[i].strip()

    return get_video_attributes(video, [], [], [])



'''
get_video_attributes(search, stack, attributes, result) Produces a list
   containing the different attributes of each video
'''
def get_video_attributes(search: List[str], stack: List[str], attributes: List[Union[str, List[str]]], result: List[List[Union[str, List[str]]]]) -> List[List[Union[str, List[str]]]]:
    if (not search):
        return result

    #if the first element is the { open bracket
    elif(search[0] == "{"):
      if(not stack):
        stack.insert(0,"{")
        return get_video_attributes(search[1:], stack, attributes, result)

      else:
        inner_list = get_inner_list(search[1:], "{" ,[], [])
        attributes.append(inner_list[0])
        return get_video_attributes(inner_list[1], stack,attributes, result)

    #if the first element is the [ open bracket
    elif(search[0] == '"search_result": [' or search[0] == '"thumbnails": ['):
      if(not stack):
        stack.insert(0,"[")
        return get_video_attributes(search[1:], stack, attributes, result)

      else:
        inner_list = get_inner_list(search[1:], "[" ,[], [])
        attributes.append(inner_list[0])
        return get_video_attributes(inner_list[1], stack,attributes, result)

    #if the first element is the } closed bracket
    elif(search[0] == "}" or search[0] == "},"):
        if (stack[0] == "{"):
            stack.pop(0)
            result.append(attributes)
            attributes = []
            return get_video_attributes(search[1:], stack, attributes, result)
        else:
            print("Error: Invalid Brackets for {}")

    #if the first element is the } closed bracket
    elif(search[0] == "]" or search[0] == "],"):
        if(stack[0] == "["):
            stack.pop(0)
            result.append(attributes)
            attributes = []
            return get_video_attributes(search[1:], stack, attributes, result)
        else:
            print("Error: Invalid Brackets for []")

    #any other element that is not part of the {} or [] brackets
    else:
        attributes.append(get_only_attribute(search[0]))
        return get_video_attributes(search[1:], stack, attributes, result)


'''
get_inner_list(search, bracket, stack, result) Returns a list containing the
   elements of child array and the rest of the element in the parent array
'''
def get_inner_list(search: List[str], bracket: List[str] ,stack: List[str], result: List[str]) -> [List[str], List[str]]:
  if(not search):
    print("0. Error: Invalid Brackets")

  # if the first element is the open bracket "{"
  elif(search[0] == "{"):
    stack.insert(0,"{")
    result.append(search[0])
    return get_inner_list(search[1:], bracket, stack, result)

  # if the first element is the open bracket "["
  elif(search[0] == '"search_result": [' or search[0] == '"thumbnails": ['):
    stack.insert(0,"[")
    result.append(search[0])
    return get_inner_list(search[1:], bracket, stack, result)

  #if the first element is the closed bracket "}"
  elif(search[0] == "}" or search[0] == "},"):
    #checks if the ending bracket corresponds with the to check open bracket
    if(not stack and bracket == "{"):
      result.insert(0, bracket)
      result.append("}")
      return [result, search[1:]]

    elif(stack):
      if(stack[0] == "{"):
        stack.pop(0)
        result.append("}")
        return get_inner_list(search[1:], bracket, stack, result)
      else:
        print("1. Error: Invalid Brackets {}")
    else:
      print("2. Error: Invalid Brackets {}")

  #if the first element is the closed bracket "]"
  elif(search[0] == "]" or search[0] == "],"):
    #checks if the ending bracket corresponds with the to check open bracket
    if(not stack and bracket == "["):
      return [result, search[1:]]

    elif(stack):
      if(stack[0] == "["):
        stack.pop(0)
        result.append("]")
        return get_inner_list(search[1:], bracket, stack, result)
      else:
        print("1. Error: Invalid Brackets []")
    else:
      print("2. Error: Invalid Brackets []")

  #appends any other character that is not a bracket to the result
  else:
    attribute = remove_comma(search[0])
    result.append(attribute[1:-1])
    return get_inner_list(search[1:], bracket, stack, result)



'''
get_only_attribute(attribute) Gets only the value of the attribute, removing all
   labels around the attribute
'''
def get_only_attribute(attribute: str) -> str:
    attribute = remove_comma(attribute)

    colon = attribute.find(":")
    attribute = attribute[colon+1:].strip()

    if (attribute[0] == '"' and attribute[-1] == '"'):
        attribute = attribute[1:-1]

    return attribute


'''
remove_comma(attribute) Removes the comma at the end of an attribute
remove_comma: str -> str
'''
def remove_comma(attribute: str) -> str:
    if (attribute[-1] == ","):
        attribute = attribute[:-1]
    return attribute


# valid_yt_link(link) determines when the link is a valid youtube video link
def valid_yt_link(link:str) -> bool:
    if (link[0] == "<" and link[-1] == ">"):
        link = link[1:-1]

    valid_link = validators.url(link)

    if (valid_link and (link.startswith("https://www.youtube.com/watch?v="))):
        return True
    else:
        return False


# valid_yt_channel_link(link) Determines if the link is a valid link to a youtube channel
def valid_yt_channel_link(link: str) -> bool:
    if (link[0] == "<" and link[-1] == ">"):
        link = link[1:-1]

    valid_link = validators.url(link)
    if (valid_link and (link.startswith("https://www.youtube.com/channel/"))):
        return True
    else:
        return False

# get_metadata(url) Prepares the metadata for the youtube video by the link
#   'url'
async def get_metadata(url: str) -> Dict[str, Any]:
    if (url[0] == "<" and url[-1] == ">"):
        url = url[1:-1]

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        meta = ydl.extract_info(url, download=False)

    meta["duration"] = format_time(meta["duration"])
    return meta


'''
format_time(time) Produces a string that divides 'time' into days, hours,
    minutes and seconds
'''
def format_time(time: int) -> str:

    if (not time):
        str_time = "LIVE"
    else:
        min = 60
        hr = 60
        day = 24

        formatted_min, formatted_sec = divmod(time, min)
        formatted_hr, formatted_min = divmod(formatted_min, hr)
        formatted_day, formatted_hr = divmod(formatted_hr, day)

        str_time = f"{formatted_min}:{formatted_sec}"

        if (formatted_day):
            str_time = f"{formatted_day}:{formatted_hr}:{str_time}"
        elif (formatted_hr):
            str_time = f"{formatted_hr}:{str_time}"

    return str_time
