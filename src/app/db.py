from __future__ import annotations

import os
from typing import Optional

from pymongo import MongoClient


def get_mongo_client() -> MongoClient:
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    username = os.getenv("MONGO_USER")
    password = os.getenv("MONGO_PASSWORD")
    auth_db = os.getenv("MONGO_AUTH_DB", "admin")

    if username and password:
        client = MongoClient(uri, username=username, password=password, authSource=auth_db)
    else:
        client = MongoClient(uri)
    return client


def get_collection(name: str):
    db_name = os.getenv("MONGO_DB", "tiktok_live")
    client = get_mongo_client()
    return client[db_name][name]
