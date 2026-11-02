"""Offline coverage of filter auto-deletion. No Telegram calls or MongoDB writes."""
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from config import _parse_filter_auto_delete_seconds
from helpers import filter_auto_delete as deletion
from plugins import filters as filter_handlers


def run(coro):
    return asyncio.run(coro)


def make_message(chat_id=-100, message_id=1):
    return SimpleNamespace(chat=SimpleNamespace(id=chat_id), id=message_id)


def make_job(ids=(11, 10), attempts=0):
    return {
        "_id": "-100:11",
        "chat_id": -100,
        "pending_message_ids": list(ids),
        "created_at": datetime.now(timezone.utc),
        "delete_at": datetime.now(timezone.utc),
        "attempts": attempts,
        "lease_until": datetime.now(timezone.utc) + timedelta(seconds=120),
    }


def test_config_accepts_zero_and_positive_seconds():
    assert _parse_filter_auto_delete_seconds("0") == 0
    assert _parse_filter_auto_delete_seconds("60") == 60
    assert _parse_filter_auto_delete_seconds("172799") == 172799


@pytest.mark.parametrize("value", ["oops", "", "-1", "172800", "0.5"])
def test_config_rejects_invalid_or_unachievable_deadlines(value):
    with pytest.raises(ValueError):
        _parse_filter_auto_delete_seconds(value)


def test_disabled_mode_does_not_write_to_queue(monkeypatch):
    queue = SimpleNamespace(update_one=AsyncMock())
    monkeypatch.setattr(deletion, "QUEUE", queue)
    monkeypatch.setattr(deletion, "FILTER_AUTO_DELETE_SECONDS", 0)
    run(deletion.schedule_filter_deletion(make_message(message_id=10), make_message(message_id=11)))
    queue.update_one.assert_not_awaited()


def test_scheduling_creates_pair_without_touching_filter_storage(monkeypatch):
    queue = SimpleNamespace(update_one=AsyncMock())
    monkeypatch.setattr(deletion, "QUEUE", queue)
    monkeypatch.setattr(deletion, "FILTER_AUTO_DELETE_SECONDS", 60)
    run(deletion.schedule_filter_deletion(make_message(message_id=10), make_message(message_id=11)))
    call = queue.update_one.await_args
    assert call.kwargs == {"upsert": True}
    job = call.args[1]["$setOnInsert"]
    assert job["chat_id"] == -100
    assert job["pending_message_ids"] == [11, 10]
    assert timedelta(seconds=59) <= job["delete_at"] - job["created_at"] <= timedelta(seconds=61)


def test_private_chat_is_supported(monkeypatch):
    queue = SimpleNamespace(update_one=AsyncMock())
    monkeypatch.setattr(deletion, "QUEUE", queue)
    monkeypatch.setattr(deletion, "FILTER_AUTO_DELETE_SECONDS", 5)
    run(deletion.schedule_filter_deletion(make_message(50, 2), make_message(50, 3)))
    assert queue.update_one.await_args.args[1]["$setOnInsert"]["chat_id"] == 50


def test_mismatched_reply_chat_never_scheduled(monkeypatch):
    queue = SimpleNamespace(update_one=AsyncMock())
    monkeypatch.setattr(deletion, "QUEUE", queue)
    monkeypatch.setattr(deletion, "FILTER_AUTO_DELETE_SECONDS", 5)
    run(deletion.schedule_filter_deletion(make_message(-100, 2), make_message(-200, 3)))
    queue.update_one.assert_not_awaited()


def test_deleted_messages_are_idempotent_and_both_attempted(monkeypatch):
    class MessageIdInvalid(Exception):
        pass

    queue = SimpleNamespace(delete_one=AsyncMock(), update_one=AsyncMock())
    monkeypatch.setattr(deletion, "QUEUE", queue)
    client = SimpleNamespace(delete_messages=AsyncMock(side_effect=[MessageIdInvalid(), None]))
    run(deletion._process_job(client, make_job()))
    assert [c.args for c in client.delete_messages.await_args_list] == [(-100, 11), (-100, 10)]
    queue.delete_one.assert_awaited_once()
    queue.update_one.assert_not_awaited()


