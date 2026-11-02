from wzgram import filters, Client
from wzgram.types import InlineKeyboardButton, InlineKeyboardMarkup
from wzgram.enums import ChatType, ChatMemberStatus
from config import CONNECT_COMMAND, DISCONNECT_COMMAND, CONNECTIONS_COMMAND
from database.connections_mdb import add_connection, all_connections, if_active, make_active, make_inactive
from helpers.user_activity import record_user_activity
from helpers.error_handling import log_handler_errors
from helpers.logger import logger
from helpers.use_bot import user_can_use_bot
from database.auth_users import is_user_authorized

@Client.on_message((filters.private | filters.group) & filters.command(CONNECT_COMMAND))
@log_handler_errors("plugins/connections.py:addconnection")
async def addconnection(client, message):
    if not message.from_user:
        return
    userid = str(message.from_user.id)

    user_id = message.from_user.id
    if not await user_can_use_bot(user_id):
        await message.reply_text(
            "You are not authorized to use this bot."
        )
        return
    # Add user to database
    await record_user_activity(message)

    chat_type = message.chat.type

    group_ids = await all_connections(userid)

    
    # Determine group ID depending on chat type (private or group)
    if chat_type == ChatType.PRIVATE:
        try:
            # Try to extract group ID from the command
            _, group_id_str = message.text.split(" ", 1)
            group_id = str(group_id_str).strip()
        except ValueError:
            await message.reply_text(
                "<b>Enter the correct format!</b>\n\n"
                "<code>/connect groupid</code>\n\n"
                "<i>Get your Group ID by adding this bot to your group and use <code>/id</code></i>"
            )
            return
    elif chat_type in [ChatType.SUPERGROUP, ChatType.GROUP]:
        group_id = str(message.chat.id)  # Use group ID from the chat
    
    else:
        return
    try:
        group_id = str(int(group_id))
    except (ValueError, TypeError):
        await message.reply_text("Invalid group ID.")
        return

    try:
        st = await client.get_chat_member(int(group_id), int(userid))
    except Exception:
        logger.exception("Failed to verify connect permissions user_id=%s group_id=%s", userid, group_id)
        await message.reply_text("Cannot access this group. Check bot logs.")
        return
    if st.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
        if not await is_user_authorized(int(userid)):
            await message.reply_text("You should be an admin or owner in the given group!")
            return
    
    # Check if the bot is an admin in the group
    try:
        bot_status = await client.get_chat_member(int(group_id), "me")
        if bot_status.status != ChatMemberStatus.ADMINISTRATOR:
            await message.reply_text("Add me as an admin in the group")
            return
        
        # Get group title and add connection
        group_info = await client.get_chat(group_id)
        title = group_info.title
        if group_ids is not None and group_id in group_ids:
            if_active_var = await if_active(userid, group_id)
            if if_active_var:
                await message.reply_text("You're already connected to this chat!")
            else:
                if not await make_active(userid, group_id):
                    await message.reply_text("Could not activate that connection.")
                    return
                await message.reply_text(
                    f"Successfully connected to **{title}**\nNow manage your group from my PM!"
                )
        else:
            addcon = await add_connection(group_id, userid)
            
            if addcon:
                await message.reply_text(
                    f"Successfully connected to **{title}**\nNow manage your group from my PM!"
                )
                # Notify the user via private message if the chat is a group
                if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                    try:
                        await client.send_message(userid, f"Connected to **{title}**!")
                    except Exception:
                        logger.exception("Connection saved but PM notification failed user_id=%s group_id=%s",
                                         userid, group_id)
            else:
                
                await message.reply_text("You're already connected to this chat! Use connections command to make it active")
    
    except Exception:
        logger.exception("Connect request failed user_id=%s group_id=%s", userid, group_id)
        await message.reply_text(
            "Some error occurred! Try again later."
        )


@Client.on_message((filters.private | filters.group) & filters.command(DISCONNECT_COMMAND))
@log_handler_errors("plugins/connections.py:diconnectconnection")
async def diconnectconnection(client,message):
    if not message.from_user:
        return
    userid = message.from_user.id

    if not await user_can_use_bot(userid):
        await message.reply_text(
            "You are not authorized to use this bot."
        )
        return
    await record_user_activity(message)
    
    chat_type = message.chat.type
    group_ids = await all_connections(str(userid))
    if chat_type == ChatType.PRIVATE:
        try:
            _, group_id_str = message.text.split(" ", 1)
        except ValueError:
            await message.reply_text(
                "<b>Enter the correct format!</b>\n\n"
                f"<code>/{DISCONNECT_COMMAND} groupid</code>\n\n"
                "<i>Get your Group ID by adding this bot to your group and use <code>/id</code></i>\n\n"
                "<b>OR</b>\n\n"
                f"<code>send /{DISCONNECT_COMMAND}</code> as a message to the group"
            )
            return
        group_id = str(group_id_str)
        st = await client.get_chat_member(int(group_id), int(userid))
        if not ((st.status == ChatMemberStatus.ADMINISTRATOR) or (st.status == ChatMemberStatus.OWNER) or await is_user_authorized(int(userid))):
            return
        #delcon = await delete_connection(str(userid), str(group_id))
        if group_ids is not None and group_id in group_ids:
            if_active_var = await if_active(str(userid), str(group_id))
            if if_active_var:
                await make_inactive(str(userid))
                await message.reply_text("Successfully disconnected from this chat")
            else:
                await message.reply_text("This chat is already disconnected")

    elif (chat_type == ChatType.GROUP) or (chat_type == ChatType.SUPERGROUP):
        group_id = message.chat.id

        st = await client.get_chat_member(int(group_id), int(userid))
        if not ((st.status == ChatMemberStatus.ADMINISTRATOR) or (st.status == ChatMemberStatus.OWNER) or await is_user_authorized(int(userid))):
            return
        if group_ids is not None and str(group_id) in group_ids:
            if_active_var = await if_active(str(userid), str(group_id))
            if if_active_var:
                await make_inactive(str(userid))
                await message.reply_text("Successfully disconnected from this chat")
            else:
                await message.reply_text("This chat is already disconnected")


@Client.on_message(filters.private & filters.command(CONNECTIONS_COMMAND))
@log_handler_errors("plugins/connections.py:connections")
async def connections(client,message):
    if not message.from_user:
        return
    userid = message.from_user.id
    if not await user_can_use_bot(userid):
        await message.reply_text(
            "You are not authorized to use this bot."
        )
        return
    await record_user_activity(message)
    groupids = await all_connections(str(userid))

    if groupids is None or groupids == []:
        await message.reply_text(
            "There are no active connections!! Connect to some groups first."
        )
        return
    buttons = []
    for groupid in groupids:
        try:
            ttl = await client.get_chat(int(groupid))
            title = ttl.title
            active = await if_active(str(userid), str(groupid))
            if active:
                act = " - ACTIVE"
            else:
                act = ""
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{title}{act}", callback_data=f"groupcb:{groupid}"
                    )
                ]
            )
        except Exception:
            logger.exception("Could not load connection button user_id=%s group_id=%s", userid, groupid)
    if buttons:
        await message.reply_text(
            "Your connected group details ;\n\n",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        await message.reply_text("No accessible groups found in your connections.")
