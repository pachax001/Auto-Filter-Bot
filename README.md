# Auto-Filter-Bot

Telegram filter bot using [WZGram](https://wzgram.com/) and the native
asynchronous [PyMongo driver](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/).

This branch repairs existing behavior and security issues. It adds no bot
commands, no database collections, and no schema migration.

## Existing behavior

- Group administrators can add and remove keyword filters, including saved
  media, URL buttons and alert buttons.
- Authorized users can use the existing administrator override.
- Users can connect eligible groups and manage filters from private chat.
- Deleting a **personal connection** does not delete shared group filters.
- Deleting all group filters remains an explicit privileged action with
  user- and group-bound confirmation.
- Existing filter documents and their legacy button representations remain
  readable. Malformed button records are never executed.

## Install and run with Docker Compose

1. Clone `https://github.com/rumalg123/Auto-Filter-Bot.git`.
2. Copy `sample_config.env` to `config.env` and configure the credentials.
3. Start with `docker compose up -d --build`.
4. Inspect logs with `docker compose logs -f bot`.

The container environment is supplied by `env_file`. `config.env`,
session files, and local data are excluded from Docker build context so
credentials are not embedded into the image.

## Configuration

| Key | Purpose |
| --- | --- |
| `API_ID` / `API_HASH` | Telegram API credentials from my.telegram.org |
| `TG_BOT_TOKEN` | Telegram bot token |
| `DATABASE_URI` | MongoDB connection URI |
| `DATABASE_NAME` | Existing MongoDB database name, defaults to `FilterBot` |
| `OWNER_ID` | Telegram owner ID |
| `AUTH_USERS` | Comma-separated authorized Telegram IDs |
| `IS_PUBLIC` | Initial public-access mode when no saved setting exists |
| `SAVE_USER` | Enable/disable saving user activity, `yes` or `no` |
| `ADD_FILTER_CMD`, `DELETE_FILTER_CMD`, `DELETE_ALL_CMD` | Filter commands |
| `CONNECT_COMMAND`, `DISCONNECT_COMMAND`, `CONNECTIONS_COMMAND` | Connection commands |
| `VIEW_FILTERS_COMMAND` | List filters command |

Allow only known deployment IPs in MongoDB Atlas network access. Do not
use unrestricted `0.0.0.0/0` access for production.

## Before deploying to an existing database

Read [the database and security repair notes](docs/security-repair.md).
Back up the database, restore to a separate test database, and verify
existing filters there. No scripts should perform bulk rewrites of old
button values. The bot parses legacy values in memory without executing them.

## Offline regression checks

```bash
python -m pip install -r requirements.txt pytest
python -m compileall -q .
python -m pytest -q
```

These tests do not send Telegram messages and do not modify MongoDB.
A separate staging validation is required for Telegram and database integration.

## Credits

Originally based on [Unlimited-Filter-Bot](https://github.com/TroJanzHEX/Unlimited-Filter-Bot).
