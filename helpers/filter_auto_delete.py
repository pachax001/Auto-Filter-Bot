"""Persistent, restart-safe expiration of sent Telegram filter message pairs.

This queue is separate from saved filter documents and does not modify them.
"""
import asyncio
from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument
from wzgram.errors import FloodWait

from config import FILTER_AUTO_DELETE_SECONDS, db
from helpers.logger import logger

QUEUE = db["FILTER_MESSAGE_DELETE_QUEUE"]
POLL_INTERVAL_SECONDS = 1
LEASE_SECONDS = 120
MAX_ATTEMPTS = 6
TELEGRAM_DELETE_WINDOW = timedelta(hours=48)

# These RPC errors mean the message is missing or cannot be deleted.
# Always continue with the other message in the pair.
PERMANENT_DELETE_ERRORS = frozenset({
    "MessageIdInvalid", "MessageIdsEmpty", "MessageEmpty", "MessageTooOld",
    "MessageDeleteForbidden", "MessageAuthorRequired", "ChatAdminRequired",
    "ChatWriteForbidden", "ChannelPrivate", "PeerIdInvalid",
})


def _now():
    return datetime.now(timezone.utc)


async def schedule_filter_deletion(trigger, reply):
    """Schedule deletion of Telegram messages, never the stored MongoDB filter."""
    if FILTER_AUTO_DELETE_SECONDS == 0:
        return
    chat_id = getattr(getattr(trigger, "chat", None), "id", None)
    reply_chat_id = getattr(getattr(reply, "chat", None), "id", None)
    trigger_id = getattr(trigger, "id", None)
    reply_id = getattr(reply, "id", None)
    if (not isinstance(chat_id, int)
            or reply_chat_id != chat_id
            or not isinstance(trigger_id, int)
            or not isinstance(reply_id, int)):
        logger.warning("Cannot schedule filter auto-deletion: missing or mismatched message IDs")
        return

    now = _now()
    job = {
        "_id": f"{chat_id}:{reply_id}",
        "chat_id": chat_id,
        # Delete the reply first so a failed user-message deletion cannot leave it behind.
        "pending_message_ids": [reply_id, trigger_id] if reply_id != trigger_id else [reply_id],
        "created_at": now,
        "delete_at": now + timedelta(seconds=FILTER_AUTO_DELETE_SECONDS),
        "attempts": 0,
    }
    try:
        await QUEUE.update_one({"_id": job["_id"]}, {"$setOnInsert": job}, upsert=True)
    except Exception:
        logger.exception(
            "Could not queue filter message auto-deletion chat_id=%s trigger_id=%s reply_id=%s",
            chat_id, trigger_id, reply_id,
        )


async def clear_pending_deletions():
    """Disable mode: cancel leftovers so re-enabling cannot delete old messages."""
    try:
        result = await QUEUE.delete_many({})
        if result.deleted_count:
            logger.info("Canceled %d pending filter message deletions (disabled)", result.deleted_count)
    except Exception:
        logger.exception("Could not cancel previous filter auto-deletion jobs")


async def _process_job(client, job):
    """Delete each message independently and retry only unfinished transient failures."""
    ids = job.get("pending_message_ids") or []
    chat_id = job["chat_id"]
    attempts = job.get("attempts", 0)
    now = _now()
    created = job.get("created_at")
    # MongoDB's default decoder returns naive UTC datetimes.
    if created is not None and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if created is not None and now - created >= TELEGRAM_DELETE_WINDOW:
        logger.warning("Dropping expired filter auto-delete job chat_id=%s job_id=%s", chat_id, job["_id"])
        await QUEUE.delete_one({"_id": job["_id"], "lease_until": job["lease_until"]})
        return

    remaining = []
    wait_seconds = 0
    for index, message_id in enumerate(ids):
        try:
            await client.delete_messages(chat_id, message_id)
        except FloodWait as exc:
            remaining = ids[index:]
            wait_seconds = max(1, int(getattr(exc, "value", 1)))
            logger.warning(
                "FloodWait deleting filter messages chat_id=%s message_id=%s wait=%ss",
                chat_id, message_id, wait_seconds,
            )
            break
        except Exception as exc:
            if type(exc).__name__ in PERMANENT_DELETE_ERRORS:
                logger.info(
                    "Filter message already missing or cannot be deleted chat_id=%s message_id=%s reason=%s",
                    chat_id, message_id, type(exc).__name__,
                )
                continue
            remaining = ids[index:]
            wait_seconds = min(2 ** min(attempts + 1, 8), 300)
            logger.exception(
                "Filter message deletion failed, retry scheduled chat_id=%s message_id=%s",
                chat_id, message_id,
            )
            break

    selector = {"_id": job["_id"], "lease_until": job["lease_until"]}
    if not remaining:
        await QUEUE.delete_one(selector)
    elif attempts + 1 >= MAX_ATTEMPTS:
        logger.error(
            "Filter auto-deletion exhausted retries chat_id=%s remaining_message_ids=%s",
            chat_id, remaining,
        )
        await QUEUE.delete_one(selector)
    else:
        await QUEUE.update_one(
            selector,
            {
                "$set": {
                    "pending_message_ids": remaining,
                    "delete_at": _now() + timedelta(seconds=wait_seconds),
                },
                "$unset": {"lease_until": ""},
                "$inc": {"attempts": 1},
            },
        )


async def run_deletion_worker(client):
    """Process due jobs off the message-handler path; survive worker/API failures."""
    try:
        await QUEUE.create_index("delete_at")
    except Exception:
        logger.exception("Could not create filter auto-delete queue index")

    logger.info("Filter message auto-deletion enabled delay=%ss", FILTER_AUTO_DELETE_SECONDS)
    while True:
        try:
            now = _now()
            job = await QUEUE.find_one_and_update(
                {
                    "delete_at": {"$lte": now},
                    "$or": [
                        {"lease_until": {"$exists": False}},
                        {"lease_until": {"$lte": now}},
                    ],
                },
                {"$set": {"lease_until": now + timedelta(seconds=LEASE_SECONDS)}},
                sort=[("delete_at", 1)],
                return_document=ReturnDocument.AFTER,
            )
            if job is None:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
            else:
                await _process_job(client, job)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Filter auto-delete worker failed; retrying")
            await asyncio.sleep(5)
