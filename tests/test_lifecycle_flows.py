"""Regression checks for deletion, disconnection and group lifecycle."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from database import connections_mdb, filters_mdb


def run(coro):
    return asyncio.run(coro)


def test_remove_one_keyword_never_drops_group(monkeypatch):
    group = SimpleNamespace(
        delete_one=AsyncMock(return_value=SimpleNamespace(deleted_count=1)),
        drop=AsyncMock(),
    )
    monkeypatch.setattr(filters_mdb, "group_collection", lambda _id: group)
    message = SimpleNamespace(reply_text=AsyncMock())
    run(filters_mdb.delete_filter(message, "hello", -100))
    group.delete_one.assert_awaited_once_with({"text": "hello"})
    group.drop.assert_not_awaited()
    assert "deleted" in message.reply_text.await_args.args[0].lower()


def test_disconnect_preserves_saved_connections(monkeypatch):
    update = AsyncMock(return_value=SimpleNamespace(matched_count=1))
    monkeypatch.setattr(connections_mdb, "mycol", SimpleNamespace(update_one=update))
    assert run(connections_mdb.make_inactive("55")) is True
    assert update.await_args.args == (
        {"_id": "55"}, {"$set": {"active_group": None}}
    )


def test_delete_connection_selects_remaining_group(monkeypatch):
    collection = SimpleNamespace(
        update_one=AsyncMock(side_effect=[
            SimpleNamespace(modified_count=1), SimpleNamespace(modified_count=1)
        ]),
        find_one=AsyncMock(return_value={
            "active_group": "-100", "group_details": [{"group_id": "-200"}]
        })
    )
    monkeypatch.setattr(connections_mdb, "mycol", collection)
    assert run(connections_mdb.delete_connection("55", "-100")) is True
    assert collection.update_one.await_count == 2
    assert collection.update_one.await_args.args[1] == {"$set": {"active_group": "-200"}}


def test_delete_final_connection_sets_inactive(monkeypatch):
    collection = SimpleNamespace(
        update_one=AsyncMock(side_effect=[
            SimpleNamespace(modified_count=1), SimpleNamespace(modified_count=1)
        ]),
        find_one=AsyncMock(return_value={
            "active_group": "-100", "group_details": []
        })
    )
    monkeypatch.setattr(connections_mdb, "mycol", collection)
    assert run(connections_mdb.delete_connection("55", "-100")) is True
    assert collection.update_one.await_args.args[1] == {"$set": {"active_group": None}}


def test_only_explicit_delete_all_drops_group_collection(monkeypatch):
    group = SimpleNamespace(drop=AsyncMock())
    monkeypatch.setattr(filters_mdb, "group_collection", lambda _id: group)
    monkeypatch.setattr(filters_mdb, "db", SimpleNamespace(
        list_collection_names=AsyncMock(return_value=["-100", "CONNECTION"])
    ))
    assert run(filters_mdb.del_all_filters_connection(-100)) == 2
    group.drop.assert_awaited_once()
