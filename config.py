import os
import time
from dotenv import load_dotenv
load_dotenv("config.env")
class Config(object):

    TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")


    API_ID = int(os.environ.get("API_ID", 12345))


    API_HASH = os.environ.get("API_HASH", "")
    
    
    DATABASE_URI = os.environ.get("DATABASE_URI", "")


    DATABASE_NAME = str(os.environ.get("DATABASE_NAME", "Cluster0"))


    AUTH_USERS = set(int(x) for x in os.environ.get("AUTH_USERS", "").split(",") if x.isdigit())


    OWNER_ID = int(os.environ.get("OWNER_ID", "1445283714"))


    SAVE_USER = os.environ.get("SAVE_USER", "no").lower()

    ADD_FILTER_CMD = os.environ.get("ADD_FILTER_CMD", "add")
    DELETE_FILTER_CMD = os.environ.get("DELETE_FILTER_CMDD", "del")
    DELETE_ALL_CMD = os.environ.get("DELETE_ALL_CMD", "delall")
    CONNECT_COMMAND = os.environ.get("CONNECT_COMMAND", "connect")
    DISCONNECT_COMMAND = os.environ.get("DISCONNECT_COMMAND", "disconnect")
    VIEW_FILTERS_COMMAND = os.environ.get("VIEW_FILTERS_COMMAND", "filters")
    CONNECTIONS_COMMAND = os.environ.get("CONNECTIONS_COMMAND", "connections")
    BOT_START_TIME = time.time()