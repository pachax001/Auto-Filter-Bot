FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /bot

COPY requirements.txt /bot/requirements.txt
RUN python -m pip install --no-cache-dir -r /bot/requirements.txt \
    && useradd --create-home --uid 10001 botuser

COPY --chown=botuser:botuser . /bot/
# WORKDIR may be root-owned; non-root logger and Telegram session need write access.
RUN chown botuser:botuser /bot
USER botuser

CMD ["python", "bot.py"]
