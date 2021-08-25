import discord, random
from tools.string import StringTools
from tools.validate import Validate
from typing import Optional, List, Callable, Any, Union

BOT_NICKNAMES = ["Haku Yowane", "Haku" ,"Haku Chan", "Haku Onee-chan", "Haku Ojou-sama", "Haku Hime-sama", "弱音ハク"]

NICKNAMES = {The_Bots_id: BOT_NICKNAMES[random.randrange(0, len(BOT_NICKNAMES))],
             User_Ids: Nickname_for_the_user,
             ...
             ...
             ...
             }

IGNORED_MEMBERS = [The_Bots_id]
OWNER_ID = My_Id

INVISIBLE_MEMBERS = {}


#convert_name(id, author) Converts a given member by 'id' to their corresponding
#   nickname
def convert_name(id: int, author: str) -> str:
    #change corresonding discord id to the corresponding names
    if (id in list(NICKNAMES.keys())):
        name_display = NICKNAMES[id]

    #test if the name exists
    try:
        name = name_display;
    except NameError:
        name = author;

    #return the name
    return name;


# notify_invisible(name, member, status, message, record) Notifies whether a user is invisible
def notify_invisible(name: str, member: discord.Member, status: discord.Status, message: str, record: bool = True) -> str:
    if (status == discord.Status.offline):
        if (record):
            INVISIBLE_MEMBERS[member.id] = len(member.mutual_guilds)
        return message + f"\n\nNote: {name} is currently \U0001F575 __***INVISIBLE***__ \U0001F575 !"
    else:
        return message


# filter(group, condition, desired_status) Filters elements from 'group'
#   based off 'condition'
def filter(group: List[Any], condition: Optional[Union[Callable[[Any, discord.Role], bool], Callable[[Any, discord.Role], bool]]] = None,
           desired_status: Optional[discord.Status] = None, desired_role: Optional[discord.Role] = None) -> List[Any]:
    filter_lst = []

    for e in group:
        if(condition is None or
           (desired_status is None and condition(e, desired_role)) or
           (desired_status is not None and condition(e, desired_status, desired_role))):
            filter_lst.append(e);

    return filter_lst
