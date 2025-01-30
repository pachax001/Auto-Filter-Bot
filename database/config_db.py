from config import DATABASE_NAME,DATABASE_URI
import pymongo
db = pymongo.MongoClient(DATABASE_URI)[DATABASE_NAME]
settings_collection = db["settings"]


def set_public_mode(status: bool):
    """Set the bot public mode status (True for on, False for off)."""
    settings_collection.update_one(
        {"key": "public_mode"},
        {"$set": {"value": status}},
        upsert=True
    )

def get_public_mode():
    """Retrieve the current public mode status."""
    setting = settings_collection.find_one({"key": "public_mode"})
    return setting["value"] if setting else False  # Default to False if not found