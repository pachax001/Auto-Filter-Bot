import time
import shutil

from pyrogram import filters
from pyrogram import Client as pachax001
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType

from config import Config

from script import Script
from plugins.helpers import humanbytes
from database.filters_mdb import filter_stats
from database.users_mdb import add_user, find_user, all_users
OWNER_ID = int(Config.OWNER_ID)
AUTH_USERS = Config.AUTH_USERS
  
@pachax001.on_message(filters.command('id') & filters.user([OWNER_ID] + list(AUTH_USERS)))
async def showid(client, message):
    chat_type = message.chat.type

    if chat_type == ChatType.PRIVATE:
        user_id = message.chat.id
        await message.reply_text(
            f"Your ID : `{user_id}`",
            quote=True
        )
    else:  # This handles both "group" and "supergroup"
        user_id = message.from_user.id
        chat_id = message.chat.id
        reply_id = ""

        if message.reply_to_message and message.reply_to_message.from_user:
            reply_id = f"Replied User ID : `{message.reply_to_message.from_user.id}`"

        await message.reply_text(
            f"Your ID : `{user_id}`\nThis Group ID : `{chat_id}`\n\n{reply_id}",
            quote=True
        )


# @pachax001.on_message(filters.command('info') & (filters.user(OWNER_ID)))
# async def showinfo(client, message):
#     try:
#         cmd, id = message.text.split(" ", 1)
#     except:
#         id = False
#         pass

#     if id:
#         if (len(id) == 10 or len(id) == 9):
#             try:
#                 checkid = int(id)
#             except:
#                 await message.reply_text("__Enter a valid USER ID__", quote=True)
#                 return
#         else:
#             await message.reply_text("__Enter a valid USER ID__", quote=True)
#             return           

#         if Config.SAVE_USER == "yes":
#             name, username, dcid = await find_user(str(id))
#         else:
#             try:
#                 user = await client.get_users(int(id))
#                 name = str(user.first_name + (user.last_name or ""))
#                 username = user.username
#                 dcid = user.dc_id
#             except:
#                 name = False
#                 pass

#         if not name:
#             await message.reply_text("__USER Details not found!!__")
#             return
#     else:
#         if message.reply_to_message:
#             name = str(message.reply_to_message.from_user.first_name\
#                     + (message.reply_to_message.from_user.last_name or ""))
#             id = message.reply_to_message.from_user.id
#             username = message.reply_to_message.from_user.username
#             dcid = message.reply_to_message.from_user.dc_id
#         else:
#             name = str(message.from_user.first_name\
#                     + (message.from_user.last_name or ""))
#             id = message.from_user.id
#             username = message.from_user.username
#             dcid = message.from_user.dc_id
    
#     if not str(username) == "None":
#         user_name = f"@{username}"
#     else:
#         user_name = "none"

#     await message.reply_text(
#         f"<b>Name</b> : {name}\n\n"
#         f"<b>User ID</b> : <code>{id}</code>\n\n"
#         f"<b>Username</b> : {user_name}\n\n"
#         f"<b>Permanant USER link</b> : <a href='tg://user?id={id}'>Click here!</a>\n\n"
#         f"<b>DC ID</b> : {dcid}\n\n",
#         quote=True
#     )


@pachax001.on_message((filters.private & filters.user(OWNER_ID)) & filters.command('status'))
async def bot_status(client,message):
    if (str(message.from_user.id)) not in Config.AUTH_USERS and (str(message.from_user.id)) != str(Config.OWNER_ID):
        return

    chats, filters = await filter_stats()

    if Config.SAVE_USER == "yes":
        users = await all_users()
        userstats = f"> __**{users} users have interacted with your bot!**__\n\n"
    else:
        userstats = ""

    uptime = time.strftime("%Hh %Mm %Ss", time.gmtime(time.time() - Config.BOT_START_TIME))

    try:
        t, u, f = shutil.disk_usage(".")
        total = humanbytes(t)
        used = humanbytes(u)
        free = humanbytes(f)

        disk = "\n**Disk Details**\n\n" \
            f"> USED  :  {used} / {total}\n" \
            f"> FREE  :  {free}\n\n"
    except:
        disk = ""

    await message.reply_text(
        "**Current status of your bot!**\n\n"
        f"> __**{filters}** filters across **{chats}** chats__\n\n"
        f"{userstats}"
        f"> __BOT Uptime__ : **{uptime}**\n\n"
        f"{disk}",
        quote=True
    )


@pachax001.on_message(filters.command('start') & filters.private)
async def start(client, message):
    await message.reply_text(
        text=Script.START_MSG.format(message.from_user.mention),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("OWNER", url="https://t.me/gunaya001")

                ],
                [
                    InlineKeyboardButton("Source Code", url="https://github.com/pachax001"),
                    
            ]
            ]
        ),
        reply_to_message_id=message.id
    )
    # if Config.SAVE_USER == "yes":
    #     try:
    #         await add_user(
    #             str(message.from_user.id),
    #             str(message.from_user.username),
    #             str(message.from_user.first_name + " " + (message.from_user.last_name or "")),
    #             str(message.from_user.dc_id)
    #         )
    #     except:
    #         pass


@pachax001.on_message(filters.command('help') & filters.private & filters.user([OWNER_ID] + list(AUTH_USERS)))
async def help(client, message):
    await message.reply_text(
        text=Script.HELP_MSG,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Filters", callback_data="help_filters"),
                    InlineKeyboardButton("Connection", callback_data="help_connection")
                ],
                [
                    InlineKeyboardButton("Others", callback_data="help_other"),
                    InlineKeyboardButton("Owner", url="https://t.me/gunaya001")
                ]
            ]
        ),
        reply_to_message_id=message.id
    )


@pachax001.on_message(filters.command('about') & filters.private & filters.user([OWNER_ID] + list(AUTH_USERS)))
async def about(client, message):
    bot_details = await client.get_me()
    first_name = bot_details.first_name
    await message.reply_text(
        text=Script.ABOUT_MSG.format(first_name),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "SOURCE CODE", url="https://github.com/pachax001")
                ],
                [
                    InlineKeyboardButton("BACK", callback_data="help_data"),
                    InlineKeyboardButton("CLOSE", callback_data="close_data"),
                ]                
            ]
        ),
        reply_to_message_id=message.id
    )
