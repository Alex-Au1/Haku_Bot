import discord, random, datetime, os, re
from discord.ext import commands
from text.bot_texting import Embed
import set_up.prefix as Prefix

#bot definition
APP_ID = 'MY APPLICATION ID'
client = commands.Bot(command_prefix=Prefix.determine_prefix, intents=discord.Intents.all())


#load cogs onto the bot
@client.command()
async def load(ctx, file, extension):
    client.load_extension(f'{file}.{extension}')

#unload cogs onto the bot
@client.command()
async def unload(ctx, file, extension):
    client.unload_extension(f'{file}.{extension}')


#list of directories contatining files
dir = ["onload", "text", "server_info", "reaction", "search", "rpg", "media_edit", "count", "betting", "backup", "set_up", "time_and_place"];

#load the cog files
for d in dir:
    for filename in os.listdir(f'./{d}'):
        if filename.endswith('music_client.py'):
            client.load_extension(f"""{d}.{filename[:-3]}""")

        elif filename.endswith('.py'):
            try:
                client.load_extension(f"""{d}.{filename[:-3]}""")
            except:
                pass

client.run(APP_ID)
