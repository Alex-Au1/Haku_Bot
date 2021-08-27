import random
from typing import Dict, List, Optional, Union

class StringTools():
    NONE = "none"
    FALSE = ["no", "n", "false", "f", "0", "nah", "nope"]
    TRUE = ["yes", "y", "yeah", "true", "t", "1", "yea", "yep"]

    FALSE_DEFAULT  = FALSE[0]
    TRUE_DEFAULT = TRUE[0]
    FALSE_INT = FALSE[4]
    TRUE_INT = TRUE[4]


    # str_capitalize(cls, str) Capitalizes all the words in the string 'str'
    @classmethod
    def str_capitalize(cls, str: str) -> str:
        result_pts = str.split()
        result_pts = [word.capitalize() for word in result_pts]
        result = ' '.join(result_pts)
        return result


    # word_replace(self, str, word_dict) Replaces words in 'str' with its
    #   corresponding replacement from 'word_dict'
    @classmethod
    def word_replace(cls, str: str, word_dict: Dict[str, str], capitalize: bool = False) -> str:
        for w in word_dict:
            replace_word = word_dict[w]
            if (capitalize):
                replace_word = cls.str_capitalize(replace_word)
            str = str.replace(w, replace_word)

        return str


    # replace_quotes(cls, str) Replaces double quotes in 'str' with single
    #    quotes
    @classmethod
    def replace_quotes(cls, str: str) -> str:
        return cls.word_replace(str, {"\"": "'"})


    # convert_none(cls, str) Checks if 'str' represents a null value
    @classmethod
    def convert_none(cls, str: str) -> str:
        if (str == "\\none"):
            return cls.NONE
        elif (str == cls.NONE):
            return None
        else:
            return str


    # convert_str(cls, str) Converts 'str' to the desired data
    @classmethod
    def convert_str(cls, str: str)-> str:
        str_len = len(str)
        if (str_len >= 2 and str[0:2] == "\\"):
            return str[1:]
        else:
            return cls.convert_none(str)


    # convert_list(str, seperator) Converts 'str' to a list
    @classmethod
    def convert_list(cls, str:str, seperator: str = ";", allow_optional: bool = False) -> List[str]:
        str = cls.convert_str(str)
        if (str is None and allow_optional):
            return None
        elif (str is None):
            return []

        return str.split(seperator)

    # convert_dict(str, seperator) Converts 'str' to a dict
    @classmethod
    def convert_dict(cls, str: str, seperator: str = ",", equal: str = ":", allow_optional: bool = False) -> Dict[str, str]:
        str = cls.convert_str(str)
        if (str is None and allow_optional):
            return None
        elif (str is None):
            return {}

        result = {}
        lst = str.split(seperator)
        lst_len = len(lst)
        for i in range(lst_len):
            if (i and lst[i][0] == " "):
                lst[i] = lst[i][1:]
            current_items = lst[i].split(equal)
            result[current_items[0]] = current_items[1]

        return result


    # convert_bool(cls, str) Checks if 'str' is a boolean value
    @classmethod
    def convert_bool(cls, str: str) -> Optional[bool]:
        if (str in cls.FALSE):
            return False
        elif (str in cls.TRUE):
            return True
        else:
            return None


    # determines if 'search' matches with the front portion of 'str'
    @classmethod
    def front_substr_match(cls, search: str, str: str) -> bool:
        search = search.lower()
        str = str.lower()

        if (not (str.find(search))):
            return True
        else:
            return False

    # is_tag(str) determines if the string 'str' is a tag
    @classmethod
    def is_tag(cls, str: str) -> bool:
        str_len = len(str)
        return ((str[0:2] == "<@" or str[0:2] == "<#") and str[str_len - 1: str_len] == ">")


    # get_tag_id(str) Gets the tag id from 'str'
    @classmethod
    def get_tag_id(cls, str: str) -> Optional[str]:
        if (cls.is_tag(str)):
            result = str[2:-1]
            if (result[0] == "!" or result[0] == "&"):
                return result[1:]
            else:
                return result
        else:
            return None


    # get_link(url) Retrieves the url
    @classmethod
    def get_link(cls, url: str) -> str:
        if (url[0] == "<" and url[-1] == ">"):
            url = url[1:-1]

        return url


    # format_channel(channel_id) Retreives the string format of a discord channel
    @classmethod
    def format_channel(cls, channel_id: int) -> str:
        return f"<#{channel_id}>"


    # format_mention(channel_id) Retreives the string format of a discord mention of a member
    @classmethod
    def format_mention(cls, member_id: int) -> str:
        return f"<@!{member_id}>"


    # format_role_mention(channel_id) Retreives the string format of a discord mention of a role
    @classmethod
    def format_role_mention(cls, role_id: int) -> str:
        return f"<@&{role_id}>"


    # limit_str(str, limit, continue_indicator) Limits the length of 'str'
    # requires: limit >= 0
    @classmethod
    def limit_str(cls, str: str, limit: int, continue_indicator: str = "...") -> str:
        str_len = len(str)

        if (str_len > limit):
            str = str[:limit] + continue_indicator
        else:
            str += (" " * (limit - str_len + len(continue_indicator)))
        return str


    # get_pronouns(cls, nat, pronouns) Get the pronoun for number of objects
    @classmethod
    def get_pronouns(cls, nat: int, pronouns: Dict[int, str]) -> str:
        counts = list(pronouns.keys())

        if (nat in counts and nat):
            return f"{nat} {pronouns[nat]}"
        elif (nat in counts):
            return f"{pronouns[nat]}"
        else:
            return f"{nat} {pronouns[-1]}"

    # get_percentage(decimal, with_unit) Gets the percentage representation of
    #   of a decimal
    @classmethod
    def get_percentage(cls, decimal: int, with_unit: bool = True) -> Union[str, int]:
        decimal *= 100
        result = int(decimal)

        if (with_unit):
            return f"{result}%"
        else:
            return result


    #function to generate a random password
    @classmethod
    def generate_password(cls) -> str:
        #password
        password = ""

        #list of letters
        letters = ["a", "b", "c", "d", "e", "f", "g", "h" , "i" ,"j", "k", "l",
                   "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x",
                   "y","z"]

        #list of numbers
        numbers = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]

        #list of symbols
        symbols = ["!", "#", "$", "%", "&", "*", "(", ")", "_", "-",
                   "+", "{", "}", "[", "]", "|", ":", ";", "?", "<", ">",
                   "~"]

        #number of characters in the password
        no_of_char = random.randrange(15, 101)

        #generate password
        for i in range(no_of_char):

            #pick which list symbol comes from, first character cannot be symbol
            if (i == 0):
                character_list = random.randrange(1,3)
            else:
                character_list = random.randrange(1,4)


            #generate random character to be added to the password
            if (character_list == 1):
                max = len(letters)
                pos = random.randrange(max)

                #randomly select if letter is uppercase or lowercase
                case = random.randrange(1,3)

                if (case == 1):
                    password += letters[pos]
                elif (case == 2):
                    upper_letter = letters[pos].upper()
                    password = password + upper_letter

            elif (character_list == 2):
                max = len(numbers)
                pos = random.randrange(max)
                password += numbers[pos]

            elif (character_list == 3):
                max = len(symbols)
                pos = random.randrange(max)
                password += symbols[pos]

        return password
