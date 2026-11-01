from config import db

mycol = db["CONNECTION"]


async def add_connection(group_id, user_id):
    group_id, user_id = str(group_id), str(user_id)
    row = await mycol.find_one({"_id": user_id})
    if row is not None:
        if group_id in [str(x.get("group_id")) for x in row.get("group_details", [])]:
            return False
        result = await mycol.update_one(
            {"_id": user_id, "group_details.group_id": {"$ne": group_id}},
            {"$push": {"group_details": {"group_id": group_id}},
             "$set": {"active_group": group_id}}
        )
        return result.modified_count > 0
    try:
        await mycol.insert_one({
            "_id": user_id, "group_details": [{"group_id": group_id}],
            "active_group": group_id
        })
        return True
    except Exception:
        return False


async def active_connection(user_id):
    row = await mycol.find_one({"_id": str(user_id)}, {"active_group": 1})
    if not row or row.get("active_group") is None:
        return None
    try:
        return int(row["active_group"])
    except (ValueError, TypeError):
        return None


async def all_connections(user_id):
    row = await mycol.find_one({"_id": str(user_id)}, {"group_details": 1})
    if row is None:
        return None
    return [str(x["group_id"]) for x in row.get("group_details", []) if "group_id" in x]


async def if_active(user_id, group_id):
    row = await mycol.find_one({"_id": str(user_id)}, {"active_group": 1})
    return bool(row and str(row.get("active_group")) == str(group_id))


async def make_active(user_id, group_id):
    groups = await all_connections(user_id)
    if not groups or str(group_id) not in groups:
        return False
    result = await mycol.update_one(
        {"_id": str(user_id)}, {"$set": {"active_group": str(group_id)}}
    )
    return result.matched_count > 0


async def make_inactive(user_id):
    result = await mycol.update_one(
        {"_id": str(user_id)}, {"$set": {"active_group": None}}
    )
    return result.matched_count > 0


async def delete_connection(user_id, group_id):
    user_id, group_id = str(user_id), str(group_id)
    result = await mycol.update_one(
        {"_id": user_id},
        {"$pull": {"group_details": {"group_id": group_id}}}
    )
    if not result.modified_count:
        return False
    row = await mycol.find_one({"_id": user_id})
    if row and str(row.get("active_group")) == group_id:
        groups = row.get("group_details", [])
        next_id = str(groups[-1]["group_id"]) if groups else None
        await mycol.update_one({"_id": user_id}, {"$set": {"active_group": next_id}})
    return True
