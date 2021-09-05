import discord
from discord.ext import commands
from tools.embed import Embed
from text.bot_texting import Texting
from tools.string import StringTools


# The client module for handling texting related commands
class Text(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.texting = Texting(client)

    # on_raw_message_delete(payload) logs when someone deletes a message
    # effects: sends an embed or message
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        await self.texting.on_raw_message_delete(payload)


    # on_raw_bulk_message_delete(payload) logs when someone deletes messages by bulk
    # effects: sends an embed or a message
    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        await self.texting.on_raw_bulk_message_delete(payload)


    # on_raw_message_edit(payload) logs when someone edits any message that is out of the cache
    # effects: sends a message or embed
    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        await self.texting.on_raw_message_edit(payload)


    # on_message_edit(self, before, after) logs for editted message, if the message is still in the cache
    # effects: sends a message or an embed
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        await self.texting.on_message_edit(before, after)


    # on_message(message) Deletes the message if the message is in a
    #   server's activity channel
    # effects: may delete a message
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self.texting.on_message(message)


    # embed(ctx, description, title, colour, display_thumbnail, thumbnail, image, search_channel, search_guild)
    #   converts user's messages to embeded messages
    # effects: sends an embed and deletes message
    @commands.command(name="embed",
                          description="Converts user's messages to embeded messages \n \n <description>: message to be converted \n <title>: title of the message\n <colour>: colour of the side bar of the embed \n <display_thumbnail> (yes or no): option of displaying embed picture \n <thumbnail> (url, \"self\", \"bot\"): pictures of the embed" )
    async def embed(self, ctx: commands.Context, description: str, title: str = StringTools.NONE, colour: str = Embed.EMBED_DEFAULT_COLOUR.name,
                    thumbnail: str = StringTools.NONE, image: str = StringTools.NONE, search_channel: str = StringTools.NONE,
                    search_guild: str = StringTools.NONE):
        await self.texting.user_embed(ctx, description, title, colour, thumbnail, image, search_channel, search_guild)


    # hello(ctx) greets the user with hello
    # effects: sends an embed
    @commands.command(name="hello", description="greets the bot" ,aliases=["hi", "aloha", "whatsup", "yo", "wasup", "wazup", "watsup"])
    async def hello(self, ctx: commands.Context):
        await self.texting.hello(ctx)


    # clear(self, ctx, no_of_messages, no_from_last_message, search_channel)
    #   deletes a number of messages
    # effects: sends an embed and deletes messages
    @commands.command(name="clear")
    async def clear(self, ctx: commands.Context, no_of_messages: str, no_from_last_message: str = "0", search_channel: str = "none"):
        await self.texting.clear(ctx, no_of_messages, no_from_last_message, search_channel)


#set up of the cog to the bot
def setup(client):
    client.add_cog(Text(client))
