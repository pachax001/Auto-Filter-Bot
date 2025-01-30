import os
import pymongo
from datetime import datetime, timedelta
from config import DATABASE_URI, DATABASE_NAME
 
myclient = pymongo.MongoClient(DATABASE_URI)
mydb = myclient[DATABASE_NAME]
mycol = mydb['USERS']



# async def add_user(id, username, name, dcid):
#     data = {
#         '_id': id,
#         'username' : username,
#         'name' : name,
#         'dc_id' : dcid
#     }
#     try:
#         mycol.update_one({'_id': id},  {"$set": data}, upsert=True)
#     except:
#         pass

async def add_or_update_user(user_id, username, full_name, name, dcid):
    """Add or update a user with the latest interaction timestamp."""
    existing_user = mycol.find_one({"_id": user_id})

    if existing_user:
        # Update last active timestamp
       mycol.update_one(
            {"_id": user_id},
            {"$set": {"last_active": datetime.utcnow(), "username": username, "full_name": full_name, "name": name, "dc_id": dcid}}
        )
    else:
        # Add new user with join date
        user_data = {
            "_id": user_id,
            "username": username,
            "full_name": full_name,
            "name": name,
            "dc_id": dcid,
            "joined_at": datetime.utcnow(),
            "last_active": datetime.utcnow()
        }
        mycol.insert_one(user_data)
# async def all_users():
#     count = mycol.count_documents({})
#     return count


async def find_user(id):
    query = mycol.find( {"_id":id})

    try:
        for file in query:
            name = file['name']
            username = file['username']
            dc_id = file['dc_id']
        return name, username, dc_id
    except:
        return None, None, None
    


async def get_total_users():
    """Get the total number of users in the database."""
    return mycol.count_documents({})

async def get_recent_users(days=7):
    """Get the count of users who interacted with the bot in the last 'days' days."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    return mycol.count_documents({"last_active": {"$gte": cutoff_date}})

async def get_all_users():
    """Fetch all user IDs from the database."""
    return mycol.find({}, {"_id": 1})
