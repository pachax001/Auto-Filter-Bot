from config import Config

from pyrogram import filters, Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ChatType, ChatMemberStatus

from database.connections_mdb import add_connection, all_connections, if_active, delete_connection

@Client.on_message((filters.private | filters.group) & filters.command(Config.CONNECT_COMMAND))
async def addconnection(client, message):
    userid = str(message.from_user.id)  # Ensure userid is a string
    print(f"User ID: {userid}")
    
    chat_type = message.chat.type
    print(f"Chat Type: {chat_type}")
    
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

        if st.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER] and int(userid) not in Config.AUTH_USERS:
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
            await message.reply_text("You're already connected to this chat!", quote=True)
    
    except Exception as e:
        print(f"Error connecting to the group: {e}")
        await message.reply_text(
            "Some error occurred! Try again later.",
            quote=True
        )


@Client.on_message((filters.private | filters.group) & filters.command(Config.DISCONNECT_COMMAND))
async def deleteconnection(client,message):
    userid = message.from_user.id
    chat_type = message.chat.type

    if chat_type == ChatType.PRIVATE:
        await message.reply_text("Run /connections to view or disconnect from groups!", quote=True)

    elif (chat_type == ChatType.GROUP) or (chat_type == ChatType.SUPERGROUP):
        group_id = message.chat.id

        st = await client.get_chat_member(group_id, userid)
        if not ((st.status == ChatMemberStatus.ADMINISTRATOR) or (st.status == ChatMemberStatus.OWNER) or (str(userid) in Config.AUTH_USERS)):
            return

        delcon = await delete_connection(str(userid), str(group_id))
        if delcon:
            await message.reply_text("Successfully disconnected from this chat", quote=True)
        else:
            await message.reply_text("This chat isn't connected to me!\nDo /connect to connect.", quote=True)


@Client.on_message(filters.private & filters.command(["connections"]))
async def connections(client,message):
    userid = message.from_user.id

    groupids = await all_connections(str(userid))
    if groupids is None:
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