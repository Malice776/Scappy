import os
import hashlib
from typing import Any, Dict
from pymongo import MongoClient
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
        num = d.get("EnterpriseNumber")
        src = d.get("source")
        
        if not num:
            spider.logger.warning(f"Item sans EnterpriseNumber: {d}")
            return item
        
        # Préparation de l'update selon la source
        if src == "ejustice":
            pubs = d.get("ejustice_publications", [])
            for pub in pubs:
                if pub.get("detail_url") or pub.get("reference"):
                    # Générer un hash unique
                    hash_content = f"{pub.get('detail_url', '')}{pub.get('reference', '')}{pub.get('date', '')}"
                    pub["_hash"] = hashlib.md5(hash_content.encode()).hexdigest()
            if pubs:
                update = {
                    "$addToSet": {
                        "ejustice_publications": {
                            "$each": [pub for pub in pubs if pub.get("_hash")]
                        }
                    },
                    "$setOnInsert": {"_id": num}
                }
            else:
                update = {
                    "$setOnInsert": {
                        "_id": num,
                        "ejustice_publications": []
                    }
                }
        else:
            # fallback générique
            update = {
                "$set": d,
                "$setOnInsert": {"_id": num}
            }
        
        # Exécuter l'upsert
        try:
            result = self.col.update_one({"_id": num}, update, upsert=True)
            if result.upserted_id:
                spider.logger.info(f"Nouveau document créé pour {num}")
            elif result.modified_count > 0:
                spider.logger.info(f"Document mis à jour pour {num}")
            else:
                spider.logger.debug(f"Aucune modification pour {num}")
        except Exception as e:
            spider.logger.error(f"Erreur MongoDB pour {num}: {e}")
        
        return item
