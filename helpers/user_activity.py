"""Optional saved-user tracking, retaining the existing USERS schema."""
from config import SAVE_USER
from database.users_mdb import add_or_update_user
from helpers.logger import logger


async def record_user_activity(message):
    if SAVE_USER != "yes" or not getattr(message, "from_user", None):
        return
    user = message.from_user
    try:
        await add_or_update_user(
            str(user.id),
            str(user.username or "None"),
            (user.first_name or "") + " " + (user.last_name or ""),
            str(user.first_name or ""),
            str(user.dc_id or "None"),
        )
    except Exception:
        logger.exception(
            "Failed to update USERS activity user_id=%s chat_id=%s",
            user.id, getattr(getattr(message, "chat", None), "id", None)
        )
