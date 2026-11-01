from datetime import datetime, timezone
from config import db
from helpers.logger import logger

mycol = db["BROADCAST"]

async def log_broadcast_result(message: str, sent_count: int, failed_count: int, failed_users: list):
    try:
        await mycol.insert_one({
            "message": message,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "failed_users": failed_users,
            "timestamp": datetime.now(timezone.utc)
        })
    except Exception:
        logger.exception("Failed to save BROADCAST result sent=%s failed=%s", sent_count, failed_count)
