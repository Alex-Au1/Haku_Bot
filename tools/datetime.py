from datetime import datetime, timedelta
from tools.validate import Validate
import enum, discord
import pics.image_links as Pics
from tools.string import StringTools
from database.database import Database
import tools.error as Error
from dateutil.relativedelta import *
from typing import Dict, Union, List, Any, Optional
import pytz

TIMEZONES = {discord.VoiceRegion.amsterdam: "Europe/Amsterdam", discord.VoiceRegion.brazil: "Brazil/East", discord.VoiceRegion.dubai: "Asia/Dubai", discord.VoiceRegion.eu_central: "Europe/Luxembourg",
             discord.VoiceRegion.eu_west: "UTC", discord.VoiceRegion.europe: "UTC", discord.VoiceRegion.frankfurt: "Europe/Zurich", discord.VoiceRegion.hongkong: "Hongkong", discord.VoiceRegion.india: "Asia/Kolkata",
             discord.VoiceRegion.japan: "Japan",  discord.VoiceRegion.london: "Europe/London", discord.VoiceRegion.russia: "Europe/Moscow", discord.VoiceRegion.singapore: "Singapore", discord.VoiceRegion.southafrica: "Etc/GMT+2",
             discord.VoiceRegion.south_korea: "Asia/Seoul",  discord.VoiceRegion.sydney: "Australia/Sydney", discord.VoiceRegion.us_central: "America/North_Dakota/Center", discord.VoiceRegion.us_east: "America/Toronto",
             discord.VoiceRegion.us_south: "America/Mexico_City", discord.VoiceRegion.us_west: "America/Los_Angeles", discord.VoiceRegion.vip_amsterdam: "Europe/Amsterdam", discord.VoiceRegion.vip_us_east: "America/Toronto",
             discord.VoiceRegion.vip_us_west: "America/Los_Angeles"}

DATETIME_WAIT = 10
SHORT_FORMAT = 0
LONG_FORMAT = 1
DATABASE_FORMAT = 2

DAWN_DUSK_TIME = 3
TIME_LIMITS = [23, 59, 59]
DAYS_PER_WEEK = 7

class SeasonName(enum.Enum):
    Spring = "spring"
    Summer = "summer"
    Fall = "fall"
    Winter = "winter"

class TimeOfDayName(enum.Enum):
    Day = "Day"
    Night = "Night"
    Dawn = "Dawn"
    Dusk = "Dusk"

class MoonPhaseName(enum.Enum):
    WaxingCrescent = "\U0001F312"
    FistQuarter = "\U0001F313"
    WaxingGibbous = "\U0001F314"
    FullMoon = "\U0001F315"
    WanningGibbous = "\U0001F316"
    LastQuarter = "\U0001F317"
    WanningCrescent = "\U0001F318"
    NewMoon = "\U0001F311"


# class for a time of day
class TimeOfDay():
    def __init__(self, hour: int, min: int):
        self.hour = hour
        self.min = min


