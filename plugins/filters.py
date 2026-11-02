import io
import re
import shlex

from wzgram import Client, filters
from wzgram.enums import ChatType, ChatMemberStatus
from wzgram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import ADD_FILTER_CMD, VIEW_FILTERS_COMMAND, DELETE_FILTER_CMD, DELETE_ALL_CMD, SAVE_USER
from database.auth_users import is_user_authorized
from database.filters_mdb import add_filter, find_filter, get_filters, delete_filter, count_filters
from database.connections_mdb import active_connection
from helpers.user_activity import record_user_activity
from helpers.use_bot import user_can_use_bot
from helpers.logger import logger
from helpers.error_handling import log_handler_errors
from plugins.helpers import parser, split_quotes
from plugins.button_codec import deserialize_buttons, serialize_buttons


async def _can_manage(client, user_id, group_id):
    if await is_user_authorized(user_id):
        return True
    try:
        member = await client.get_chat_member(int(group_id), int(user_id))
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        logger.exception("Could not check group permissions user_id=%s group_id=%s", user_id, group_id)
        return False


async def _save_user(message):
    await record_user_activity(message)


async def _target_group(client, message):
    if message.chat.type == ChatType.PRIVATE:
        group_id = await active_connection(message.from_user.id)
        if group_id is None:
            await message.reply_text("I'm not connected to any groups!")
            return None
        try:
            chat = await client.get_chat(group_id)
            return group_id, chat.title
        except Exception:
            logger.exception("Failed to resolve connected group group_id=%s user_id=%s",
                             group_id, message.from_user.id)
            await message.reply_text("Make sure I'm present in your group!")
            return None
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        return message.chat.id, message.chat.title
    return None


@Client.on_message(filters.command(ADD_FILTER_CMD))
@log_handler_errors("plugins/filters.py:addfilter")
async def addfilter(client, message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    if not await user_can_use_bot(user_id):
        await message.reply_text("You are not authorized to use this bot.")
        return
    target = await _target_group(client, message)
    if target is None:
        return
    group_id, title = target
    if not await _can_manage(client, user_id, group_id):
        await message.reply_text("Group admin privileges required.")
        return
    parts = (message.text.html if hasattr(message.text, "html") else (message.text or "")).split(None, 1)
    if len(parts) < 2:
        await message.reply_text("Command incomplete!")
        return
    extracted = split_quotes(parts[1])
    if not extracted or not extracted[0].strip():
        await message.reply_text("Specify a filter name.")
        return
    keyword = extracted[0].lower().strip()
    source = message.reply_to_message
    if source is None and len(extracted) < 2:
        await message.reply_text("Add some content to save your filter!")
        return
    media = None
    body = extracted[1] if len(extracted) > 1 else ""
    if source is not None:
        media = next(
            (item for item in (source.document, source.video, source.photo,
                               source.audio, source.animation, source.sticker)
             if item is not None), None
        )
        if source.caption:
            body = source.caption.html
        elif source.text:
            body = source.text.html
        elif not body:
            body = ""
    reply_text, parsed_buttons, alert = parser(body, keyword)
    buttons = (
        source.reply_markup.inline_keyboard
        if source and getattr(source.reply_markup, "inline_keyboard", None)
        else parsed_buttons
    )
    file_id = media.file_id if media else None
    if not reply_text and file_id is None:
        await message.reply_text("You cannot create an empty text filter.")
        return
    try:
        # Validate before writing. Stored 'btn' stays a string, now JSON.
        buttons = serialize_buttons(buttons)
    except (ValueError, TypeError, SyntaxError, RecursionError) as exc:
        await message.reply_text(f"Invalid buttons: {exc}")
        return
    if not await add_filter(group_id, keyword, reply_text, buttons, file_id, alert):
        await message.reply_text("Could not save the filter. Check the bot logs.")
        return
    await message.reply_text(f"Filter for `{keyword}` added in **{title}**")
    await _save_user(message)


@Client.on_message(filters.command(VIEW_FILTERS_COMMAND))
@log_handler_errors("plugins/filters.py:get_all")
async def get_all(client, message):
    if not message.from_user:
        return
    
    chat_type = message.chat.type
    userid = message.from_user.id
    if not await user_can_use_bot(userid):
        await message.reply_text(
            "You are not authorized to use this bot."
        )
        return
    await record_user_activity(message)
    if chat_type == ChatType.PRIVATE:
        
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except Exception:
                logger.exception("Could not resolve group group_id=%s user_id=%s", grpid, userid)
                await message.reply_text("Make sure I'm present in your group!!")
                return
        else:
            await message.reply_text("I'm not connected to any groups!")
            return

    elif (chat_type == ChatType.GROUP) or (chat_type == ChatType.SUPERGROUP):
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    if not await _can_manage(client, userid, grp_id):
        return

    texts = await get_filters(grp_id)
    count = await count_filters(grp_id)
    if count:
        texts = sorted(texts)
        filterlist = f"Total number of filters in **{title}** : {count}\n\n"
        keywords = "\n".join(f"{idx + 1}.  `{text}`" for idx, text in enumerate(texts))
        filterlist = f"Total number of filters in **{title}** : {count}\n\n{keywords}"
        doc_keywords = "\n".join(f"{idx + 1}.  {text}" for idx, text in enumerate(texts))
        doc_filterlist = f"Total number of filters in {title} : {count}\n\n{doc_keywords}"
        if len(filterlist) > 4096:
            
            with io.BytesIO(str.encode(doc_filterlist)) as keyword_file:
                keyword_file.name = "keywords.txt"
                await message.reply_document(
                    document=keyword_file,
                    caption=f"Total number of filters in **{title}** : {count}"
                )
            return
    else:
        filterlist = f"There are no active filters in **{title}**"

    await message.reply_text(
        text=filterlist
    )
        
@Client.on_message(filters.command(DELETE_FILTER_CMD))
@log_handler_errors("plugins/filters.py:deletefilter")
async def deletefilter(client, message):
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

    if chat_type == ChatType.PRIVATE:
        grpid  = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except Exception:
                logger.exception("Could not resolve group group_id=%s user_id=%s", grpid, userid)
                await message.reply_text("Make sure I'm present in your group!!")
                return
        else:
            await message.reply_text("I'm not connected to any groups!")
            return

    elif (chat_type == ChatType.GROUP) or (chat_type == ChatType.SUPERGROUP):
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    if not await _can_manage(client, userid, grp_id):
        return

    try:
        args = shlex.split(message.text)
        if len(args) < 2:
            raise ValueError("No filter names provided")
        filters_to_delete = args[1:]
    except ValueError:
        view_filter_cmd = VIEW_FILTERS_COMMAND
        await message.reply_text(
            "<i>Mention the filtername which you wanna delete!</i>\n\n"
            "<code>/del filtername</code>\n\n"
            f"Use /{view_filter_cmd} to view all available filters"
        )
        return
    for filter_name in filters_to_delete:
        await delete_filter(message, filter_name.lower(), grp_id)
        

@Client.on_message(filters.command(DELETE_ALL_CMD))
@log_handler_errors("plugins/filters.py:delallconfirm")
async def delallconfirm(client, message):
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

    if chat_type == ChatType.PRIVATE:
        grpid  = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except Exception:
                logger.exception("Could not resolve group group_id=%s user_id=%s", grpid, userid)
                await message.reply_text("Make sure I'm present in your group!!")
                return
        else:
            await message.reply_text("I'm not connected to any groups!")
            return

    elif (chat_type == ChatType.GROUP) or (chat_type == ChatType.SUPERGROUP):
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    try:
        st = await client.get_chat_member(grp_id, userid)
        owner = st.status == ChatMemberStatus.OWNER
    except Exception:
        logger.exception("Could not check group owner user_id=%s group_id=%s", userid, grp_id)
        owner = False
    if owner or await is_user_authorized(userid):
        await message.reply_text(
            f"This will delete all filters from '{title}'.\nDo you want to continue??",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(text="YES",callback_data=f"delallconfirm:{grp_id}:{userid}")],
                [InlineKeyboardButton(text="CANCEL",callback_data=f"delallcancel:{grp_id}:{userid}")]
            ])
        )


