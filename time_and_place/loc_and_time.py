import discord
from discord.ext import commands
from datetime import datetime
import tools.datetime as DateTools
import tools.weather as Weather
from tools.embed import Embed, EmbededMessage
import pics.image_links as Pics
from tools.string import StringTools
from tools.pagination import Pagination
import tools.channels as ChannelTools
import tools.members as Members
from database.database import Database, SelectType
from set_up.server_settings import ServerSettings
from set_up.user_settings import UserSettings
from typing import Optional, Any, Dict, Union


MAX_FORECAST_PER_PAGE = 1


class LocationAndTime():
    def __init__(self, client):
        self.client = client
        self.embed = Embed(client)


    # make_date(ctx, timezone, thumbnail, today, season, time_of_day) Formats
    #   the embed for displaying the date
    async def make_date(self, ctx: commands.Context, timezone: str, thumbnail: Optional[str] = None,
                        today: Optional[datetime] = None, season: Optional[DateTools.Season] = None,
                        time_of_day: Optional[DateTools.TimeOfDay] = None) -> EmbededMessage:
        # retrieves today's date if not found yet
        if (today is None):
            # get current datetime
            utc_today = DateTools.get_current_dt(utc = True)
            today = await DateTools.convert_date(utc_today, timezone)

        # get the season, time of day, moon phase
        if (season is None):
            season = DateTools.get_season(today)

        if (time_of_day is None):
            time_of_day = season.get_time_of_day(today)

        # emoji for the title of the embed
        emoji = season.emoji
        colour = "black"
        image_choice = 0

        if (time_of_day == DateTools.TimeOfDayName.Night):
            emoji += DateTools.get_moonphase(today).name.value
            colour = "dark-purple"
        elif (time_of_day == DateTools.TimeOfDayName.Dawn):
            emoji += "\U00002600"
            colour = "dark-yellow"
            image_choice = 1
        elif (time_of_day == DateTools.TimeOfDayName.Day):
            emoji += "\U00002600"
            colour = "light-blue"
            image_choice = 2
        elif (time_of_day == DateTools.TimeOfDayName.Dusk):
            emoji += "\U00002600"
            colour = "dark-orange"
            image_choice = 3

        # format the thumbnail
        set_thumbnail = StringTools.TRUE_DEFAULT
        if (thumbnail is None):
            set_thumbnail = StringTools.FALSE_DEFAULT
            thumbnail = set_thumbnail

        image = Pics.get_image_link(season.img_category, image_choice)
        embeded_message = self.embed.context_embed(ctx, f"Today is **{today.strftime('%A, %B %d %Y')}** and the current time is **{today.strftime('%I:%M:%S %p')}**", f"{emoji} Today's Date", colour, thumbnail, f"{image}")
        return embeded_message


    # date(ctx) Displays the date for the server or the user
    # effects: sends an embed
    async def date(self, ctx: commands.Context):
        error = False
        in_server = bool(ctx.guild is not None)

        if (in_server):
            error = await ChannelTools.validate_activity_channel(ctx, error)

        if (not error):
            # get current datetime
            if (in_server):
                timezone = Database.default_select(ServerSettings.default_setting, SelectType.List, ["timezone", "Server_Accounts"], {"conditions": {"id": ctx.guild.id}}, [ctx], {})[0]
                thumbnail = str(ctx.guild.icon_url)
            else:
                timezone = Database.default_select(UserSettings.default_setting, SelectType.List, ["timezone", "User_Accounts"], {"conditions": {"id": ctx.author.id}}, [ctx], {})[0]
                thumbnail = str(ctx.author.avatar_url)

            embeded_message = await self.make_date(ctx, timezone, thumbnail = thumbnail)

            if (in_server):
                embeded_message.embed.description += f" in the server `{ctx.guild.name}`"
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # generate_forecast_pg(current_page, max_page, kwargs) Adds the weather to the
    #   display for the date in the embed
    # requires: current_page >= 1
    #           max_page >= 1
    async def generate_forecast_pg(self, current_page: int, max_page: int, kwargs: Dict[str, Any]) -> EmbededMessage:
        forecasts = kwargs["forecasts"]
        embeded_message = kwargs["embeded_message"]
        forecast_len = len(forecasts)
        indices = Pagination.get_indices(current_page, MAX_FORECAST_PER_PAGE, forecast_len)

        start_index = indices["start_index"]
        end_index = indices["end_index"]

        embeded_message.embed.clear_fields()

        for i in range(start_index, end_index):
            weather_info = forecasts[i]
            message = f"{weather_info.sky_emoji}  **{weather_info.sky_text}**\n\n"
            message += f"***temperature***:  `{weather_info.temperature}°C`\n"

            if (isinstance(weather_info, Weather.WeatherInfo)):
                if (weather_info.feels_like != weather_info.temperature):
                    message += f"***feels like***:  `{weather_info.feels_like}°C`\n\n"
                message += f"***humidity***:  `{weather_info.humidity}%`\n"
                message += f"***wind***:  `{weather_info.wind_display}`"

            elif (isinstance(weather_info, Weather.WeatherForecastInfo)):
                message += f"***high \U0001F53A***:  `{weather_info.high}°C`\n"
                message += f"***low \U0001F53B***:  `{weather_info.low}°C`\n"

                if (weather_info.precipitation is not None):
                    message += f"***precipitation***:  `{weather_info.precipitation}%`"
            embeded_message = self.embed.add_section(embeded_message, f"{weather_info.relative_date} Weather in {weather_info.name}", message, inline = False)

            embeded_message.embed.set_image(url = StringTools.get_link(weather_info.sky_image))

        return embeded_message


    # make_weather(ctx, region, thumbnail) Generates the weather and
    #   the current date for 'region'
    async def make_weather(self, ctx: commands.Context, region: str, thumbnail: Optional[str] = None) -> EmbededMessage:
        weather_info = await Weather.get_weather(region)
        utc_today = DateTools.get_current_dt(utc = True)
        today = await DateTools.add_date(utc_today, weather_info.tz_offset)

        # get the time of day
        season = DateTools.get_season(today)
        time_of_day = season.get_time_of_day(today)

        # get the image for the weather
        weather_info.sky_image = weather_info.sky_weather.get_image(time_of_day)

        embeded_message = await self.make_date(ctx, None, thumbnail = thumbnail, today = today, season = season, time_of_day = time_of_day)
        embeded_message.embed.description += f" in **{weather_info.name}**"
        embeded_message.embed.title = embeded_message.embed.title[0:3] + "Today's Weather"

        generate_forecast_pg_kwargs = {"forecasts": [weather_info], "embeded_message": embeded_message}
        embeded_message = await self.generate_forecast_pg(1, 1, generate_forecast_pg_kwargs)
        return embeded_message


    # make_weather_forecast(ctx, embed, region, thumbnail) Generates the
    #   5-day weather forecast for 'region'
    async def make_weather_forecast(self, ctx: commands.Context, region: str,
                                    thumbnail: Optional[str] = None) -> Dict[str, Union[EmbededMessage, int, Dict[str, Any]]]:
        utc_today = DateTools.get_current_dt(utc = True)
        time_of_day = DateTools.TimeOfDayName.Day

        weather_forecast_info = await Weather.get_weather_forecast(region, utc_today, time_of_day)

        set_thumbnail = StringTools.FALSE_DEFAULT
        if (thumbnail is not None):
            set_thumbnail = StringTools.TRUE_DEFAULT

        embeded_message = self.embed.context_embed(ctx, f"Here is the 5-day forecast for **{weather_forecast_info[0].name}**",
                                                   f"5-Day Forecast for {weather_forecast_info[0].name}", "light-purple", thumbnail, None)

        max_page = Pagination.get_total_pages(MAX_FORECAST_PER_PAGE, len(weather_forecast_info))
        current_page = 1

        generate_forecast_pg_kwargs = {"forecasts": weather_forecast_info, "embeded_message": embeded_message}
        embeded_message = await self.generate_forecast_pg(current_page, max_page, generate_forecast_pg_kwargs)
        return {"embeded_message": embeded_message, "current_page": current_page, "max_page": max_page, "generate_pg_kwargs": generate_forecast_pg_kwargs}


    # weather(ctx) Shows the weather of the region of the server
    # effects: sends an embed
    async def weather(self, ctx: commands.Context):
        error = False
        in_server = bool(ctx.guild is not None)

        if (in_server):
            error = await ChannelTools.validate_activity_channel(ctx, error)

        if (not error):
            # get current region
            if (in_server):
                region = Database.default_select(ServerSettings.default_setting, SelectType.List, ["region", "Server_Accounts"], {"conditions": {"id": ctx.guild.id}}, [ctx], {})[0]
                thumbnail = str(ctx.guild.icon_url)
            else:
                region = Database.default_select(UserSettings.default_setting, SelectType.List, ["region", "User_Accounts"], {"conditions": {"id": ctx.author.id}}, [ctx], {})[0]
                thumbnail = str(ctx.author.avatar_url)

            embeded_message = await self.make_weather(ctx, region, thumbnail = thumbnail)
            await ctx.send(embed = embeded_message.embed, file = embeded_message.file)


    # weather_forecast(ctx) Show the 5-day weather forecast of the region of
    #   the server
    # effects: sends and edits an embed
    #          listens to button presses
    async def weather_forecast(self, ctx: commands.Context):
        error = False
        in_server = bool(ctx.guild is not None)
        if (in_server):
            error = await ChannelTools.validate_activity_channel(ctx, error)

        if (not error):
            # get current region
            if (in_server):
                region = Database.default_select(ServerSettings.default_setting, SelectType.List, ["region", "Server_Accounts"], {"conditions": {"id": ctx.guild.id}}, [ctx], {})[0]
                thumbnail = str(ctx.guild.icon_url)
            else:
                region = Database.default_select(UserSettings.default_setting, SelectType.List, ["region", "User_Accounts"], {"conditions": {"id": ctx.author.id}}, [ctx], {})[0]
                thumbnail = str(ctx.author.avatar_url)

            generate_embed_data = await self.make_weather_forecast(ctx, region, thumbnail = thumbnail)

            current_page = generate_embed_data["current_page"]
            max_page = generate_embed_data["max_page"]
            embeded_message = generate_embed_data["embeded_message"]
            generate_pg_kwargs = generate_embed_data["generate_pg_kwargs"]
            paginated_components = Pagination.make_page_buttons(current_page, max_page)

            sent_message = await ctx.send(embed = embeded_message.embed, file = embeded_message.file, components = paginated_components)
            await Pagination.page_react(self.client, sent_message, current_page, max_page, self.generate_forecast_pg, generate_pg_kwargs)
