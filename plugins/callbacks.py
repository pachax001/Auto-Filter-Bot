import ast
from wzgram import Client
from wzgram.types import InlineKeyboardMarkup, InlineKeyboardButton
from wzgram.enums import ChatType, ChatMemberStatus
from database.auth_users import is_user_authorized
from helpers.use_bot import user_can_use_bot
from script import Script
from database.filters_mdb import del_all, find_filter
from database.connections_mdb import (
    all_connections, active_connection, if_active, delete_connection,
    make_active, make_inactive
)


async def _can_manage(client, user_id, group_id):
    if await is_user_authorized(user_id):
        return True
    try:
        member = await client.get_chat_member(int(group_id), int(user_id))
        return member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR)
    except Exception:
        return False


async def _can_delete_all(client, user_id, group_id):
    if await is_user_authorized(user_id):
        return True
    try:
        member = await client.get_chat_member(int(group_id), int(user_id))
        return member.status == ChatMemberStatus.OWNER
    except Exception:
        return False


@Client.on_callback_query()
async def cb_handler(client, query):
    if not query.from_user or not query.data:
        return
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
                    InlineKeyboardButton("Owner", url="https://t.me/Tonbidmaster")
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
                        "OWNER", url="https://t.me/Tonbidmaster")
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
        

    elif query.data.startswith("delallconfirm:"):
        try:
            _, group_id, requestor = query.data.split(":", 2)
            group_id = int(group_id)
            if int(requestor) != query.from_user.id:
                raise ValueError("Wrong requestor")
            if query.message.chat.type == ChatType.PRIVATE:
                if await active_connection(query.from_user.id) != group_id:
                    raise ValueError("Different active connection")
            elif query.message.chat.id != group_id:
                raise ValueError("Wrong chat")
        except (ValueError, TypeError, AttributeError):
            await query.answer("This confirmation is no longer valid.", show_alert=True)
            return
        if not await _can_delete_all(client, query.from_user.id, group_id):
            await query.answer("Only the group owner or authorized user may delete all filters.", show_alert=True)
            return
        await query.answer()
        try:
            title = (await client.get_chat(group_id)).title
        except Exception:
            await query.answer("Group unavailable", show_alert=True)
            return
        await del_all(query.message, group_id, title)
        return

    elif query.data.startswith("delallcancel:"):
        try:
            requestor = int(query.data.rsplit(":", 1)[1])
        except ValueError:
            return
        if requestor != query.from_user.id:
            await query.answer("This confirmation belongs to another user.", show_alert=True)
            return
        await query.answer("Cancelled")
        await query.message.delete()
        return

    elif query.data.startswith("groupcb:"):
        if query.message.chat.type != ChatType.PRIVATE:
            await query.answer("Use connections in private chat.", show_alert=True)
            return
        group_id = query.data.split(":", 2)[1]
        groups = await all_connections(query.from_user.id)
        if not groups or group_id not in groups or not await _can_manage(client, query.from_user.id, group_id):
            await query.answer("Connection is no longer available.", show_alert=True)
            return
        try:
            title = (await client.get_chat(int(group_id))).title
        except Exception:
            await query.answer("Group unavailable", show_alert=True)
            return
        active = await if_active(query.from_user.id, group_id)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("DISCONNECT" if active else "CONNECT",
                                  callback_data=("disconnect:" if active else "connectcb:") + group_id),
             InlineKeyboardButton("DELETE", callback_data="deletecb:" + group_id)],
            [InlineKeyboardButton("BACK", callback_data="backcb")]
        ])
        await query.answer()
        await query.message.edit_text(
            f"Group Name : **{title}**\nGroup ID : `{group_id}`", reply_markup=keyboard
        )
        return

    elif query.data.startswith("connectcb:"):
        if query.message.chat.type != ChatType.PRIVATE:
            await query.answer("Private connections only.", show_alert=True)
            return
        group_id = query.data.split(":", 2)[1]
        if not await _can_manage(client, query.from_user.id, group_id):
            await query.answer("Group admin privileges required.", show_alert=True)
            return
        activated = await make_active(query.from_user.id, group_id)
        await query.answer()
        await query.message.edit_text(
            "Connected." if activated else "Connection is no longer available."
        )
        return

    elif query.data.startswith("disconnect:"):
        if query.message.chat.type != ChatType.PRIVATE:
            await query.answer("Private connections only.", show_alert=True)
            return
        group_id = query.data.split(":", 2)[1]
        if not await if_active(query.from_user.id, group_id):
            await query.answer("This is not your active connection.", show_alert=True)
            return
        inactive = await make_inactive(query.from_user.id)
        await query.answer()
        await query.message.edit_text("Disconnected." if inactive else "Already disconnected.")
        return

    elif query.data.startswith("deletecb:"):
        # Removing one user's connection must NEVER delete a group's shared filters.
        if query.message.chat.type != ChatType.PRIVATE:
            await query.answer("Private connections only.", show_alert=True)
            return
        group_id = query.data.split(":", 2)[1]
        removed = await delete_connection(query.from_user.id, group_id)
        await query.answer()
        await query.message.edit_text(
            "Connection deleted. Group filters were kept." if removed else "Connection not found."
        )
        return

    elif query.data == "backcb":
        if query.message.chat.type != ChatType.PRIVATE:
            await query.answer("Private connections only.", show_alert=True)
            return
        groups = await all_connections(query.from_user.id) or []
        keyboard = []
        for group_id in groups:
            if not await _can_manage(client, query.from_user.id, group_id):
                continue
            try:
                title = (await client.get_chat(int(group_id))).title
                active = await if_active(query.from_user.id, group_id)
                keyboard.append([InlineKeyboardButton(
                    title + (" - ACTIVE" if active else ""),
                    callback_data="groupcb:" + group_id
                )])
            except Exception:
                continue
        await query.answer()
        await query.message.edit_text(
            "Your connected groups:" if keyboard else "No accessible connections.",
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
        )
        return

    elif query.data.startswith("alertmessage:"):
        try:
            _, index, keyword = query.data.split(":", 2)
            index = int(index)
            if index < 0:
                raise ValueError("Invalid alert")
            group_id = query.message.chat.id
            if query.message.chat.type == ChatType.PRIVATE:
                group_id = await active_connection(query.from_user.id)
                if group_id is None or not await _can_manage(client, query.from_user.id, group_id):
                    raise ValueError("No accessible connection")
            _, _, stored_alerts, _ = await find_filter(group_id, keyword)
            if not isinstance(stored_alerts, str) or len(stored_alerts) > 20000:
                raise ValueError("Missing alert")
            alerts = ast.literal_eval(stored_alerts)
            if not isinstance(alerts, list) or index >= len(alerts) or not isinstance(alerts[index], str):
                raise ValueError("Invalid alert")
            text = alerts[index].replace("\\n", "\n").replace("\\t", "\t")
        except (ValueError, TypeError, IndexError, SyntaxError, MemoryError, RecursionError):
            await query.answer("Alert unavailable.", show_alert=True)
            return
        await query.answer(text[:200], show_alert=True)
        return
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
