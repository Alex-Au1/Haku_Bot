import random, enum
from tools.string import StringTools

class DialogueCategory(enum.Enum):
    SongEnterEmbarassed = "song_enter_embarassed"
    Everybody = "everybody"
    ConcertWelcome = "concert_welcome"
    FirstSong = "first_song"
    Singing = "singing"
    NextSong = "next_song"
    LastSong = "last_song"
    SongDone = "song_done"
    SongBreak = "song_break"
    SongBreakEnd = "song_break_end"


DIALOGUE_LST = {DialogueCategory.SomeCategory: ["some list of dialogues..."]
                ...
                ...
                ...}


# get_dialogue(category, code) Retrives an available dialogue based from
#   'code'
# note: if code is -1, then retrieves a random image from 'category'
def get_dialogue(category: DialogueCategory, code: int = -1, **kwargs) -> str:
    result = None
    try:
        if (code != -1):
            result = DIALOGUE_LST[category][code]
        elif (category in DialogueCategory):
            code = random.randrange(0, len(DIALOGUE_LST[category]))
            result = DIALOGUE_LST[category][code]
    except:
        pass

    # replace any words
    if (result is not None):
        kw_keys = list(kwargs.keys())
        for k in kw_keys:
            new_key = "{" + k + "}"
            kwargs[new_key] = kwargs.pop(k)
        result = StringTools.word_replace(result, kwargs)

    return result
