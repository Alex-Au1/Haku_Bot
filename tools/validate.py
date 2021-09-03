import discord, validators, enum
from discord.ext import commands
import tools.error as Error
from tools.string import StringTools
import tools.search_yt as YtSearchTools
from typing import Any, Optional, Union, List


class DataTypes(enum.Enum):
    Str = "str"
    Int = "int"
    Nat = "nat"
    Bool = "bool"
    List = "list"
    Dict = "dict"


class Validate():
    def __init__(self, client: discord.Client):
        self.client = client

    # check_integer(ctx, param) Checks if 'param' is an integer
    async def check_integer(self, ctx: commands.Context, param: Any, param_name: str,
                            verbose: bool = True) -> Optional[int]:
        try:
            param = int(param)
        except:
            if (verbose):
                embeded_message = Error.display_error(self.client, 6, parameter = f"{param_name}",
                                                      type_article = "an", correct_type = "integer")
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
            return None
        else:
            return param


    # check_natural(self, ctx, param, param_name) Checks if 'param' is an
    #   integer greater than or equal to 0
    async def check_natural(self, ctx: commands.Context, param: Any, param_name: str, verbose: bool = True,
                            check_equal: bool = True) -> Optional[int]:
        param = await self.check_integer(ctx, param, param_name, verbose = verbose)

        if (param is not None):
            if ((check_equal and param >= 0) or (not check_equal and param > 0)):
                return param
            elif (verbose):
                if (check_equal):
                    embeded_message = Error.display_error(self.client, 7, parameter = param_name,
                                                          type_article = "an", correct_type = "integer", value = "0")
                else:
                    embeded_message = Error.display_error(self.client, 11, parameter = param_name,
                                                          type_article = "an", correct_type = "integer", value = "0")
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
                return None

        return param


    # check_float(ctx, param) Checks if 'param' is a floating point
    async def check_float(self, ctx: commands.Context, param: Any, param_name: str,
                          verbose: bool = True) -> Optional[float]:
        try:
            param = float(param)
        except:
            if (verbose):
                embeded_message = Error.display_error(self.client, 6, parameter = f"{param_name}",
                                                      type_article = "a", correct_type = "decimal")
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
            return None
        else:
            return param


    # check_natural(self, ctx, param, param_name) Checks if 'param' is an
    #   in between 'left' and 'right'
    # requires: 'left' and 'right' must be the same type
    async def check_inbetween(self, ctx: commands.Context, param: Any, param_name: Union[float, str], left: Union[float, str],
                              right: Union[float, str], verbose = True, check_equal = True) -> bool:
        if (check_equal):
            scope = "inclusively"
            in_between = (param >= left and param <=  right)
        else:
            scope = "exclusively"
            in_between = (param > left and param <  right)

        if (not in_between):
            if (verbose):
                embeded_message = Error.display_error(self.client, 19, parameter = param_name, type_article = "an",
                                                      correct_type = "integer", scope = scope, left = str(left), right = str(right))
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

        return in_between


    # check_url(self, url) Checks if 'url' is valid
    def check_url(self, url: str) -> bool:
        result = bool(validators.url(url))
        return result


    # validate_inbetween(ctx, param, param_name, left, right, error, verbose, check_equal) Determines
    #   if 'param' is in between 'left' and 'right'
    # requires: 'left' and 'right' must be the same type
    async def validate_inbetween(self, ctx: commands.Context, param: Any, param_name: str,
                                 left: Union[str, float], right: Union[str, float], error: bool,
                                 verbose: bool = True, check_equal: bool = True) -> bool:
        if (not error):
            error = not (await self.check_inbetween(ctx, param, param_name, left, right, verbose, check_equal))

        return error


    # validate_yt_channel_url(ctx, err0=or, var, var_name, allow_optional) Determines if 'var'
    #   is a valid link to a youtube channel
    async def validate_yt_channel_url(self, ctx: commands.Context, error: bool, var: str,
                                      var_name: str, allow_optional: bool = False) -> List[Union[bool, Optional[str]]]:
        var = StringTools.convert_none(var)
        var = StringTools.get_link(var)
        if (var is not None or (not allow_optional and var is None)):
            if (not error and not YtSearchTools.valid_yt_channel_link(var)):
                error = True
                embeded_message = Error.display_error(self.client, 6, parameter = f"{var_name}",
                                                      type_article = "a", correct_type = "link to a youtube channel")
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

        return [error, var]


    # validate_nat(self, ctx, client, error, var, var_name) Determines if
    #   'var' is a natural number and displays an error if it is not
    async def validate_natural(self, ctx: commands.Context, error: bool, var: Any,
                               var_name: str, allow_optional: bool = False,
                               check_equal: bool = False) -> List[Union[bool, Optional[int]]]:
        var = StringTools.convert_none(var)
        if (var is not None or (not allow_optional and var is None)):
            if (not error):
                var = await self.check_natural(ctx, var, var_name, verbose = True, check_equal = check_equal)

                if (var is None):
                    error = True

        return [error, var]


    # validate_float(self, ctx, client, error, var, var_name) Determines if
    #   'var' is a floating point and displays an error if it is not
    async def validate_float(self, ctx: commands.Context, error: bool, var: Any,
                             var_name: str, allow_optional: bool = False) -> List[Union[bool, Optional[float]]]:
        var = StringTools.convert_none(var)
        if (var is not None or (not allow_optional and var is None)):
            if (not error):
                var = await self.check_float(ctx, var, var_name, verbose = True)

                if (var is None):
                    error = True

        return [error, var]


    # validate_nat(self, ctx, client, error, var, var_name) Determines if
    #   'var' is a natural number and displays an error if it is not
    async def validate_page(self, ctx: commands.Context, error: bool, page: int,
                            max_page: int, var_name: str, allow_optional: bool = False) -> List[Union[bool, int]]:
        error, page = await self.validate_natural(ctx, error, page, var_name, allow_optional = allow_optional)
        if (page is not None or (not allow_optional and page is None)):
            if (page > max_page and max_page):
                if (not error):
                    embeded_message = Error.display_error(self.client, 8, type_article = "an",
                                                          correct_type = "integer", value = f"{max_page}", parameter = "page")
                    await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

                error = True

        return [error, page]


    # validate_bool(self, ctx, client, error, var, var_name) Determines if
    #   'var' is a bool and displays an error if it is not
    async def validate_bool(self, ctx: commands.Context, error: bool, var: Any, var_name: str,
                            allow_optional: bool = False) -> List[Union[bool, Optional[bool]]]:
        var = StringTools.convert_bool(var)
        if (var is not None or (not allow_optional and var is None)):
            if (not error):
                embeded_message = Error.display_error(self.client, 6, type_article= "a",
                                                      correct_type = "boolean", parameter = var_name)
                await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
            error = True

        return [error, var]


    # validate_bool(self, ctx, client, error, var, var_name) Determines if
    #   'var' is an image url and displays an error if it is not
    async def validate_image(self, ctx: commands.Context, error: bool, var: Any,
                             var_name: str) -> List[Union[bool, Optional[str]]]:
        var = StringTools.convert_none(var)

        if (var is not None):
            var = StringTools.get_link(var)
            valid_image = self.check_url(var)

            if (not valid_image):
                if (not error):
                    embeded_message = Error.display_error(self.client, 14, type_article= "an",
                                                          correct_type = "image", parameter = var_name)
                    await ctx.send(embed = embeded_message.embed, file = embeded_message.file)
                error = True

        return [error, var]
