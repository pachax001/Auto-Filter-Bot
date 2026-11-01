"""Application and WZGram logging, including tracebacks in Docker and /log."""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(filename)s:%(lineno)d %(message)s"
root = logging.getLogger()
root.setLevel(logging.INFO)

# Avoid adding the same handlers if imported again.
if not any(getattr(handler, "_auto_filter_handler", False) for handler in root.handlers):
    formatter = logging.Formatter(FORMAT)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console._auto_filter_handler = True
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        os.getenv("BOT_LOG_FILE", "log.txt"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler._auto_filter_handler = True
    root.addHandler(file_handler)

# WZGram uses the 'pyrogram' logger internally.
logging.getLogger("pyrogram").setLevel(logging.INFO)
logger = logging.getLogger("auto_filter_bot")
