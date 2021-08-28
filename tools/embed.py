import discord, enum, random
from discord.ext import commands
import pics.image_links as pics
import tools.members as members
from tools.pagination import Pagination
from tools.string import StringTools
from discord_components import Button
from typing import Optional, Dict, Union, Callable, Any, List


#colours for an embed
class Colour():
    def __init__(self, name: str, hex: int):
        self.name = name
        self.hex = hex

# colours for the side bar of an embeded message
class ColourList(enum.Enum):
    Red = Colour("red", 0xFF0000);
    DarkRed = Colour("dark-red", 0x8B0000)
    LightRed = Colour("light-red", 0xF08080)
    Orange = Colour("orange", 0xFFA500)
    DarkOrange = Colour("dark-orange", 0xFF8C00)
    LightOrange = Colour("light-orange", 0xFFCC66)
    Yellow = Colour("yellow", 0xFFFF00)
    LightYellow = Colour("light-yellow", 0xFFFFE0)
    DarkYellow = Colour("dark-yellow", 0xCC9900)
    Green = Colour("green", 0x008000)
    DarkGreen = Colour("dark-green", 0x006400)
    LightGreen = Colour("light-green", 0x90EE90)
    Blue = Colour("blue", 0x0000FF)
    LightBlue = Colour("light-blue", 0x8DD8E6)
    DarkBlue = Colour("dark-blue", 0x00008B)
    Purple = Colour("purple", 0x800080)
    DarkPurple = Colour("dark-purple", 0x8B008B)
    LightPurple = Colour("light-purple", 0xCC99FF)
    Grey = Colour("grey", 0x808080)
    DarkGrey = Colour("dark-grey", 0xA9A9A9)
    LightGrey = Colour("light-grey", 0xD3D3D3)
    Brown = Colour("brown", 0xA52A2A)
    DarkBrown = Colour("dark-brown", 0x800000)
    LightBrown = Colour("light-brown", 0xCC6600)
    RedOrange = Colour("red-orange", 0xFF6600)
    DarkRedOrange = Colour("dark-red-orange", 0xB34700)
    LightRedOrange = Colour("light-red-orange", 0xFFb380)
    YellowOrange = Colour("yellow-orange", 0xFFCC00)
    DarkYellowOrange = Colour("dark-yellow-orange", 0xCCA300)
    LightYellowOrange = Colour("light-yellow-orange", 0xFFE066)
    Lime = Colour("lime", 0xCCFF33)
    DarkLime = Colour("dark-lime", 0x66CC00)
    LightLime = Colour("light-lime", 0xBFFF80)
    Turquoise = Colour("turquoise", 0x40E0D0)
    DarkTurquoise = Colour("dark-turquoise", 0x00CED1)
    LightTurquoise = Colour("light-turquoise", 0xAFEEEE)
    BluePurple = Colour("blue-purple", 0x6666FF)
    DarkBluePurple = Colour("dark-blue-purple", 0x7300E6)
    LightBluePurple = Colour("light-blue-purple", 0xD9B3FF)
    Pink = Colour("pink", 0xFFC0CB)
    DarkPink = Colour("dark-pink", 0xFF1493)
    LightPink = Colour("light-pink", 0xFFB6C1)
    White = Colour("white", 0xFFFFFF)
    Black = Colour("black", 0x000000)


    # get_name(self, colour) Gets the colour object from the key 'colour'
    @classmethod
    def get_name(cls, colour: str) -> Optional[Colour]:
        found_colour = None
        for c in ColourList:
            if (c.value.name == colour):
                found_colour = c.value
                break

        return found_colour