# class for a season
class Season():
    def __init__(self, name: SeasonName, emoji: str, img_category: Pics.ImageCategory,
                 start: datetime, end: datetime, sunrise: TimeOfDay, sunset: TimeOfDay):
        self.name = name
        self.emoji = emoji
        self.img_category = img_category
        self.start = {"day": int(start.strftime("%d")), "month": int(start.strftime("%m"))}
        self.end = {"day": int(end.strftime("%d")), "month": int(end.strftime("%m"))}
        self.sunrise = sunrise
        self.sunset = sunset

    # is_season(self, date) Determines if 'date' is within the period of the
    #   season
    def is_season(self, date: datetime) -> bool:
        month = int(date.strftime("%m"))
        year = int(date.strftime("%Y"))
        tzinfo = date.tzinfo

        # if the season is between 2 years
        if (self.start["month"] > self.end["month"] and month < self.start["month"]):
            year += 1

        self.start_date = datetime(year, self.start["month"], self.start["day"], tzinfo = tzinfo)
        self.end_date = datetime(year, self.end["month"], self.end["day"], tzinfo = tzinfo)

        return (datetime_inbetween(date, self.start_date, self.end_date))


    # get_time_of_day(self, date) Finds the time of day for 'date' during a
    #   certain season
    def get_time_of_day(self, date: datetime) -> TimeOfDayName:
        td_sunrise = date.replace(hour=self.sunrise.hour, minute=self.sunrise.min)
        td_sunset = date.replace(hour=self.sunset.hour, minute=self.sunset.min)
        td_dawn_end = td_sunrise.replace(hour = self.sunrise.hour + DAWN_DUSK_TIME)
        td_dusk_start = td_sunset.replace(hour = self.sunset.hour - DAWN_DUSK_TIME)

        if (datetime_inbetween(date, td_sunrise, td_dawn_end)):
            return TimeOfDayName.Dawn
        elif (datetime_inbetween(date, td_dawn_end, td_dusk_start)):
            return TimeOfDayName.Day
        elif (datetime_inbetween(date, td_dusk_start, td_sunset)):
            return TimeOfDayName.Dusk
        else:
            return TimeOfDayName.Night


# class for a moonphase
class MoonPhase():
    def __init__(self, name: MoonPhaseName, start_day: int, end_day: int):
        self.name = name
        self.start_day = start_day
        self.end_day = end_day

    # is_phase(self, date) Determines if the day of the month for 'date' has
    #   the certain moon phase
    def is_phase(self, date: datetime) -> bool:
        day = int(date.strftime("%d"))
        return (day >= self.start_day and day <= self.end_day)


SEASON_LIST = [Season(SeasonName.Spring, "\U0001F337", Pics.ImageCategory.Spring, datetime(2020, 3, 20), datetime(2020, 6, 20), TimeOfDay(6, 27), TimeOfDay(20, 16)),
               Season(SeasonName.Summer, "\U0001F3D6", Pics.ImageCategory.Summer, datetime(2020, 6, 20), datetime(2020, 9, 22), TimeOfDay(6, 20), TimeOfDay(20, 10)),
               Season(SeasonName.Fall, "\U0001F342", Pics.ImageCategory.Fall, datetime(2020, 9, 22), datetime(2020, 12, 21), TimeOfDay(7, 26), TimeOfDay(17, 58)),
               Season(SeasonName.Winter, "\U00002744", Pics.ImageCategory.Winter, datetime(2020,12, 21), datetime(2021, 3, 20), TimeOfDay(7, 33), TimeOfDay(18, 6))]

MOON_PHASES = [MoonPhase(MoonPhaseName.WaxingCrescent, 1, 4), MoonPhase(MoonPhaseName.FistQuarter, 5, 8),
               MoonPhase(MoonPhaseName.WaxingGibbous, 9, 12), MoonPhase(MoonPhaseName.FullMoon, 13, 15),
               MoonPhase(MoonPhaseName.WanningGibbous, 16, 19), MoonPhase(MoonPhaseName.LastQuarter, 20, 23),
               MoonPhase(MoonPhaseName.WanningCrescent, 24, 27), MoonPhase(MoonPhaseName.NewMoon, 28, 31)]


# get_season(datetime) Determines the season period for 'utc_datetime'
def get_season(datetime: datetime) -> Season:
    season = None
    for s in SEASON_LIST:
        if (s.is_season(datetime)):
            season = s
            break

    return season


# get_moonphase(datetime) Determines the moon phase for 'datetime'
def get_moonphase(datetime: datetime) -> MoonPhase:
    phase = None
    for p in MOON_PHASES:
        if(p.is_phase(datetime)):
            phase = p
            break
    return phase


# get_timezone(guild) Retrieves the timezone of a specific guild
def get_timezone(guild: discord.Guild) -> str:
    return TIMEZONES[guild.region]


# db_get_timezone(guild_id) Retrieves an existing timezone of a certain guild
def db_get_timezone(guild_id: int) -> Optional[str]:
    result = Database.select(["timezone"], "Server_Accounts",conditions = {"id": f"{guild_id}"})
    if (result):
        return result[0][0]
    else:
        return None


