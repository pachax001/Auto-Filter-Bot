from config import db
from helpers.logger import logger
from wzgram.enums import ParseMode

EXCLUDED_COLLECTIONS = {"CONNECTION", "USERS", "authorised_users", "settings", "BROADCAST"}


def group_collection(group_id):
    if group_id is None:
        raise ValueError("No group selected")
    return db[str(group_id)]


async def add_filter(grp_id, text, reply_text, btn, file, alert):
    from plugins.button_codec import serialize_buttons
    data = {
        "text": str(text),
        "reply": str(reply_text or ""),
        "btn": serialize_buttons(btn),
        "file": str(file),
        "alert": str(alert),
    }
    try:
        await group_collection(grp_id).update_one(
            {"text": str(text)}, {"$set": data}, upsert=True
        )
        return True
    except Exception:
        logger.exception("Failed to save filter group_id=%s keyword=%r", grp_id, text)
        return False


async def find_filter(group_id, name):
    if group_id is None:
        return None, None, None, None
    row = await group_collection(group_id).find_one({"text": name})
    if not row:
        return None, None, None, None
    return row.get("reply"), row.get("btn"), row.get("alert"), row.get("file")


async def get_filters(group_id):
    if group_id is None:
        return []
    return [row["text"] async for row in group_collection(group_id).find(
        {}, {"text": 1, "_id": 0}
    ) if isinstance(row.get("text"), str)]


async def delete_filter(message, text, group_id):
    result = await group_collection(group_id).delete_one({"text": text})
    if result.deleted_count:
        await message.reply_text(
            "Filter deleted: " + text, parse_mode=ParseMode.DISABLED
        )
    else:
        await message.reply_text("Couldn't find that filter!")


async def del_all(message, group_id, title):
    result = await del_all_filters_connection(group_id)
    if result == 1:
        await message.edit_text(f"Nothing to remove in {title}!")
    elif result == 2:
        await message.edit_text(f"All filters from {title} have been removed")
    else:
        await message.edit_text("Couldn't remove all filters from group!")


async def del_all_filters_connection(group_id):
    if str(group_id) not in await db.list_collection_names():
        return 1
    try:
        await group_collection(group_id).drop()
        return 2
    except Exception:
        logger.exception("Unable to delete group filters group_id=%s", group_id)
        return None


async def count_filters(group_id):
    if group_id is None:
        return False
    return await group_collection(group_id).count_documents({}) or False


async def filter_stats():
    collections = await db.list_collection_names()
    groups = [name for name in collections
              if name not in EXCLUDED_COLLECTIONS and name.lstrip("-").isdigit()]
    total = 0
    for name in groups:
        total += await db[name].count_documents({})
    return len(groups), total
