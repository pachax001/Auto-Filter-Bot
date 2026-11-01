"""Log unexpected handler exceptions with full tracebacks and safe context."""
from functools import wraps
from helpers.logger import logger


def log_handler_errors(action):
    def decorate(handler):
        @wraps(handler)
        async def wrapped(client, update):
            try:
                return await handler(client, update)
            except Exception:
                message = getattr(update, "message", None) or update
                chat = getattr(message, "chat", None)
                user = getattr(update, "from_user", None)
                logger.exception(
                    "Unhandled %s error user_id=%s chat_id=%s",
                    action,
                    getattr(user, "id", None),
                    getattr(chat, "id", None),
                )
                # Keep raw stack traces in logs, never send internals to Telegram.
                try:
                    if hasattr(update, "answer"):
                        await update.answer("Something went wrong. Check bot logs.", show_alert=True)
                    elif hasattr(update, "reply_text"):
                        await update.reply_text(
                            "Something went wrong. Check bot logs.", quote=True
                        )
                except Exception:
                    logger.exception(
                        "Could not send failure notification for %s user_id=%s chat_id=%s",
                        action, getattr(user, "id", None), getattr(chat, "id", None),
                    )
                return None
        return wrapped
    return decorate
