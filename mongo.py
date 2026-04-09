"""MongoDB client wrapper.
"""
from __future__ import annotations
from typing import Optional
from pymongo import MongoClient
import os
from pathlib import Path
from dotenv import load_dotenv

_client: Optional[MongoClient] = None
_db = None

# Resolve the .env at the project root regardless of CWD
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def init_mongo() -> None:
    global _client, _db
    if _client is not None:
        return
    load_dotenv(dotenv_path=_ENV_PATH, override=True)
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("DB_NAME", "newsbot")
    _client = MongoClient(uri)
    _db = _client[db_name]


def get_db():
    if _db is None:
        init_mongo()
    return _db


def get_posts_collection():
    db = get_db()
    return db["posts"]


def get_users_collection():
    db = get_db()
    col = db["users"]
    # Ensure unique index on username (idempotent)
    col.create_index("username", unique=True, background=True)
    return col
