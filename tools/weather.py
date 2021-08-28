import python_weather, discord, random
from datetime import datetime
import pics.image_links as Pics
import tools.datetime as DateTools
from typing import Dict, Union

REGIONS = {discord.VoiceRegion.amsterdam: "Amsterdam", discord.VoiceRegion.brazil: "Rio de Janeiro",
           discord.VoiceRegion.dubai: "Dubai", discord.VoiceRegion.eu_central: "Luxembourg",
           discord.VoiceRegion.eu_west: "Greenwich England", discord.VoiceRegion.europe: "Greenwich England",
           discord.VoiceRegion.frankfurt: "Frankfurt", discord.VoiceRegion.hongkong: "Hong Kong",
           discord.VoiceRegion.india: "New Delhi", discord.VoiceRegion.japan: "Tokyo",
           discord.VoiceRegion.london: "London England", discord.VoiceRegion.russia: "Moscow",
           discord.VoiceRegion.singapore: "Singapore", discord.VoiceRegion.southafrica: "Pretoria South Africa",
           discord.VoiceRegion.south_korea: "Seoul",  discord.VoiceRegion.sydney: "Sydney",
           discord.VoiceRegion.us_central: "North Dakota", discord.VoiceRegion.us_east: "New York",
           discord.VoiceRegion.us_south: "Florida", discord.VoiceRegion.us_west: "Washington",
           discord.VoiceRegion.vip_amsterdam: "Amsterdam", discord.VoiceRegion.vip_us_east: "New York",
           discord.VoiceRegion.vip_us_west: "Washington"}


# WeatherIndices: Class for the indices for the images of an image
class WeatherIndices():
    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end


IMG_TIME_OF_DAY_INDICES = {DateTools.TimeOfDayName.Dawn: WeatherIndices(4, 7),
                           DateTools.TimeOfDayName.Day: WeatherIndices(0, 3),
                           DateTools.TimeOfDayName.Dusk: WeatherIndices(4, 7),
                           DateTools.TimeOfDayName.Night: WeatherIndices(8, 11)}


# SkyWeather: Class for the displayed weather
class SkyWeather():
    def __init__(self, name: str, emoji: str, image_category: Pics.ImageCategory):
        self.name = name
        self.emoji = emoji
        self.image_category = image_category


    # get_image(time_of_day) Gets the associated image for the weather
    def get_image(self, time_of_day: DateTools.TimeOfDayName) -> Union[str, Dict[str, str]]:
        img_index = random.randrange(IMG_TIME_OF_DAY_INDICES[time_of_day].start, IMG_TIME_OF_DAY_INDICES[time_of_day].end)
        return Pics.get_image_link(self.image_category, img_index)


# GeneralWeatherInfo: Class for all the information needed to display about the weather
#   of a certain place for any time
class GeneralWeatherInfo():
    def __init__(self, name: str, latitude: float, longitude: float, tz_offset: float,
                 temperature: float, sky_text: str, relative_date: str, sky_emoji: str,
                 sky_weather: SkyWeather, sky_image: str):
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.tz_offset = tz_offset
        self.temperature = temperature
        self.sky_text = sky_text
        self.relative_date = relative_date
        self.sky_emoji = sky_emoji
        self.sky_weather = sky_weather
        self.sky_image = sky_image


# WeatherInfo: Class for all the information needed to display about the weather
#   of a certain place for the current date
class WeatherInfo(GeneralWeatherInfo):
    def __init__(self, name: str, latitude: float, longitude: float, tz_offset: float,
                 temperature: float, sky_text: str, humidity: float, wind_display: str,
                 relative_date: str, sky_emoji: str, sky_weather: SkyWeather, sky_image: str, feels_like: str):
        super().__init__(name, latitude, longitude, tz_offset, temperature, sky_text, relative_date, sky_emoji, sky_weather, sky_image)
        self.humidity = humidity
        self.wind_display = wind_display
        self.feels_like = feels_like


# WeatherForecastInfo: Class for all the information needed to display about the weather
#   for a 5 day forecast
class WeatherForecastInfo(GeneralWeatherInfo):
    def __init__(self, name: str, latitude: float, longitude: float, tz_offset: float,
                 temperature: float, sky_text: str, relative_date: str, sky_emoji: str,
                 sky_weather: SkyWeather, sky_image: str, low: float, high:float, precipitation: float):
        super().__init__(name, latitude, longitude, tz_offset, temperature, sky_text, relative_date, sky_emoji, sky_weather, sky_image)
        self.low = low
        self.high = high
        self.precipitation = precipitation