# format_date(utc_datetime) Formats the utc date, 'utc_datetime'
async def format_date(utc_datetime: datetime, format: str = SHORT_FORMAT, convert: bool = True,
                      timezone:str = TIMEZONES[discord.VoiceRegion.vip_us_east]) -> str:
    if (convert):
        date = await convert_date(utc_datetime, timezone)
    else:
        date = utc_datetime

    formatted_date = None
    if (format == SHORT_FORMAT):
        formatted_date = date.strftime('%m/%d/%Y  %I:%M:%S %p')
    elif (format == LONG_FORMAT):
        formatted_date = f"**{date.strftime('%A, %B %d %Y')}** at **{date.strftime('%I:%M:%S %p')}**"
    elif (format == DATABASE_FORMAT):
        formatted_date = f"{date.strftime('%Y-%m-%d-%H-%M-%S')}"

    return formatted_date


# format_timezone(timezone, region, sync) Formats the timezone to be displayed
# requires: 0 <= sync <= 1
def format_timezone(timezone: str, region: str, sync: int) -> str:
    tz_float = None
    try:
        tz_float = float(timezone)
    except:
        return timezone
    else:
        if (sync):
            return f"Synced with {region}"
        else:
            sign = ""
            if (tz_float >= 0):
                sign = "+"
            return f"UTC {sign}{tz_float} Hours"



# match_date(utc_datetime) Determines if 'utc_datetime' matches with the
#   current datetime with a certain tolerance
def match_date(utc_datetime: datetime) -> bool:
    utc_now = datetime.utcnow()
    difference = (utc_now - utc_datetime).total_seconds()
    return (difference <= DATETIME_WAIT)


# datetime_comp(current_dt, dt_to_compare) Compares 'current_dt' with
#   'dt_to_compare'
def datetime_comp(current_dt: datetime, dt_to_compare: datetime) -> float:
    return (current_dt - dt_to_compare).total_seconds()


# datetime_inbetween(current_dt, start_dt, end_dt) Determines if 'current_dt' is
#   in between 'start_dt' and 'end_dt'
def datetime_inbetween(current_dt: datetime, start_dt: datetime, end_dt: datetime) -> bool:
    return (datetime_comp(current_dt, start_dt) >= 0 and datetime_comp(current_dt, end_dt) <= 0)


# get_current_dt() Retrieves the current datetime
def get_current_dt(utc: bool = False) -> datetime:
    utc_now = datetime.utcnow()
    if (not utc):
        date = utc_now - timedelta(hours = 4)
    else:
        date = utc_now
    return date

# get_time_parts(hours) Seperates the total number of hours to days, hours,
#   minutes and seconds
def get_time_parts(hours: int) -> Dict[str, Union[bool, List[int]]]:
    negative_duration = False
    if (hours < 0):
        negative_duration = True
        hours *= -1

    time_parts = []
    hour_parts = int(hours)
    days, hours = divmod(hour_parts, TIME_LIMITS[0] + 1)

    time_parts.append(days)
    time_parts.append(hours)

    remaining_parts = hours - hour_parts
    for i in range(1, 3):
        remaining_parts *= (TIME_LIMITS[i] + 1)
        desired_part = int(remaining_parts)

        time_parts.append(desired_part)
        remaining_parts -= desired_part

    return {"negative_duration": negative_duration, "time_parts": time_parts}


# get_time_diff(time_parts) Retrieves the time difference from 'time_parts'
# requires: 'time_parts' has length at most 4
async def get_time_diff(client, time_parts: List[int]) -> timedelta:
    validate = Validate(client)

    time_diff = [0, 0, 0, 0]
    time_len = len(time_parts)
    time_diff_len = len(time_diff)
    result = None

    if (time_len < 0 or time_len > time_diff_len):
        return result

    shift = time_diff_len - time_len
    for i in range(shift, time_diff_len):
        current_time_pt = await validate.check_natural(None, time_parts[i - shift], i, verbose = False)

        if (((current_time_pt is not None) and (not i)) or ((current_time_pt is not None) and (i) and (current_time_pt <= TIME_LIMITS[i - 1]))):
            time_diff[i] = current_time_pt
        else:
            return result

    result = timedelta(days = time_diff[0], hours = time_diff[1], minutes = time_diff[2], seconds = time_diff[3])
    return result


