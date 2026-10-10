
import os

from pymongo import MongoClient
from pymongo.errors import PyMongoError

_mongo_client = None
_database = None


def init_database():
    global _mongo_client, _database

    mongo_uri = os.getenv("MONGODB_URI")
    database_name = os.getenv("MONGODB_DB_NAME")

    if not mongo_uri or not database_name:
        raise RuntimeError(
            "MONGODB_URI and MONGODB_DB_NAME must be configured."
        )

    try:
        _mongo_client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=10000,
        )

        # Verify the Atlas connection before returning.
        _mongo_client.admin.command("ping")

        _database = _mongo_client[database_name]
        print("MongoDB Atlas connected successfully.")

        return _database

    except PyMongoError:
        if _mongo_client is not None:
            _mongo_client.close()

        _mongo_client = None
        _database = None

        raise RuntimeError(
            "Could not connect to MongoDB Atlas. "
            "Check your URI, database credentials, and IP access list."
        ) from None


def get_database():
    if _database is None:
        raise RuntimeError(
            "MongoDB is not initialized. Call init_database() first."
        )

    return _database


def close_database():
    global _mongo_client, _database

    if _mongo_client is not None:
        _mongo_client.close()

    _mongo_client = None
    _database = None