def test_transient_failure_preserves_remaining_ids_for_retry(monkeypatch):
    queue = SimpleNamespace(delete_one=AsyncMock(), update_one=AsyncMock())
    monkeypatch.setattr(deletion, "QUEUE", queue)
    client = SimpleNamespace(delete_messages=AsyncMock(side_effect=[None, RuntimeError("network")]))
    run(deletion._process_job(client, make_job()))
    queue.delete_one.assert_not_awaited()
    update = queue.update_one.await_args.args[1]
    assert update["$set"]["pending_message_ids"] == [10]
    assert update["$inc"]["attempts"] == 1


def test_retry_exhaustion_is_bounded(monkeypatch):
    queue = SimpleNamespace(delete_one=AsyncMock(), update_one=AsyncMock())
    monkeypatch.setattr(deletion, "QUEUE", queue)
    client = SimpleNamespace(delete_messages=AsyncMock(side_effect=RuntimeError("offline")))
    run(deletion._process_job(client, make_job(attempts=deletion.MAX_ATTEMPTS - 1)))
    queue.delete_one.assert_awaited_once()
    queue.update_one.assert_not_awaited()


def test_expired_jobs_are_dropped_without_deleting_messages(monkeypatch):
    queue = SimpleNamespace(delete_one=AsyncMock())
    monkeypatch.setattr(deletion, "QUEUE", queue)
    job = make_job()
    job["created_at"] -= timedelta(hours=49)
    client = SimpleNamespace(delete_messages=AsyncMock())
    run(deletion._process_job(client, job))
    client.delete_messages.assert_not_awaited()
    queue.delete_one.assert_awaited_once()


def test_disabling_cancels_previous_pending_jobs(monkeypatch):
    queue = SimpleNamespace(delete_many=AsyncMock(return_value=SimpleNamespace(deleted_count=2)))
    monkeypatch.setattr(deletion, "QUEUE", queue)
    run(deletion.clear_pending_deletions())
    queue.delete_many.assert_awaited_once_with({})


def test_filter_playback_enqueues_text_reply_only_when_sent(monkeypatch):
    monkeypatch.setattr(filter_handlers, "get_filters", AsyncMock(return_value=["john wick"]))
    monkeypatch.setattr(filter_handlers, "find_filter", AsyncMock(
        return_value=("A reply", "[]", None, "None")
    ))
    enqueue = AsyncMock()
    monkeypatch.setattr(filter_handlers, "schedule_filter_deletion", enqueue)
    reply = make_message(-100, 11)
    trigger = make_message(-100, 10)
    trigger.text = "John wick"
    trigger.reply_text = AsyncMock(return_value=reply)
    trigger.reply_cached_media = AsyncMock()
    run(filter_handlers._playback(trigger, -100))
    enqueue.assert_awaited_once_with(trigger, reply)


def test_filter_playback_enqueues_media_reply(monkeypatch):
    monkeypatch.setattr(filter_handlers, "get_filters", AsyncMock(return_value=["john wick"]))
    monkeypatch.setattr(filter_handlers, "find_filter", AsyncMock(
        return_value=("", "[]", None, "file-id")
    ))
    enqueue = AsyncMock()
    monkeypatch.setattr(filter_handlers, "schedule_filter_deletion", enqueue)
    reply = make_message(7, 2)
    trigger = make_message(7, 1)
    trigger.text = "John wick"
    trigger.reply_text = AsyncMock()
    trigger.reply_cached_media = AsyncMock(return_value=reply)
    run(filter_handlers._playback(trigger, -100))
    enqueue.assert_awaited_once_with(trigger, reply)
    trigger.reply_text.assert_not_awaited()


def test_failed_reply_does_not_schedule_deletion(monkeypatch):
    monkeypatch.setattr(filter_handlers, "get_filters", AsyncMock(return_value=["john wick"]))
    monkeypatch.setattr(filter_handlers, "find_filter", AsyncMock(
        return_value=("Hello", "[]", None, "None")
    ))
    enqueue = AsyncMock()
    monkeypatch.setattr(filter_handlers, "schedule_filter_deletion", enqueue)
    trigger = make_message(-100, 10)
    trigger.text = "john wick"
    trigger.reply_text = AsyncMock(side_effect=RuntimeError("send failed"))
    trigger.reply_cached_media = AsyncMock()
    run(filter_handlers._playback(trigger, -100))
    enqueue.assert_not_awaited()
