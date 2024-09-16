import ast

from pyrogram import Client as pachax001
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType, ChatMemberStatus


from config import Config

from script import Script
from database.filters_mdb import del_all, find_filter

from database.connections_mdb import(
    all_connections,
    active_connection,
    if_active,
    delete_connection,
    make_active,
    make_inactive
)


@pachax001.on_callback_query()
async def cb_handler(client, query):

    if query.data == "start_data":
        await query.answer()
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Command Help", callback_data="help_data")
                ]
            ]
        )

        await query.message.edit_text(
            Script.START_MSG.format(query.from_user.mention),
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        return

    elif query.data == "help_data":
        await query.answer()
        keyboard=InlineKeyboardMarkup(
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
        )

        await query.message.edit_text(
            Script.HELP_MSG,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        return

    elif query.data == "about_data":
        await query.answer()
        keyboard = InlineKeyboardMarkup(
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
        )

        await query.message.edit_text(
            Script.ABOUT_MSG,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        return

    elif query.data == "close_data":
        await query.message.delete()
        

    elif query.data == "delallconfirm":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == ChatType.PRIVATE:
            grpid  = await active_connection(str(userid))
            if grpid is not None:
                grp_id = grpid
                try:
                    chat = await client.get_chat(grpid)
                    title = chat.title
                except:
                    await query.message.edit_text("Make sure I'm present in your group!!", quote=True)
                    return
            else:
                await query.message.edit_text(
                    "I'm not connected to any groups!\nCheck /connections or connect to any groups",
                    quote=True
                )
                return

        elif (chat_type == ChatType.GROUP) or (chat_type == ChatType.SUPERGROUP):
            grp_id = query.message.chat.id
            title = query.message.chat.title

        else:
            return

        st = await client.get_chat_member(grp_id, userid)
        if (st.status == ChatMemberStatus.OWNER) or (str(userid) in Config.AUTH_USERS):    
            await del_all(query.message, grp_id, title)
        else:
            await query.answer("You need to be Group Owner or an Auth User to do that!",show_alert=True)
    
    elif query.data == "delallcancel":
        userid = query.from_user.id
        chat_type = query.message.chat.type
        
        if chat_type == ChatType.PRIVATE:
            await query.message.reply_to_message.delete()
            await query.message.delete()

        elif (chat_type == ChatType.GROUP) or (chat_type == ChatType.SUPERGROUP):
            grp_id = query.message.chat.id
            st = await client.get_chat_member(grp_id, userid)
            if (st.status == ChatMemberStatus.OWNER) or (str(userid) in Config.AUTH_USERS):
                await query.message.delete()
                try:
                    await query.message.reply_to_message.delete()
                except:
                    pass
            else:
                await query.answer("Thats not for you!!",show_alert=True)


    elif "groupcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]
        title = query.data.split(":")[2]
        act = query.data.split(":")[3]
        user_id = query.from_user.id

        if act == "":
            stat = "CONNECT"
            cb = "connectcb"
        else:
            stat = "DISCONNECT"
            cb = "disconnect"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{stat}", callback_data=f"{cb}:{group_id}:{title}"),
                InlineKeyboardButton("DELETE", callback_data=f"deletecb:{group_id}")],
            [InlineKeyboardButton("BACK", callback_data="backcb")]
        ])

        await query.message.edit_text(
            f"Group Name : **{title}**\nGroup ID : `{group_id}`",
            reply_markup=keyboard
        )
        return

    elif "connectcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]
        title = query.data.split(":")[2]
        user_id = query.from_user.id

        mkact = await make_active(str(user_id), str(group_id))

        if mkact:
            await query.message.edit_text(
                f"Connected to **{title}**"
            )
            return
        else:
            await query.message.edit_text(
                f"Some error occured!!"
            )
            return

    elif "disconnect" in query.data:
        await query.answer()

        title = query.data.split(":")[2]
        user_id = query.from_user.id

        mkinact = await make_inactive(str(user_id))

        if mkinact:
            await query.message.edit_text(
                f"Disconnected from **{title}**"
            )
            return
        else:
            await query.message.edit_text(
                f"Some error occured!!"
            )
            return
    elif "deletecb" in query.data:
        await query.answer()

        user_id = query.from_user.id
        group_id = query.data.split(":")[1]

        delcon = await delete_connection(str(user_id), str(group_id))

        if delcon:
            await query.message.edit_text(
                "Successfully deleted connection"
            )
            return
        else:
            await query.message.edit_text(
                f"Some error occured!!"
            )
            return
    
    elif query.data == "backcb":
        await query.answer()

        userid = query.from_user.id

        groupids = await all_connections(str(userid))
        if groupids is None:
            await query.message.edit_text(
                "There are no active connections!! Connect to some groups first.",
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
            await query.message.edit_text(
                "Your connected group details ;\n\n",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

    elif "alertmessage" in query.data:
        chat_type = query.message.chat.type
        grp_id = query.message.chat.id
        i = query.data.split(":")[1]
        keyword = query.data.split(":")[2]
        if chat_type == ChatType.PRIVATE:
            grpid = await active_connection(str(query.from_user.id))
            if grpid is not None:
                grp_id = grpid
            else:
                await query.answer("I'm not connected to any groups!\nCheck /connections or connect to any groups",show_alert=True)
                return
        reply_text, btn, alerts, fileid = await find_filter(grp_id, keyword)
        if alerts is not None:
            alerts = ast.literal_eval(alerts)
            alert = alerts[int(i)]
            alert = alert.replace("\\n", "\n").replace("\\t", "\t")
            await query.answer(alert,show_alert=True)
    elif "help_filters" in query.data:
        await query.answer()
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("BACK", callback_data="help_data"),
                 InlineKeyboardButton("Buttons", callback_data="help_buttons")]

            ]
        )
        await query.message.edit_text(Script.FILTER_HELP, reply_markup=keyboard)
    elif "help_buttons" in query.data:
        bot_details = await client.get_me()
        username = bot_details.username
        await query.answer()
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("BACK", callback_data="help_filters")]
            ]
        )
        await query.message.edit_text(Script.BUTTON_HELP.format(username), reply_markup=keyboard)

    elif query.data == "help_connection":
        await query.answer()
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("BACK", callback_data="help_data")]
            ]
        )
        await query.message.edit_text(
            Script.CONNECTION_HELP,
            reply_markup=keyboard
        )
    elif query.data == "help_other":
        await query.answer()
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("BACK", callback_data="help_data")]
            ]
        )
        await query.message.edit_text(
            Script.OTHER_HELP,
            reply_markup=keyboard
        )