@Client.on_message(filters.group & filters.text)
@log_handler_errors("plugins/filters.py:give_filter")
async def give_filter(client, message):
    await _playback(message, message.chat.id)


@Client.on_message(filters.private & filters.text)
@log_handler_errors("plugins/filters.py:give_filter_private")
async def give_filter_private(client, message):
    if not message.from_user or not await user_can_use_bot(message.from_user.id):
        return
    group_id = await active_connection(message.from_user.id)
    if group_id is None:
        return
    if not await _can_manage(client, message.from_user.id, group_id):
        return
    await _playback(message, group_id)
    await _save_user(message)


async def _playback(message, group_id):
    content = message.text or ""
    keywords = await get_filters(group_id)
    for keyword in sorted(keywords, key=len, reverse=True):
        if not keyword:
            continue
        pattern = r"(^|[^\w])" + re.escape(keyword) + r"($|[^\w])"
        if not re.search(pattern, content, flags=re.IGNORECASE):
            continue
        reply_text, stored_buttons, _, file_id = await find_filter(group_id, keyword)
        if reply_text is None and file_id is None:
            return
        text = (reply_text or "").replace("\\n", "\n").replace("\\t", "\t")
        try:
            buttons = deserialize_buttons(stored_buttons)
        except (ValueError, TypeError, SyntaxError, RecursionError) as exc:
            logger.warning("Rejected unsafe or malformed filter buttons group_id=%s keyword=%r: %s",
                           group_id, keyword, exc, exc_info=True)
            buttons = []
        markup = InlineKeyboardMarkup(buttons) if buttons else None
        try:
            if file_id is not None and file_id != "None":
                await message.reply_cached_media(file_id, caption=text or "",
                                                 reply_markup=markup)
            elif text:
                await message.reply_text(text, disable_web_page_preview=True,
                                         reply_markup=markup)
        except Exception:
            logger.exception("Failed to send filter reply group_id=%s keyword=%r chat_id=%s media=%s",
                             group_id, keyword, getattr(message.chat, "id", None),
                             file_id not in (None, "None"))
        return