# validate_time_diff(self, ctx, client, error, var, var_name, sperator) Determines if
#   'var' is a valid duration input and displays an error if it is not
# effects: may send an embed
async def validate_time_diff(ctx, client: discord.Client, error: bool, var: Any, var_name: str, seperator: str = ":") -> List[Any]:
    # check if the duration entered is valid
    var = StringTools.convert_none(var)
    result = None

    if (var is not None):
        var = var.split(seperator)
        time_diff = await get_time_diff(client, var)

        if (time_diff is None):
            if (not error):
                embeded_message = Error.display_error(client, 15, correct_type = "datetime", parameter = var_name)
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
            error = True
            result = var
        else:
            result = time_diff

    return [error, result]


# add_date(utc_datetime, time_offset) Adds 'time_offset' to the utc datetime
async def add_date(utc_datetime: datetime, time_offset: int) -> datetime:
    time_parts = get_time_parts(time_offset)
    time_diff = await get_time_diff(None, time_parts["time_parts"])

    if (time_parts["negative_duration"]):
        date = utc_datetime - time_diff
    else:
        date = utc_datetime + time_diff

    return date


# convert_date(utc_datetime, timezone) Converts the utc datetime to the datetime
#   according to 'timezone'
async def convert_date(utc_datetime: datetime, timezone: str) -> datetime:
    try:
        tz_float = float(timezone)
    except:
        current_timezone = pytz.timezone(timezone)
        utc_dt = utc_datetime.replace(tzinfo=pytz.utc)
        date = utc_dt.astimezone(current_timezone)
    else:
        date = await add_date(utc_datetime, tz_float)

    return date


# add_leading_zero(str) Adds a leading zero to 'str'
def add_leading_zero(str: str, limit: int = 10) -> str:
    result = str

    try:
        int_str = int(str)

        if (int_str < limit):
            result = f"0{int_str}"
    except:
        pass

    return result


# format_time(time, verbose) Produces a string that divides 'time' into days, hours,
#    minutes and seconds
def format_time(time: int, verbose: bool = False) -> str:
    min = 60
    hr = 60
    day = 24

    formatted_min, formatted_sec = divmod(time, min)
    formatted_hr, formatted_min = divmod(formatted_min, hr)
    formatted_day, formatted_hr = divmod(formatted_hr, day)

    formatted_sec = add_leading_zero(formatted_sec)

    if (formatted_day or formatted_hr):
        formatted_min = add_leading_zero(formatted_min)

        if (formatted_day):
            formatted_hr = add_leading_zero(formatted_hr)

    if (not verbose):
        str_time = f"{formatted_min}:{formatted_sec}"

        if (formatted_day):
            str_time = f"{formatted_day}:{formatted_hr}:{str_time}"
        elif (formatted_hr):
            str_time = f"{formatted_hr}:{str_time}"
    else:
        str_time = f"{formatted_min} minute(s), {formatted_sec} second(s)"

        if (formatted_day):
            str_time = f"{formatted_day} day(s), {formatted_hr} hour(s), {str_time}"
        elif (formatted_hr):
            str_time = f"{formatted_hr} hour(s), {str_time}"

    return str_time


# get_duration(str_date, seperator) Gets the datetime for the string 'str_date'
def get_duration(str_date: str, seperator: str = "-") -> datetime:
    date_pt = str_date.split(seperator)
    return datetime(int(date_pt[0]), int(date_pt[1]), int(date_pt[2]), hour = int(date_pt[3]), minute = int(date_pt[4]), second = int(date_pt[5]))


# sec_duration(end_date, start_date) Gets the difference between 'end_date' and
#   'start_date' in seconds
def sec_duration(end_date: datetime, start_date: datetime) -> int:
    return int((end_date - start_date).total_seconds())


