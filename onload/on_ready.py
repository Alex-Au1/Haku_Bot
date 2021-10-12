import discord, random, asyncio
from discord.ext import commands, tasks
import tools.audit as audit
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType

#statuses of the bot
status = [["playing", "having fun with you! <3"], ["watching", "you in pleasure! <3"], ["listening", "to your rhythm! <3"], ["playing", "love with you! <3"], ["listening", "you! <3"], ["playing","with you! <3"]]

class Ready(commands.Cog):

    #constructor
    def __init__(self, client: discord.Client):
        self.client = client
        self.index = -1
        self.change_activity.start()
        self.change_status.start()
        self.status_color = "online"
        self.audits = audit.Audits(client)

    #stopping the status background task
    def cog_unload(self):
        self.change_activity.cancel()
        self.change_status.cancel()

    #method telling that the bot just got online
    @commands.Cog.listener()
    async def on_ready(self):
        DiscordComponents(self.client)
        print('We have logged in as {0.user}'.format(self.client))
        await self.audits.get_recent_audit()
        await self.client.change_presence(activity=discord.Game("with you! <3"))


    #change the bot's activity continuosly
    @tasks.loop(seconds=10)
    async def change_activity(self):
        #increment the index
        if (self.index + 1 >= len(status)):
            self.index = 0
        else:
            self.index += 1

        #status of the bot
        if (self.status_color == "online"):
            color = discord.Status.online
        elif (self.status_color == "idle"):
            color = discord.Status.idle
        elif (self.status_color == "dnd"):
            color = discord.Status.dnd

        #change the bot's activity
        if (status[self.index][0] == "playing"):
            await self.client.change_presence(activity=discord.Game(status[self.index][1]), status=color)
        elif (status[self.index][0] == "watching"):
            await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status[self.index][1]), status=color)
        elif (status[self.index][0] == "listening"):
            await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=status[self.index][1]), status=color)


    #change the bot's statuses continuosly
    @tasks.loop(seconds=15)
    async def change_status(self):
        color_status = random.randrange(3)

        #continue the activity that is being played
        if (status[self.index][0] == "playing"):
            activity = discord.Game(status[self.index][1])
        elif (status[self.index][0] == "watching"):
            activity = discord.Activity(type=discord.ActivityType.watching, name=status[self.index][1])
        elif (status[self.index][0] == "listening"):
            activity=discord.Activity(type=discord.ActivityType.listening, name=status[self.index][1])

        if (color_status == 0):
            await self.client.change_presence(activity = activity, status=discord.Status.online)
            self.status_color = "online"

        elif (color_status == 1):
            await self.client.change_presence(activity = activity, status=discord.Status.idle)
            self.status_color = "idle"

        elif(color_status == 2):
            await self.client.change_presence(activity = activity, status=discord.Status.dnd)
            self.status_color = "dnd"


    @change_activity.before_loop
    async def before_change_activity(self):
        print('waiting...')
        await self.client.wait_until_ready()


    @change_status.before_loop
    async def before_change_status(self):
        print('and waiting...')
        await self.client.wait_until_ready()


    #ping pong method
    @commands.command()
    async def ping(self, ctx):
        await ctx.send("Pong");
        await ctx.send("1/1 packets received, 100% success connection to {0.user}".format(self.client))



def setup(client):
    client.add_cog(Ready(client))
