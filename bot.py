import asyncio
from contextlib import suppress
from wzgram import Client, idle
from config import TG_BOT_TOKEN, API_ID, API_HASH, initialize_settings, client as mongo_client
from helpers.logger import logger
from helpers.filter_auto_delete import run_deletion_worker, clear_pending_deletions
from config import FILTER_AUTO_DELETE_SECONDS

async def main():
    try:
        await initialize_settings()
        app = Client("filter_bot", bot_token=TG_BOT_TOKEN, api_id=API_ID,
                     api_hash=API_HASH, plugins={"root": "plugins"}, workers=32)
        async with app:
            worker = None
            if FILTER_AUTO_DELETE_SECONDS:
                worker = asyncio.create_task(
                    run_deletion_worker(app), name="filter-message-auto-delete"
                )
            else:
                await clear_pending_deletions()
            try:
                await idle()
            finally:
                if worker is not None:
                    worker.cancel()
                    with suppress(asyncio.CancelledError):
                        await worker
    except Exception:
        logger.exception("Bot initialization or Telegram session failed")
        raise
    finally:
        await mongo_client.close()

if __name__ == "__main__":
    asyncio.run(main())
