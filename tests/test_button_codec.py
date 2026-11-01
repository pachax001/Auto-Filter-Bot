import ast
import json
import pytest

from wzgram.types import InlineKeyboardButton
from plugins.button_codec import _decode, serialize_buttons, deserialize_buttons


@pytest.mark.parametrize("value", [
    "[]", None, "None",
    "[[InlineKeyboardButton(text='Site', url='https://example.org')]]",
    "[[pyrogram.types.bots_and_keyboards.inline_keyboard_button.InlineKeyboardButton(text='Site', url='https://example.org')]]",
    "[[InlineKeyboardButton(text='Alert', callback_data='alertmessage:0:test')]]",
])
def test_existing_button_formats(value):
    result = deserialize_buttons(value)
    assert isinstance(result, list)
    assert _decode(serialize_buttons(value)) == _decode(value)


def test_new_button_format_is_json_and_not_executable():
    original = [[InlineKeyboardButton("URL", url="https://example.org")],
                [InlineKeyboardButton("Alert", callback_data="alertmessage:0:hello")]]
    encoded = serialize_buttons(original)
    assert isinstance(json.loads(encoded), list)
    decoded = deserialize_buttons(encoded)
    assert decoded[0][0].url == "https://example.org"
    assert decoded[1][0].callback_data == "alertmessage:0:hello"


@pytest.mark.parametrize("unsafe", [
    "[[__import__('os').system('echo unsafe')]]",
    "[[InlineKeyboardButton(text='X', url=__import__('os').getcwd())]]",
    "[[InlineKeyboardButton(text='X', url='javascript:alert(1)')]]",
    "[[InlineKeyboardButton(text='X', callback_data='x'*100)]]",
    "[[InlineKeyboardButton(text='X', __class__='something')]]",
    "[[os.system('anything')]]",
    '{"text": "bad"}',
    "{'foo':'bar'}",
])
def test_unsafe_legacy_and_json_data_rejected(unsafe):
    with pytest.raises((ValueError, SyntaxError, TypeError, RecursionError)):
        deserialize_buttons(unsafe)


def test_callback_limit_and_url_scheme():
    with pytest.raises(ValueError):
        serialize_buttons([[InlineKeyboardButton("Too long", callback_data="x"*65)]])
    with pytest.raises(ValueError):
        serialize_buttons([[InlineKeyboardButton("No", url="javascript:alert(1)")]])


def test_nested_empty_buttons_rejected():
    with pytest.raises(ValueError):
        deserialize_buttons("[[]]")


def test_invalid_json_objects_are_rejected():
    with pytest.raises(ValueError):
        deserialize_buttons(json.dumps([[{"text": "x", "url": "https://example.org",
                                        "callback_data": "alert:0:x"}]]))

def test_historical_telegram_url_shorthand():
    button = deserialize_buttons(
        "[[InlineKeyboardButton(text='Open', url='t.me/example')]]"
    )
    assert button[0][0].url == "https://t.me/example"
