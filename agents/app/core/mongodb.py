from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

client = AsyncIOMotorClient(settings.mongodb_uri)
database = client[settings.mongodb_database]


def get_collection(name: str):
    return database[name]
