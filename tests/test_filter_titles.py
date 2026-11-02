"""Parsing regression tests for quote-rich filter names and /add responses."""
import asyncio
from html import escape
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from wzgram.enums import ChatType, ParseMode

from plugins.helpers import split_quotes, split_filter_command, split_filter_names
from plugins import filters as filter_handlers


class TelegramText(str):
    """Emulates WZGram's HTML rendering of text with styled reply content."""

    def __new__(cls, plain, formatted=None):
        obj = super().__new__(cls, plain)
        obj.formatted = formatted if formatted is not None else escape(plain)
        return obj

    @property
    def html(self):
        return self.formatted


@pytest.mark.parametrize("command,keyword,body", [
    ('/add "Dive into You" Watch this', "Dive into You", "Watch this"),
    ('/add "Misha\'s car" Details', "Misha's car", "Details"),
    ("/add 'Misha\\'s car' Details", "Misha's car", "Details"),
    ('/add "The \\"Special\\" One" Details', 'The "Special" One', "Details"),
    ('/add “Dive into You” Details', "Dive into You", "Details"),
    ('/add ‘Misha’s car’ Details', "Misha’s car", "Details"),
    ("/add Misha's Details", "Misha's", "Details"),
    (r"/add C:\Movies Details", r"C:\Movies", "Details"),
    ('/add "C:\\Movies" Details', r"C:\Movies", "Details"),
    ('/add "He said \\"hi\\"" Hi', 'He said "hi"', "Hi"),
    ('/add "John & Jane" Details', "John & Jane", "Details"),
    ('/add "A < B" Details', "A < B", "Details"),
])
def test_keyword_parsing_from_html_escaped_commands(command, keyword, body):
    assert split_filter_command(TelegramText(command)) == (keyword, escape(body))


def test_preserves_formatted_reply_in_quoted_add():
    plain = '/add "Dive into You" Watch this'
    formatted = '/add &quot;Dive into You&quot; <b>Watch this</b>'
    assert split_filter_command(TelegramText(plain, formatted)) == (
        "Dive into You", "<b>Watch this</b>"
    )


def test_preserves_formatted_reply_after_apostrophe_in_name():
    plain = '/add "Misha\'s car" Watch this'
    formatted = '/add &quot;Misha&#x27;s car&quot; <i>Watch this</i>'
    assert split_filter_command(TelegramText(plain, formatted)) == (
        "Misha's car", "<i>Watch this</i>"
    )


def test_formatted_body_keeps_literal_html_entities_safe():
    plain = '/add "Title" <hello & world>'
    formatted = '/add &quot;Title&quot; &lt;hello &amp; world&gt;'
    assert split_filter_command(TelegramText(plain, formatted)) == (
        "Title", "&lt;hello &amp; world&gt;"
    )


@pytest.mark.parametrize("command", [
    '/add "Dive into You',
    "/add 'Misha\\'s car",
    '/add "Title"Suffix some text',
])
def test_invalid_quoting_is_rejected(command):
    with pytest.raises(ValueError):
        split_filter_command(TelegramText(command))


def test_empty_quoted_keyword_is_rejected():
    assert split_filter_command(TelegramText('/add "" Hello'))[0] == ""


def test_unquoted_and_quoted_delete_names():
    assert split_filter_names(r'''Dive "Dive into You" "Misha's car" "The \"Special\" One"''') == [
        "Dive", "Dive into You", "Misha's car", 'The "Special" One'
    ]
    assert split_filter_names("Misha's") == ["Misha's"]


def test_legacy_split_quotes_remains_compatible():
    assert split_quotes('"Dive into You" Hi') == ["Dive into You", "Hi"]
    assert split_quotes("plain Hi") == ["plain", "Hi"]


def run(coro):
    return asyncio.run(coro)


def make_group_message(text, source=None):
    return SimpleNamespace(
        text=text,
        from_user=SimpleNamespace(id=23),
        chat=SimpleNamespace(id=-100, type=ChatType.SUPERGROUP, title="K-Drama World Chat"),
        reply_to_message=source,
        reply_text=AsyncMock(),
    )


@pytest.mark.parametrize("keyword,command", [
    ("dive into you", '/add "Dive into You" <b>Content</b>'),
    ("misha's car", '/add "Misha\'s car" Content'),
    ('the "special" one', '/add "The \\"Special\\" One" Content'),
])
def test_add_handler_persists_full_keyword(monkeypatch, keyword, command):
    monkeypatch.setattr(filter_handlers, "user_can_use_bot", AsyncMock(return_value=True))
    monkeypatch.setattr(filter_handlers, "_can_manage", AsyncMock(return_value=True))
    save = AsyncMock(return_value=True)
    monkeypatch.setattr(filter_handlers, "add_filter", save)
    monkeypatch.setattr(filter_handlers, "_save_user", AsyncMock())
    message = make_group_message(TelegramText(command))
    run(filter_handlers.addfilter(None, message))
    save.assert_awaited_once()
    assert save.await_args.args[1] == keyword
    confirmation = message.reply_text.await_args
    assert escape(keyword) in confirmation.args[0]
    assert confirmation.kwargs["parse_mode"] == ParseMode.HTML


def test_add_handler_preserves_formatted_body(monkeypatch):
    monkeypatch.setattr(filter_handlers, "user_can_use_bot", AsyncMock(return_value=True))
    monkeypatch.setattr(filter_handlers, "_can_manage", AsyncMock(return_value=True))
    save = AsyncMock(return_value=True)
    monkeypatch.setattr(filter_handlers, "add_filter", save)
    monkeypatch.setattr(filter_handlers, "_save_user", AsyncMock())
    message = make_group_message(TelegramText(
        '/add "Dive into You" formatted body',
        '/add &quot;Dive into You&quot; <b>formatted</b> body',
    ))
    run(filter_handlers.addfilter(None, message))
    assert save.await_args.args[1] == "dive into you"
    assert save.await_args.args[2] == "<b>formatted</b> body"


def test_invalid_add_name_never_writes_mongodb(monkeypatch):
    monkeypatch.setattr(filter_handlers, "user_can_use_bot", AsyncMock(return_value=True))
    monkeypatch.setattr(filter_handlers, "_can_manage", AsyncMock(return_value=True))
    save = AsyncMock()
    monkeypatch.setattr(filter_handlers, "add_filter", save)
    message = make_group_message(TelegramText('/add "Unclosed name content'))
    run(filter_handlers.addfilter(None, message))
    save.assert_not_awaited()
    assert "unclosed" in message.reply_text.await_args.args[0].lower()


def test_delete_handler_supports_multiword_and_escaped_quotes(monkeypatch):
    monkeypatch.setattr(filter_handlers, "user_can_use_bot", AsyncMock(return_value=True))
    monkeypatch.setattr(filter_handlers, "_can_manage", AsyncMock(return_value=True))
    monkeypatch.setattr(filter_handlers, "record_user_activity", AsyncMock())
    remove = AsyncMock()
    monkeypatch.setattr(filter_handlers, "delete_filter", remove)
    message = make_group_message(TelegramText(
        '/del "Dive into You" "Misha\'s car" "The \\"Special\\" One"'
    ))
    run(filter_handlers.deletefilter(None, message))
    assert [call.args[1] for call in remove.await_args_list] == [
        "dive into you", "misha's car", 'the "special" one'
    ]
