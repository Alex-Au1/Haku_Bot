import discord
from discord.ext import commands
from time_and_place.loc_and_time import LocationAndTime


class TimeAndPlace(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.loc_and_time = LocationAndTime(client)

    # date(ctx) Displays the date for the server or the user
    # effects: sends an embed
    @commands.command(name="date", description= "Shows current date and time")
    async def date(self, ctx):
        await self.loc_and_time.date(ctx)


    # weather(ctx) Shows the weather of the region of the server
    # effects: sends an embed
    @commands.command(name = "weather", description = "Show the date and weather of the region for the server or the user")
    async def weather(self, ctx):
        await self.loc_and_time.weather(ctx)


    # weather_forecast(ctx) Show the 5-day weather forecast of the region of
    #   the server
    # effects: sends and edits an embed
    #          listens to button presses
    @commands.command(name = "weather_forecast", description = "Show the 5-day weather forecast of the region selected by the server or the user")
    async def weather_forecast(self, ctx):
        await self.loc_and_time.weather_forecast(ctx)


#setup the Cog for the bot
def setup(client):
    client.add_cog(TimeAndPlace(client))