WEATHERS = {"sunny": SkyWeather("Sunny", "\U00002600", Pics.ImageCategory.Sunny),
            "partly sunny": SkyWeather("Partly Sunny", "\U0001F324", Pics.ImageCategory.PartlyCloudy),
            "mostly sunny": SkyWeather("Mostly Sunny", "\U0001F324", Pics.ImageCategory.Sunny),
            "clear": SkyWeather("Clear", "\U00002600", Pics.ImageCategory.Clear),
            "partly clear": SkyWeather("Partly Clear", "\U0001F324", Pics.ImageCategory.PartlyCloudy),
            "mostly clear": SkyWeather("Mostly Clear", "\U0001F324", Pics.ImageCategory.Clear),
            "cloudy": SkyWeather("Cloudy", "\U00002601", Pics.ImageCategory.Cloudy),
            "partly cloudy": SkyWeather("Partly Cloudy", "\U000026C5", Pics.ImageCategory.PartlyCloudy),
            "mostly cloudy": SkyWeather("Mostly Cloudy", "\U0001F325", Pics.ImageCategory.MostlyCloudy),
            "rain": SkyWeather("Rain", "\U0001F327", Pics.ImageCategory.Rain),
            "light rain": SkyWeather("Light Rain", "\U0001F327", Pics.ImageCategory.Rain),
            "heavy rain": SkyWeather("Heavy Rain", "\U0001F327", Pics.ImageCategory.Rain),
            "rain showers": SkyWeather("Rain Showers", "\U0001F327", Pics.ImageCategory.Rain),
            "t-storms": SkyWeather("Thunder Storms", "\U000026C8", Pics.ImageCategory.Thunder),
            "snow": SkyWeather("Snow", "\U0001F328", Pics.ImageCategory.Snow),
            "light snow": SkyWeather("Light Snow", "\U0001F328", Pics.ImageCategory.Snow),
            "heavy snow": SkyWeather("Heavy Snow", "\U0001F328", Pics.ImageCategory.Snow),
            "s-storms": SkyWeather("Snow Storms", "\U0001F328", Pics.ImageCategory.Snow)}



# get_timezone(guild) Retrieves the default region for a guild
def get_weather_region(guild: discord.Guild) -> str:
    return REGIONS[guild.region]


# get_weather_tz(weather) Retrieves the offset of the timezone of the location
#   of the weather to UTC
def get_weather_tz(weather: python_weather.response.Weather) -> float:
    offset = weather._get('@timezone')
    offset_val = None
    if (offset):
        offset_val = float(offset)

    return offset_val


# get_weather(region) Gets the information about the weather of a certain region
async def get_weather(region: str) -> WeatherInfo:
    try:
        client = python_weather.Client(format=python_weather.METRIC)
        weather = await client.find(region)
    except:
        return None
    else:

        # returns the current day's forecast temperature (int)
        current_weather = weather.current
        offset_val = get_weather_tz(weather)

        # get the emoji and image to display for the weather
        sky_text = current_weather.sky_text.lower()
        sky_weather = WEATHERS[sky_text]

        result = WeatherInfo(weather.location_name, weather.latitude, weather.longitude,
                            offset_val, current_weather.temperature, sky_weather.name,
                            current_weather.humidity, current_weather.wind_display, "Today's",
                            sky_weather.emoji, sky_weather, None, current_weather.feels_like)

        await client.close()
        return result

# get_weather(region, utc_today, time_of_day) Gets the information about the 5-day weather forecast
#   of a certain region
async def get_weather_forecast(region: str, utc_today: datetime, time_of_day: DateTools.TimeOfDay) -> WeatherForecastInfo:
    try:
        client = python_weather.Client(format=python_weather.METRIC)
        weather = await client.find(region)
    except:
        return None
    else:
        results = []
        offset_val = get_weather_tz(weather)

        for forecast in weather.forecasts:
            sky_text = forecast.sky_text.lower()
            sky_weather = WEATHERS[sky_text]
            sky_image = sky_weather.get_image(time_of_day)

            today = await DateTools.add_date(utc_today, offset_val)
            today = DateTools.only_date(today)
            relative_date = f"{DateTools.format_relative_weekday(today, forecast.date)}'s"

            current_result = WeatherForecastInfo(weather.location_name, weather.latitude, weather.longitude,
                                                 offset_val, forecast.temperature, sky_weather.name, relative_date,
                                                 sky_weather.emoji, sky_weather, sky_image, forecast.low, forecast.high, forecast.precip)
            results.append(current_result)

        await client.close()
        return results
