import os
# Offline-only tests: the async MongoDB client is constructed but never connects.
os.environ.setdefault("TG_BOT_TOKEN", "123456:test")
os.environ.setdefault("API_ID", "12345")
os.environ.setdefault("API_HASH", "test-api-hash")
os.environ.setdefault("OWNER_ID", "1")
os.environ.setdefault("DATABASE_URI", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DATABASE_NAME", "FilterBotTestNeverConnected")
