from src.database.mongo_storage import SovereignMongoStorage
from src.config import MongoConfig
mongo = SovereignMongoStorage()
user_email = "zebfred22@gmail.com"
print("Intentions:", mongo.db["event_intentions"].count_documents({"user_id": user_email}))
print("Actuals:", mongo.db["event_actuals"].count_documents({"user_id": user_email}))
print("Unified:", mongo.db["unified_events"].count_documents({"user_id": user_email}))
print("Raw Timeseries staged:", mongo.db[MongoConfig.RAW_TIMESERIES_COLLECTION].count_documents({"metadata.user_email": user_email, "metadata.sync_status": "staged"}))
