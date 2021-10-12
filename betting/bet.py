import discord, random, os, datetime, validators, asyncio, enum, copy
from datetime import timedelta
from discord.ext import commands
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType

from templates.game import Game, RankAttribute
from tools.embed import Embed, EmbededMessage
import tools.channels as ChannelTools
import tools.error as Error
import tools.members as Members
from tools.string import StringTools
from tools.discord_search  import SearchTools
import tools.datetime as DateTools
from tools.pagination import Pagination, ButtonedMsg
from tools.validate import Validate
import tools.error as Error
from tools.sort import object_merge_sort
from database.database import Database
from text.bot_texting import Texting
import pics.image_links as Pics
from tools.abs_func import AbsFunc
from typing import List, Union, Dict, Any, Optional

BET_COL_NAMES = ["id", "bets", "server_id", "message_id", "date", "bet_title", "bet_message", "gamemode", "public", "channel_id",
                 "original_host", "additional_hosts", "thumbnail", "image"]
USER_BET_COL_NAMES = ["id", "user_name", "money", "deaths", "bets_won", "bets_lost", "money_won", "money_lost", "current_bets"]

BET_RANK_ATT = {"value": RankAttribute("value", "", "" ,{}),
                "money": RankAttribute("money", "$", "", {}),
                "money lost": RankAttribute("money_lost", "$", "", {}),
                "money won": RankAttribute("money_won", "$", "", {}),
                "deaths": RankAttribute("deaths", "", " \U00002620", {}),
                "wins": RankAttribute("bets_won", "", "", {}),
                "loss": RankAttribute("bets_lost", "", "", {}),
                "win ratio": RankAttribute("win_ratio", "", "%", {-100: "No Record"}),
                "loss ratio": RankAttribute("loss_ratio", "", "%", {-100: "No Record"}),
                "money won ratio": RankAttribute("money_won_ratio", "", "%", {-100: "No Record"}),
                "money lost ratio": RankAttribute("money_lost_ratio", "", "%", {-100: "No Record"})}


# ModeColours: Class for the embed colours of different game modes
class ModeColours():
    def __init__(self, bet: str, result: str):
        self.bet = bet
        self.result = result


# BetEmbedState: class for the context of invoking a betting embed
class BetEmbedState(enum.Enum):
    Create = 0
    Detail = 1
    Result = 2
    Hist = 3
    Confirm = 4
    Question = 5
    Preview = 6


# BetDurationState: class for the state of the betting period
class BetDurationState(enum.Enum):
    Available = "\U0001F7E2"
    NotSet = "\U0001F7E1"
    Past = "\U0001F534"


# BetViewState: class for the context of viewing the available bets
class BetViewState(enum.Enum):
    User = 0
    Server = 1


# BetPlayState: class for the state of making a bet
class BetPlayState(enum.Enum):
    Make = "make"
    Change = "change"
    Delete = "delete"
    Result = "result"


# BetHostUpdate: class to update state of additional hosts
class BetHostUpdate(enum.Enum):
    Add = "add"
    Remove = "Remove"


# BetResultState: class to update the state of winning or losing a bet
class BetResultState(enum.Enum):
    Win = "win"
    Lose = "lose"


# UserBets: class for the bets a of a user
class UserBets():
    def __init__(self, id: int, choice: int, amount: int):
        self.id = int(id)
        self.choice = int(choice)
        self.amount = int(amount)


# StatusPage: class for formatting the status pages of a user's betting account
class StatusPage():
    def __init__(self, death_lower: int, death_upper: int, emoji_lst: List[str],
                 colour: Union[str, int], image_lst: List[str]):
        self.death_lower = death_lower
        self.death_upper = death_upper
        self.emoji_lst = emoji_lst
        self.colour = colour
        self.image_lst = image_lst
        self.image_lst_len = len(image_lst)


    # generate_status_pg(self, ctx, name, user_account) Generates the embed
    #   to display the status of the user's account
    def generate_status_pg(self, embed: Embed, ctx: commands.Context, name: str,
                           author_name: str, user_account: Dict[str, Any]) -> EmbededMessage:
        image_index = 0
        deaths = user_account["deaths"]

        if (deaths <= self.death_upper and deaths >= self.death_lower):
            image_index = deaths - self.death_lower
        elif (deaths < self.death_lower):
            image_index = 0
        else:
            image_index = random.randrange(self.image_lst_len)

        embeded_message = embed.context_embed(ctx, f"Here is the status of `{name}`", f"{self.emoji_lst[0]} {self.emoji_lst[1]} The Status of {StringTools.str_capitalize(name)} {self.emoji_lst[1]} {self.emoji_lst[0]}",
                                              self.colour, image = self.image_lst[image_index], name = author_name)

        status_properties = {"\U00002620 Death Count": f"`{user_account['deaths']}`",
                             "\U0001F4B5 Amount of Money:": f"`{user_account['money']}`",
                             "\U0001F4C8 Bets Won": f"`{user_account['bets_won']}`",
                             "\U0001F4C9 Bets Lost": f"`{user_account['bets_lost']}`",
                             "\U0001F4B5 Total Money Won": f"`{user_account['money_won']}`",
                             "\U0001F62D Total Money Lost": f"`{user_account['money_lost']}`"}

        embeded_message = embed.multi_add_section(embeded_message, status_properties)
        return embeded_message


BET_STATUSES = {"alive": StatusPage(0, 0, ["\U0001F31F", "\U0001F33F"], "light-yellow", Pics.IMAGE_LIST[Pics.ImageCategory.BetAlive]),
                "fallen": StatusPage(1, 3, ["\U00002620", "\U0001F480"], "grey", Pics.IMAGE_LIST[Pics.ImageCategory.BetFallen]),
                "dead": StatusPage(4, 7, ["\U0001F47B", "\U0001FA78"], "dark-turquoise", Pics.IMAGE_LIST[Pics.ImageCategory.BetDead]),
                "over_dead": StatusPage(7, 10, ["\U0001F479", "\U0001F47A"], "dark-red", Pics.IMAGE_LIST[Pics.ImageCategory.BetOverDead]),
                "beyond_dead": StatusPage(10, -1, ["\U0001F608", "\U0001F47F"], "black", Pics.IMAGE_LIST[Pics.ImageCategory.BetBeyondDead])}


# BetDeathEmbed: class for notifiying of a kill
class BetDeathEmbed():
    def __init__(self, description: str, image: str):
        self.description = description
        self.image = image

    # generate_death_pg(self, user_name, thumbnail) generates
    #   the death notification after announcing the result to a bet
    def generate_death_pg(self, embed: EmbededMessage, ctx: commands.Context, user_name: str,
                          thumbnail: Optional[str]) -> EmbededMessage:
        description = self.description.replace("name", f"**{user_name}**")
        embeded_message = embed.embed_message(ctx, description, f"\U00002620 {user_name} Died! \U00002620", "dark-red", user_name, thumbnail, thumbnail, self.image)
        return embeded_message


BET_DEATH_POSSIBILITIES = [BetDeathEmbed("name died from being beat up by loan sharks.", Pics.IMAGE_LIST[Pics.ImageCategory.BetDeaths][0]),
                           BetDeathEmbed("name was sold onto the blackmarket.", Pics.IMAGE_LIST[Pics.ImageCategory.BetDeaths][1]),
                           BetDeathEmbed("name was deported to Siberia and froze to death.", Pics.IMAGE_LIST[Pics.ImageCategory.BetDeaths][2]),
                           BetDeathEmbed("name was sold to a brothel and died from over-exhaustion.", Pics.IMAGE_LIST[Pics.ImageCategory.BetDeaths][3]),
                           BetDeathEmbed("name was sentenced to death from attempting to rob a bank", Pics.IMAGE_LIST[Pics.ImageCategory.BetDeaths][4]),
                           BetDeathEmbed("name became a slave and died from over-exhaustion.", Pics.IMAGE_LIST[Pics.ImageCategory.BetDeaths][5]),
                           BetDeathEmbed("name became **Haku**'s personal slave and died from over-exhaustion", Pics.IMAGE_LIST[Pics.ImageCategory.BetDeaths][6]),
                           BetDeathEmbed("name became **Haku**'s personal toy and died from over-exhaustion", Pics.IMAGE_LIST[Pics.ImageCategory.Smug][0]),
                           BetDeathEmbed("name was dumped into the sea and fed to sharks", Pics.IMAGE_LIST[Pics.ImageCategory.BetDeaths][7]),
                           BetDeathEmbed("name was eaten alive after being deserted on an island full of cannibals", Pics.IMAGE_LIST[Pics.ImageCategory.BetDeaths][8]),
                           BetDeathEmbed("**Haku** had too much fun with name all night and name died from over-exhaustion", Pics.IMAGE_LIST[Pics.ImageCategory.Smug][1]),
                           BetDeathEmbed("name died after **Haku** thought name was ~too cute~ and brought them home", Pics.IMAGE_LIST[Pics.ImageCategory.Satisfied][0]),
                           BetDeathEmbed("name rotted to death after being thrown into a dungeon", Pics.IMAGE_LIST[Pics.ImageCategory.BetDeaths][9]),
                           BetDeathEmbed("name died cuz **Haku** chan saids so", Pics.IMAGE_LIST[Pics.ImageCategory.Smug][2]),
                           BetDeathEmbed("name was exiled to a desert and died from dehydration", Pics.IMAGE_LIST[Pics.ImageCategory.BetDeaths][10])]


