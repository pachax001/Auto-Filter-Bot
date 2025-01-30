import os
import time
from dotenv import load_dotenv
from pymongo import MongoClient
from helpers.logger import logger
import sys
load_dotenv("config.env")


TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")


API_ID = int(os.environ.get("API_ID", ""))


API_HASH = os.environ.get("API_HASH", "")


DATABASE_URI = os.environ.get("DATABASE_URI", "")


DATABASE_NAME = str(os.environ.get("DATABASE_NAME", "FilterBot"))


AUTH_USERS = set(int(x) for x in os.environ.get("AUTH_USERS", "").split(",") if x.isdigit())

OWNER_ID = int(os.environ.get("OWNER_ID"))


SAVE_USER = os.environ.get("SAVE_USER", "no").lower()

IS_PUBLIC_ENV = os.getenv("IS_PUBLIC", "false").lower() == "true"

ADD_FILTER_CMD = os.environ.get("ADD_FILTER_CMD", "add")
DELETE_FILTER_CMD = os.environ.get("DELETE_FILTER_CMDD", "del")
DELETE_ALL_CMD = os.environ.get("DELETE_ALL_CMD", "delall")
CONNECT_COMMAND = os.environ.get("CONNECT_COMMAND", "connect")
DISCONNECT_COMMAND = os.environ.get("DISCONNECT_COMMAND", "disconnect")
CONNECTIONS_COMMAND = os.environ.get("CONNECTIONS_COMMAND", "connections")
VIEW_FILTERS_COMMAND = os.environ.get("VIEW_FILTERS_COMMAND", "filters")

BOT_START_TIME = time.time()



def validate_config():
    missing_vars = []
    if not TG_BOT_TOKEN:
        missing_vars.append("TG_BOT_TOKEN")
    if not API_ID:
        missing_vars.append("API_ID")
    if not API_HASH:
        missing_vars.append("API_HASH")
    if not DATABASE_URI:
        missing_vars.append("DATABASE_URI")
    if not OWNER_ID:
        missing_vars.append("OWNER_ID")
    if missing_vars:
        raise ValueError(f"Missing value for the following environment variables: {missing_vars}")
        sys.exit(1)
    
validate_config()


client = MongoClient(DATABASE_URI)
db = client[DATABASE_NAME]
settings_collection = db["settings"]
authorised_collection = db["authorised_users"]

def get_public_mode():
    """Retrieve the current public mode status from the database."""
    setting = settings_collection.find_one({"key": "public_mode"})
    return setting["value"] if setting else None

def set_public_mode(status: bool):
    """Store the public mode status in the database."""
    settings_collection.update_one(
        {"key": "public_mode"},
        {"$set": {"value": status}},
        upsert=True
    )
def add_auth_user_from_config():
    #check if user is already added
    for user in AUTH_USERS:
        user = authorised_collection.find_one({"user_id": user})
        if not user:
            authorised_collection.insert_one({"user_id": user})
            logger.info(f"Added {user} to the authorised users list.")
        else:
            logger.info(f"{user} is already in the authorised users list.")
    logger.info("Authorised users list updated.")
    #add owner to authorised users list
    owner = authorised_collection.find_one({"user_id": OWNER_ID})
    if not owner:
        authorised_collection.insert_one({"user_id": OWNER_ID})
        logger.info(f"Added owner to the authorised users list.")
    else:
        logger.info("Owner is already in the authorised users list.")

db_public_mode = get_public_mode()

def initialize_settings():
    """Ensure required settings are stored in the database when bot starts."""
    # add_auth_user_from_config()
    add_auth_user_from_config()
    if get_public_mode() is None:
        logger.info("🔧 IS_PUBLIC not found in the database. Initializing...")
        set_public_mode(IS_PUBLIC_ENV)
    else:
        logger.info("🔧 IS_PUBLIC found in the database. Synchronizing...")