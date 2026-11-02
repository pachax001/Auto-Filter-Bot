from config import OWNER_ID
from database.config_db import get_public_mode
from database.auth_users import is_user_authorized

async def user_can_use_bot(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    if await get_public_mode():
        return True
    return await is_user_authorized(user_id)
