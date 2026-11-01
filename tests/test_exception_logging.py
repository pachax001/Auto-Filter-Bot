"""Exceptions must leave a useful traceback in the logger, never in Telegram."""
import ast
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from helpers.error_handling import log_handler_errors
from helpers import user_activity
from database import filters_mdb, connections_mdb



def run(awaitable):
    import asyncio
    return asyncio.run(awaitable)


def test_handler_error_logs_real_exception_and_safe_reply(caplog):
    async def fail(_client, _update):
        raise RuntimeError("Unexpected Telegram RPC failure")

    wrapped = log_handler_errors("test:fail")(fail)
    update = SimpleNamespace(
        from_user=SimpleNamespace(id=123),
        chat=SimpleNamespace(id=-999),
        reply_text=AsyncMock()
    )
    with caplog.at_level(logging.ERROR):
        assert run(wrapped(None, update)) is None
    assert any(
        record.exc_info is not None
        and record.exc_info[0] is RuntimeError
        and "user_id=123" in record.getMessage()
        and "chat_id=-999" in record.getMessage()
        for record in caplog.records
    )
    update.reply_text.assert_awaited_once()
    assert "Unexpected Telegram" not in update.reply_text.await_args.args[0]


def test_handler_notification_failure_is_also_logged(caplog):
    async def fail(_client, _update):
        raise OSError("MongoDB timeout")

    wrapped = log_handler_errors("test:failure_notification")(fail)
    update = SimpleNamespace(
        from_user=SimpleNamespace(id=12),
        chat=SimpleNamespace(id=-123),
        reply_text=AsyncMock(side_effect=ValueError("Reply not allowed"))
    )
    with caplog.at_level(logging.ERROR):
        run(wrapped(None, update))
    error_types = [record.exc_info[0] for record in caplog.records if record.exc_info]
    assert OSError in error_types
    assert ValueError in error_types


def test_user_activity_error_logs_traceback_without_interrupting_flow(monkeypatch, caplog):
    monkeypatch.setattr(user_activity, "SAVE_USER", "yes")
    monkeypatch.setattr(
        user_activity, "add_or_update_user",
        AsyncMock(side_effect=RuntimeError("database unavailable"))
    )
    update = SimpleNamespace(
        from_user=SimpleNamespace(id=5, username=None, first_name="Test",
                                  last_name=None, dc_id=None),
        chat=SimpleNamespace(id=-100)
    )
    with caplog.at_level(logging.ERROR):
        run(user_activity.record_user_activity(update))
    assert any(
        record.exc_info and record.exc_info[0] is RuntimeError
        and "user_id=5" in record.getMessage()
        for record in caplog.records
    )


def test_filter_write_failure_logs_real_traceback(monkeypatch, caplog):
    failing = SimpleNamespace(
        update_one=AsyncMock(side_effect=ConnectionError("simulated MongoDB failure"))
    )
    monkeypatch.setattr(filters_mdb, "group_collection", lambda _id: failing)
    with caplog.at_level(logging.ERROR):
        ok = run(filters_mdb.add_filter(-100, "keyword", "reply", [], None, []))
    assert ok is False
    assert any(
        record.exc_info and record.exc_info[0] is ConnectionError
        and "group_id=-100" in record.getMessage()
        for record in caplog.records
    )


def test_connection_insert_failure_does_not_look_like_a_duplicate(monkeypatch, caplog):
    collection = SimpleNamespace(
        find_one=AsyncMock(return_value=None),
        insert_one=AsyncMock(side_effect=ConnectionError("simulated write failure")),
    )
    monkeypatch.setattr(connections_mdb, "mycol", collection)
    with caplog.at_level(logging.ERROR), pytest.raises(ConnectionError):
        run(connections_mdb.add_connection("-100", "20"))
    assert any(
        record.exc_info and record.exc_info[0] is ConnectionError
        for record in caplog.records
    )


def test_no_bare_except_blocks_in_runtime():
    root = Path(__file__).resolve().parents[1]
    for location in ("plugins", "database", "helpers"):
        for path in (root / location).glob("*.py"):
            parsed = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(parsed):
                if isinstance(node, ast.ExceptHandler):
                    assert node.type is not None, f"{path}: bare except is not allowed"
