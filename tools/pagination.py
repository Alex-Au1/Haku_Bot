import discord, asyncio
from discord.ext import commands
from tools.embed import EmbededMessage
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType
from tools.abs_func import AbsFunc
from typing import Dict, Callable, Any, Optional, List

PAGES_PER_PAGINATION = 5
MIDDLE_PAGE_INDEX = int(PAGES_PER_PAGINATION / 2)
FIRST_PAGE = 1
PAGE_NAV_LABELS = ["First Page", "Previous", "Next", "Last Page"]
PAGE_REACT_TIME = 60
CONTINUOUS_LOOP_SLEEP_TIME = 5


# ButtonedMsg: A class for handling reactions for message with components
class ButtonedMsg():
    def __init__(self, message: discord.Message, page: int, max_page: int):
        self.message = message
        self.page = page
        self.max_page = max_page


# Pagination: Class that deals with paginating embeds
class Pagination():
    # get_total_pages(cls, items_per_page, total_items) Determines the total
    #   number of pages to display all items
    # requires: items_per_page > 0
    #           total_items >= 0
    @classmethod
    def get_total_pages(cls, items_per_page: int, total_items: int, none_option: bool = True) -> int:
        quot, rem = divmod(total_items, items_per_page)

        if (rem):
            total_pages = (quot + 1)
        else:
            total_pages = quot

        if (none_option and not total_pages):
            total_pages = 1
        return total_pages


    # get_indices(cls, page, items_per_page, item_len) Get the start and end
    #   indices for each page
    # requires: items_per_page > 0
    #           total_items >= 0
    #           item_len >= 0
    # note: 'item_len' is the length of the list of objects to be partitioned into
    #           different pages in the embed
    @classmethod
    def get_indices(cls, page: int, items_per_page: int, item_len: int) -> Dict[str, int]:
        start_index = (page - 1) * items_per_page
        end_index = page * items_per_page

        # adjust the start and end index
        if (end_index > item_len):
            end_index = item_len

        if (start_index >= end_index):
            start_index = end_index - items_per_page

            if (start_index < 0):
                start_index = 0

        return {"start_index": start_index, "end_index": end_index}


    @classmethod
    # get_current_page(index, items_per_page) Get the current page for the pagination
    def get_current_page(cls, index, items_per_page):
        page, extra_items = divmod(index, items_per_page)
        return page + 1


    # make_page_buttons(current_page, max_page) Generates the page buttons
    #   for a paginated message
    # requires: max_page > 0
    #           current_page > 0
    @classmethod
    def make_page_buttons(cls, current_page: int, max_page: int) -> List[List[Button]]:
        page_num_buttons = [Button(style=ButtonStyle.grey, label="0"),
                            Button(style=ButtonStyle.grey, label="0"),
                            Button(style=ButtonStyle.grey, label="0"),
                            Button(style=ButtonStyle.grey, label="0"),
                            Button(style=ButtonStyle.grey, label="0")]


        if (max_page < PAGES_PER_PAGINATION):
            for i in range(PAGES_PER_PAGINATION - max_page):
                page_num_buttons.pop(0)

        first_pg_diff = current_page - FIRST_PAGE
        last_pg_diff = max_page - current_page
        current_index = 0
        page_button_len = len(page_num_buttons)

        if (first_pg_diff <= 1):
            current_index = first_pg_diff
        elif (last_pg_diff <= 1):
            current_index = page_button_len - 1 - last_pg_diff
        else:
            current_index = MIDDLE_PAGE_INDEX

        page_num_buttons[current_index].label = f"{current_page}"
        page_num_buttons[current_index].style = ButtonStyle.blue

        for i in range(current_index + 1, page_button_len):
            page_num_buttons[i].label = f"{current_page + (i - current_index)}"

        for i in range(0, current_index):
            page_num_buttons[i].label = f"{current_page - (current_index - i)}"

        components = [page_num_buttons,
                      [Button(style=ButtonStyle.grey, label= PAGE_NAV_LABELS[0], emoji="\U000023EA"),
                       Button(style=ButtonStyle.grey, label= PAGE_NAV_LABELS[1], emoji = "\U000025C0"),
                       Button(style=ButtonStyle.grey, label= PAGE_NAV_LABELS[2], emoji = "\U000025B6"),
                       Button(style=ButtonStyle.grey, label= PAGE_NAV_LABELS[3], emoji = "\U000023E9")]
                     ]

        return components



    # page_react(client, current_page, max_page, generate_pg, **kwargs) Turns to a
    #   new embed page based on the users button interactions
    # requires: max_page > 0
    #           current_page > 0
    #           items_per_page >= 0
    # effects: edits messages
    #           'pages' is not empty and 'pages' only has 1 element where pages[0] > 0
    # note: when 'update_max_page' is True, the page buttons on the embed will also
    #           be updated based off the changing size of the list from 'item_lst'
    @classmethod
    async def page_react(cls, client: discord.Client, message: discord.Message, current_page: int,
                         max_page: int, generate_pg: AbsFunc, pages: Optional[List[int]] = None,
                         update_max_page: bool = False, items_per_page: int = 0, item_lst: Optional[List[Any]] = None,
                         check_func: Optional[AbsFunc] = None, update_items = False, after_react = False) -> int:
        if (check_func is None):
            check_func = AbsFunc(lambda: True)
            limit = PAGE_REACT_TIME
            after_react = False
        else:
            limit = None

        while (check_func.run()):
            #updates the current and max page
            if (update_max_page):
                current_page = pages[0]
                new_max_page = cls.get_total_pages(items_per_page, len(item_lst))

                if (new_max_page != max_page):
                    max_page = new_max_page
                    embeded_message = await generate_pg.async_run(pre_args = [current_page, max_page])
                    new_buttons = cls.make_page_buttons(current_page, max_page)
                    await message.edit(embed = embeded_message.embed, components = new_buttons)
                elif (update_items):
                    embeded_message = await generate_pg.async_run(pre_args = [current_page, max_page])
                    await message.edit(embed = embeded_message.embed)

            try:
                if (not update_items):
                    interaction = await client.wait_for("button_click", timeout = limit, check = lambda i: (i.component and i.message.id == message.id))
                else:
                    finished_task, unfinished_tasks = await asyncio.wait([client.wait_for("button_click", timeout = limit, check = lambda i: (i.component and i.message.id == message.id)),
                                                                          asyncio.sleep(CONTINUOUS_LOOP_SLEEP_TIME)], return_when=asyncio.FIRST_COMPLETED)

                    for t in finished_task:
                        interaction = t.result()

                    for t in unfinished_tasks:
                        t.cancel()

            except:
                break


            if (interaction is not None):
                await interaction.respond(type=InteractionType.DeferredUpdateMessage)
                button_name = interaction.component.label
            else:
                continue

            # updates the current and max page
            if (update_max_page):
                current_page = pages[0]
                max_page = cls.get_total_pages(items_per_page, len(item_lst))

            if (button_name == PAGE_NAV_LABELS[0]):
                current_page = FIRST_PAGE
            elif (button_name == PAGE_NAV_LABELS[1] and (current_page > FIRST_PAGE)):
                current_page = current_page - 1
            elif (button_name == PAGE_NAV_LABELS[2] and (current_page < max_page)):
                current_page = current_page + 1
            elif (button_name == PAGE_NAV_LABELS[3]):
                current_page = max_page
            elif (button_name not in PAGE_NAV_LABELS):
                current_page = int(button_name)

            if (update_max_page):
                pages[0] = current_page

            new_buttons = cls.make_page_buttons(current_page, max_page)

            embeded_message = await generate_pg.async_run(pre_args = [current_page, max_page])

            try:
                await message.edit(embed = embeded_message.embed, components = new_buttons)
            except:
                break

        # react to page turns a final time once the wait condition has been finished
        if (after_react):
            current_page = await cls.page_react(client, message, current_page, max_page, generate_pg)

        return current_page


    # multi_page_react(client, msg_lst, generate_pg, kwargs) Reacts to changing
    #   pages for multiple messages
    # effects: edits messages
    @classmethod
    async def multi_page_react(cls, client: discord.Client, msg_lst: List[ButtonedMsg], generate_pg: AbsFunc):
        await asyncio.gather(*(cls.page_react(client, m.message, m.page, m.max_page, generate_pg) for m in msg_lst))


    # paginated_send(ctx, embeded_message, paginated_components, current_page, max_page, generate_pg, generate_pg_kwargs)
    #   sends an embed with components and reacts to its different button interactions
    # requires: current_page >= 1
    #           max_page >= 1
    # effects: edits messages
    #          'pages' is not empty and 'pages' only has 1 element where pages[0] > 0
    @classmethod
    async def paginated_send(cls, ctx: commands.Context, client: discord.Client, embeded_message: EmbededMessage, paginated_components: List[List[Button]],
                             current_page: int, max_page: int, generate_pg: AbsFunc, pages: Optional[List[int]] = None,
                             update_max_page: bool = False, items_per_page: int = 0, item_lst: Optional[List[Any]] = None,
                             check_func: Optional[AbsFunc] = None, update_items: bool = False) -> discord.Message:
        if (not embeded_message.error):
            sent_message = await ctx.send(embed = embeded_message.embed, file = embeded_message.file, components = paginated_components)
            await cls.page_react(client, sent_message, current_page, max_page, generate_pg, pages = pages,
                                 update_max_page = update_max_page, items_per_page = items_per_page, item_lst = item_lst, check_func = check_func, update_items = update_items)
        else:
            sent_message = await ctx.send(embed = embeded_message.embed, file = embeded_message.file)

        return sent_message

