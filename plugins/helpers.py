import html
import re

from typing import List
from pyrogram.types import InlineKeyboardButton



BTN_URL_REGEX = re.compile(
    r"(\[([^\[]+?)\]\((buttonurl|buttonalert):(?:/{0,2})(.+?)(:same)?\))"
)

SMART_OPEN = "“"
SMART_CLOSE = "”"
QUOTE_PAIRS = {"'": "'", '"': '"', SMART_OPEN: SMART_CLOSE, "‘": "’"}


def _split_first_filter_name(text: str):
    """Return (name, remainder, remainder_start) from raw Telegram message text.

    Only a quote at the *start* of a name opens a quoted name. This preserves
    plain apostrophes in titles such as Misha's, and Windows-style backslashes.
    """
    index = 0
    while index < len(text) and text[index].isspace():
        index += 1
    if index == len(text):
        return "", "", index

    opening = text[index]
    closing = QUOTE_PAIRS.get(opening)
    name = []
    if closing:
        index += 1
        while index < len(text):
            char = text[index]
            if char == "\\" and index + 1 < len(text) and text[index + 1] in (
                    closing, "\\", "'", '"', "“", "”", "‘", "’"):
                name.append(text[index + 1])
                index += 2
            elif char == closing:
                index += 1
                if index < len(text) and not text[index].isspace():
                    raise ValueError("Add a space after the closing quote.")
                break
            else:
                name.append(char)
                index += 1
        else:
            raise ValueError("Unclosed quote in filter name.")
    else:
        while index < len(text) and not text[index].isspace():
            char = text[index]
            if (char == "\\" and index + 1 < len(text)
                    and (text[index + 1].isspace()
                         or text[index + 1] in QUOTE_PAIRS
                         or text[index + 1] == "\\")):
                index += 1
                char = text[index]
            name.append(char)
            index += 1

    while index < len(text) and text[index].isspace():
        index += 1
    return "".join(name).strip(), text[index:], index


def split_quotes(text: str) -> List[str]:
    """Legacy compatible list form for a single filter name and its content."""
    name, rest, _ = _split_first_filter_name(text)
    return [name] + ([rest] if rest else []) if name else []


def split_filter_names(text: str) -> List[str]:
    """Parse names for /del, supporting multiple quoted and unquoted names."""
    names = []
    while text.strip():
        name, text, _ = _split_first_filter_name(text)
        if not name:
            raise ValueError("Filter name cannot be empty.")
        names.append(name)
    return names


def _html_prefix_length(formatted: str, raw_prefix: str):
    """Locate the end of a *plain-text* prefix in Telegram's HTML rendering.

    Escaped entities may be written as &quot;, &#34;, &#x22;, &apos;, etc.
    Never unescape the response body, because it can contain HTML entities and
    text formatting we must preserve as-is.
    """
    position = 0
    raw_position = 0
    while raw_position < len(raw_prefix):
        if position >= len(formatted):
            return None
        if formatted[position] == "&":
            match = re.match(r"&(?:#[xX][0-9a-fA-F]+|#[0-9]+|[A-Za-z][A-Za-z0-9]+);", formatted[position:])
            if match:
                token = match.group()
                value = html.unescape(token)
                width = len(token)
            else:
                value = "&"
                width = 1
        else:
            value = formatted[position]
            width = 1
        if not raw_prefix.startswith(value, raw_position):
            return None
        raw_position += len(value)
        position += width
    return position


def split_filter_command(message_text):
    """Parse /add from raw text but preserve HTML styling in the response body."""
    raw = str(message_text or "")
    command = re.match(r"^\s*\S+\s+", raw)
    if command is None:
        return "", ""
    name, body, consumed = _split_first_filter_name(raw[command.end():])
    formatted = getattr(message_text, "html", None)
    if isinstance(formatted, str):
        offset = _html_prefix_length(formatted, raw[:command.end() + consumed])
        if offset is not None:
            body = formatted[offset:]
        else:
            # If the command itself was styled, preserve literal content safely.
            body = html.escape(body)
    return name, body

def parser(text, keyword):
    if "buttonalert" in text:
        text = (text.replace("\n", "\\n").replace("\t", "\\t"))
    buttons = []
    note_data = ""
    prev = 0
    i = 0
    alerts = []
    for match in BTN_URL_REGEX.finditer(text):
        # Check if btnurl is escaped
        n_escapes = 0
        to_check = match.start(1) - 1
        while to_check >= 0 and text[to_check] == "\\":
            n_escapes += 1
            to_check -= 1

        # if even, not escaped -> create button
        if n_escapes % 2 == 0:
            note_data += text[prev:match.start(1)]
            prev = match.end(1)
            if match.group(3) == "buttonalert":
                # create a thruple with button label, url, and newline status
                if bool(match.group(5)) and buttons:
                    buttons[-1].append(InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"alertmessage:{i}:{keyword}"
                    ))
                else:
                    buttons.append([InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"alertmessage:{i}:{keyword}"
                    )])
                i = i + 1
                alerts.append(match.group(4))
            else:
                if bool(match.group(5)) and buttons:
                    buttons[-1].append(InlineKeyboardButton(
                        text=match.group(2),
                        url=match.group(4).replace(" ", "")
                    ))
                else:
                    buttons.append([InlineKeyboardButton(
                        text=match.group(2),
                        url=match.group(4).replace(" ", "")
                    )])

        # if odd, escaped -> move along
        else:
            note_data += text[prev:to_check]
            prev = match.start(1) - 1
    else:
        note_data += text[prev:]

    return note_data, buttons, alerts

def remove_escapes(text: str) -> str:
    counter = 0
    res = ""
    is_escaped = False
    while counter < len(text):
        if is_escaped:
            res += text[counter]
            is_escaped = False
        elif text[counter] == "\\":
            is_escaped = True
        else:
            res += text[counter]
        counter += 1
    return res


def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'