from datetime import datetime, timedelta, timezone
from config import db

mycol = db["USERS"]

async def add_or_update_user(user_id, username, full_name, name, dcid):
    now = datetime.now(timezone.utc)
    await mycol.update_one(
        {"_id": user_id},
        {"$set": {"last_active": now, "username": username,
                  "full_name": full_name, "name": name, "dc_id": dcid},
         "$setOnInsert": {"joined_at": now}},
        upsert=True
    )

async def find_user(id):
    row = await mycol.find_one({"_id": id})
    if not row:
        return None, None, None
    return row.get("name"), row.get("username"), row.get("dc_id")

async def get_total_users():
    return await mycol.count_documents({})

async def get_recent_users(days=7):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return await mycol.count_documents({"last_active": {"$gte": cutoff}})

async def get_all_users():
    return mycol.find({}, {"_id": 1})
