import time
import shutil
from pyrogram.types import Message
from pyrogram import filters
from pyrogram import Client as pachax001
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType, ParseMode
import os
from config import OWNER_ID, BOT_START_TIME, SAVE_USER
from database.auth_users import authorize_user,load_authorized_users,is_user_authorized,unauthorize_user
from script import Script
from plugins.helpers import humanbytes
from database.filters_mdb import filter_stats
from database.users_mdb import find_user, add_or_update_user,get_total_users,get_recent_users
from helpers.broadcast import broadcast_to_users
from helpers.use_bot import user_can_use_bot
from helpers.broadcast import broadcast_to_users
from database.config_db import get_public_mode, set_public_mode
from helpers.logger import logger
import shlex
@pachax001.on_message(filters.command('id') & (filters.private | filters.group))
async def showid(client, message):
    userId = message.from_user.id
    if user_can_use_bot(userId):
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
            if SAVE_USER == "yes":
                try:
                    await add_or_update_user(
                        str(message.from_user.id),
                        str(message.from_user.username) or "None",
                        str(message.from_user.first_name + " " + (message.from_user.last_name or "")),
                        str(message.from_user.first_name),
                        str(message.from_user.dc_id)
                    )
                except:
                    pass
    else:
        await message.reply_text("You are not authorized to use this bot.")

@pachax001.on_message(filters.command('info') & (filters.private | filters.group))
async def showinfo(client, message):
    userId = message.from_user.id
    if user_can_use_bot(userId):
        try:
            cmd, id = message.text.split(" ", 1)
        except:
            id = False
            pass

        if id:
            if (len(id) == 10 or len(id) == 9):
                try:
                    checkid = int(id)
                except:
                    await message.reply_text("__Enter a valid USER ID__", quote=True)
                    return
            else:
                await message.reply_text("__Enter a valid USER ID__", quote=True)
                return           

            if SAVE_USER == "yes":
                name, username, dcid = await find_user(str(id))
            else:
                try:
                    user = await client.get_users(int(id))
                    name = str(user.first_name + (user.last_name or ""))
                    username = user.username
                    dcid = user.dc_id
                except:
                    name = False
                    pass

            if not name:
                await message.reply_text("__USER Details not found!!__")
                return
        else:
            if message.reply_to_message:
                name = str(message.reply_to_message.from_user.first_name\
                        + (message.reply_to_message.from_user.last_name or ""))
                id = message.reply_to_message.from_user.id
                username = message.reply_to_message.from_user.username
                dcid = message.reply_to_message.from_user.dc_id
            else:
                name = str(message.from_user.first_name\
                        + (message.from_user.last_name or ""))
                id = message.from_user.id
                username = message.from_user.username
                dcid = message.from_user.dc_id
        
        if not str(username) == "None":
            user_name = f"@{username}"
        else:
            user_name = "none"

        await message.reply_text(
            f"<b>Name</b> : {name}\n\n"
            f"<b>User ID</b> : <code>{id}</code>\n\n"
            f"<b>Username</b> : {user_name}\n\n"
            f"<b>Permanant USER link</b> : <a href='tg://user?id={id}'>Click here!</a>\n\n"
            f"<b>DC ID</b> : {dcid}\n\n",
            quote=True
        )
    else:
        await message.reply_text("You are not authorized to use this bot.")


@pachax001.on_message((filters.private | filters.group) & filters.command('status'))
async def bot_status(client,message):
    userId = message.from_user.id
    if (is_user_authorized(userId) or userId == OWNER_ID):
    # if (str(message.from_user.id)) not in Config.AUTH_USERS and (str(message.from_user.id)) != str(Config.OWNER_ID):
    #     return

        chats, filters = await filter_stats()

        if SAVE_USER == "yes":
            users = await get_total_users()
            recent_users = await get_recent_users()
            userstats = f"> __**{users} users have interacted with your bot!**__\n\n"
            userstats += f"> __**{recent_users} users have interacted with your bot in the last 7 days!**__\n\n"
        else:
            userstats = ""

        uptime = time.strftime("%Hh %Mm %Ss", time.gmtime(time.time() - BOT_START_TIME))

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
    else:
        await message.reply_text("You are not authorized to use this bot.")



@pachax001.on_message(filters.command('start') & filters.private)
async def start(client, message):

    if message.from_user.id == OWNER_ID:
        total_users = await get_total_users()
        text = (
            f"👋 Hello, Owner (ID: <code>{OWNER_ID}</code>).\n\n"
            f"🔓 <b>Bot Public Mode:</b> {'Enabled' if get_public_mode() else 'Disabled'}\n\n"
            f"👥 <b>Total Users:</b> {total_users}\n\n"
            "⚙️ Use the following commands to manage access:\n"
            "/authorize <user_id> - Grant access\n"
            "/unauthorize <user_id> - Revoke access\n\n"
            "📄 Use /help to see all available commands."
        )
        await message.reply_text(text, parse_mode=ParseMode.HTML) 
        return  
    await message.reply_text(
        text=Script.START_MSG.format(message.from_user.mention),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Command Help", callback_data="help_data"),
                    InlineKeyboardButton("OWNER", url="https://t.me/Tonbidmaster")

                ]
            #     [
            #         InlineKeyboardButton("Source Code", url="https://github.com/pachax001/Auto-Filter-Bot"),
                    
            # ]
            ]
        ),
        reply_to_message_id=message.id
    )
    if SAVE_USER == "yes":
        try:
            await add_or_update_user(
                str(message.from_user.id),
                str(message.from_user.username) or "None",
                str(message.from_user.first_name + " " + (message.from_user.last_name or "")),
                str(message.from_user.first_name),
                str(message.from_user.dc_id)
            )
        except:
            pass