# format_duration(end_date, start_date) Formats the duration
def format_duration(end_date: datetime, start_date: Union[str, datetime] = "now") -> str:
    if (start_date == "now"):
        start = get_current_dt()
    else:
        start = start_date

    diff = sec_duration(end_date, start)
    if (diff <= 0):
        return None
    else:
        return format_time(diff, verbose = True)


# get_weekday_num(date) Gets the number representing the day of the week
#   where Monday is the start of the week
def get_weekday_num(date: datetime) -> int:
    weekday = int(date.strftime("%w"))

    if (not weekday):
        return 7
    else:
        return weekday


# format_relative_weekday(reference_date, target_date) Gets the relative date
#   to call 'target_date' based from 'reference_date'
def format_relative_weekday(reference_date: datetime, target_date: datetime) -> str:
    reference_weekday = get_weekday_num(reference_date)

    if (reference_date == target_date):
        return "Today"
    elif (reference_date > target_date):
        yesterday = reference_date - timedelta(days = 1)
        current_week_start = reference_date - timedelta(days = (reference_weekday - 1))
        last_week_start = current_week_start - timedelta(days = DAYS_PER_WEEK)

        if (yesterday == target_date):
            return "Yesterday"
        elif (datetime_inbetween(target_date, current_week_start, yesterday)):
            return target_date.strftime("%A")
        elif (datetime_inbetween(target_date, last_week_start, current_week_start)):
            return f"Last {target_date.strftime('%A')}"

    else:
        tomorrow = reference_date + timedelta(days = 1)
        current_week_end = reference_date + timedelta(days = (DAYS_PER_WEEK - reference_weekday + 1))
        next_week_end = current_week_end + timedelta(days = DAYS_PER_WEEK)

        if (tomorrow == target_date):
            return "Tomorrow"
        elif (datetime_inbetween(target_date, tomorrow, current_week_end)):
            return target_date.strftime("%A")
        elif (datetime_inbetween(target_date, current_week_end, next_week_end)):
            return f"Next {target_date.strftime('%A')}"

    return target_date.strftime('%A, %B %d %Y')


# only_date(datetime) Retrieves only the date portion from 'datetime'
def only_date(datetime: datetime) -> datetime:
    return datetime.replace(hour = 0, minute = 0, second = 0, microsecond = 0)


# yt_format_to_dict(date) Formats the publising time difference from a youtube
#   video to a dictionary
def yt_format_to_dict(date: str) -> Optional[Dict[str, int]]:
    if (date.endswith("ago")):
        date = date.replace(" ago", "")
        date = StringTools.word_replace(date, {" ago": "", "Streamed": ""})
        date_lst = date.split()
        result = {}
        current_value = 0

        date_lst_len = len(date_lst)
        for i in range(date_lst_len):
            if (i % 2):
                key = date_lst[i].strip()
                if (key[-1] == "s"):
                    key = key[:-1]

                result[key] = current_value
            else:
                current_value = int(date_lst[i])
    else:
        result = None

    return result


# yt_format_to_dict(date) Formats the publishing time difference from youtube
#   video to the string of the date the video was published
def get_yt_format_date(date: str) -> datetime:
    date_dict = yt_format_to_dict(date)
    if (date_dict is not None):
        date_kwargs = {"year": 0, "month": 0, "week": 0, "day":0, "hour": 0, "minute": 0, "second": 0}
        date_keys = list(date_kwargs.keys())

        for d in date_dict:
            if (d in date_keys):
                date_kwargs[d] = date_dict[d]

        datediff = relativedelta(years = date_kwargs["year"], months = date_kwargs["month"], weeks = date_kwargs["week"], days = date_kwargs["day"], hours = date_kwargs["hour"], minutes = date_kwargs["minute"], seconds = date_kwargs["second"])
        publish_date = get_current_dt(utc = True) - datediff

    else:
        publish_date = get_current_dt(utc = True)
    return publish_date

