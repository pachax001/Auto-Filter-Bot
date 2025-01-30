
import pyrogram
from config import TG_BOT_TOKEN, API_ID, API_HASH,initialize_settings



if __name__ == "__main__" :
    initialize_settings()
    plugins = dict(
        root="plugins"
    )
    app = pyrogram.Client(
        "filter_bot",
        bot_token=TG_BOT_TOKEN,
        api_id=API_ID,
        api_hash=API_HASH,
        plugins=plugins,
        workers=300
    )
    
    
    app.run()
