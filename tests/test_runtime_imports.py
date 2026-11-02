def test_bot_entrypoint_imports():
    from bot import main
    assert callable(main)


def test_runtime_uses_single_async_client():
    from config import client
    from pymongo import AsyncMongoClient
    assert isinstance(client, AsyncMongoClient)
