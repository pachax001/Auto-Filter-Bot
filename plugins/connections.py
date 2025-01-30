from pyrogram import filters, Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ChatType, ChatMemberStatus
from config import CONNECT_COMMAND, DISCONNECT_COMMAND, CONNECTIONS_COMMAND, SAVE_USER
from database.connections_mdb import add_connection, all_connections, if_active, delete_connection,make_active,make_inactive
from database.filters_mdb import del_all_filters_connection
from database.users_mdb import add_or_update_user
from helpers.use_bot import user_can_use_bot
from database.auth_users import is_user_authorized

@Client.on_message((filters.private | filters.group) & filters.command(CONNECT_COMMAND))
async def addconnection(client, message):
    userid = str(message.from_user.id)  # Ensure userid is a string
    print(f"User ID: {userid}")
    user_id = message.from_user.id
    if not user_can_use_bot(user_id):
        await message.reply_text(
            "You are not authorized to use this bot.",
            quote=True
        )
        return
    # Add user to database
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

    chat_type = message.chat.type
    print(f"Chat Type: {chat_type}")
    group_ids = await all_connections(userid)
    print(f"Group IDs: {group_ids}")
    
    # Determine group ID depending on chat type (private or group)
    if chat_type == ChatType.PRIVATE:
        try:
            # Try to extract group ID from the command
            _, group_id_str = message.text.split(" ", 1)
            group_id = str(group_id_str)
        except ValueError:
            await message.reply_text(
                "<b>Enter the correct format!</b>\n\n"
                "<code>/connect groupid</code>\n\n"
                "<i>Get your Group ID by adding this bot to your group and use <code>/id</code></i>",
                quote=True
            )
            return
    elif chat_type in [ChatType.SUPERGROUP, ChatType.GROUP]:
        group_id = str(message.chat.id)  # Use group ID from the chat
    
    # Check if the user is an admin or in authorized users
    try:
        st = await client.get_chat_member(group_id, userid)
        print(f"User status: {st}")

        if st.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER] and not is_user_authorized(int(userid)):
            await message.reply_text("You should be an admin or owner in the given group!", quote=True)
            return
    except Exception as e:
        print(f"Error fetching chat member: {e}")
        await message.reply_text(
            "Invalid Group ID!\n\nIf correct, make sure I'm present in your group!!",
            quote=True
        )
        return
    
    # Check if the bot is an admin in the group
    try:
        bot_status = await client.get_chat_member(group_id, "me")
        if bot_status.status != ChatMemberStatus.ADMINISTRATOR:
            await message.reply_text("Add me as an admin in the group", quote=True)
            return
        
        # Get group title and add connection
        group_info = await client.get_chat(group_id)
        title = group_info.title
        if group_ids is not None and group_id in group_ids:
            if_active_var = await if_active(userid, group_id)
            if if_active_var:
                await message.reply_text("You're already connected to this chat!", quote=True)
            else:
                await make_inactive(userid)
                await make_active(userid, group_id)
                await message.reply_text(
                    f"Successfully connected to **{title}**\nNow manage your group from my PM!",
                    quote=True
                )
        else:
            addcon = await add_connection(group_id, userid)
            
            if addcon:
                await message.reply_text(
                    f"Successfully connected to **{title}**\nNow manage your group from my PM!",
                    quote=True
                )
                # Notify the user via private message if the chat is a group
                if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                    await client.send_message(
                        userid,
                        f"Connected to **{title}**!"
                    )
            else:
                
                await message.reply_text("You're already connected to this chat! Use connections command to make it active", quote=True)
    
    except Exception as e:
        print(f"Error connecting to the group: {e}")
        await message.reply_text(
            "Some error occurred! Try again later.",
            quote=True
        )


@Client.on_message((filters.private | filters.group) & filters.command(DISCONNECT_COMMAND))
async def diconnectconnection(client,message):
    userid = message.from_user.id
    print(userid)
    if not user_can_use_bot(userid):
        await message.reply_text(
            "You are not authorized to use this bot.",
            quote=True
        )
        return
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
                f"<code>send /{DISCONNECT_COMMAND}</code> as a message to the group",
                quote=True
            )
            return
        group_id = str(group_id_str)
        st = await client.get_chat_member(group_id, userid)
        if not ((st.status == ChatMemberStatus.ADMINISTRATOR) or (st.status == ChatMemberStatus.OWNER) or is_user_authorized(int(userid))):
            return
        #delcon = await delete_connection(str(userid), str(group_id))
        if group_ids is not None and group_id in group_ids:
            if_active_var = await if_active(str(userid), str(group_id))
            if if_active_var:
                await make_inactive(str(userid))
                await message.reply_text("Successfully disconnected from this chat", quote=True)
            else:
                await message.reply_text("This chat is already disconnected", quote=True)

    elif (chat_type == ChatType.GROUP) or (chat_type == ChatType.SUPERGROUP):
        group_id = message.chat.id

        st = await client.get_chat_member(group_id, userid)
        if not ((st.status == ChatMemberStatus.ADMINISTRATOR) or (st.status == ChatMemberStatus.OWNER) or is_user_authorized(int(userid))):
            return
        if group_ids is not None and str(group_id) in group_ids:
            if_active_var = await if_active(str(userid), str(group_id))
            if if_active_var:
                await make_inactive(str(userid))
                await message.reply_text("Successfully disconnected from this chat", quote=True)
            else:
                await message.reply_text("This chat is already disconnected", quote=True)


@Client.on_message(filters.private & filters.command(CONNECTIONS_COMMAND))
async def connections(client,message):
    userid = message.from_user.id
    print(userid)
    if not user_can_use_bot(userid):
        await message.reply_text(
            "You are not authorized to use this bot.",
            quote=True
        )
        return
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
    groupids = await all_connections(str(userid))
    print(groupids)
    if groupids is None or groupids == []:
        await message.reply_text(
            "There are no active connections!! Connect to some groups first.",
            quote=True
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
                        text=f"{title}{act}", callback_data=f"groupcb:{groupid}:{title}:{act}"
                    )
                ]
            )
        except:
            pass
    if buttons:
        await message.reply_text(
            "Your connected group details ;\n\n",
            reply_markup=InlineKeyboardMarkup(buttons),
            quote=True
        )