#embed messages
class Embed:
    #constructor
    def __init__(self, client: discord.Client):
        self.client = client
        self.RANDOM_NAME = -1
        self.names = members.BOT_NICKNAMES
        self.EMBED_LIMIT = 6000
        self.EMBED_ERRORS = {"thumbnail": 0, "image": 1, "too long": 2}

    # embed_message(ctx, description, title, colour, author_name, display_thumbnail,
    #               thumbnail, display_author_pic, author_pic, image)
    #   Make an embeded message
    def embed_message(self, ctx: commands.Context, description: str, title: str, colour: Union[str, int],
                      author_name: str, display_thumbnail: str, thumbnail: str, display_author_pic: str,
                      author_pic: str, image: str = StringTools.FALSE_DEFAULT) -> Optional[discord.Embed]:

        #if the user does not want a description
        if (description.lower() == StringTools.NONE):
            description = ""
        try:
            embeded_message = discord.Embed(description = description)
        except:
            return self.EMBED_ERRORS["too long"]


        #set the title
        title_check = StringTools.convert_str(title.lower())
        if (title_check is not None):
            if (title_check == f"\\{StringTools.NONE}"):
                title = StringTools.NONE

            try:
                embeded_message.title = title
            except:
                return self.EMBED_ERRORS["too long"]

        #check if the entered colour matches a colour on the list
        found_colour = ColourList.get_name(colour)
        if (found_colour is not None):
            embeded_message.colour = found_colour.hex
        else:
            try:
                embeded_message.colour = colour
            except:
                embeded_message.colour = 0x33CCFF


        #error if the user does not want to display author name but accepts to
        #display author picture
        if (author_name.lower() == StringTools.NONE and display_author_pic.lower() == StringTools.TRUE_DEFAULT):

            error_message = "author's image cannot be displayed without an author name"

            error_embed = discord.Embed(title="ERROR",
                                        description="author's image cannot be displayed without an author name",
                                        color=0xFF0000)

            error_embed.set_author(name = ctx.message.author.name,
                                   icon_url = ctx.message.author.avatar_url)

            return error_embed


        elif (author_name.lower() != StringTools.NONE):

            #set the author's image
            if (display_author_pic == StringTools.TRUE_DEFAULT):
                if (author_pic.lower() == "self"):
                    embeded_message.set_author(name = author_name,
                                               icon_url = ctx.message.author.avatar_url)

                elif(author_pic.lower() == "bot"):
                    embeded_message.set_author(name = author_name,
                                               icon_url = self.client.user.avatar_url)
                else:
                    if (author_pic[0] == "<" and author_pic[-1] == ">"):
                        author_url = author_pic[1:-1]
                    else:
                        author_url = author_pic

                    embeded_message.set_author(name = author_name,
                                               icon_url = author_url)


        #set the thumbnail
        if (display_thumbnail.lower() != StringTools.FALSE_DEFAULT):

            if (thumbnail.lower() == "self"):
                embeded_message.set_thumbnail(url = ctx.message.author.avatar_url)
            elif (thumbnail.lower() == "bot"):
                embeded_message.set_thumbnail(url = self.client.user.avatar_url)
            else:
                if (thumbnail[0] == "<" and thumbnail[-1] == ">"):
                    thumbnail = thumbnail[1:-1]

                try:
                    embeded_message.set_thumbnail(url = thumbnail)
                except:
                    return self.EMBED_ERRORS["thumbnail"]

        #set the image
        if (image.lower() != StringTools.FALSE_DEFAULT):
            if (image.lower() == "self"):
                embeded_message.set_image(url = ctx.message.author.avatar_url)
            elif (image.lower() == "bot"):
                embeded_message.set_image(url = self.client.user.avatar_url)
            else:
                if (image[0] == "<" and image[-1] == ">"):
                    image = image[1:-1]

                try:
                    embeded_message.set_image(url = image)
                except:
                    return self.EMBED_ERRORS["image"]

        return embeded_message


    # add_section(self, embeded_message, field_title, field_message, inline)
    #   adds a field to the embed
    def add_section(self, embeded_message: discord.Embed, field_title: str, field_message: str,
                    inline: bool = False) -> discord.Embed:
        embeded_message.add_field(name=field_title, value=field_message, inline=inline)
        return embeded_message


    # multi_add_section(self, embeded_message, section_contents) Adds multiple
    #   sections to an embed
    def multi_add_section(self, embeded_message: discord.Embed, section_contents: Dict[str, str]) -> discord.Embed:
        section_len = len(section_contents)

        for title in section_contents:
            embeded_message = self.add_section(embeded_message, title, section_contents[title])

        return embeded_message


    #add a footer to the embed
    def add_footer(self, ctx, embeded_message: discord.Embed, text: str, footer_pic:str = StringTools.NONE):

        #if the user does not want to set an image for the footer
        if (footer_pic == StringTools.NONE):
            embeded_message.set_footer(text=text)

        #set the image for the footer
        else:
            if (footer_pic == "self"):
                url = ctx.message.author.avatar_url
            elif (footer_pic == "bot"):
                url = self.client.user.avatar_url
            else:
                url = footer_pic

            embeded_message.set_footer(text=text, icon_url=url)

        return embeded_message


    # retrieve_img(image) Retrieves an image to put into the embed
    def retrieve_img(self, image: Union[str, Dict[pics.ImageCategory, int]]) -> List[Union[bool, str, Dict[str, str]]]:
        if (isinstance(image, dict)):
            category = (list(image.keys()))[0]
            code = image[category]
            image_link = pics.get_image_link(category, code)

            if (image_link is None):
                image_link = pics.IMAGE_LIST[pics.ImageCategory.Default][0]

        elif (isinstance(image, str)):
            image_link = image

        elif (image is None):
            image_link = StringTools.FALSE_DEFAULT

        img_is_file = False
        if (isinstance(image_link, dict)):
            img_is_file = True

        return [img_is_file, image_link]


    # context_embed(ctx, description, title, colour, thumbnail, image, name) Embed template for the user context
    def context_embed(self, ctx: commands.Context, description: str, title: str, colour: Union[str, int],
                      thumbnail:str = StringTools.NONE, image: Optional[Union[str, Dict[pics.ImageCategory, int]]] = None,
                      name: Optional[str] = None) -> Union[Optional[discord.Embed], Dict[str, Union[str, Optional[discord.Embed]]]]:
        if (name is None):
            name = members.convert_name(ctx.author.id, ctx.author)
        img_is_file, image_link = self.retrieve_img(image)

        if (thumbnail == StringTools.NONE):
            thumbnail = StringTools.FALSE_DEFAULT
            set_thumbnail = StringTools.FALSE_DEFAULT
        else:
            set_thumbnail = StringTools.TRUE_DEFAULT

        if (img_is_file):
            url = image_link["url"]
            embeded_message = self.embed_message(ctx, description, title, colour, name, set_thumbnail, thumbnail, StringTools.TRUE_DEFAULT, "self", url)
            return {"file": image_link["file"], "embed": embeded_message}
        else:
            embeded_message = self.embed_message(ctx, description, title, colour, name, set_thumbnail, thumbnail, StringTools.TRUE_DEFAULT, "self", image_link)
            return embeded_message



    # bot_embed(ctx, description, title, colour, name_choice, image) Embed template for the bot
    # requires: -1 <= name_choice < len(self.names)
    def bot_embed(self, ctx: commands.Context, description: str, title: str, colour: Union[str, int],
                  name_choice: int, image: Optional[Union[str, Dict[pics.ImageCategory, int]]] = None) -> Union[Optional[discord.Embed], Dict[str, Union[str, Optional[discord.Embed]]]]:
        img_is_file, image_link = self.retrieve_img(image)

        # name for the author of the embed
        if (name_choice == self.RANDOM_NAME):
            name_choice = random.randrange(0, len(self.names))

        try:
            name = self.names[name_choice]
        except:
            name = self.names[0]

        if (img_is_file):
            url = image_link["url"]
            embeded_message = self.embed_message(ctx, description, title, colour, name, "no", "no", "yes", "bot", url)
            return {"file": image_link["file"], "embed": embeded_message}
        else:
            embeded_message = self.embed_message(ctx, description, title, colour, name, "no", "no", "yes", "bot", image_link)
            return embeded_message


    #error_embed(self, ctx, description, title) Embed an error message for the bot to display
    def error_embed(self, description: str, title: str) -> Optional[discord.Embed]:
        name_choice = random.randrange(0, len(self.names))
        embeded_message = self.bot_embed(None, description, title, "red", self.RANDOM_NAME, {pics.ImageCategory.Disappointed: 0})
        return embeded_message


    #warning_embed(self, ctx, description, title) Embed a warning embed for the bot to display
    #   requires: 0 <= choice
    def warning_embed(self, description: str, title: str, choice: int = 0) -> Optional[discord.Embed]:
        name_choice = random.randrange(0, len(self.names))

        if (choice == 0):
            embeded_message = self.bot_embed(None, description, title, "yellow", self.RANDOM_NAME, {pics.ImageCategory.Disappointed: 0})
        elif (choice == 1):
            embeded_message = self.bot_embed(None, description, title, "yellow", self.RANDOM_NAME, {pics.ImageCategory.Disappointed: 1})
        return embeded_message


    # paginated_safe_send(self, ctx, embeded_message, paginated_componenets)
    #    Sends a paginated embed if the embed does not exceed the maximum length
    # requires: 0 < page
    #           0 < max_page
    # effects: sends and edits messages
    async def paginated_safe_send(self, ctx: commands.Context, embeded_message: discord.Embed,
                                  paginated_components: List[List[Button]], page: int, max_page: int,
                                  generate_pg: Callable[[int, int, Dict[str, Any]], discord.Embed],
                                  generate_pg_kwargs: Dict[str, Any]):
        embed_len = len(embeded_message)
        if (embed_len <= self.EMBED_LIMIT):
            sent_message = await ctx.send(embed = embeded_message, components = paginated_components)
            await Pagination.page_react(self.client, sent_message, page, max_page, generate_pg, generate_pg_kwargs)
        else:
            embeded_message = Error.display_error(self.client, 16, object = "embed", measure = "character length of", your_size = str(embed_len), limit_size = str(self.EMBED_LIMIT))
            await ctx.send(embed = embeded_message)
