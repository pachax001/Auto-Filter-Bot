"""Safe storage for filter buttons, including the historical Python repr format.

The existing 'btn' MongoDB field remains a string. New writes use JSON.
Legacy repr values are parsed as syntax trees, never executed.
"""
import ast
import json
from urllib.parse import urlparse

from wzgram.types import InlineKeyboardButton

FIELDS = ("url", "callback_data", "switch_inline_query",
          "switch_inline_query_current_chat", "user_id")
MAX_STORED_LENGTH = 20000


def _validate(item):
    if not isinstance(item, dict) or set(item) - ({"text"} | set(FIELDS)):
        raise ValueError("Unsupported button format")
    text = item.get("text")
    if not isinstance(text, str) or not text or len(text) > 256:
        raise ValueError("Invalid button label")
    available = [(key, item[key]) for key in FIELDS if item.get(key) is not None]
    if len(available) != 1:
        raise ValueError("Exactly one button action is required")
    key, value = available[0]
    if key == "user_id":
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError("Invalid user ID")
    elif not isinstance(value, str):
        raise ValueError("Invalid button action")
    elif key == "callback_data" and len(value.encode("utf-8")) > 64:
        raise ValueError("Callback data exceeds Telegram limit")
    elif key == "url":
        url = urlparse(value)
        if url.scheme not in ("http", "https", "tg") or not url.netloc:
            raise ValueError("Unsupported button URL")
    return {"text": text, key: value}


def _legacy_button(node):
    if isinstance(node, ast.Dict):
        item = ast.literal_eval(node)
        return _validate(item)
    if not isinstance(node, ast.Call) or node.keywords is None:
        raise ValueError("Legacy button is not a constructor")
    parts = []
    func = node.func
    while isinstance(func, ast.Attribute):
        parts.insert(0, func.attr)
        func = func.value
    if not isinstance(func, ast.Name):
        raise ValueError("Unknown legacy constructor")
    parts.insert(0, func.id)
    if parts[-1] != "InlineKeyboardButton" or parts[0] not in (
            "InlineKeyboardButton", "pyrogram", "wzgram"):
        raise ValueError("Unknown legacy constructor")
    if len(node.args) > 1:
        raise ValueError("Unexpected positional arguments")
    item = {}
    if node.args:
        item["text"] = ast.literal_eval(node.args[0])
    for keyword in node.keywords:
        if keyword.arg is None or keyword.arg in item:
            raise ValueError("Invalid legacy button keyword")
        value = ast.literal_eval(keyword.value)
        if value is not None:
            item[keyword.arg] = value
    return _validate(item)


def _normalize(buttons):
    if not isinstance(buttons, list) or len(buttons) > 30:
        raise ValueError("Invalid keyboard rows")
    result = []
    total = 0
    for row in buttons:
        if not isinstance(row, (list, tuple)) or not row or len(row) > 8:
            raise ValueError("Invalid keyboard row")
        converted = []
        for button in row:
            if isinstance(button, dict):
                item = button
            else:
                item = {"text": getattr(button, "text", None)}
                for name in FIELDS:
                    value = getattr(button, name, None)
                    if value is not None:
                        item[name] = value
            converted.append(_validate(item))
            total += 1
            if total > 100:
                raise ValueError("Too many buttons")
        result.append(converted)
    return result


def _decode(value):
    if value is None or value == "None" or value == "[]":
        return []
    if isinstance(value, list):
        return _normalize(value)
    if not isinstance(value, str) or len(value) > MAX_STORED_LENGTH:
        raise ValueError("Invalid stored keyboard")
    try:
        parsed = json.loads(value)
    except (ValueError, TypeError):
        tree = ast.parse(value, mode="eval").body
        if not isinstance(tree, ast.List) or len(tree.elts) > 30:
            raise ValueError("Invalid legacy keyboard")
        parsed = []
        for row in tree.elts:
            if not isinstance(row, (ast.List, ast.Tuple)):
                raise ValueError("Invalid legacy row")
            parsed.append([_legacy_button(node) for node in row.elts])
    return _normalize(parsed)


def serialize_buttons(value):
    if value is None:
        return "[]"
    normalized = _decode(value) if isinstance(value, str) else _normalize(value)
    return json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))


def deserialize_buttons(value):
    return [
        [InlineKeyboardButton(**item) for item in row]
        for row in _decode(value)
    ]