#Counting Function
class Betting(Game):

    #constructor
    def __init__(self, client: discord.Client):
        super().__init__(client)
        self.database = Database()
        self.validate = Validate(client)
        self.text = Texting(client)
        self.MAX_BET_TITLE_LEN = 16
        self.searchtools = SearchTools(client)
        self.HIST_CHOICE_LEN = 12
        self.MAX_CHOICE_PER_PAGE = 10
        self.MAX_HOSTS_PER_PAGE = 5
        self.MAX_BETS_PER_PAGE = 10
        self.DEFAULT_MONEY = 1500
        self.SEPERATORS = [":::", ":"]
        self.DEFAULT_USER_BETS = "0"
        self.MODE_COLOURS = {"normal": ModeColours("light-blue", "light-red"),
                             "hardcore": ModeColours("dark-red", "purple")}
        self.MODE_MULTIPLIERS = {"normal": {BetResultState.Win: 2},
                                 "hardcore": {BetResultState.Win: 3.125, BetResultState.Lose: 1.75, "TotalIncrease": 1.25}}


    # not_in_guild(guild, kwargs) Checks if the guild are not the same
    def not_in_guild(self, guild: discord.Guild, kwargs: Dict[str, Any]) -> bool:
        return (guild.id != kwargs["guild"].id)


    # unpin_bet(self, channel_id, message_id) Unpins a bet if already pinned
    async def unpin_bet(self, channel_id: int, message_id: int):
        # unpin the bet if it still exists
        bet_channel = self.client.get_channel(channel_id)
        if (bet_channel is not None):
            try:
                bet_message = await bet_channel.fetch_message(message_id)
            except:
                pass
            else:
                await bet_message.unpin()


    # create_new_account(ctx, name) Creates a new account for a user
    def create_new_account(self, ctx: commands.Context, name: str, columns_needed: List[str]) -> List[Dict[str, Any]]:
        self.database.insert({"id":f"{ctx.author.id}", "user_name":f"'{name}'", "money":f"{self.DEFAULT_MONEY}", "deaths":"0",
                              "bets_won":"0", "bets_lost":"0", "money_won":"0", "money_lost":"0", "current_bets":"'0'"}, "User_Bets")
        user_account = self.database.formatted_select(columns_needed, columns_needed, "User_Bets", conditions = {"id": f"{ctx.author.id}"})
        return user_account


    # get_user_account(ctx, name, columns_needed) Retrieves the user's betting
    #   account, or creates a new account for them, if their account does not
    #   exist
    def get_user_account(self, ctx: commands.Context, name: str, columns_needed: List[str]) -> List[Dict[str, Any]]:
        user_account = self.database.formatted_select(columns_needed, columns_needed, "User_Bets", conditions = {"id": f"{ctx.author.id}"})

        if (not user_account):
            user_account = self.create_new_account(ctx, name, columns_needed)

        user_account = user_account[0]
        return user_account


    # get_formatted_duration(end_date) Gets the formatted duration of a bet to be displayed
    #   onto an embed
    def get_formatted_duration(self, end_date: str) -> str:
        if (end_date != StringTools.NONE):
            end_date = DateTools.get_duration(end_date)
            duration = DateTools.format_duration(end_date)

            if (duration is None):
                duration = "Past"
        else:
            duration = "Not Set"

        return duration


    # get_recent_bet_id(self) Gets the most recent bet id
    def get_recent_bet_id(self) -> int:
        id_list = self.database.select(["none"], "none", custom_command = f'SELECT id FROM public."Server_Bets" ORDER BY id DESC LIMIT 1')
        return id_list[0][0]


    # get_additional_host_names(self, additional_hosts) Gets the names of the
    #   additional hosts based on their id
    def get_additional_host_names(self, additional_hosts: List[Union[str, int]]) -> List[str]:
        add_host_names = []
        for h in additional_hosts:
            add_host_names.append(self.get_username(h))
        return add_host_names


    # update_user_bets(user_total_bets, bet_id, choice_no, amount, state, old_bet) Updates
    #   the user's bets to be updated into the database
    def update_user_bets(self, user_total_bets: str, bet_id: int, choice_no: int, amount: int,
                         state: BetPlayState = BetPlayState.Make, old_bet: Optional[UserBets] = None) -> str:
        formatted_bet = f"{bet_id}:{choice_no}:{amount}"
        if (state == BetPlayState.Make):
            if (user_total_bets == self.DEFAULT_USER_BETS):
                new_bet = formatted_bet
            else:
                new_bet = user_total_bets + f",{formatted_bet}"

        elif (state == BetPlayState.Delete):
            new_bet = user_total_bets.replace(formatted_bet, "")
            if (new_bet == ""):
                new_bet = self.DEFAULT_USER_BETS
            elif (new_bet[-1] == ","):
                new_bet = new_bet[:-1]
            elif (new_bet[0] == ","):
                new_bet = new_bet[1:]

            new_bet = new_bet.replace(",,", ",")

        elif (state == BetPlayState.Change):
            old_formatted_bet = f"{old_bet.id}:{old_bet.choice}:{old_bet.amount}"
            new_bet = user_total_bets.replace(old_formatted_bet, formatted_bet)

        return new_bet


    # update_additional_hosts(self, additional_hosts, user_id, state) Formats
    #   the additional hosts to be updated to the database
    def update_additional_hosts(self, additional_hosts: str, user_id: int, state: BetHostUpdate = BetHostUpdate.Add) -> str:
        if (state == BetHostUpdate.Add):
            if (additional_hosts == StringTools.NONE):
                additional_hosts = str(user_id)
            else:
                additional_hosts += f",{user_id}"

        elif (state == BetHostUpdate.Remove):
            additional_hosts = additional_hosts.replace(f"{user_id}", "")

            if (additional_hosts == ""):
                additional_hosts = StringTools.NONE

            elif (additional_hosts[-1] == ","):
                additional_hosts = additional_hosts[:-1]
            elif (additional_hosts[0] == ","):
                additional_hosts = additional_hosts[1:]

            additional_hosts = additional_hosts.replace(",,", ",")

        return additional_hosts


    # get_all_user_bets(bet_id, remove_bet) Gets all the bets of the users who
    #   participated in the bet by the id 'bet_id'
    async def get_all_user_bets(self, bet_id: int, remove_bet: bool = False) -> Dict[int, str]:
        columns_needed = ["id", "money", "money_lost", "current_bets"]
        user_bets = self.database.formatted_select(columns_needed, columns_needed, "User_Bets")
        result = {}

        for b in user_bets:
            current_bet = await self.bet_participated(None, bet_id, b["current_bets"])
            if (current_bet is not None):
                result[b["id"]] = current_bet

                if (remove_bet):
                    new_bet = self.update_user_bets(b["current_bets"], current_bet.id, current_bet.choice, current_bet.amount, state = BetPlayState.Delete)
                    self.database.update({"current_bets": f"'{new_bet}'", "money": f"{b['money'] + current_bet.amount}",
                                          "money_lost": f"{b['money_lost'] - current_bet.amount}"}, "User_Bets", {"id":f"{b['id']}"})

        return result


    # get_server_bets(self, ctx, bet_columns, conditions) Get the server bets
    #   based off the id of the member
    def get_server_bets(self, ctx: commands.Context, bet_columns: List[str], conditions: Dict[str, str]) -> List[Dict[str, Any]]:
        if (ctx.author.id == Members.OWNER_ID):
            current_searched_bet = self.database.formatted_select(bet_columns, bet_columns, "Server_Bets", conditions = conditions)
        else:
            current_conditions = ""
            if (conditions):
                current_conditions = self.database.sop("", [conditions])
                current_conditions += " AND ("
            else:
                current_conditions = "("
            custom_condition = self.database.sop(f"{current_conditions}", [{"server_id": f"{ctx.guild.id}", "public": "0"}, {"public": "1"}]) + ")"
            current_searched_bet = self.database.formatted_select(bet_columns, bet_columns, "Server_Bets", custom_condition = custom_condition)

        return current_searched_bet


    # choice_exist_to_bet(ctx, name) Determines if the choice chosen exists
    async def choice_exist_to_bet(self, ctx: commands.Context, name: str, choice_no: int, choice_len: int) -> bool:
        choice_exist = True
        if (choice_no > choice_len):
            choice_exist = False

        if (not choice_exist):
            embeded_message = self.embed.context_embed(ctx, f"The betting choice number  `({choice_no})` entered does not exist",
                                                       f"Error: Bet Choice Does Not Exist! \U0001F6AB", "red", None, name = name)
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
        return choice_exist


    # enough_to_bet(self, ctx, name, user_money, amount, verbose) Determines if the
    #   user has enough money to bet on a bet
    async def enough_to_bet(self, ctx: commands.Context, name: str, user_money: int, amount: int, verbose: bool = True) -> bool:
        lack_money = False
        if (amount > user_money):
            lack_money = True

        if (lack_money):
            embeded_message = self.embed.context_embed(ctx, f"You do not have enough money to bet this amount: `{amount}`",
                                                       "Warning: Not Enough Money \U000026A0", "yellow", None, name = name)
            embeded_message = self.embed.add_section(embeded_message, "\U0001F4B5 Amount of Money in Account", f"`{user_money}`", inline = False)
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

        return lack_money


    # during_bet_time(self, ctx, name, end_date, verbose) Determines if the user
    #   can update their bet during the betting period
    async def during_bet_time(self, ctx: commands.Context, name: str, end_date: str, verbose: bool = True,
                              state: BetPlayState = BetPlayState.Make) -> bool:
        valid_time = True
        if (end_date != StringTools.NONE):
            end_date = DateTools.get_duration(end_date)
            duration = DateTools.format_duration(end_date)

            if (duration is None):
                valid_time = False
        elif (state != BetPlayState.Make):
            valid_time = False

        if (not valid_time and verbose):
            if (end_date != StringTools.NONE):
                now = DateTools.get_current_dt()
                diff = int((now - end_date).total_seconds())
                formatted_diff = DateTools.format_time(diff, verbose = True)
                embeded_message = self.embed.context_embed(ctx, f"The betting period is already over by `{formatted_diff}`", "\U0000274C Cannot Bet After Betting Period", "red", None, name = name)
            else:
                description = ""
                title = ""
                if (state == BetPlayState.Change):
                    description = "You cannot change your choice to this bet"
                    title = "\U0000274C Cannot Change Your Bet"
                elif (state == BetPlayState.Delete):
                    description = "You cannot opt-out of this bet"
                    title = "\U0000274C Cannot Opt-Out of the Bet"

                description += "\n\nSince **the betting period was not set** to this betting match, **ALL BETS ARE __FINAL__**"
                embeded_message = self.embed.context_embed(ctx, description, title, "red", None, name = name)
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

        return valid_time


    # get_duration_state(self, ctx, name, end_date) Gets the state of the betting
    #   period of a bet
    async def get_duration_state(self, ctx: commands.Context, name: str, end_date: str) -> BetDurationState:
        if (end_date == StringTools.NONE):
            return BetDurationState.NotSet
        else:
            valid_date = await self.during_bet_time(ctx, name, end_date, verbose = False)
            if (valid_date):
                return BetDurationState.Available
            else:
                return BetDurationState.Past


    # get_scope(self, public) Get the scope of playing for the bet
    def get_scope(self, public: Union[int, bool]) -> str:
        # get the type of bet
        if (public):
            bet_type = "public"
        else:
            bet_type = "local"
        return bet_type


    # get_gamemode(self, gamemode) Get the gamemode for the bet
    def get_gamemode(self, gamemode: Union[int, bool]) -> str:
        if (gamemode):
            return "hardcore"
        else:
            return "normal"


    # get_additional_hosts(self, add_hosts_lst) Gets the list of additional hosts
    #   for a bet
    def get_additional_hosts(self, add_hosts_lst: str) -> List[str]:
        if (add_hosts_lst == StringTools.NONE):
            additional_hosts = []
        else:
            additional_hosts = add_hosts_lst.split(",")
        return additional_hosts


    # get_title(self, title, bet_id) Gets the title for a bet
    def get_title(self, title: str, bet_id: int) -> str:
        # title for the embed if the user did not specify
        if (title is None or title == StringTools.NONE):
            return f"Bet {bet_id}"
        elif (title == f"\{StringTools.NONE}"):
            return StringTools.NONE
        elif (title[0:2] == "\\\\"):
            return title[1:]
        else:
            return title

    # get_game_colour(self, gamemode, state) Get the specific colour for the embed
    def get_game_colour(self, gamemode: Union[int, bool], state: BetEmbedState) -> str:
        colour_palette = None
        if (gamemode):
            colour_palette = self.MODE_COLOURS["hardcore"]
        else:
            colour_palette = self.MODE_COLOURS["normal"]

        if (state != BetEmbedState.Result):
            return colour_palette.bet
        else:
            return colour_palette.result


    # is_host(id, original_host_id, additional_hosts_id) Determines if the 'id'
    #   matches with the ids of the hosts
    def is_host(self, id: int, original_host_id: str, additional_hosts_id: str) -> bool:
        if (id == int(original_host_id)):
            return True

        if (additional_hosts_id == StringTools.NONE):
            return False

        lo_ahosts_ids = additional_hosts_id.split(",")
        return (str(id) in lo_ahosts_ids)


    # get_hosted_bets(self, bet_lst, search_member) Filter all the bets that
    #   are hosted by 'search_member'
    def get_hosted_bets(self, bet_lst: List[Dict[str, Any]], search_member: discord.Member):
        bet_lst_len = len(bet_lst)
        i = 0
        while (i < bet_lst_len):
            if (not self.is_host(search_member.id, bet_lst[i]["original_host"], bet_lst[i]["additional_hosts"])):
                bet_lst.pop(i)
                i -= 1
                bet_lst_len -= 1
            i += 1


    # bet_participated(bet_id, bets) Determines whether someone participated
    #    in a certain bet
    async def bet_participated(self, ctx: commands.Context, bet_id: int, bets: str, verbose: bool = False) -> Optional[UserBets]:
        bets = bets.split(",")

        if (bets[0] != "0"):
            for b in bets:
                current_elements = b.split(":")
                current_bet = UserBets(current_elements[0], current_elements[1], current_elements[2])
                if (bet_id == current_bet.id):
                    return current_bet

        if (verbose):
            embeded_message = self.embed.context_embed(ctx, f"You have not participated in `bet {bet_id}`", "\U0000274C Have not Participated in Bet", "red", None, name = name)
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

        return None


    # bet_exist(bet_id, columns_needed, conditions, title, name) Checks whether
    #   a bet exist
    async def bet_exist(self, ctx: commands.Context, bet_id: int, columns_needed: List[str], title: str, name: str) -> List[Dict[str, Any]]:
        conditions = {"id": f"{bet_id}"}
        bet_result = self.get_server_bets(ctx, columns_needed, conditions)

        unaccessible = False
        try:
            server_id = int(bet_result[0]["server_id"])
            public = int(bet_result[0]["public"])

            if (ctx.author.id != Members.OWNER_ID and ctx.guild.id != server_id and not public):
                unaccessible = True
        except:
            pass

        if (not bet_result or unaccessible):
            description = "```css\n\U0000274C  No Bets Found!\n```"
            embeded_message = self.embed.context_embed(ctx, description, title, "yellow", None, name = name)
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
            bet_result = []

        return bet_result


    # generate_host_pg(self, current_page, max_page, kwargs) Generates the current
    #   page to display only the hosts of a bet
    # requires: current_page >= 1
    #           max_page >= 1
    async def generate_host_pg(self, current_page: int, max_page: int, kwargs: Dict[str, Any]) -> EmbededMessage:
        description = kwargs["description"]
        title = kwargs["title"]
        name = kwargs["name"]
        original_host = kwargs["original_host"]
        additional_hosts = kwargs["additional_hosts"]
        ctx = kwargs["ctx"]
        thumbnail = kwargs["thumbnail"]
        image = kwargs["image"]
        colour = kwargs["colour"]

        embeded_message = self.embed.context_embed(ctx, description, title, colour, thumbnail, image = image, name = name)
        embeded_message = self.embed.add_section(embeded_message, f"\U0001F4CC Original Host", f"```css\n{original_host}\n```", False)

        hosts_len = len(additional_hosts)
        indices = Pagination.get_indices(current_page, self.MAX_HOSTS_PER_PAGE, hosts_len)
        start_index = indices["start_index"]
        end_index = indices["end_index"]

        formatted_hosts = self.format_list(additional_hosts, start_index, end_index)
        if (formatted_hosts != "```css\n```"):
            embeded_message = self.embed.add_section(embeded_message, f"\U0001F4E5 Additional Hosts", f"{formatted_hosts}", False)

        return embeded_message


    # generate_bet_view_pg(current_page, max_page, kwargs) Generates the current
    #   page to display the viewing of the available bets
    # requires: current_page >= 1
    #           max_page >= 1
    async def generate_bet_view_pg(self, current_page: int, max_page: int, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        author_name = kwargs["author_name"]
        bet_results = kwargs["bet_results"]
        search_member = kwargs["search_member"]
        server = kwargs["server"]
        channel = kwargs["channel"]
        ctx = kwargs["ctx"]
        bet_view_state = kwargs["bet_view_state"]
        bet_id = kwargs["bet_id"]

        # description and title for the embed
        description = "Here are all the available bets"

        if (bet_id is not None):
            description += f" with the id `{bet_id}`"

        if (bet_view_state == BetViewState.Server):
            title = "Bet Match Search Results"

            if (server is not None):
                description += f" from the server `{server.name}`"

            if (search_member is not None):
                name = Members.convert_name(search_member.id, search_member)
                description += f" that are hosted by `{name}`"

            if (channel is not None):
                description += f" and created in the channel `{channel.name}`"
        elif (bet_view_state == BetViewState.User):
            title = "Available Bets Made"

            if (search_member is None):
                description += " that you have made"
            else:
                name = Members.convert_name(search_member.id, search_member)
                description += f" that `{name}` has made"

        embeded_message = self.embed.context_embed(ctx, description, title, "light-blue", None, name = author_name)
        embeded_message = self.embed.add_section(embeded_message, "\U000023F1 Betting Period", f"`{BetDurationState.Available.value}: Available`\n`{BetDurationState.NotSet.value}: Not Set`\n`{BetDurationState.Past.value}: Past`", False)

        bet_len = len(bet_results)
        indices = Pagination.get_indices(current_page, self.MAX_BETS_PER_PAGE, bet_len)

        start_index = indices["start_index"]
        end_index = indices["end_index"]

        formatted_bets = "```css\n"

        # format each bet entry
        for i in range(start_index, end_index):
            current_title = bet_results[i]['bet_title']
            current_id = bet_results[i]['id']
            current_title = self.get_title(current_title, current_id)
            current_title = StringTools.limit_str(current_title, self.MAX_BET_TITLE_LEN)
            current_duration = await self.get_duration_state(ctx, author_name, bet_results[i]["date"])

            if (bet_view_state == BetViewState.Server):
                current_gamemode = int(bet_results[i]["gamemode"])
                current_gamemode = self.get_gamemode(current_gamemode)
                current_scope = int(bet_results[i]["public"])
                current_scope = self.get_scope(current_scope)

                formatted_bets += f"#id-{current_id}  {current_title}  {current_duration.value} [{current_gamemode}]  [{current_scope}]\n"

            elif (bet_view_state == BetViewState.User):
                current_choice = bet_results[i]["choice"]
                current_amount = bet_results[i]["amount"]
                formatted_bets += f"#id-{current_id}  {current_title}  {current_duration.value} [Choice {current_choice}]  [${current_amount}]\n"

        if (formatted_bets == "```css\n"):
            formatted_bets += "\U0000274C No Bets Found!\n"
        formatted_bets += "```"
        embeded_message = self.embed.add_section(embeded_message, f"\U0001F3B2 Bets", formatted_bets, False)

        footer_msg = f"\U0001F4C3 pg:  {current_page} / {max_page}   Please Refer to the \"Bet Id\" When Wanting to Interact with a Bet"
        embeded_message = self.embed.add_footer(ctx, embeded_message, footer_msg)
        return embeded_message



    # generate_bet_pg(self, current_page, max_page, kwargs) Generates the current
    #   page to display the bet match
    async def generate_bet_pg(self, current_page: int, max_page: int, kwargs: Dict[str, Any]) -> EmbededMessage:
        choices = kwargs["choices"]
        bet_embed_state = kwargs["bet_embed_state"]
        description = kwargs["description"]
        embed_title = kwargs["embed_title"]
        colour = kwargs["colour"]
        name = kwargs["name"]
        thumbnail = kwargs["thumbnail"]
        image = kwargs["image"]
        ctx = kwargs["ctx"]
        bet_id = kwargs["bet_id"]

        if (bet_embed_state != BetEmbedState.Create):
            bet_result = kwargs["bet_result"]
            user_bet = kwargs["user_bet"]

        if (bet_embed_state != BetEmbedState.Confirm and bet_embed_state != BetEmbedState.Question and bet_embed_state != BetEmbedState.Result):
            duration = kwargs["duration"]
        else:
            bet_play_state = kwargs["bet_play_state"]
            old_user_bet = kwargs["old_user_bet"]

        if (bet_embed_state != BetEmbedState.Create and bet_embed_state != BetEmbedState.Confirm and bet_embed_state != BetEmbedState.Question and bet_embed_state != BetEmbedState.Preview and bet_embed_state != BetEmbedState.Result):
            original_host = kwargs["original_host"]
            additional_hosts = kwargs["additional_hosts"]
            bet_counts = kwargs["bet_counts"]

        if (bet_embed_state == BetEmbedState.Result or (bet_embed_state == BetEmbedState.Question and bet_play_state == BetPlayState.Result)):
            chosen_result = kwargs['result']

        embeded_message = self.embed.context_embed(ctx, f"{description}", embed_title, colour, thumbnail, image = image, name = name)

        if (bet_embed_state == BetEmbedState.Question or bet_embed_state == BetEmbedState.Preview):
            embeded_message = self.embed.add_section(embeded_message, "Yes (y)", "\U0001F44D", True)
            embeded_message = self.embed.add_section(embeded_message, "No (n)", "\U0001F44E", True)

        if (bet_id is not None):
            embeded_message = self.embed.add_section(embeded_message, f"\U0001F194 Bet ID", f"```fix\n{bet_id}\n```", False)

        if (bet_embed_state == BetEmbedState.Detail or bet_embed_state == BetEmbedState.Preview):
            if (bet_result["gamemode"]):
                gamemode = "-hardcore"
            else:
                gamemode = "+normal"

            scope = self.get_scope(bet_result["public"])
            embeded_message = self.embed.add_section(embeded_message, f"\U0001F3AE Gamemode", f"```diff\n{gamemode}\n```", False)
            embeded_message = self.embed.add_section(embeded_message, f"\U0001F3AF Scope", f"```ini\n[{scope}]\n```", False)

        if (bet_embed_state == BetEmbedState.Detail or bet_embed_state == BetEmbedState.Create or bet_embed_state == BetEmbedState.Preview):
            embeded_message = self.embed.add_section(embeded_message, f"\U000023F1 Betting Period", f"`{duration}`", False)

        if (bet_embed_state != BetEmbedState.Create):
            embeded_message = self.embed.add_section(embeded_message, f"\U0001F3F7 Bet Title", f"```\n{self.get_title(bet_result['bet_title'], bet_id)}\n```", False)
            embeded_message = self.embed.add_section(embeded_message, f"\U0001F4DD Bet Description", f"```\n{bet_result['bet_message']}\n```", False)

        # list the choices to be displayed
        choices_len = len(choices)
        indices = Pagination.get_indices(current_page, self.MAX_CHOICE_PER_PAGE, choices_len)

        start_index = indices["start_index"]
        end_index = indices["end_index"]

        if (bet_embed_state != BetEmbedState.Hist):
            formated_choices = self.format_list(choices, start_index, end_index, item_length = None)
        else:
            formated_choices = self.format_list(choices, start_index, end_index, item_length = self.MAX_BET_TITLE_LEN, values = bet_counts)

        if (bet_embed_state != BetEmbedState.Hist):
            embeded_message = self.embed.add_section(embeded_message, f"\U0001F530 Bet Choices", f"{formated_choices}", False)
        else:
            embeded_message = self.embed.add_section(embeded_message, f"\U0001F4CA Betting Statistics", f"{formated_choices}", False)

        #list the hosts
        if (bet_embed_state == BetEmbedState.Detail):
            embeded_message = self.embed.add_section(embeded_message, f"\U0001F4CC Original Host", f"```css\n{original_host}\n```", False)

            hosts_len = len(additional_hosts)
            indices = Pagination.get_indices(current_page, self.MAX_HOSTS_PER_PAGE, hosts_len)
            start_index = indices["start_index"]
            end_index = indices["end_index"]

            formatted_hosts = self.format_list(additional_hosts, start_index, end_index)
            if (formatted_hosts != "```css\n```"):
                embeded_message = self.embed.add_section(embeded_message, f"\U0001F4E5 Additional Hosts", f"{formatted_hosts}", False)

        if ((bet_embed_state == BetEmbedState.Confirm or bet_embed_state == BetEmbedState.Question) and bet_play_state == BetPlayState.Change):
            embeded_message = self.embed.add_section(embeded_message, "\U0001F530 Your Old Bet", f"```css\nChoice #{old_user_bet.choice}  {StringTools.limit_str(choices[int(old_user_bet.choice) - 1], self.MAX_BET_TITLE_LEN)} [${old_user_bet.amount}]\n```", False)

        if (bet_embed_state == BetEmbedState.Result or (bet_embed_state == BetEmbedState.Question and bet_play_state == BetPlayState.Result)):
            embeded_message = self.embed.add_section(embeded_message, f"\U0001F3C1 Bet Result", f"```css\n#{chosen_result + 1}   {choices[chosen_result]}\n```", False)
        elif ((bet_embed_state == BetEmbedState.Detail or bet_embed_state == BetEmbedState.Confirm or bet_embed_state == BetEmbedState.Question) and user_bet is not None):
            made_bet_title = "\U0001F530 Your Bet"

            if (bet_embed_state == BetEmbedState.Confirm and bet_play_state == BetPlayState.Change):
                made_bet_title = "\U0001F195 Your New Bet"
            embeded_message = self.embed.add_section(embeded_message, made_bet_title, f"```css\nChoice #{user_bet.choice}  {StringTools.limit_str(choices[int(user_bet.choice) - 1], self.MAX_BET_TITLE_LEN)} [${user_bet.amount}]\n```", False)

        footer_msg = f"\U0001F4C3 pg:  {current_page} / {max_page}"
        footer_msg += "   Please Refer to the \"Bet Id\" When Wanting to Interact with this Bet"

        embeded_message = self.embed.add_footer(ctx, embeded_message, footer_msg)
        return embeded_message


    # check_host(ctx, bet_id, original_host, additional_hosts) Checks if a member
    #   is the host for a bet and prints an error message if they are not
    async def check_host(self, ctx: commands.Context, bet_id: int, original_host: str,
                         additional_hosts: str, embed_title: str, check_additional: bool = False,
                         check_member: bool = None) -> bool:
        if (check_member is None):
            id_to_check = ctx.author.id
            member_to_check = ctx.author
        else:
            id_to_check = check_member.id
            member_to_check = check_member

        hosted_bet = self.is_host(id_to_check, original_host, additional_hosts)

        if (not hosted_bet):
            additional_hosts = self.get_additional_hosts(additional_hosts)
            current_page = 1
            max_page = Pagination.get_total_pages(self.MAX_HOSTS_PER_PAGE, len(additional_hosts))
            name = Members.convert_name(id_to_check, member_to_check)

            original_host = self.get_username(original_host)
            add_host_names = []
            description = f"You are not a host of `bet {bet_id}`. The hosts to this bet are:"

            if (not check_additional):
                for h in additional_hosts:
                    add_host_names.append(self.get_username(h))
            else:
                description = f"You are not the original host to `bet {bet_id}`. The original host is:"

            if (check_member is not None):
                description = description.replace("You are", f"{name} is")
                author_name = Members.convert_name(ctx.author.id, ctx.author)
            else:
                author_name = name

            generate_host_pg_kwargs = {"description": description, "title": embed_title, "name": author_name, "thumbnail": None,
                                       "image": None, "original_host": original_host, "additional_hosts": add_host_names, "ctx": ctx, "colour": "yellow"}
            generate_pg = AbsFunc(self.generate_host_pg, kwargs = {"kwargs": generate_host_pg_kwargs})
            embeded_message = await self.generate_host_pg(current_page, max_page, generate_host_pg_kwargs)
            paginated_components = Pagination.make_page_buttons(current_page, max_page)

            await Pagination.paginated_send(ctx, self.client, embeded_message, paginated_components, current_page, max_page, generate_pg)
        return hosted_bet


    # create(ctx, description, choices, title, hardcore, duration, public, image, thumbnail, channel)
    #   creates a new bet match
    async def create(self, ctx: commands.Context, description: str, choices: str, title: str = StringTools.NONE,
                     hardcore: str = StringTools.FALSE_DEFAULT, duration: str = StringTools.NONE, public: str = StringTools.FALSE_DEFAULT,
                     image: str = StringTools.NONE, thumbnail: str = StringTools.NONE, channel: str = StringTools.NONE):
        # author who invoked the command
        name = Members.convert_name(ctx.message.author.id, ctx.message.author)
        error = False

        # convert the parameters that may have none types
        title = StringTools.convert_str(title)
        image = StringTools.convert_str(image)
        thumbnail = StringTools.convert_str(thumbnail)

        # validate the input parameters
        error = await ChannelTools.validate_private_channel(ctx, self.client, error, name, "create a bet")
        error = await ChannelTools.validate_activity_channel(ctx, error)
        error, image = await self.validate.validate_image(ctx, error, image, "image")
        error, thumbnail = await self.validate.validate_image(ctx, error, thumbnail, "thumbnail")
        error, hardcore = await self.validate.validate_bool(ctx, error, hardcore, "hardcore")
        error, public = await self.validate.validate_bool(ctx, error, public, "public")
        error, sending_channel = await self.searchtools.validate_channel(ctx, error, channel)
        error, duration_diff = await DateTools.validate_time_diff(ctx, self.client, error, duration, "duration", seperator = ":")

        if (not error):
            # Strip all quotes from the description, title and choices
            word_replacements = {"\"": "", "'": "", self.SEPERATORS[0]: "-"}
            description = StringTools.word_replace(description, word_replacements)
            choices = StringTools.word_replace(choices, word_replacements)
            if (title is not None):
                title = StringTools.word_replace(title, word_replacements)

            #get the choices
            choices = choices.split(";")
            bet_choices = ""
            choice_len = len(choices)

            for i in range(choice_len):
                if (i == choice_len - 1):
                    bet_choices += f"{choices[i]}"
                else:
                    bet_choices += f"{choices[i]}:::"

            # format the data to be inserted
            if (title is None):
                title = StringTools.NONE
                embed_title = None

            elif (title == StringTools.NONE):
                title = f"\\{title}"
                embed_title = f"\\{title}"
            else:
                embed_title = title

            if (duration_diff is None):
                end_date = StringTools.NONE
                formatted_duration = "Not Set"
            else:
                today = DateTools.get_current_dt(utc = True)
                end_date = await DateTools.format_date(today + duration_diff, format = DateTools.DATABASE_FORMAT)
                formatted_duration = DateTools.format_time(int(duration_diff.total_seconds()), verbose = True)

            hardcore = int(hardcore)
            public = int(public)

            # get the number of pages to display the bet
            max_page = Pagination.get_total_pages(self.MAX_CHOICE_PER_PAGE, choice_len)
            page = 1

            thumbnail, image = self.get_thumbnail_and_image(thumbnail, image)

            input_thumbnail = thumbnail
            input_image = image

            if (thumbnail is None):
                input_thumbnail = StringTools.NONE
            if (image is None):
                input_image = StringTools.NONE

            generate_bet_pg_kwargs = {"choices": choices, "bet_embed_state": BetEmbedState.Preview, "ctx": ctx,
                                      "bet_result": {"bet_title": title, "bet_message": description, "gamemode": hardcore, "public": int(public)},
                                      "duration": formatted_duration, "user_bet": None,
                                      "description": "Do you want to create this bet?", "embed_title": "\U0001F50D Preview of Bet",
                                      "colour": "yellow", "name": name, "thumbnail": thumbnail, "image": image, "bet_id": None}
            generate_pg = AbsFunc(self.generate_bet_pg, kwargs = {"kwargs": generate_bet_pg_kwargs})
            confirm_make_bet = await self.text.paginated_continual_ask(ctx, page, max_page, generate_pg, self.values_to_check)


            if (confirm_make_bet in StringTools.TRUE):
                #insert the data into the database
                self.database.insert({"server_id":f"{ctx.message.guild.id}", "channel_id":f"{ctx.channel.id}",
                                      "message_id":f"{ctx.message.id}", "date":f"'{end_date}'", "gamemode":f"{hardcore}",
                                      "bets":f"'{bet_choices}'", "bet_message":f"'{description}'", "bet_title":f"'{title}'",
                                      "public": f"{public}", "original_host": f"{ctx.author.id}", "additional_hosts": "'none'",
                                      "thumbnail": f"'{input_thumbnail}'", "image": f"'{input_image}'"}, "Server_Bets")

                #get the id of the bet
                bet_id = self.get_recent_bet_id()

                #colour to indicate if the bet is in hardcore mode
                colour = self.get_game_colour(hardcore, BetEmbedState.Create)
                # title for the embed if the user did not specify
                embed_title = self.get_title(embed_title, bet_id)
                # get the type of bet
                bet_type = self.get_scope(public)

                #send the bet to the channel
                generate_bet_pg_kwargs = {"choices": choices, "bet_embed_state": BetEmbedState.Create,
                                          "bet_id": bet_id, "ctx": ctx, "duration": formatted_duration,
                                          "description": description, "embed_title": embed_title, "colour": colour,
                                          "name": name, "thumbnail": thumbnail, "image": image}
                generate_pg = AbsFunc(self.generate_bet_pg, kwargs = {"kwargs": generate_bet_pg_kwargs})
                embeded_message = await self.generate_bet_pg(page, max_page, generate_bet_pg_kwargs)

                await ctx.message.delete()
                paginated_components = Pagination.make_page_buttons(page, max_page)

                msg_lst = []
                sent_message = await sending_channel.send(embed = embeded_message.embed, file = embeded_message.file, components = paginated_components)
                msg_lst.append(ButtonedMsg(sent_message, page, max_page))
                await sent_message.pin()

                if (public):
                    for g in self.client.guilds:
                        if (g.id != ctx.guild.id):
                            announcement_channel = self.searchtools.get_announcment_channel(g)
                            temp_message = await announcement_channel.send(embed = embeded_message.embed, file = embeded_message.file, components = paginated_components)
                            await temp_message.pin()
                            msg_lst.append(ButtonedMsg(temp_message, page, max_page))

                    await asyncio.gather(*([m.message.channel.purge(limit=1) for m in msg_lst] + [Pagination.multi_page_react(self.client, msg_lst, generate_pg)]))

                else:
                    await sending_channel.purge(limit=1)
                    await Pagination.page_react(self.client, sent_message, page, max_page, generate_pg)

                self.database.update({"message_id": f"{sent_message.id}"}, "Server_Bets", {"id":f"{bet_id}"})


    # edit(ctx, description, choices, title, hardcore, duration, public, image, thumbnail)
    #   Edits the contents to an existing betting match
    async def bet_edit(self, ctx: commands.Context, bet_id: str, duration: str = StringTools.NONE,
                       image: str = StringTools.NONE, thumbnail: str = StringTools.NONE):
        name = Members.convert_name(ctx.message.author.id, ctx.message.author)
        error = False

        # convert the parameters that may have none types
        duration = StringTools.convert_str(duration)
        image = StringTools.convert_str(image)
        thumbnail = StringTools.convert_str(thumbnail)

        # validate the input parameters
        error = await ChannelTools.validate_private_channel(ctx, self.client, error, name, "edit a bet")
        error = await ChannelTools.validate_activity_channel(ctx, error)
        error, bet_id = await self.validate.validate_natural(ctx, error, bet_id, "bet_id")
        if (image is not None):
            error, image = await self.validate.validate_editted_image(ctx, error, image, "image")

        if (thumbnail is not None):
            error, thumbnail = await self.validate.validate_editted_image(ctx, error, image, "thumbnail")

        if (duration is not None):
            negative_duration = False
            if (duration[0] == "-"):
                negative_duration = True
                duration = duration[1:]
            error, duration_diff = await DateTools.validate_time_diff(ctx, self.client, error, duration, "duration", seperator = ":")
        else:
            duration_diff = StringTools.NONE

        if (not error):
            # retrieve the bet
            columns_needed = ["id", "bets", "server_id", "date", "bet_title", "bet_message", "gamemode", "public", "original_host", "additional_hosts", "thumbnail", "image"]
            bet_result = await self.bet_exist(ctx, bet_id, columns_needed, f"Bet {bet_id} not Found!", name)

            # if the bet exists
            if (bet_result):
                bet_result = bet_result[0]
                original_host = bet_result["original_host"]
                additional_hosts = bet_result["additional_hosts"]
                host_of_bet = await self.check_host(ctx, bet_id, original_host, additional_hosts, "Cannot Edit Bet")

                # if the user is a host of the bet
                if (host_of_bet):
                    choices = bet_result["bets"].split(self.SEPERATORS[0])
                    choice_len = len(choices)
                    bet_embed_state = BetEmbedState.Preview
                    gamemode = bet_result["gamemode"]
                    colour = "yellow"
                    title = "\U00002753 Are you sure you want to change this bet?"
                    description = f"Here are the new changes that will be applied to `bet {bet_id}`"
                    display_thumbnail, display_image = self.get_thumbnail_and_image(bet_result["thumbnail"], bet_result["image"])

                    current_end_date = bet_result["date"]
                    current_duration = self.get_formatted_duration(current_end_date)

                    original_host = self.get_username(original_host)
                    add_host_names = self.get_additional_host_names(additional_hosts)

                    # get the number of pages to display the bet
                    max_page = Pagination.get_total_pages(self.MAX_CHOICE_PER_PAGE, choice_len)
                    page = 1

                    generate_bet_pg_kwargs = {"choices": choices, "bet_embed_state": bet_embed_state, "bet_id": bet_id, "ctx": ctx, "bet_result": bet_result, "duration": current_duration,
                                              "description": description, "embed_title": title, "colour": colour, "name": name, "thumbnail": display_thumbnail, "image": display_image, "user_bet": None}
                    generate_pg = AbsFunc(self.generate_bet_pg, kwargs = {"kwargs": generate_bet_pg_kwargs})

                    # when no changes are made to the bet
                    if (duration_diff is None and image is None and thumbnail is None):
                        generate_pg.kwargs["kwargs"]["description"] = f"No changes made to `bet {bet_id}`"
                        generate_pg.kwargs["kwargs"]["embed_title"] = "No Changes Made"
                        generate_pg.kwargs["kwargs"]["colour"] = "light-green"

                        embeded_message = await self.generate_bet_pg(page, max_page, generate_bet_pg_kwargs)
                        paginated_components = Pagination.make_page_buttons(page, max_page)
                        await Pagination.paginated_send(ctx, self.client, embeded_message, paginated_components, page, max_page, generate_pg)

                    else:
                        # change for the thumbnail and the image
                        if (thumbnail is not None and thumbnail.lower() == self.validate.REMOVE_IMG):
                            thumbnail = StringTools.NONE
                        elif (thumbnail is not None):
                            display_thumbnail = thumbnail
                        else:
                            thumbnail = bet_result["thumbnail"]

                        if (image is not None and image.lower() == self.validate.REMOVE_IMG):
                            image = StringTools.NONE
                        elif (image is not None):
                            display_image = image
                        else:
                            image = bet_result["image"]

                        # change for the duration
                        if (duration_diff is None):
                            end_date = bet_result["date"]
                            formatted_duration = self.get_formatted_duration(end_date)

                        elif (duration_diff == StringTools.NONE):
                            end_date = StringTools.NONE
                            formatted_duration = "Not Set"

                        else:
                            if (current_end_date != StringTools.NONE):
                                today = DateTools.get_current_dt()
                                current_end_date = DateTools.get_duration(current_end_date)

                                if (not negative_duration):
                                    new_end_date = current_end_date + duration_diff
                                    duration_diff = (current_end_date - today) + duration_diff
                                else:
                                    new_end_date = current_end_date - duration_diff
                                    duration_diff = (current_end_date - today) - duration_diff

                                convert = False

                            else:
                                today = DateTools.get_current_dt(utc = True)
                                new_end_date = today + duration_diff
                                convert = True

                            end_date = await DateTools.format_date(new_end_date, format = DateTools.DATABASE_FORMAT, convert = convert)
                            duration_seconds = int(duration_diff.total_seconds())
                            if (duration_seconds > 0):
                                formatted_duration = DateTools.format_time(duration_seconds, verbose = True)
                            else:
                                formatted_duration = "Past"

                        # ask the user to confirm the change
                        display_thumbnail, display_image = self.get_thumbnail_and_image(thumbnail, image)
                        generate_pg.kwargs["kwargs"]["duration"] = formatted_duration
                        generate_pg.kwargs["kwargs"]["thumbnail"] = display_thumbnail
                        generate_pg.kwargs["kwargs"]["image"] = display_image
                        confirm_make_bet = await self.text.paginated_continual_ask(ctx, page, max_page, generate_pg, self.values_to_check)

                        # send the confimation for the change
                        if (confirm_make_bet in StringTools.TRUE):
                            self.database.update({"date": f"'{end_date}'", "thumbnail": f"'{thumbnail}'", "image": f"'{image}'"}, "Server_Bets", {"id":f"{bet_id}"})

                            generate_pg.kwargs["kwargs"]["description"] = f"Change successfully made to `bet {bet_id}`"
                            generate_pg.kwargs["kwargs"]["embed_title"] = "\U00002705 Changes Made"
                            generate_pg.kwargs["kwargs"]["colour"] = "light-green"

                            embeded_message = await self.generate_bet_pg(page, max_page, generate_bet_pg_kwargs)
                            paginated_components = Pagination.make_page_buttons(page, max_page)
                            await Pagination.paginated_send(ctx, self.client, embeded_message, paginated_components, page, max_page, generate_pg)


    # update_hosts(self, ctx, bet_id, search_member, name, image, thumbnail, bet_update_state)
    #   Updates the additional hosts to a certain bet
    async def update_hosts(self, ctx: commands.Context, bet_id: int, search_member: discord.Member, name: str,
                           image: Optional[str], thumbnail: Optional[str], original_host: str,
                           additional_hosts: str, bet_update_state: BetHostUpdate):
        # prepare the embed to ask the user
        add_member_name = self.get_username(search_member.id)
        description = "Are you aure you want to "
        if (bet_update_state == BetHostUpdate.Add):
            description += "add"
            title = "\U00002753 Add Host?"
        elif (bet_update_state == BetHostUpdate.Remove):
            description += "remove"
            title = "\U00002753 Remove Host?"

        description += f" `{add_member_name}` as a host of `bet {bet_id}`?"
        thumbnail, image = self.get_thumbnail_and_image(thumbnail, image)
        embeded_message = self.embed.context_embed(ctx, description, title, "yellow", thumbnail, image = image, name = name)
        confirm_msg = await self.text.continual_ask(ctx, embeded_message, self.values_to_check)

        if (confirm_msg in StringTools.TRUE):
            new_additional_hosts = self.update_additional_hosts(additional_hosts, search_member.id, state = bet_update_state)
            self.database.update({"additional_hosts": f"'{new_additional_hosts}'"}, "Server_Bets", {"id":f"{bet_id}"})

            if (bet_update_state == BetHostUpdate.Add):
                description = f"`{add_member_name}` has been added as a host of `bet {bet_id}`"
                title = "\U00002705 Successfully Added Host"
            elif (bet_update_state == BetHostUpdate.Remove):
                description = f"`{add_member_name}` has been removed as a host of `bet {bet_id}`"
                title = "\U00002705 Successfully Removed Host"

            additional_hosts = self.get_additional_hosts(new_additional_hosts)
            current_page = 1
            max_page = Pagination.get_total_pages(self.MAX_HOSTS_PER_PAGE, len(additional_hosts))
            original_host = self.get_username(original_host)

            add_host_names = []
            for h in additional_hosts:
                add_host_names.append(self.get_username(h))

            # send the confirmation message
            generate_host_pg_kwargs = {"description": description, "title": title, "name": name, "image": image, "thumbnail": thumbnail,
                                       "original_host": original_host, "additional_hosts": add_host_names, "ctx": ctx, "colour": "light-green"}
            generate_pg = AbsFunc(self.generate_host_pg, kwargs = {"kwargs": generate_host_pg_kwargs})
            embeded_message = await self.generate_host_pg(current_page, max_page, generate_host_pg_kwargs)
            paginated_components = Pagination.make_page_buttons(current_page, max_page)
            sent_message = await Pagination.paginated_send(ctx, self.client, embeded_message, paginated_components, current_page, max_page, generate_pg)


    # add_host(ctx, bet_id, person) Adds another person who can also host the bet
    #   with the id, 'bet_id'
    async def add_host(self, ctx: commands.Context, bet_id: str, player: str):
        name = Members.convert_name(ctx.message.author.id, ctx.message.author)
        error = False

        # validate the data
        error = await ChannelTools.validate_private_channel(ctx, self.client, error, name, "add a host")
        error = await ChannelTools.validate_activity_channel(ctx, error)
        error, bet_id = await self.validate.validate_natural(ctx, error, bet_id, "bet_id")

        if (not error):
            # retrieve the bet
            columns_needed = ["id", "server_id", "public", "original_host", "additional_hosts", "thumbnail", "image"]
            bet_result = await self.bet_exist(ctx, bet_id, columns_needed, f"Bet {bet_id} not Found!", name)

            # if the bet exists
            if (bet_result):
                bet_result = bet_result[0]
                condition = None
                condition_kwargs = None

                if (not bet_result["public"]):
                    condition = self.searchtools.in_server
                    condition_kwargs = {"guild": ctx.guild}

                # get the member
                error, search_member = await self.searchtools.validate_member(ctx, error, player, allow_optional = False, condition = condition, condition_kwargs = condition_kwargs)

                if (not error):
                    original_host = bet_result["original_host"]
                    additional_hosts = bet_result["additional_hosts"]
                    host_of_bet = await self.check_host(ctx, bet_id, original_host, StringTools.NONE, "Cannot Add Host to Bet", check_additional = True)

                    # if the user is the original host of the bet
                    if (host_of_bet):
                        already_host = self.is_host(search_member.id, original_host, additional_hosts)

                        # if the desired member is not a host of the bet
                        if (not already_host):
                            await self.update_hosts(ctx, bet_id, search_member, name, bet_result["image"], bet_result["thumbnail"], original_host, additional_hosts, bet_update_state = BetHostUpdate.Add)

                        else:
                            member_name = self.get_username(search_member.id)
                            embeded_message = self.embed.context_embed(ctx, f"`{member_name}`  is already a host of `bet {bet_id}`", "\U000026A0 Already Host", "yellow", None, name = name)
                            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)



    # remove_host(ctx, bet_id, person) removes another person who can also host the bet
    #   with the id, 'bet_id'
    async def remove_host(self, ctx: commands.Context, bet_id: str, player: str):
        name = Members.convert_name(ctx.message.author.id, ctx.message.author)
        error = False

        # validate the data
        error = await ChannelTools.validate_private_channel(ctx, self.client, error, name, "remove a host")
        error = await ChannelTools.validate_activity_channel(ctx, error)
        error, bet_id = await self.validate.validate_natural(ctx, error, bet_id, "bet_id")

        if (not error):
            # retrieve the bet
            columns_needed = ["id", "server_id", "public", "original_host", "additional_hosts", "thumbnail", "image"]
            bet_result = await self.bet_exist(ctx, bet_id, columns_needed, f"Bet {bet_id} not Found!", name)

            # if the bet exists
            if (bet_result):
                bet_result = bet_result[0]
                condition = None
                condition_kwargs = None

                if (not bet_result["public"]):
                    condition = self.searchtools.in_server
                    condition_kwargs = {"guild": ctx.guild}

                # get the member
                error, search_member = await self.searchtools.validate_member(ctx, error, player, allow_optional = False, condition = condition, condition_kwargs = condition_kwargs)

                if (not error):
                    original_host = bet_result["original_host"]
                    additional_hosts = bet_result["additional_hosts"]
                    host_of_bet = await self.check_host(ctx, bet_id, original_host, StringTools.NONE, "Cannot Add Host to Bet", check_additional = True)

                    # if the user is the original host of the bet
                    if (host_of_bet):
                        already_host = await self.check_host(ctx, bet_id, original_host, StringTools.NONE, "Cannot Add Host to Bet", check_additional = True)

                        # remove the member if they are host of the bet
                        if (already_host and search_member.id != int(original_host)):
                            await self.update_hosts(ctx, bet_id, search_member, name, bet_result["image"], bet_result["thumbnail"], original_host, additional_hosts, bet_update_state = BetHostUpdate.Remove)

                        elif (already_host):
                            member_name = self.get_username(search_member.id)
                            embeded_message = self.embed.context_embed(ctx, f"Cannot remove `{member_name}`as a host to `bet {bet_id}` since they are the original host of the bet", "\U000026A0 Member is the Original Host", "yellow", name = name)
                            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

                        # if the desired member is not a host of the bet
                        else:
                            member_name = self.get_username(search_member.id)
                            embeded_message = self.embed.context_embed(ctx, f"`{member_name}`  is not a host of `bet {bet_id}`", "\U000026A0 Not Host", "yellow", name = name)
                            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)



    # remove(self, ctx, bet_id) Removes a bet by the id, 'bet_id'
    async def remove(self, ctx: commands.Context, bet_id: str):
        # name of the user
        name = Members.convert_name(ctx.author.id, ctx.author)
        error = False

        # validate the data
        error = await ChannelTools.validate_private_channel(ctx, self.client, error, name, "remove a bet")
        error = await ChannelTools.validate_activity_channel(ctx, error)
        error, bet_id = await self.validate.validate_natural(ctx, error, bet_id, "bet_id")

        if (not error):
            # retrieve the bet
            columns_needed = BET_COL_NAMES
            bet_result = await self.bet_exist(ctx, bet_id, columns_needed, f"Bet {bet_id} not Found!", name)

            if (bet_result):
                bet_result = bet_result[0]
                original_host = bet_result["original_host"]
                additional_hosts = bet_result["additional_hosts"]
                host_of_bet = await self.check_host(ctx, bet_id, original_host, additional_hosts, "Cannot Remove Bet")

                if (host_of_bet):
                    title = f"Remove Bet {bet_id}?"
                    description = f"Are you sure you want to remove `bet {bet_id}`?"
                    bet_embed_state = BetEmbedState.Question

                    choices = bet_result["bets"].split(self.SEPERATORS[0])
                    choice_len = len(choices)

                    page = 1
                    max_page = Pagination.get_total_pages(self.MAX_CHOICE_PER_PAGE, choice_len)
                    colour = "yellow"
                    image = bet_result["image"]
                    thumbnail, image = self.get_thumbnail_and_image(bet_result["thumbnail"], bet_result["image"])

                    generate_bet_pg_kwargs = {"choices": choices, "bet_embed_state": bet_embed_state, "bet_id": bet_id, "ctx": ctx, "bet_result": bet_result, "user_bet": None, "bet_play_state": None, "old_user_bet": None,
                                              "description": description, "embed_title": title, "colour": colour, "name": name, "thumbnail": thumbnail, "image": image}
                    generate_pg = AbsFunc(self.generate_bet_pg, kwargs = {"kwargs": generate_bet_pg_kwargs})

                    # continuosly asks the user
                    answer_msg = await self.text.paginated_continual_ask(ctx, page, max_page, generate_pg, self.values_to_check)

                    # remove the bet
                    if (answer_msg in StringTools.TRUE):
                        await self.unpin_bet(bet_result["channel_id"], bet_result["message_id"])
                        self.database.delete("Server_Bets", {"id":f"{bet_id}"})
                        await self.get_all_user_bets(bet_id, remove_bet = True)

                        generate_pg.kwargs["kwargs"]["embed_title"] = "Bet Successfully Removed \U00002705"
                        generate_pg.kwargs["kwargs"]["description"] = f"`bet {bet_id}` has been removed"
                        generate_pg.kwargs["kwargs"]["colour"] = "light-green"
                        generate_pg.kwargs["kwargs"]["bet_embed_state"] = BetEmbedState.Confirm

                        embeded_message = await self.generate_bet_pg(page, max_page, generate_bet_pg_kwargs)
                        paginated_components = Pagination.make_page_buttons(page, max_page)

                        await Pagination.paginated_send(ctx, self.client, embeded_message, paginated_components, page, max_page, generate_pg)


    # update_bet(self, ctx, bet_result, choices, bet_id, choice_no, amount)
    #   Updates the bet of a user
    async def update_bet(self, ctx: commands.Context, name: str, bet_result: Dict[str, Any], user_bets: Dict[str, Any],
                         user_money: int, choices: str, bet_id: int, choice_no: int, amount: int,
                         state: BetPlayState = BetPlayState.Make, old_user_bet: Optional[UserBets] = None):
        # page numbers
        choice_len = len(choices)
        page = 1
        max_page = Pagination.get_total_pages(self.MAX_CHOICE_PER_PAGE, choice_len)

        # set up the question embed
        bet_embed_state = BetEmbedState.Question
        description = "Are you sure you want to make this bet?"
        embed_title = "Make Bet? \U00002753"
        colour = "yellow"

        if (state == BetPlayState.Change):
            description = description.replace("make", "change")
            embed_title = embed_title.replace("Make", "Change")

        elif (state == BetPlayState.Delete):
            description = description.replace("make", "opt-out of")
            embed_title = embed_title.replace("Make", "Opt-Out of")

        thumbnail, image = self.get_thumbnail_and_image(bet_result["thumbnail"], bet_result["image"])

        generate_bet_pg_kwargs = {"choices": choices, "bet_embed_state": bet_embed_state, "bet_id": bet_id, "ctx": ctx,
                                  "bet_result": bet_result, "user_bet": UserBets(bet_id, choice_no, amount),
                                  "description": description, "embed_title": embed_title, "colour": colour, "name": name,
                                  "thumbnail": thumbnail, "image": image, "bet_play_state": state, "old_user_bet": old_user_bet}
        generate_pg = AbsFunc(self.generate_bet_pg, kwargs = {"kwargs": generate_bet_pg_kwargs})

        # continuosly asks the user
        answer_msg = await self.text.paginated_continual_ask(ctx, page, max_page, generate_pg, self.values_to_check)

        if (answer_msg in StringTools.TRUE):
            new_bet = self.update_user_bets(user_bets["current_bets"], bet_id, choice_no, amount, state = state, old_bet = old_user_bet)

            # update the user's account
            if (state == BetPlayState.Make):
                new_money = user_money - amount
                new_lost_money = user_bets['money_lost'] + amount

            elif (state == BetPlayState.Change):
                amount_diff = amount - old_user_bet.amount
                new_money = user_money - amount_diff
                new_lost_money = user_bets['money_lost'] + amount_diff

            elif (state == BetPlayState.Delete):
                new_money = user_money + amount
                new_lost_money = user_bets['money_lost'] - amount

            self.database.update({"current_bets": f"'{new_bet}'", "money": f"{new_money}", "money_lost": f"{new_lost_money}"},
                                  "User_Bets", {"id":f"{ctx.author.id}"})

            description = "Bet Successfully Made \U00002705"
            embed_title = f"Your bet to `bet {bet_id}` has been made"

            if (state == BetPlayState.Change):
                description = description.replace("made", "changed")
                embed_title = embed_title.replace("Made", "Changed")

            elif (state == BetPlayState.Delete):
                description = description.replace("made", "removed")
                embed_title = embed_title.replace("Made", "Removed")

            generate_pg.kwargs["kwargs"]["embed_title"] = description
            generate_pg.kwargs["kwargs"]["description"] = embed_title
            generate_pg.kwargs["kwargs"]["colour"] = "light-green"
            generate_pg.kwargs["kwargs"]["bet_embed_state"] = BetEmbedState.Confirm

            if (state == BetPlayState.Change):
                generate_pg.kwargs["kwargs"]["old_user_bet"] = old_user_bet

            embeded_message = await self.generate_bet_pg(page, max_page, generate_bet_pg_kwargs)
            paginated_components = Pagination.make_page_buttons(page, max_page)

            await Pagination.paginated_send(ctx, self.client, embeded_message, paginated_components, page, max_page, generate_pg)


    # play(self, ctx, bet_id, choice_no, amount) Participate in a bet by the id
    #   'bet_id'
    async def play(self, ctx: commands.Context, bet_id: str, choice_no: str, amount: str):
        # name of the user
        name = Members.convert_name(ctx.author.id, ctx.author)
        error = False

        # validate the data
        error = await ChannelTools.validate_private_channel(ctx, self.client, error, name, "make a bet")
        error = await ChannelTools.validate_activity_channel(ctx, error)
        error, bet_id = await self.validate.validate_natural(ctx, error, bet_id, "bet_id")
        error, choice_no = await self.validate.validate_natural(ctx, error, choice_no, "choice_no")
        error, amount = await self.validate.validate_natural(ctx, error, amount, "amount")

        if (not error):
            # retrieve the bet
            columns_needed = ["id", "bets", "server_id", "date", "bet_title", "bet_message", "gamemode", "public", "thumbnail", "image"]
            bet_result = await self.bet_exist(ctx, bet_id, columns_needed, f"Bet {bet_id} not Found!", name)

            # if the bet exist
            if (bet_result):
                bet_result = bet_result[0]
                choices = bet_result["bets"].split(self.SEPERATORS[0])
                choice_len = len(choices)
                choice_exist = await self.choice_exist_to_bet(ctx, name, choice_no, choice_len)

                end_date = bet_result["date"]
                valid_time = await self.during_bet_time(ctx, name, end_date, verbose = True)

                # create a new account if the user does not already have one
                columns_needed = ["money", "money_lost", "current_bets"]
                user_bets = self.get_user_account(ctx, name, columns_needed)

                if (valid_time and choice_exist):
                    columns_needed = ["money", "money_lost", "current_bets"]
                    user_bets = self.get_user_account(ctx, name, columns_needed)
                    current_bet = await self.bet_participated(ctx, bet_id, user_bets["current_bets"])
                    user_money = user_bets["money"]
                    lack_money = await self.enough_to_bet(ctx, name, user_money, amount, verbose = True)

                    # if the user has not betted on the bet
                    if (not lack_money and current_bet is None):
                        await self.update_bet(ctx, name, bet_result, user_bets, user_money, choices, bet_id, choice_no, amount)

                    elif (not lack_money):
                        # get the valid time for editting a bet
                        valid_time = await self.during_bet_time(ctx, name, end_date, verbose = True, state = BetPlayState.Change)

                        if (valid_time):
                            await self.update_bet(ctx, name, bet_result, user_bets, user_money, choices, bet_id, choice_no, amount, state = BetPlayState.Change, old_user_bet = current_bet)


    # bet_change(self, ctx, bet_id, choice_no, amount) Changes a user's existing made
    #   bet
    async def bet_change(self, ctx: commands.Context, bet_id: str, choice_no: str, amount: str):
        # name of the user
        name = Members.convert_name(ctx.author.id, ctx.author)
        error = False

        # validate the data
        error = await ChannelTools.validate_private_channel(ctx, self.client, error, name, "change a bet")
        error = await ChannelTools.validate_activity_channel(ctx, error)
        error, bet_id = await self.validate.validate_natural(ctx, error, bet_id, "bet_id")
        error, choice_no = await self.validate.validate_natural(ctx, error, choice_no, "choice_no")
        error, amount = await self.validate.validate_natural(ctx, error, amount, "amount")

        if (not error):
            # retrieve the bet
            columns_needed = ["id", "bets", "server_id", "date", "bet_title", "bet_message", "gamemode", "public", "thumbnail", "image"]
            bet_result = await self.bet_exist(ctx, bet_id, columns_needed, f"Bet {bet_id} not Found!", name)

            # if the bet_exists
            if (bet_result):
                bet_result = bet_result[0]
                choices = bet_result["bets"].split(self.SEPERATORS[0])
                choice_len = len(choices)
                choice_exist = await self.choice_exist_to_bet(ctx, name, choice_no, choice_len)

                end_date = bet_result["date"]
                # get the valid time for making a bet
                valid_time = await self.during_bet_time(ctx, name, end_date, verbose = True)

                # create a new account if the user does not already have one
                columns_needed = ["money", "money_lost", "current_bets"]
                user_bets = self.get_user_account(ctx, name, columns_needed)

                if (valid_time and choice_exist):
                    current_bet = await self.bet_participated(ctx, bet_id, user_bets["current_bets"])
                    user_money = user_bets["money"]

                    # updates the users bet
                    if (current_bet is not None):
                        # get the valid time for editting a bet
                        valid_time = await self.during_bet_time(ctx, name, end_date, verbose = True, state = BetPlayState.Change)
                        lack_money = await self.enough_to_bet(ctx, name, user_money + current_bet.amount, amount, verbose = True)

                        if (not lack_money and valid_time):
                            await self.update_bet(ctx, name, bet_result, user_bets, user_money, choices, bet_id, choice_no, amount, state = BetPlayState.Change, old_user_bet = current_bet)

                    # create the bet
                    else:
                        lack_money = await self.enough_to_bet(ctx, name, user_money, amount, verbose = True)

                        if (not lack_money):
                            await self.update_bet(ctx, name, bet_result, user_bets, user_money, choices, bet_id, choice_no, amount, state = BetPlayState.Make)


    # opt_out(self, ctx, bet_id) opt out of a certain betting match
    async def opt_out(self, ctx: commands.Context, bet_id: str):
        # name of the user
        name = Members.convert_name(ctx.author.id, ctx.author)
        error = False

        # validate the data
        error = await ChannelTools.validate_private_channel(ctx, self.client, error, name, "opt-out of a bet")
        error = await ChannelTools.validate_activity_channel(ctx, error)
        error, bet_id = await self.validate.validate_natural(ctx, error, bet_id, "bet_id")

        if (not error):
            # retrieve the bet
            columns_needed = ["id", "bets", "server_id", "date", "bet_title", "bet_message", "gamemode", "public", "thumbnail", "image"]
            bet_result = await self.bet_exist(ctx, bet_id, columns_needed, f"Bet {bet_id} not Found!", name)

            # if the bet exist
            if (bet_result):
                bet_result = bet_result[0]
                choices = bet_result["bets"].split(self.SEPERATORS[0])

                end_date = bet_result["date"]
                # get the valid time for editting a bet
                valid_time = await self.during_bet_time(ctx, name, end_date, verbose = True, state = BetPlayState.Delete)

                # create a new account if the user does not already have one
                columns_needed = ["money", "money_lost", "current_bets"]
                user_bets  = self.get_user_account(ctx, name, columns_needed)

                if (valid_time):
                    current_bet = await self.bet_participated(ctx, bet_id, user_bets["current_bets"])
                    user_money = user_bets["money"]

                    if (current_bet is not None):
                        amount = current_bet.amount
                        choice_no = current_bet.choice
                        await self.update_bet(ctx, name, bet_result, user_bets, user_money, choices, bet_id, choice_no, amount, state = BetPlayState.Delete)
                    else:
                        embeded_message = self.embed.context_embed(ctx, f"You have not participated in `bet {bet_id}`", "\U000026A0	Have Not Participated in Bet", "yellow", name = name)
                        await ctx.send(embed =  embeded_message.embed, file = embeded_message.file)


    # made(ctx, player, bet_id) Displays the bets made by a user
    async def made(self, ctx: commands.Context, player: str = StringTools.NONE, bet_id: str = StringTools.NONE):
        error = False

        # validate the data
        error = await ChannelTools.validate_activity_channel(ctx, error)
        error, bet_id = await self.validate.validate_natural(ctx, error, bet_id, "bet_id", allow_optional = True)
        error, search_member = await self.searchtools.validate_member(ctx, error, player)

        if (search_member is None):
            search_member = ctx.author

        # get the user bets
        if (not error):
            # get the authors name
            author_name = Members.convert_name(ctx.author.id, ctx.author)

            columns_needed = ["current_bets"]
            user_bets = self.get_user_account(ctx, author_name, columns_needed)
            user_bets = self.database.formatted_select(columns_needed, columns_needed, "User_Bets", conditions = {"id": f"{search_member.id}"})[0]

            if (user_bets):
                bets_made = []
                if (user_bets["current_bets"] != "0" and bet_id is None):
                    bets = user_bets["current_bets"].split(",")
                    bets_made = []

                    for b in bets:
                        current_bet_atts = b.split(":")
                        current_bet_atts[0] = int(current_bet_atts[0])
                        bets_made.append(current_bet_atts)

                    object_merge_sort(bets_made, 0)
                    bet_len = len(bets_made)

                    for i in range(bet_len):
                        current_bet_atts = bets_made[i]
                        bets_made[i] = UserBets(current_bet_atts[0], current_bet_atts[1], current_bet_atts[2])

                elif (user_bets["current_bets"] != "0"):
                    bet_found = await self.bet_participated(ctx, bet_id, user_bets["current_bets"])

                    if (bet_found is None):
                        bets_made = []
                    else:
                        bets_made = [bet_found]

                else:
                    bet_len = len(bets_made)

                if (bets_made is None):
                    bets_made = []

                page = 1
                max_page = Pagination.get_total_pages(self.MAX_BETS_PER_PAGE, bet_len)

                # get the title for each bet
                bet_columns = ["date", "bet_title"]
                bet_result = []

                # format the results
                for b in bets_made:
                    current_bet = {}
                    current_searched_bet = self.get_server_bets(ctx, bet_columns, {"id": f"{b.id}"})

                    if (current_searched_bet):
                        current_searched_bet = current_searched_bet[0]
                        current_bet["date"] = current_searched_bet["date"]
                        current_bet["bet_title"] = current_searched_bet["bet_title"]
                        current_bet["id"] = b.id
                        current_bet["choice"] = b.choice
                        current_bet["amount"] = b.amount
                        bet_result.append(current_bet)

                # format the embeds and buttons to be sent
                generate_bet_view_pg_kwargs = {"author_name": author_name, "bet_results": bet_result, "search_member": search_member, "server": None, "channel": None, "ctx": ctx, "bet_view_state": BetViewState.User, "bet_id": bet_id}
                generate_pg = AbsFunc(self.generate_bet_view_pg, kwargs = {"kwargs": generate_bet_view_pg_kwargs})
                embeded_message = await self.generate_bet_view_pg(page, max_page, generate_bet_view_pg_kwargs)
                paginated_components = Pagination.make_page_buttons(page, max_page)

                # send the message
                await Pagination.paginated_send(ctx, self.client, embeded_message, paginated_components, page, max_page, generate_pg)

            else:
                member_name = Members.convert_name(search_member.id, search_member)
                description = f"```bash\n\U0000274C  '{member_name}' does not have an account!\n```"
                title = "User Not Found!"
                embeded_message = self.embed.context_embed(ctx, description, title, "yellow", name = author_name)
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # available(self, ctx, bet_id, page, host, server, channel): Checks all the available
    #   bets based on the filtered parameters
    async def available(self, ctx: commands.Context, bet_id: str = StringTools.NONE, page: str = "1", host: str = StringTools.NONE, server: str = StringTools.NONE, channel: str = StringTools.NONE):
        author_name = Members.convert_name(ctx.author.id, ctx.author)
        error = False

        # validate each parameter
        error = await ChannelTools.validate_private_channel(ctx, self.client, error, author_name, "check which bets are available")
        error = await ChannelTools.validate_activity_channel(ctx, error)
        error, bet_id = await self.validate.validate_natural(ctx, error, bet_id, "bet_id", allow_optional = True)
        error, page = await self.validate.validate_natural(ctx, error, page, "page")
        error, search_server, search_channel = await self.searchtools.validate_sev_ch(ctx, error, channel, server)
        error, search_member = await self.searchtools.validate_member(ctx, error, host)

        if (search_server is not None and search_channel is not None and channel == StringTools.NONE):
            search_channel = None

        if (not error):
            columns_needed = ["id", "date", "bet_title", "gamemode", "public", "original_host", "additional_hosts"]
            conditions = {}

            # get the bet result
            if (bet_id is not None):
                conditions["id"] = f"{bet_id}"
            if (search_server is not None):
                conditions["server_id"] = f"{search_server.id}"

                if (ctx.author.id != Members.OWNER_ID and search_server.id != ctx.guild.id):
                    conditions["public"] = "1"

            if (search_channel is not None):
                conditions["channel_id"] = f"{search_channel.id}"

                if (ctx.author.id != Members.OWNER_ID and search_channel not in ctx.guild.channels):
                    conditions["public"] = "1"

            if (not conditions):
                conditions = None

            bet_result = self.get_server_bets(ctx, columns_needed, conditions)

            # filter the bets where the user is the host
            if (search_member is not None):
                self.get_hosted_bets(bet_result, search_member)

            # get the maximum number of pages to display the data
            object_merge_sort(bet_result, "id")
            bet_len = len(bet_result)
            max_page = Pagination.get_total_pages(self.MAX_BETS_PER_PAGE, bet_len)

            # check if the indicated page does not exceed the max number of pages
            if (page > max_page and max_page):
                embeded_message = Error.display_error(self.client, 8, type_article = "an", correct_type = "integer", value = f"{max_page}", parameter = "page")
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
            elif (not error):
                if (not max_page):
                    max_page = 1

                generate_bet_view_pg_kwargs = {"author_name": author_name, "bet_results": bet_result, "search_member": search_member, "server": search_server, "channel": search_channel, "ctx": ctx, "bet_view_state": BetViewState.Server, "bet_id": bet_id}
                generate_pg = AbsFunc(self.generate_bet_view_pg, kwargs = {"kwargs": generate_bet_view_pg_kwargs})
                embeded_message = await self.generate_bet_view_pg(page, max_page, generate_bet_view_pg_kwargs)
                paginated_components = Pagination.make_page_buttons(page, max_page)

                # send the message
                await Pagination.paginated_send(ctx, self.client, embeded_message, paginated_components, page, max_page, generate_pg)


    # bet_details(ctx, bet_id) Lists the details of a certain bet match
    async def bet_details(self, ctx: commands.Context, bet_id: str, stats: str = StringTools.FALSE_DEFAULT):
        # name of the user
        name = Members.convert_name(ctx.author.id, ctx.author)
        error = False

        # validate the parameters
        error = await ChannelTools.validate_private_channel(ctx, self.client, error, name, "check the details of a bet")
        error = await ChannelTools.validate_activity_channel(ctx, error)
        error, bet_id = await self.validate.validate_natural(ctx, error, bet_id, "bet_id")
        error, stats = await self.validate.validate_bool(ctx, error, stats, "stats")

        # get the bet
        if (not error):
            title = f"Details on Bet {bet_id}"

            columns_needed = ["id", "bets", "server_id", "date", "bet_title", "bet_message", "gamemode", "public", "original_host", "additional_hosts", "thumbnail", "image"]
            bet_result = await self.bet_exist(ctx, bet_id, columns_needed, title, name)

            if (bet_result):
                choices = bet_result[0]["bets"].split(self.SEPERATORS[0])
                additional_hosts = self.get_additional_hosts(bet_result[0]["additional_hosts"])

                choice_len = len(choices)
                add_hosts_len = len(additional_hosts)

                page = 1
                choice_max_page = Pagination.get_total_pages(self.MAX_CHOICE_PER_PAGE, choice_len)

                if (not stats):
                    host_max_page = Pagination.get_total_pages(self.MAX_HOSTS_PER_PAGE, add_hosts_len)
                    max_page = max(choice_max_page, host_max_page)
                    conditions = {"id": f"{ctx.author.id}"}
                    bet_embed_state = BetEmbedState.Detail
                    description = f"Here are the details for bet {bet_id}"
                else:
                    max_page = choice_max_page
                    conditions = None
                    bet_embed_state = BetEmbedState.Hist
                    description = f"Here are the statistics for bet {bet_id}"

                # check if the user has particpated in the bet
                columns_needed = ["id", "current_bets"]
                user_bets = self.database.formatted_select(columns_needed, columns_needed, "User_Bets", conditions = conditions)

                # get the data for each bet
                bet_counts = None
                bet_ratio = None
                current_bet = None
                if (not stats):
                    if (not user_bets):
                        user_bets = [self.get_user_account(ctx, name, columns_needed)]
                    current_bet = await self.bet_participated(ctx, bet_id, user_bets[0]["current_bets"])
                else:
                    bet_counts = [0] * choice_len
                    bet_ratio = []
                    total_users = 0
                    # get the count for each choice
                    for c in user_bets:
                        temp_bet = await self.bet_participated(ctx, bet_id, c["current_bets"])
                        if (temp_bet is not None):
                            bet_counts[temp_bet.choice - 1] += 1
                            total_users += 1

                            if (c["id"] == f"{ctx.author.id}"):
                                current_bet = temp_bet

                    # if nobody betted on the bet
                    if (not total_users):
                        total_users = 1

                    # get the ratio of each choice
                    for i in range(choice_len):
                        temp_ratio = StringTools.get_percentage(bet_counts[i]/total_users)
                        bet_ratio.append(temp_ratio)

                    bet_counts_len = len(bet_counts)
                    for i in range(bet_counts_len):
                        bet_counts[i] = StringTools.get_pronouns(bet_counts[i], {0: "no bets", 1: "person", -1: "people"})

                if (not max_page):
                    max_page = 1

                #colour of the gamemode
                gamemode = bet_result[0]["gamemode"]
                colour = self.get_game_colour(gamemode, BetEmbedState.Detail)

                # the names of the hosts and additional hosts
                original_host = self.get_username(bet_result[0]["original_host"])
                add_host_names = self.get_additional_host_names(additional_hosts)

                thumbnail, image = self.get_thumbnail_and_image(bet_result[0]["thumbnail"], bet_result[0]["image"])

                # format the duration
                duration = None
                if (not stats):
                    duration = self.get_formatted_duration(bet_result[0]["date"])
                generate_bet_pg_kwargs = {"choices": choices, "bet_embed_state": bet_embed_state, "bet_id": bet_id, "ctx": ctx, "bet_result": bet_result[0], "original_host": original_host, "additional_hosts": add_host_names, "duration": duration,
                                          "description": description, "embed_title": title, "colour": colour, "name": name, "thumbnail": thumbnail, "image": image, "user_bet": current_bet, "bet_counts": [bet_counts, bet_ratio]}
                generate_pg = AbsFunc(self.generate_bet_pg, kwargs = {"kwargs": generate_bet_pg_kwargs})
                embeded_message = await self.generate_bet_pg(page, max_page, generate_bet_pg_kwargs)
                paginated_components = Pagination.make_page_buttons(page, max_page)

                # send the message
                await Pagination.paginated_send(ctx, self.client, embeded_message, paginated_components, page, max_page, generate_pg)


    # get_player_values(self, lo_players) Get the value for a player's betting
    #   account
    def get_player_values(self, lo_players: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for p in lo_players:
            p["value"] = int(p["money"] / (p["deaths"] + 1))

        return lo_players


    # get_win_loss_ratio(self, lo_players) Get the players win or loss ratio
    #   for each betting account
    def get_win_loss_ratio(self, lo_players: List[Dict[str, Any]], state: str) -> List[Dict[str, Any]]:
        for p in lo_players:
            state_index_name = BET_RANK_ATT[state].name
            if (state == "win ratio"):
                index_name = BET_RANK_ATT["wins"].name
                opposite_index_name = BET_RANK_ATT["loss"].name

            elif (state == "loss ratio"):
                index_name = BET_RANK_ATT["loss"].name
                opposite_index_name = BET_RANK_ATT["wins"].name

            elif (state == "money won ratio"):
                index_name = BET_RANK_ATT["money won"].name
                opposite_index_name = BET_RANK_ATT["money lost"].name

            elif (state == "money lost ratio"):
                index_name = BET_RANK_ATT["money lost"].name
                opposite_index_name = BET_RANK_ATT["money won"].name

            total = p[index_name] + p[opposite_index_name]
            if (not total):
                p[state_index_name] = -1
            else:
                p[state_index_name] = float("{:.2f}".format(p[index_name] / total))

            p[state_index_name] = StringTools.get_percentage(p[state_index_name], with_unit = False)

        return lo_players


    # betting_rank(self, ctx, rank_attribute, reverse_order)
    async def betting_rank(self, ctx: commands.Context, rank_attribute: str = "value", reverse_order: str = StringTools.FALSE_DEFAULT, page: str = "1"):
        error = False

        # validate the data
        error = await ChannelTools.validate_activity_channel(ctx, error)
        rank_attribute = StringTools.convert_str(rank_attribute)
        rank_attribute = rank_attribute.lower()
        if (rank_attribute not in BET_RANK_ATT.keys()):
            error = True
            embeded_message = Error.display_error(self.client, 10, element = rank_attribute, group = "Bet Rank Attributes", parameter = "rank_attribute")
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

        error, reverse_order = await self.validate.validate_bool(ctx, error, reverse_order, "reverse_order")
        error, page = await self.validate.validate_natural(ctx, error, page, "page")

        if (not error):
            # get all the user accounts
            name = Members.convert_name(ctx.author.id, ctx.author)
            user_bet = self.get_user_account(ctx, name, USER_BET_COL_NAMES)
            all_user_bets = self.database.formatted_select(USER_BET_COL_NAMES, USER_BET_COL_NAMES, "User_Bets")

            bet_len = len(all_user_bets)
            max_page = Pagination.get_total_pages(self.MAX_BETS_PER_PAGE, bet_len)

            # check if the indicated page does not exceed the max number of pages
            error, page = await self.validate.validate_page(ctx, error, str(page), max_page, "page")

            if (rank_attribute == "value"):
                all_user_bets = self.get_player_values(all_user_bets)

            elif (rank_attribute.endswith("ratio")):
                all_user_bets = self.get_win_loss_ratio(all_user_bets, rank_attribute)


            if (not error):
                description = f"This is a list of players ranked by `{rank_attribute}`"

                if (reverse_order):
                    description += " in reverse order"

                if (rank_attribute == "value"):
                    description += "\n\n\U0001F4DD **note**:\n The player's **value** is derived from the equation:\n"
                    description += "`amount_of_money / (deaths + 1)\n`"
                await self.rank(ctx, BET_RANK_ATT, rank_attribute, all_user_bets, name, page, reverse = reverse_order, description = description)


    # betting_status(self, ctx, person) Checks someone's betting account
    async def betting_status(self, ctx: commands.Context, player: str = StringTools.NONE):
        error = False

        # validate the data
        error = await ChannelTools.validate_activity_channel(ctx, error)
        error, search_member = await self.searchtools.validate_member(ctx, error, player)

        # get the user's account
        if (not error):
            author_name = Members.convert_name(ctx.author.id, ctx.author)
            user_account = self.get_user_account(ctx, author_name, USER_BET_COL_NAMES)

            if (search_member is not None):
                user_account = self.database.formatted_select(USER_BET_COL_NAMES, USER_BET_COL_NAMES, "User_Bets", conditions = {"id": f"{search_member.id}"})
                if (user_account):
                    user_account = user_account[0]
                name = self.get_username(search_member.id)
            else:
                name = author_name

            if (user_account):

                # get the status for the user
                deaths = user_account["deaths"]
                if (await self.validate.check_inbetween(ctx, deaths, "deaths", BET_STATUSES["alive"].death_lower, BET_STATUSES["alive"].death_upper, verbose = False)):
                    embeded_message = BET_STATUSES["alive"].generate_status_pg(self.embed, ctx, name, author_name, user_account)
                elif (await self.validate.check_inbetween(ctx, deaths, "deaths", BET_STATUSES["fallen"].death_lower, BET_STATUSES["fallen"].death_upper, verbose = False)):
                    embeded_message = BET_STATUSES["fallen"].generate_status_pg(self.embed, ctx, name, author_name, user_account)
                elif (await self.validate.check_inbetween(ctx, deaths, "deaths", BET_STATUSES["dead"].death_lower, BET_STATUSES["dead"].death_upper, verbose = False)):
                    embeded_message = BET_STATUSES["dead"].generate_status_pg(self.embed, ctx, name, author_name, user_account)
                elif (await self.validate.check_inbetween(ctx, deaths, "deaths", BET_STATUSES["over_dead"].death_lower, BET_STATUSES["over_dead"].death_upper, verbose = False)):
                    embeded_message = BET_STATUSES["over_dead"].generate_status_pg(self.embed, ctx, name, author_name, user_account)
                else:
                    embeded_message = BET_STATUSES["beyond_dead"].generate_status_pg(self.embed, ctx, name, author_name, user_account)

                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

            else:
                description = f"`{name}` does not have a betting account!"
                title = "\U0001F6AB No Account Found"
                embeded_message = self.embed.context_embed(ctx, description, title, "red", name = author_name)
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # normalmode_result(user_account, user_bet, dead_members, state) Updates a
    #   a user's account based if they were playing a bet in normal mode
    async def normalmode_result(self, ctx: commands.Context, bet_id: int, user_name: str, user_account: Dict[str, Any],
                                user_bet: UserBets, dead_members: List[Dict[str, Any]], thumbnail: str,
                                state: BetResultState, public: bool):
        user_identity = {"name": user_name, "thumbnail": thumbnail}

        # lose
        if (state == BetResultState.Lose):
            user_account["bets_lost"] += 1
            if (not user_account["money"] and user_account["current_bets"] == self.DEFAULT_USER_BETS):
                user_account["deaths"] += 1
                user_account["money"] = self.DEFAULT_MONEY
                dead_members.append(user_identity)
            self.database.update({"money":f"{user_account['money']}", "deaths": f"{user_account['deaths']}", "bets_lost": f"{user_account['bets_lost']}", "current_bets":f"'{user_account['current_bets']}'"}, "User_Bets", {"id":f"{user_account['id']}"})

            # send the notification
            embeded_message = self.embed.context_embed(ctx, f"{user_name} lost `bet {bet_id}`", f"{user_name} Lost Bet {bet_id}", "red", thumbnail, name = user_name)

            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
            if (public):
                await self.text.announcment(ctx, embeded_message, condition = self.not_in_guild, condition_kwargs = {"guild": ctx.guild})

        # win
        elif (state == BetResultState.Win):
            amount_won = int(self.MODE_MULTIPLIERS["normal"][BetResultState.Win] * user_bet.amount)
            user_account["money_won"] += amount_won
            user_account["money"] += amount_won
            user_account["bets_won"] += 1
            self.database.update({"money":f"{user_account['money']}", "bets_won": f"{user_account['bets_won']}","current_bets":f"'{user_account['current_bets']}'", "money_won": f"{user_account['money_won']}"}, "User_Bets", {"id":f"{user_account['id']}"})

            # send the notification
            embeded_message = self.embed.context_embed(ctx, f"{user_name} won `${amount_won}` from `bet {bet_id}`", f"{user_name} Won Bet {bet_id}", "light-green", thumbnail, name = user_name)
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
            if (public):
                await self.text.announcment(ctx, embeded_message, condition = self.not_in_guild, condition_kwargs = {"guild": ctx.guild})


    # hardmode_result(user_account, user_bet, dead_members, state) Updates a
    #   a user's account based if they were playing a bet in hardcore mode
    async def hardmode_result(self, ctx: commands.Context, bet_id: int, user_name: str, user_account: str,
                              user_bet: UserBets, dead_members: List[Dict[str, Any]], winners: List[Dict[str, Any]],
                              winner_accounts: List[Dict[str, Any]], total_money_lost: int, thumbnail: str,
                              state: BetResultState, public: bool):
        user_identity = {"name": user_name, "thumbnail": thumbnail, "user_bet": user_bet}

        # lose
        if (state == BetResultState.Lose):
            amount_lost = int(self.MODE_MULTIPLIERS["hardcore"][BetResultState.Lose] * user_bet.amount)
            user_account["money_lost"] += amount_lost
            user_account["bets_lost"] += 1
            user_account["money"] -= amount_lost
            total_money_lost += user_bet.amount

            if (user_account["money"] < 0 or (user_account["money"] == 0 and user_account["current_bets"] == self.DEFAULT_USER_BETS)):
                user_account["deaths"] += 1
                user_account["money"] = self.DEFAULT_MONEY
                dead_members.append(user_identity)

            self.database.update({"money":f"{user_account['money']}", "deaths": f"{user_account['deaths']}", "money_lost": f"{user_account['money_lost']}", "bets_lost": f"{user_account['bets_lost']}",
                                  "current_bets":f"'{user_account['current_bets']}'"}, "User_Bets", {"id":f"{user_account['id']}"})

            # send the notification
            embeded_message = self.embed.context_embed(ctx, f"{user_name} lost `${amount_lost}` from `bet {bet_id}`", f"{user_name} Lost Bet {bet_id}", "red", thumbnail, name = user_name)
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
            if (public):
                await self.text.announcment(ctx, embeded_message, condition = self.not_in_guild, condition_kwargs = {"guild": ctx.guild})

        # win
        elif (state == BetResultState.Win):
            winners.append(user_identity)
            winner_accounts.append(user_account)

        return total_money_lost


    # hardmode_total_win(self, ctx, user_name, user_account, user_bet, additional_money, thumbnail)
    #   Updates the winnings of the winners in hardcore mode
    async def hardmode_total_win(self, ctx: commands.Context, bet_id: int, user_name: str, user_account: List[Dict[str, Any]],
                                 user_bet: List[Dict[str, Any]], additional_money: int, thumbnail: str, public: bool):
        amount_won = int((self.MODE_MULTIPLIERS["hardcore"][BetResultState.Win] * user_bet.amount) + additional_money)
        user_account["money_won"] += amount_won
        user_account["bets_won"] += 1
        user_account["money"] += amount_won

        self.database.update({"money":f"{user_account['money']}", "bets_won": f"{user_account['bets_won']}","current_bets":f"'{user_account['current_bets']}'", "money_won": f"{user_account['money_won']}"}, "User_Bets", {"id":f"{user_account['id']}"})

        # send the notification
        embeded_message = self.embed.context_embed(ctx, f"{user_name} won `${amount_won}` from `bet {bet_id}`", f"{user_name} Won Bet {bet_id}", "light-green", thumbnail, name = user_name)
        await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
        if (public):
            await self.text.announcment(ctx, embeded_message, condition = self.not_in_guild, condition_kwargs = {"guild": ctx.guild})


    # analyze_result(self, ctx, bet_id, choice_no, all_user_bets, bet_result) Analyze the
    #   bet result for each member
    async def analyze_result(self, ctx: commands.Context, bet_id: int, choice_no: int, gamemode: int,
                             bet_result: Dict[str, Any], public: bool):
        # get all the users who betted on the bet
        dead_members = []
        winners = []
        winner_accounts = []
        total_money_lost = 0
        all_user_bets = self.database.formatted_select(USER_BET_COL_NAMES, USER_BET_COL_NAMES, "User_Bets")

        for u in all_user_bets:
            user_bet = await self.bet_participated(ctx, bet_id, u["current_bets"])

            # if the user participated in the bet
            if (user_bet is not None):
                #remove their bet
                new_bets = self.update_user_bets(u["current_bets"], bet_id, user_bet.choice, user_bet.amount, state = BetPlayState.Delete)
                u["current_bets"] = new_bets

                # get the user
                user_name = self.get_username(u["id"])

                # get the avatar url of the person
                try:
                    user =  await self.client.fetch_user(u["id"])
                    user_name = Members.convert_name(u["id"], user)
                    thumbnail = str(user.avatar_url)
                except:
                    user_name = "Not Found"
                    thumbnail = None

                #state of winning or losing the bet
                if (user_bet.choice != choice_no):
                    result_state = BetResultState.Lose
                else:
                    result_state = BetResultState.Win

                # normal mode
                if (not gamemode):
                    await self.normalmode_result(ctx, bet_id, user_name, u, user_bet,
                                                 dead_members, thumbnail, result_state, public)

                # hardcore mode
                else:
                    total_money_lost = await self.hardmode_result(ctx, bet_id, user_name, u, user_bet, dead_members,
                                                                  winners, winner_accounts, total_money_lost, thumbnail, result_state, public)

        # winnings in hardcore mode
        no_of_winners = len(winner_accounts)
        if (no_of_winners):
            additional_money = int((self.MODE_MULTIPLIERS["hardcore"]["TotalIncrease"] * total_money_lost) / no_of_winners)

        for i in range(no_of_winners):
            await self.hardmode_total_win(ctx, bet_id, winners[i]["name"], winner_accounts[i], winners[i]["user_bet"], additional_money, winners[i]["thumbnail"], public)

        all_death_possibilities = len(BET_DEATH_POSSIBILITIES)
        # announce all the deaths
        for d in dead_members:
            death_no = random.randrange(all_death_possibilities)
            embeded_message = BET_DEATH_POSSIBILITIES[death_no].generate_death_pg(self.embed, ctx, d["name"], d["thumbnail"])
            await asyncio.sleep(1)
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
            if (public):
                await self.text.announcment(ctx, embeded_message, condition = self.not_in_guild, condition_kwargs = {"guild": ctx.guild})

        # unpin the bet if it still exists
        await self.unpin_bet(bet_result["channel_id"], bet_result["message_id"])
        # delete the bet
        self.database.delete("Server_Bets", {"id":f"{bet_id}"})


    # betting_status(self, ctx, person) Checks someone's betting account
    async def betting_result(self, ctx: commands.Context, bet_id: str, choice_no: str):
        error = False

        # validate the data
        error = await ChannelTools.validate_activity_channel(ctx, error)
        error, bet_id = await self.validate.validate_natural(ctx, error, bet_id, "bet_id")
        error, choice_no = await self.validate.validate_natural(ctx, error, choice_no, "choice_no")

        if (not error):
            # name of the user
            name = Members.convert_name(ctx.author.id, ctx.author)

            # retrieve the bet
            bet_result = await self.bet_exist(ctx, bet_id, BET_COL_NAMES, f"Bet {bet_id} not Found!", name)

            # if the bet exist
            if (bet_result):
                bet_result = bet_result[0]
                choices = bet_result["bets"].split(self.SEPERATORS[0])
                choice_len = len(choices)
                choice_exist = await self.choice_exist_to_bet(ctx, name, choice_no, choice_len)
                bet_embed_state = BetEmbedState.Question
                end_date = bet_result["date"]
                public = bet_result["public"]

                columns_needed = ["money", "money_lost", "current_bets"]

                # check if the bet exists
                if (choice_exist):
                    original_host = bet_result["original_host"]
                    additional_hosts = bet_result["additional_hosts"]
                    host_of_bet = await self.check_host(ctx, bet_id, original_host, additional_hosts, "Cannot Announce Result to Bet")

                    # check if the user is the host of the bet
                    if (host_of_bet):
                        gamemode = bet_result["gamemode"]
                        description = f"Are you sure this is the correct choice to `bet {bet_id}`?"

                        if (end_date != StringTools.NONE and await self.during_bet_time(ctx, name, end_date, verbose = False)):
                            description = "\U000026A0 **Warning**\nThe **betting period** for this bet __**is not over yet**__\n\n" + description

                        # set the image and thumbnail
                        thumbnail, image = self.get_thumbnail_and_image(bet_result["thumbnail"], bet_result["image"])

                        # get the pages
                        page = 1
                        max_page = Pagination.get_total_pages(self.MAX_CHOICE_PER_PAGE, choice_len)

                        generate_bet_pg_kwargs = {"choices": choices, "bet_embed_state": bet_embed_state, "bet_id": bet_id, "ctx": ctx, "bet_result": bet_result, "user_bet": UserBets(bet_id, choice_no, 0),
                                                  "description": description, "embed_title": f"Verification for the Result of Bet {bet_id}", "colour": "yellow", "name": name, "thumbnail": thumbnail, "image": image,
                                                  "bet_play_state": BetPlayState.Result, "old_user_bet": None, "result": choice_no - 1}
                        generate_pg = AbsFunc(self.generate_bet_pg, kwargs = {"kwargs": generate_bet_pg_kwargs})

                        # continuosly asks the user
                        answer_msg = await self.text.paginated_continual_ask(ctx, page, max_page, generate_pg, self.values_to_check)

                        if (answer_msg in StringTools.TRUE):
                            generate_pg.kwargs["kwargs"]["bet_embed_state"] = BetEmbedState.Result
                            generate_pg.kwargs["kwargs"]["colour"] = self.get_game_colour(gamemode, BetEmbedState.Result)
                            generate_pg.kwargs["kwargs"]["embed_title"] = f"Results to Bet {bet_id}"
                            generate_pg.kwargs["kwargs"]["description"] = f"Here are the results to `bet {bet_id}`"

                            embeded_message = await self.generate_bet_pg(page, max_page, generate_bet_pg_kwargs)
                            paginated_components = Pagination.make_page_buttons(page, max_page)

                            # send the message and analyze the results
                            if (not public):
                                await asyncio.gather(*[Pagination.paginated_send(ctx, self.client, embeded_message, paginated_components, page, max_page, generate_pg),
                                                       self.analyze_result(ctx, bet_id, choice_no, gamemode, bet_result, public)])

                            else:
                                msg_lst = []
                                sent_message = await ctx.send(embed = embeded_message.embed, file = embeded_message.file, components = paginated_components)
                                msg_lst.append(ButtonedMsg(sent_message, page, max_page))
                                await asyncio.gather(*[self.text.paginated_announcement(ctx, msg_lst, page, max_page, embeded_message, generate_pg, paginated_components,
                                                                                        condition = self.not_in_guild, condition_kwargs = {"guild": ctx.guild}),
                                                       self.analyze_result(ctx, bet_id, choice_no, gamemode, bet_result, public)])
