import discord, enum, random, copy
from discord.ext import commands
import pics.image_links as pics
import tools.members as members
from tools.string import StringTools
from discord_components import Button
from typing import Optional, Dict, Union, Callable, Any, List


# EmbedParts: Different parts in an embed
class EmbedParts(enum.Enum):
    Title = "title for the embed"
    Description = "description for the embed"
    Fields = "no. of fields in the embed"
    FieldTitle = "title for one of your fields"
    FieldMessage = "message for one of your fields"
    Footer = "footer for the embed"
    AuthorName = "author name for the embed"
    Total = "embed size"


# EmbedImages: Different image parts for an embed
class EmbedImages(enum.Enum):
    Thumbnail = "thumbnail"
    Image = "image"
    AuthorImage = "author pic"
    FooterImage = "footer pic"
    AuthorDesc = "author and description"


EMBED_LIMITS = {EmbedParts.Title: 256, EmbedParts.Description: 4096, EmbedParts.Fields: 25,
                EmbedParts.FieldTitle: 256, EmbedParts.FieldMessage: 1024, EmbedParts.Footer: 2048,
                EmbedParts.AuthorName: 256, EmbedParts.Total: 6000}


# EmbededMessage: class for an embed
class EmbededMessage():
    def __init__(self, embed: discord.Embed, error: bool, file: Optional[str] = None):
        self.embed = embed
        self.error = error
        self.file = file