@pachax001.on_message(filters.command('help') & filters.private)
async def help(client, message):
    if SAVE_USER == "yes":
        try:
            await add_or_update_user(
                str(message.from_user.id),
                str(message.from_user.username) or "None",
                str(message.from_user.first_name + " " + (message.from_user.last_name or "")),
                str(message.from_user.first_name),
                str(message.from_user.dc_id)
            )
        except:
            pass
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
                    InlineKeyboardButton("Owner", url="https://t.me/Tonbidmaster")
                ]
            ]
        ),
        reply_to_message_id=message.id
    )


@pachax001.on_message(filters.command('about') & filters.private)
async def about(client, message):
    if SAVE_USER == "yes":
        try:
            await add_or_update_user(
                str(message.from_user.id),
                str(message.from_user.username) or "None",
                str(message.from_user.first_name + " " + (message.from_user.last_name or "")),
                str(message.from_user.first_name),
                str(message.from_user.dc_id)
            )
        except:
            pass
    bot_details = await client.get_me()
    first_name = bot_details.first_name
    await message.reply_text(
        text=Script.ABOUT_MSG.format(first_name),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "OWNER", url="https://t.me/Tonbidmaster")
                ],
                [
                    InlineKeyboardButton("BACK", callback_data="help_data"),
                    InlineKeyboardButton("CLOSE", callback_data="close_data"),
                ]                
            ]
        ),
        reply_to_message_id=message.id
    )

@pachax001.on_message(filters.command('log') & filters.private & filters.user(OWNER_ID))
async def send_log(client, message):
    if os.path.exists("log.txt"):
        await message.reply_document(document="log.txt")
    else:
        await message.reply_text("Log file not found.")


@pachax001.on_message(filters.command('broadcast') & filters.private & filters.user(OWNER_ID))
async def manual_broadcast_command(client, message):
    #shlex is used to split the string into a list of arguments
    try:
        cmd, msg = message.text.split(" ", 1)
    except:
        await message.reply_text("Please provide a message.")
        return
    await broadcast_to_users(client, msg)
    

@pachax001.on_message(filters.command('auth') & filters.private & filters.user(OWNER_ID))
async def auth_user(client, message):
    try:
        cmd, user_id = message.text.split(" ", 1)
    except:
        await message.reply_text("Please provide a user ID.")
        return

    try:
        user_id = int(user_id)
        if user_id == OWNER_ID:
            await message.reply_text("You can't authorize yourself.")
        if is_user_authorized(user_id):
            await message.reply_text("User is already authorized.")
            return
    except:
        await message.reply_text("Invalid user ID.")
        return

    authorize_user(user_id)
    await message.reply_text(f"User {user_id} is now authorized to use the bot.")

@pachax001.on_message(filters.command('deauth') & filters.private & filters.user(OWNER_ID))
async def deauth_user(client, message):
    try:
        cmd, user_id = message.text.split(" ", 1)
    except:
        await message.reply_text("Please provide a user ID.")
        return

    try:
        user_id = int(user_id)
        if user_id == OWNER_ID:
            await message.reply_text("You can't deauthorize yourself.")
        if not is_user_authorized(user_id):
            await message.reply_text("User is not authorized.")
            return
    except:
        await message.reply_text("Invalid user ID.")
        return

    unauthorize_user(user_id)
    await message.reply_text(f"User {user_id} is no longer authorized to use the bot.")

@pachax001.on_message(filters.command('authusers') & filters.private & filters.user(OWNER_ID))
async def list_auth_users(client, message):
    users = await load_authorized_users()
    if not users:
        await message.reply_text("No authorized users.")
        return

    text = "Authorized users:\n"
    for user in users:
        text += f"- {user}\n"

    await message.reply_text(text)  

@pachax001.on_message(filters.command('public') & filters.private & filters.user(OWNER_ID))
async def toggle_public_mode(client, message):
    try:
        current = get_public_mode()
        set_public_mode(not current)
        await message.reply_text(f"Public mode turned {'off' if current else 'on'}.")
        try:
            # Broadcast the change to all users
            broadcast_messaage =(
                f"📢 Public mode has been turned {'off' if current else 'on'} by the bot owner."
                #show a message saying maintenance mode is on
                f"Bots will be down for a while for maintenance, please be patient."
                f"{'\n\nThis means only authorized users can use the bot.' if current else ''}"

            )
            await broadcast_to_users(client, broadcast_messaage)
        except Exception as e:
            logger.error(f"An error occurred while broadcasting: {e}")
    except Exception as e:
        await message.reply_text(f"An error occurred: {e}")
        logger.error(f"An error occurred: {e}")



