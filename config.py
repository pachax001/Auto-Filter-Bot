import os
import time
from dotenv import load_dotenv
from pymongo import AsyncMongoClient
from helpers.logger import logger

load_dotenv("config.env")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
API_ID = int(os.getenv("API_ID") or "0")
API_HASH = os.getenv("API_HASH", "")
DATABASE_URI = os.getenv("DATABASE_URI", "")
DATABASE_NAME = os.getenv("DATABASE_NAME", "FilterBot")
AUTH_USERS = {int(x.strip()) for x in os.getenv("AUTH_USERS", "").split(",") if x.strip().isdigit()}
OWNER_ID = int(os.getenv("OWNER_ID") or "0")
SAVE_USER = os.getenv("SAVE_USER", "no").lower()
IS_PUBLIC_ENV = os.getenv("IS_PUBLIC", "false").lower() == "true"
ADD_FILTER_CMD = os.getenv("ADD_FILTER_CMD", "add")
DELETE_FILTER_CMD = os.getenv("DELETE_FILTER_CMD", os.getenv("DELETE_FILTER_CMDD", "del"))
DELETE_ALL_CMD = os.getenv("DELETE_ALL_CMD", "delall")
CONNECT_COMMAND = os.getenv("CONNECT_COMMAND", "connect")
DISCONNECT_COMMAND = os.getenv("DISCONNECT_COMMAND", "disconnect")
CONNECTIONS_COMMAND = os.getenv("CONNECTIONS_COMMAND", "connections")
VIEW_FILTERS_COMMAND = os.getenv("VIEW_FILTERS_COMMAND", "filters")
BOT_START_TIME = time.time()

def validate_config():
    required = {"TG_BOT_TOKEN": TG_BOT_TOKEN, "API_ID": API_ID,
                "API_HASH": API_HASH, "DATABASE_URI": DATABASE_URI, "OWNER_ID": OWNER_ID}
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError("Missing required configuration: " + ", ".join(missing))

validate_config()
# Use a single async client on the bot's event loop; preserve collection names.
client = AsyncMongoClient(DATABASE_URI, serverSelectionTimeoutMS=10000)
db = client[DATABASE_NAME]
settings_collection = db["settings"]
authorised_collection = db["authorised_users"]

async def get_public_mode():
    setting = await settings_collection.find_one({"key": "public_mode"})
    return setting["value"] if setting is not None else None

async def set_public_mode(status: bool):
    await settings_collection.update_one(
        {"key": "public_mode"}, {"$set": {"value": bool(status)}}, upsert=True
    )

async def add_auth_user_from_config():
    for user_id in AUTH_USERS | {OWNER_ID}:
        await authorised_collection.update_one(
            {"user_id": user_id},
            {"$setOnInsert": {"user_id": user_id}}, upsert=True
        )
    logger.info("Configured authorized users checked.")

async def initialize_settings():
    await add_auth_user_from_config()
    if await get_public_mode() is None:
        await set_public_mode(IS_PUBLIC_ENV)
        logger.info("Initialized public mode from environment.")
