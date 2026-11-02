from plugins.helpers import parser


def test_escaped_markup_does_not_create_button():
    text, buttons, alerts = parser(r"\[Open](buttonurl://t.me/example)", "keyword")
    assert buttons == []
    assert "[Open]" in text
    assert alerts == []


def test_buttons_can_share_row():
    text, buttons, alerts = parser(
        "[First](buttonurl://t.me/first) [Second](buttonurl://t.me/second:same)",
        "keyword"
    )
    assert len(buttons) == 1
    assert len(buttons[0]) == 2
    assert alerts == []
