import os
from typing import Any, Dict
from pymongo import MongoClient, UpdateOne
from scrapy import Item
from dotenv import load_dotenv

load_dotenv()

class MongoUpsertPipeline:
    def open_spider(self, spider):
        self.client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
        db_name = os.getenv("DB_NAME", "kbo_tp")
        col_name = os.getenv("COLLECTION_NAME", "entreprises")
        self.col = self.client[db_name][col_name]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item: Dict[str, Any] | Item, spider):
        d = dict(item)
        num = d.get("ondernemingsnummer")
        src = d.get("source")

        update = {}
        if src == "kbo":
            update = {"$set": {"kbo": d.get("kbo", {})}, "$setOnInsert": {"_id": num}}
        elif src == "ejustice":
            update = {"$addToSet": {"ejustice_publications": {"$each": d.get("ejustice_publications", [])}},
                      "$setOnInsert": {"_id": num}}
        elif src == "nbb":
            update = {"$addToSet": {"nbb_depots": {"$each": d.get("nbb_depots", [])}},
                      "$setOnInsert": {"_id": num}}
        else:
            update = {"$set": d, "$setOnInsert": {"_id": num}}

        self.col.update_one({"_id": num}, update, upsert=True)
        return item