# EmbedCheck: Data for checking limits on an embed
class EmbedCheck():
    def __init__(self, error: bool, value: Any, error_embed: discord.Embed):
        self.error = error
        self.value = value
        self.error_embed = error_embed

    # get_embed(embeded_message) Retrieves the appropriate embed for based off the
    #   check
    def get_embed(self, embeded_message: discord.Embed) -> discord.Embed:
        if (self.error):
            return self.error_embed
        else:
            return embeded_message


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
    EMBED_IMG_SELF = "self"
    EMBED_IMG_BOT = "bot"
    EMBED_DEFAULT_COLOUR = ColourList.LightPurple.value

    #constructor
    def __init__(self, client: discord.Client):
        self.client = client
        self.RANDOM_NAME = -1
        self.names = members.BOT_NICKNAMES


    # embed_limit_error(type, size) Formats the error when a part of the embed
    #   exceeds its limit
    def embed_limit_error(self, type: EmbedParts, size: int) -> discord.Embed:
        description = f"Your {type.value} with the size `{size}` exceeds the limit of the size `{EMBED_LIMITS[type]}`"
        title = f"ERROR 16: Your {StringTools.str_capitalize(type.value)} is too Big"
        return discord.Embed.from_dict({"title": title, "description": description,
                                        "color": ColourList.Red.value.hex,
                                        "image": Pics.get_image_link(Pics.ImageCategory.Disappointed, 0)})


    # embed_link_error(self, type) Formats the embed when a picture in the embed
    #   is invalid
    def embed_link_error(self, type: EmbedImages, image: str) -> discord.Embed:
        if (type != EmbedImages.AuthorDesc):
            description = f"The picture for the {type.value} by the content `{image}` is invalid"
            title = f"ERROR 17: Invalid {StringTools.str_capitalize(type.value)}"
        else:
            description = "The author's image cannot be displayed without an author name in the embed"
            title = f"ERROR 18: Author Image Must Have Author Name"
        return discord.Embed.from_dict({"title": title, "description": description,
                                        "color": ColourList.Red.value.hex,
                                        "image": Pics.get_image_link(Pics.ImageCategory.Disappointed, 0)})


    # check_embed_limit(type, to_check, success_func, success_args, success_kwargs)
    #   Calls 'success_func' if the length of 'to_check' does not exceed its part's
    #   corresponding limit
    def check_embed_limit(self, type: EmbedParts, to_check: Any, success_func: Optional[Callable[[...], Any]] = None,
                          success_args: List[Any] = [], success_kwargs: Dict[str, Any] = {},
                          return_value: Optional[Any] = None) -> EmbedCheck:
        error = False
        size = len(to_check)

        if (size > EMBED_LIMITS[type]):
            error = True
            return EmbedCheck(error, None, self.embed_limit_error(type, size))
        elif (success_func is not None):
            return EmbedCheck(error, success_func(*success_args, **success_kwargs), None)
        elif (return_value is not None):
            return EmbedCheck(error, return_value, None)
        else:
            return None


    # embed_message(ctx, description, title, colour, author_name, display_thumbnail,
    #               thumbnail, display_author_pic, author_pic, image)
    #   Make an embeded message
    def embed_message(self, ctx: commands.Context, description: Optional[str], title: Optional[str], colour: Union[str, int],
                      author_name: Optional[str], thumbnail: Optional[str], author_pic: Optional[str],
                      image: Optional[str] = None) -> EmbededMessage:
        embed_check = None
        #if the user does not want a description
        if (description is None):
            description = ""
        embed_check = self.check_embed_limit(EmbedParts.Description, description, discord.Embed, success_kwargs = {"description": description})
        embeded_message = embed_check.get_embed(embed_check.value)

        #set the title
        if (not embed_check.error):
            title_check = StringTools.convert_str(title)
            if (title_check is not None and title is not None):
                if (title_check == f"\\{StringTools.NONE}"):
                    title = StringTools.NONE

                embed_check = self.check_embed_limit(EmbedParts.Title, title, return_value = title)
                embeded_message.title = embed_check.value
                embeded_message = embed_check.get_embed(embeded_message)

        if (not embed_check.error):
            #check if the entered colour matches a colour on the list
            found_colour = ColourList.get_name(colour)
            if (found_colour is not None):
                embeded_message.colour = found_colour.hex
            else:
                try:
                    embeded_message.colour = colour
                except:
                    embeded_message.colour = self.EMBED_DEFAULT_COLOUR.hex


            #error if the user does not want to display author name but accepts to
            #display author picture
            if (author_name is None and author_pic is not None):
                error_message = "author's image cannot be displayed without an author name"
                embeded_message = discord.Embed(title="ERROR",
                                                description="author's image cannot be displayed without an author name",
                                                color=0xFF0000)
                embed_check.error = True
                embeded_message.set_author(name = ctx.message.author.name,
                                           icon_url = ctx.message.author.avatar_url)

            elif (author_name is not None):
                embed_check = self.check_embed_limit(EmbedParts.AuthorName, author_name, return_value = author_name)
                author_name = embed_check.value
                embeded_message = embed_check.get_embed(embeded_message)

                #set the author's image
                if (not embed_check.error and author_pic is not None):
                    author_pic = StringTools.get_link(author_pic)
                    if (author_pic.lower() == self.EMBED_IMG_SELF):
                        embeded_message.set_author(name = author_name,
                                                   icon_url = ctx.message.author.avatar_url)

                    elif(author_pic.lower() == self.EMBED_IMG_BOT):
                        embeded_message.set_author(name = author_name,
                                                   icon_url = self.client.user.avatar_url)
                    else:
                        author_pic = StringTools.get_link(author_pic)
                        try:
                            embeded_message.set_author(name = author_name,
                                                   icon_url = author_pic)
                        except:
                            embed_check.error = True
                            embeded_message = self.embed_link_error(EmbedImages.AuthorImage, author_pic)

        #set the thumbnail
        if (not embed_check.error and thumbnail is not None):
            thumbnail = StringTools.get_link(thumbnail)
            if (thumbnail.lower() == self.EMBED_IMG_SELF):
                embeded_message.set_thumbnail(url = ctx.message.author.avatar_url)
            elif (thumbnail.lower() == self.EMBED_IMG_BOT):
                embeded_message.set_thumbnail(url = self.client.user.avatar_url)
            else:
                thumbnail = StringTools.get_link(thumbnail)
                try:
                    embeded_message.set_thumbnail(url = thumbnail)
                except:
                    embed_check.error = True
                    embeded_message = self.embed_link_error(EmbedImages.Thumbnail, thumbnail)

        #set the image
        if (not embed_check.error and image is not None):
            if (image.lower() == self.EMBED_IMG_SELF):
                embeded_message.set_image(url = ctx.message.author.avatar_url)
            elif (image.lower() == self.EMBED_IMG_BOT):
                embeded_message.set_image(url = self.client.user.avatar_url)
            else:
                image = StringTools.get_link(image)
                try:
                    embeded_message.set_image(url = image)
                except:
                    embed_check.error = True
                    embeded_message = self.embed_link_error(EmbedImages.Thumbnail, image)

        if (not embed_check.error):
            embed_check = self.check_embed_limit(EmbedParts.Total, embeded_message, return_value = embeded_message)
            embeded_message = embed_check.get_embed(embeded_message)
        return EmbededMessage(embeded_message, embed_check.error)


    # add_section(self, embeded_message, field_title, field_message, inline)
    #   adds a field to the embed
    def add_section(self, embeded_message: Union[discord.Embed, EmbededMessage], field_title: str, field_message: str,
                    inline: bool = False) -> EmbededMessage:
        file = None
        embed_check = None
        if (isinstance(embeded_message, EmbededMessage)):
            embed_check = EmbedCheck(embeded_message.error, None, None)
            file = embeded_message.file
            embeded_message = embeded_message.embed

        embed_check = self.check_embed_limit(EmbedParts.FieldTitle, field_title, return_value = field_title)
        field_title = embed_check.value
        embeded_message = embed_check.get_embed(embeded_message)

        if (not embed_check.error):
            embed_check = self.check_embed_limit(EmbedParts.FieldMessage, field_message, return_value = field_message)
            field_message = embed_check.value
            embeded_message = embed_check.get_embed(embeded_message)

        if (not embed_check.error):
            embed_check = self.check_embed_limit(EmbedParts.Fields, embeded_message.fields, embeded_message.add_field,
                                                 success_kwargs = {"name": field_title, "value": field_message, "inline": inline})
            embeded_message = embed_check.get_embed(embed_check.value)
        return EmbededMessage(embeded_message, embed_check.error, file = file)


    # multi_add_section(self, embeded_message, section_contents) Adds multiple
    #   sections to an embed
    def multi_add_section(self, embeded_message: Union[discord.Embed, EmbededMessage], section_contents: Dict[str, str]) -> EmbededMessage:
        section_len = len(section_contents)
        file = None
        error = False
        if (isinstance(embeded_message, EmbededMessage)):
            error = embeded_message.error
            file = embeded_message.file
            embeded_message = embeded_message.embed

        for title in section_contents:
            embeded_message = self.add_section(embeded_message, title, section_contents[title])

            if (embeded_message.error):
                break

        return embeded_message


    # add a footer to the embed
    def add_footer(self, ctx, embeded_message: Union[discord.Embed, EmbededMessage], text: str, footer_pic: Optional[str] = None) -> EmbededMessage:
        file = None
        embed_check = None
        if (isinstance(embeded_message, EmbededMessage)):
            embed_check = EmbedCheck(embeded_message.error, None, None)
            file = embeded_message.file
            embeded_message = embeded_message.embed

        embed_check = self.check_embed_limit(EmbedParts.Footer, text, return_value = text)
        embeded_message = embed_check.get_embed(embeded_message)

        #if the user does not want to set an image for the footer
        if (not embed_check.error and footer_pic is None):
            embeded_message.set_footer(text=text)

        #set the image for the footer
        elif (not embed_check.error):
            lowered_footer_pic = footer_pic.lower()
            if (lowered_footer_pic == self.EMBED_IMG_SELF):
                url = ctx.message.author.avatar_url
            elif (lowered_footer_pic == self.EMBED_IMG_BOT):
                url = self.client.user.avatar_url
            else:
                url = footer_pic

            embeded_message.set_footer(text=text, icon_url=url)

        return EmbededMessage(embeded_message, embed_check.error, file = file)


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
            image_link = None

        img_is_file = False
        if (isinstance(image_link, dict)):
            img_is_file = True

        return [img_is_file, image_link]


    # context_embed(ctx, description, title, colour, thumbnail, image, name) Embed template for the user context
    def context_embed(self, ctx: commands.Context, description: str, title: str, colour: Union[str, int],
                      thumbnail: Optional[str] = None, image: Optional[Union[str, Dict[pics.ImageCategory, int]]] = None,
                      name: Optional[str] = None) -> EmbededMessage:
        if (name is None):
            name = members.convert_name(ctx.author.id, ctx.author)
        img_is_file, image_link = self.retrieve_img(image)

        if (img_is_file):
            url = image_link["url"]
            embeded_message = self.embed_message(ctx, description, title, colour, name, thumbnail, self.EMBED_IMG_SELF, url)
            embeded_message.file = image_link["file"]
            return embeded_message
        else:
            embeded_message = self.embed_message(ctx, description, title, colour, name, thumbnail, self.EMBED_IMG_SELF, image_link)
            return embeded_message



    # bot_embed(ctx, description, title, colour, name_choice, image) Embed template for the bot
    # requires: -1 <= name_choice < len(self.names)
    def bot_embed(self, ctx: commands.Context, description: str, title: str, colour: Union[str, int],
                  name_choice: int, image: Optional[Union[str, Dict[pics.ImageCategory, int]]] = None) -> EmbededMessage:
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
            embeded_message = self.embed_message(ctx, description, title, colour, name, None, self.EMBED_IMG_BOT, url)
            embeded_message.file = image_link["file"]
            return embeded_message
        else:
            embeded_message = self.embed_message(ctx, description, title, colour, name, None, self.EMBED_IMG_BOT, image_link)
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
