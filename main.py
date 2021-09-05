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
dir = ["onload", "text", "server_info", "reaction", "search", "media_edit", "count", "betting", "backup", "set_up"];

#load the cog files
for d in dir:
    for filename in os.listdir(f'./{d}'):
        if filename.endswith('setting_client.py'):
            client.load_extension(f"""{d}.{filename[:-3]}""")

        elif filename.endswith('.py'):
            try:
                client.load_extension(f"""{d}.{filename[:-3]}""")
            except:
                pass

#make everyone's game status in the rpg to be off
folder = os.getcwd()
folder += "/rpg/user_data"

for user_account in os.listdir(f'./rpg/user_data'):
    file = os.path.join(folder, user_account)

    #read the file for comparison
    account = open(file, 'r')
    account.seek(0)

    file_source = account.readlines()

    account.close()

    new_account = open(file, 'w')

    #turn off the game
    i = 0
    for line in file_source:
        i += 1

        if (i == 1 or i == 19 or i == 29):
            new_account.write("0\n")
        else:
            new_account.write(line)

    new_account.close()


client.run(APP_ID)
