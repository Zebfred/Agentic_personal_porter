import sys
sys.path.append('.')
from src.database.mongo_storage import SovereignMongoStorage
import json
from bson import json_util

mongo = SovereignMongoStorage()
print("Sample Unified:")
doc = mongo.db['unified_events'].find_one()
print(json.dumps(doc, default=json_util.default, indent=2))
