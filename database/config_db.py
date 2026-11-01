from config import get_public_mode as _get_public_mode
from config import set_public_mode

async def get_public_mode():
    value = await _get_public_mode()
    return bool(value) if value is not None else False
