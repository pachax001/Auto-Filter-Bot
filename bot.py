import asyncio
from wzgram import Client, idle
from config import TG_BOT_TOKEN, API_ID, API_HASH, initialize_settings, client as mongo_client

async def main():
    try:
        await initialize_settings()
        app = Client("filter_bot", bot_token=TG_BOT_TOKEN, api_id=API_ID,
                     api_hash=API_HASH, plugins={"root": "plugins"}, workers=32)
        async with app:
            await idle()
    finally:
        await mongo_client.close()

if __name__ == "__main__":
    asyncio.run(main())
