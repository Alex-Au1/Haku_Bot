import discord
import copy
from tools.embed import Embed
from tools.string import StringTools
from typing import Optional


# Err_Embed: A template for embeding errors and warnings
class Err_Embed():
    def __init__(self, title, description):
        self.title = title
        self.description = description



errors = {1: Err_Embed("Unable to Find Error", "Haku is unable to find the error by the code `{err_code}`"),
          2: Err_Embed("Unable to Warning", "Haku is unable to find the warning by the code `{warn_code}`"),
          3: Err_Embed("Unable to Find Selected Guild and Channel", "Haku is unable to find the guild by the {guild_search_type} `{search_guild}` and the channel by the {channel_search_type} `{search_channel}`"),
          4: Err_Embed("Unable to Find Selected Guild", "Haku is unable to find the guild by the {guild_search_type} `{search_guild}`"),
          5: Err_Embed("Unable to Find Selected Channel", "Haku is unable to find the channel by the {channel_search_type} `{search_channel}`"),
          6: Err_Embed("Please Enter {type_article} {correct_type} Parameter", "Please enter {type_article} **{correct_type}** for the parameter `{parameter}`"),
          7: Err_Embed("Please Enter {type_article} {correct_type} Greater or Equal to {value}", "Please enter {type_article} **{correct_type} greater or equal to {value}** for the parameter `{parameter}`"),
          8: Err_Embed("Please Enter {type_article} {correct_type} Lesser or Equal to {value}", "Please enter {type_article} **{correct_type} lesser or equal to {value}** for the parameter `{parameter}`"),
          9: Err_Embed("Cannot Perform Action in the Channel: {channel}", "Cannot {action} to the channel, `{channel}`, in the guild, `{guild}`"),
          10: Err_Embed("{element} is not part of {group}", "The input `{element}` for the parameter `{parameter}` is not an element of `{group}`"),
          11: Err_Embed("Please Enter {type_article} {correct_type} Greater than {value}", "Please enter {type_article} **{correct_type} greater than {value}** for the parameter `{parameter}`"),
          12: Err_Embed("Please Enter {type_article} {correct_type} Lesser than {value}", "Please enter {type_article} **{correct_type} lesser than {value}** for the parameter `{parameter}`"),
          13: Err_Embed("Please Enter a Valid Subcommand", "Please enter a valid subcommand for the command `{command}`"),
          14: Err_Embed("Please Enter a Valid Url for {type_article} {correct_type}", "Please enter a valid url for **{type_article} {correct_type}** in the parameter `{parameter}`"),
          15: Err_Embed("Please Enter a Valid {correct_type}", "Please enter a valid **{correct_type}** for the parameter `{parameter}`"),
          16: Err_Embed("Your {object} is too Big", "Your {object} with {measure} `{your_size}` exceeds the limit of {measure} `{limit_size}`"),
          17: Err_Embed("Unable to Find Selected {member}", "Haku is unable to find the {member} by the {member_search_type} `{search_member}`"),
          18: Err_Embed("{action} Failed", "Haku is unable to {action}"),
          19: Err_Embed("Please Enter {type_article} {correct_type} {scope} in between {left} and {right}", "Please enter {type_article} **{correct_type} {scope} in between __{left}__ and __{right}__** for the parameter `{parameter}`")}

warnings = {}


# display_error(client, code, type, choice, **kwargs) Displays an error/ warning embeded message
#   depending on 'code'
# requires: 0 <= code
#           0 <= choice
#           'type' is either "error" or "warning"
def display_error(client: discord.Client, code: int, type: str = "error", choice: int = 0, **kwargs) -> Optional[discord.Embed]:
    embed = Embed(client)
    description = ""
    title = ""

    if (type == "error"):
        title = "ERROR "
    elif (type == "warning"):
        title = "Warning "

    kw_keys = list(kwargs.keys())
    for k in kw_keys:
        new_key = "{" + k + "}"
        kwargs[new_key] = kwargs.pop(k)

    if (type == "error"):
        if (code <= len(errors) and code > 0):
            err_title = errors[code].title
            err_description = errors[code].description
        else:
            err_title = errors[1].title
            err_description = errors[1].description
            kwargs = {"{err_code}": f"{code}"}
            code = 1

    elif (type == "warning"):
        if (code <= len(warnings) and code > 0):
            err_title = warnings[code].title
            err_description = warnings[code].description
        else:
            err_title = warnings[2].title
            err_description = warnings[2].description
            kwargs = {"{warn_code}": f"{code}"}
            code = 2

    title += f"{code}: {err_title}"
    title = StringTools.word_replace(title, kwargs, capitalize = True)
    description = StringTools.word_replace(err_description, kwargs)

    if (type == "error"):
        embeded_message = embed.error_embed(description, title)
    elif (type == "warning"):
        embeded_message = embed.warning_embed(description, title, choice = choice)

    return embeded_message
