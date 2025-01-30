import os
import pymongo
from datetime import datetime
from config import DATABASE_NAME,DATABASE_URI
from helpers.logger import logger
myclient = pymongo.MongoClient(DATABASE_URI)
mydb = myclient[DATABASE_NAME]
mycol = mydb['BROADCAST']


def log_broadcast_result(message: str, sent_count: int, failed_count: int, failed_users: list):
    """Save the broadcast results in the database for tracking."""
    try:
        broadcast_log = {
            "message": message,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "failed_users": failed_users,
            "timestamp": datetime.utcnow(),
        }

        mycol.insert_one(broadcast_log)
        logger.info("📄 Broadcast results saved to database successfully.")

    except Exception as e:
        logger.error(f"❌ Failed to log broadcast result: {e}")