"""Offline regression tests. No Telegram credentials or MongoDB server are used."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from wzgram.enums import ChatType, ChatMemberStatus
from plugins import filters as filter_handlers
from plugins import callbacks
from database import connections_mdb, filters_mdb


def run(coro):
    return asyncio.run(coro)


def test_missing_filter_has_stable_response(monkeypatch):
    collection = SimpleNamespace(find_one=AsyncMock(return_value=None))
    monkeypatch.setattr(filters_mdb, "group_collection", lambda gid: collection)
    assert run(filters_mdb.find_filter(-100, "missing")) == (None, None, None, None)


def test_invalid_stored_buttons_cannot_execute(monkeypatch):
    monkeypatch.setattr(filter_handlers, "get_filters", AsyncMock(return_value=["hello"]))
    monkeypatch.setattr(filter_handlers, "find_filter", AsyncMock(
        return_value=("Hello!", "[[__import__('os').system('echo malicious')]]", "None", "None")
    ))
    message = SimpleNamespace(
        text="hello", reply_text=AsyncMock(), reply_cached_media=AsyncMock()
    )
    run(filter_handlers._playback(message, -100))
    message.reply_text.assert_awaited_once()
    assert message.reply_text.await_args.kwargs["reply_markup"] is None
    message.reply_cached_media.assert_not_awaited()


def test_no_filter_match_sends_nothing(monkeypatch):
    monkeypatch.setattr(filter_handlers, "get_filters", AsyncMock(return_value=["there"]))
    message = SimpleNamespace(
        text="hello", reply_text=AsyncMock(), reply_cached_media=AsyncMock()
    )
    run(filter_handlers._playback(message, -100))
    message.reply_text.assert_not_awaited()


def test_private_without_connection_does_not_touch_filters(monkeypatch):
    monkeypatch.setattr(filter_handlers, "user_can_use_bot", AsyncMock(return_value=True))
    monkeypatch.setattr(filter_handlers, "active_connection", AsyncMock(return_value=None))
    find = AsyncMock()
    monkeypatch.setattr(filter_handlers, "get_filters", find)
    message = SimpleNamespace(from_user=SimpleNamespace(id=55))
    run(filter_handlers.give_filter_private(None, message))
    find.assert_not_awaited()


def test_non_admin_cannot_manage_group(monkeypatch):
    monkeypatch.setattr(filter_handlers, "is_user_authorized", AsyncMock(return_value=False))
    client = SimpleNamespace(get_chat_member=AsyncMock(
        return_value=SimpleNamespace(status=ChatMemberStatus.MEMBER)))
    assert run(filter_handlers._can_manage(client, 22, -100)) is False


def test_forged_connection_cannot_activate(monkeypatch):
    monkeypatch.setattr(connections_mdb, "all_connections", AsyncMock(
        return_value=["-100100"]))
    update = AsyncMock()
    monkeypatch.setattr(connections_mdb, "mycol",
                        SimpleNamespace(update_one=update))
    assert run(connections_mdb.make_active("22", "-100999")) is False
    update.assert_not_awaited()


def make_query(data, user_id=22, private=True):
    message = SimpleNamespace(
        chat=SimpleNamespace(type=ChatType.PRIVATE if private else ChatType.SUPERGROUP,
                             id=22 if private else -100),
        edit_text=AsyncMock(), delete=AsyncMock()
    )
    return SimpleNamespace(data=data, from_user=SimpleNamespace(id=user_id),
                           message=message, answer=AsyncMock())


def test_delete_connection_does_not_delete_filters(monkeypatch):
    removal = AsyncMock(return_value=True)
    monkeypatch.setattr(callbacks, "delete_connection", removal)
    q = make_query("deletecb:-100")
    run(callbacks.cb_handler(None, q))
    removal.assert_awaited_once_with(22, "-100")
    q.message.edit_text.assert_awaited_once()
    assert "filters were kept" in q.message.edit_text.await_args.args[0].lower()


def test_delete_connection_rejected_outside_private(monkeypatch):
    removal = AsyncMock(return_value=True)
    monkeypatch.setattr(callbacks, "delete_connection", removal)
    q = make_query("deletecb:-100", private=False)
    run(callbacks.cb_handler(None, q))
    removal.assert_not_awaited()


def test_destructive_confirmation_belongs_to_requester(monkeypatch):
    removal = AsyncMock()
    monkeypatch.setattr(callbacks, "del_all", removal)
    q = make_query("delallconfirm:-100:123", user_id=456)
    run(callbacks.cb_handler(None, q))
    removal.assert_not_awaited()
    q.answer.assert_awaited_once()

def test_filter_write_preserves_existing_document_fields(monkeypatch):
    collection = SimpleNamespace(update_one=AsyncMock())
    monkeypatch.setattr(filters_mdb, "group_collection", lambda gid: collection)
    assert run(filters_mdb.add_filter(-100, "hello", "Hi", "[]", None, []))
    data = collection.update_one.await_args.args[1]["$set"]
    assert set(data) == {"text", "reply", "btn", "file", "alert"}
    assert data["file"] == "None"
    assert data["btn"] == "[]"


def test_formatted_group_addition_is_preserved(monkeypatch):
    class DecoratedText(str):
        @property
        def html(self):
            return "/add hello <b>world</b>"

    monkeypatch.setattr(filter_handlers, "user_can_use_bot", AsyncMock(return_value=True))
    monkeypatch.setattr(filter_handlers, "_can_manage", AsyncMock(return_value=True))
    save = AsyncMock(return_value=True)
    monkeypatch.setattr(filter_handlers, "add_filter", save)
    monkeypatch.setattr(filter_handlers, "_save_user", AsyncMock())
    message = SimpleNamespace(
        text=DecoratedText("/add hello world"),
        from_user=SimpleNamespace(id=23),
        chat=SimpleNamespace(id=-100, type=ChatType.SUPERGROUP, title="Group"),
        reply_to_message=None,
        reply_text=AsyncMock(),
    )
    run(filter_handlers.addfilter(None, message))
    save.assert_awaited_once()
    assert save.await_args.args[2] == "<b>world</b>"


def test_cross_group_delete_confirmation_rejected(monkeypatch):
    delete = AsyncMock()
    monkeypatch.setattr(callbacks, "del_all", delete)
    query = make_query("delallconfirm:-100:22", user_id=22, private=False)
    query.message.chat.id = -999
    run(callbacks.cb_handler(None, query))
    delete.assert_not_awaited()


def test_valid_owner_delete_confirmation(monkeypatch):
    monkeypatch.setattr(callbacks, "_can_delete_all", AsyncMock(return_value=True))
    delete = AsyncMock()
    monkeypatch.setattr(callbacks, "del_all", delete)
    query = make_query("delallconfirm:-100:22", user_id=22, private=False)
    client = SimpleNamespace(get_chat=AsyncMock(return_value=SimpleNamespace(title="Group")))
    run(callbacks.cb_handler(client, query))
    delete.assert_awaited_once_with(query.message, -100, "Group")


def test_connection_switch_rejects_unauthorized_user(monkeypatch):
    monkeypatch.setattr(callbacks, "_can_manage", AsyncMock(return_value=False))
    change = AsyncMock()
    monkeypatch.setattr(callbacks, "make_active", change)
    query = make_query("connectcb:-100", user_id=22)
    run(callbacks.cb_handler(None, query))
    change.assert_not_awaited()


def test_corrupt_alert_payload_is_rejected(monkeypatch):
    monkeypatch.setattr(callbacks, "find_filter", AsyncMock(
        return_value=("text", "[]", "__import__('os').system('echo test')", "None")
    ))
    query = make_query("alertmessage:0:keyword", private=False)
    run(callbacks.cb_handler(None, query))
    assert "unavailable" in query.answer.await_args.args[0].lower()
