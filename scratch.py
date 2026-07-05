from src.database.mongo_storage import SovereignMongoStorage
from src.config import MongoConfig
mongo = SovereignMongoStorage()
missing = mongo.db[MongoConfig.RAW_TIMESERIES_COLLECTION].count_documents({"metadata.user_email": {"$exists": False}})
print("Actually missing email:", missing)
if missing > 0:
    mongo.db[MongoConfig.RAW_TIMESERIES_COLLECTION].delete_many({"metadata.user_email": {"$exists": False}})
    print("Deleted orphan records.")
