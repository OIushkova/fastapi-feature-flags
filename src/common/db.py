from motor.motor_asyncio import AsyncIOMotorClient

from src.settings import settings


_mongo_client = None


def get_mongo_client():
    global _mongo_client
    if not _mongo_client:
        _mongo_client = AsyncIOMotorClient(settings.MONGODB_CONNECTION_URL)

    return _mongo_client
