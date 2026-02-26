"""Seed the MongoDB menu collection with all current menu items.

Usage:
    python scripts/seed_mongodb.py

Reads MONGODB_URI, MONGODB_DB, MONGODB_COLLECTION from .env (or environment).
Drops and recreates the collection on every run (idempotent).
"""

import sys
from pathlib import Path

# Allow imports from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import os

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING

from menu import MENU

load_dotenv(Path(__file__).parent.parent / ".env")

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "food_ordering")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "menu")


def menu_item_to_doc(item) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "base_price": item.base_price,
        "options": {
            name: {
                "type": spec.type,
                "required": spec.required,
                "choices": spec.choices,
                "default": spec.default,
                "price_modifier": spec.price_modifier,
            }
            for name, spec in item.options.items()
        },
        "extras": [
            {"id": extra.id, "price": extra.price}
            for extra in item.extras
        ],
    }


def seed() -> None:
    print(f"Connecting to {MONGODB_URI} ...")
    client: MongoClient = MongoClient(MONGODB_URI)

    try:
        db = client[MONGODB_DB]
        col = db[MONGODB_COLLECTION]

        col.drop()
        col.create_index([("id", ASCENDING)], unique=True)

        docs = [menu_item_to_doc(item) for item in MENU.values()]
        result = col.insert_many(docs)

        print(f"Inserted {len(result.inserted_ids)} menu items into {MONGODB_DB}.{MONGODB_COLLECTION}.")
        for doc in docs:
            print(f"  - [{doc['id']}] {doc['name']}  ${doc['base_price']:.2f}")
    finally:
        client.close()


if __name__ == "__main__":
    seed()
