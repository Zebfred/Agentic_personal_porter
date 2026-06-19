from pymongo import MongoClient
import os
import pprint

client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
db = client["porter_collections"]

cols = ["event_intentions", "event_actuals", "unified_events", "calendar_events_timeseries", "daily_categorized_events", "formatted_calendar_events", "raw_calendar_events"]

for col in cols:
    count = db[col].count_documents({})
    print(f"\n--- {col} --- count: {count}")
    if count > 0:
        doc = db[col].find_one()
        pprint.pprint(doc)

