import discord
from discord.ext import commands
from database.database import Database
from tools.string import StringTools

DEFAULT_PREFIX = "$"

# get_prefixes(ctx) Retrieves the prefixes from a server
def get_prefixes(guild):
    prefixes = Database.select(["prefixes"], "Server_Accounts",conditions = {"id": f"{guild.id}"})
    if (prefixes):
        prefixes = prefixes[0][0]
        return StringTools.convert_list(prefixes)
    else:
        return [DEFAULT_PREFIX]


# determine_prefix(bot, message) Determines the prefix the bot listens to for each server
async def determine_prefix(bot, message):
    guild = message.guild
    if (guild):
        return get_prefixes(guild)
    else:
        return DEFAULT_PREFIX
