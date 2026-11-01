from config import db

users_collection = db["authorised_users"]

async def is_user_authorized(user_id: int) -> bool:
    return await users_collection.find_one({"user_id": int(user_id)}) is not None

async def authorize_user(user_id: int) -> None:
    await users_collection.update_one(
        {"user_id": int(user_id)},
        {"$setOnInsert": {"user_id": int(user_id)}}, upsert=True
    )

async def unauthorize_user(user_id: int) -> None:
    await users_collection.delete_one({"user_id": int(user_id)})

async def load_authorized_users() -> list[int]:
    return [row["user_id"] async for row in
            users_collection.find({}, {"_id": 0, "user_id": 1})]
