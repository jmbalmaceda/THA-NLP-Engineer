"""MongoDB-backed menu provider.

Expected document schema in the collection (one document per menu item):

{
    "id": "classic_burger",
    "name": "Classic Burger",
    "base_price": 8.50,
    "options": {
        "size": {
            "type": "single_choice",
            "required": true,
            "choices": ["regular", "large"],
            "default": "regular",
            "price_modifier": {"regular": 0, "large": 2.00}
        }
    },
    "extras": [
        {"id": "cheese", "price": 1.00}
    ]
}
"""

import os

from pymongo import MongoClient

from menu import ExtraSpec, MenuItem, OptionSpec


class MongoDBMenuProvider:
    """Loads the menu from a MongoDB collection at call time."""

    def __init__(
        self,
        uri: str | None = None,
        db_name: str | None = None,
        collection_name: str | None = None,
    ):
        self.uri = uri or os.environ["MONGODB_URI"]
        self.db_name = db_name or os.getenv("MONGODB_DB", "food_ordering")
        self.collection_name = collection_name or os.getenv("MONGODB_COLLECTION", "menu")

    def load(self) -> dict[str, MenuItem]:
        client: MongoClient = MongoClient(self.uri)
        try:
            collection = client[self.db_name][self.collection_name]
            return {
                doc["id"]: self._doc_to_menu_item(doc)
                for doc in collection.find({}, {"_id": 0})
            }
        finally:
            client.close()

    @staticmethod
    def _doc_to_menu_item(doc: dict) -> MenuItem:
        options = {
            name: OptionSpec(
                type=spec["type"],
                required=spec["required"],
                choices=spec["choices"],
                default=spec.get("default"),
                price_modifier=spec.get("price_modifier", {}),
            )
            for name, spec in doc.get("options", {}).items()
        }
        extras = [
            ExtraSpec(id=e["id"], price=e["price"])
            for e in doc.get("extras", [])
        ]
        return MenuItem(
            id=doc["id"],
            name=doc["name"],
            base_price=doc["base_price"],
            options=options,
            extras=extras,
        )
