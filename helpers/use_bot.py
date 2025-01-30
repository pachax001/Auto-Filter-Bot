import os
import pymongo
from datetime import datetime, timedelta
from config import DATABASE_URI, DATABASE_NAME,OWNER_ID
from database.config_db import get_public_mode
from database.auth_users import is_user_authorized
 


def user_can_use_bot(user_id: int) -> bool:
    """
    If IS_PUBLIC is True, any user can use the bot.
    Otherwise, only the owner or authorized users are allowed.
    """
    if user_id == OWNER_ID:
        return True
    if get_public_mode():
        return True
    return is_user_authorized(user_id)