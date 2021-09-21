import discord
from discord.ext import commands
from templates.game import Game, RankAttribute
from betting.bet import Betting
import tools.error as Error
from tools.string import StringTools


class Bet(Game):
    def __init__(self, client: discord.Client):
        self.client = client
        self.betting = Betting(client)

    # bet(ctx) Runs the subcommand to the betting system
    @commands.group(pass_context=True)
    async def bet(self, ctx: commands.Context):
        if (ctx.invoked_subcommand is None):
            embeded_message = Error.display_error(self.client, 13, command = "bet")
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # create(ctx, description, choices, title, hardcore, duration, public, image, thumbnail, channel)
    #   creates a new bet match
    @bet.command(name="create", description="creates a new betting match")
    async def create(self, ctx: commands.Context, description: str, choices: str, title: str = StringTools.NONE, hardcore: str = StringTools.FALSE_DEFAULT, duration: str = StringTools.NONE,
                     public: str = StringTools.FALSE_DEFAULT, image: str = StringTools.NONE, thumbnail: str = StringTools.NONE, channel: str = StringTools.NONE):

        await self.betting.create(ctx, description, choices, title = title, hardcore = hardcore, duration = duration, public = public,
                                  image = image, thumbnail = thumbnail, channel = channel)


    # edit(ctx, description, choices, title, hardcore, duration, public, image, thumbnail)
    #   Edits the contents to an existing betting match
    @bet.command(name="edit", description="edits an existing bet")
    async def bet_edit(self, ctx: commands.Context, bet_id: str, duration: str = StringTools.NONE, image: str = StringTools.NONE, thumbnail: str = StringTools.NONE):
        await self.betting.bet_edit(ctx, bet_id, duration = duration, image = image, thumbnail = thumbnail)


    # remove(self, ctx, bet_id) Removes a bet by the id, 'bet_id'
    @bet.command(name="remove", description="removes an existing betting match for everyone")
    async def remove(self, ctx: commands.Context, bet_id: str):
        await self.betting.remove(ctx, bet_id)


    # add_host(ctx, bet_id, person) Adds another person who can also host the bet
    #   with the id, 'bet_id'
    @bet.command(name="add_host", description="adds another member who will have the abilities to control a certain betting match")
    async def add_host(self, ctx: commands.Context, bet_id: str, player: str):
        await self.betting.add_host(ctx, bet_id, player)


    # remove_host(ctx, bet_id, person) removes another person who can also host the bet
    #   with the id, 'bet_id'
    @bet.command(name="remove_host", description="removes a member who will have the abilities to control a certain betting match")
    async def remove_host(self, ctx: commands.Context, bet_id: str, player: str):
        await self.betting.remove_host(ctx, bet_id, player)


    # play(self, ctx, bet_id, choice_no, amount) Participate in a bet by the id
    #   'bet_id'
    @bet.command(name = "play", description = "participate in a certain betting match")
    async def play(self, ctx: commands.Context, bet_id: str, choice_no: str, amount: str):
        await self.betting.play(ctx, bet_id, choice_no, amount)


    # bet_change(self, ctx, bet_id, choice_no, amount) Changes a user's existing made
    #   bet
    @bet.command(name = "change", description = "change your existing bet to a certain betting match")
    async def bet_change(self, ctx: commands.Context, bet_id: str, choice_no: str, amount: str):
        await self.betting.bet_change(ctx, bet_id, choice_no, amount)


    # opt_out(self, ctx, bet_id) opt out of a certain betting match
    @bet.command(name="opt_out", description="removes your bet from a certain betting match")
    async def opt_out(self, ctx: commands.Context, bet_id: str):
        await self.betting.opt_out(ctx, bet_id)


    # made(ctx, player, bet_id) Displays the bets made by a user
    @bet.command(name = "made", description = "View the available bets made by yourself, or a certain member")
    async def made(self, ctx: commands.Context, player: str = StringTools.NONE, bet_id: str = StringTools.NONE):
        await self.betting.made(ctx, player = player, bet_id = bet_id)


    # available(self, ctx, bet_id, page, host, server, channel): Checks all the available
    #   bets based on the filtered parameters
    @bet.command(name = "available", description = "View all the available bet matches that are taking place")
    async def available(self, ctx: commands.Context, bet_id: str = StringTools.NONE, page: str = "1",
                        host: str = StringTools.NONE, server: str = StringTools.NONE, channel: str = StringTools.NONE):
        await self.betting.available(ctx, bet_id = bet_id, page = page, host = host, server = server, channel = channel)


    # bet_details(ctx, bet_id) Lists the details of a certain bet match
    @bet.command(name="details", description="looks up the details on a certain betting match")
    async def bet_details(self, ctx, bet_id, stats = StringTools.FALSE_DEFAULT):
        await self.betting.bet_details(ctx, bet_id, stats = stats)


    # betting_rank(self, ctx, rank_attribute, reverse_order)
    @bet.command(name="rank", description="ranks the user by a certain attribute")
    async def betting_rank(self, ctx: commands.Context, rank_attribute: str = "value", reverse_order: str = StringTools.FALSE_DEFAULT, page: str = "1"):
        await self.betting.betting_rank(ctx, rank_attribute = rank_attribute, reverse_order = reverse_order, page = page)


    # betting_status(self, ctx, person) Checks someone's betting account
    @bet.command(name="status", description="checks the user's status for the betting game")
    async def betting_status(self, ctx: commands.Context, player: str = StringTools.NONE):
        await self.betting.betting_status(ctx, player = player)


    # betting_status(self, ctx, person) Checks someone's betting account
    @bet.command(name="result", description="Announces the result to a betting game")
    async def betting_result(self, ctx: commands.Context, bet_id: str, choice_no: str):
        await self.betting.betting_result(ctx, bet_id, choice_no)



#set up of the cog to the bot
def setup(client):
    client.add_cog(Bet(client))
