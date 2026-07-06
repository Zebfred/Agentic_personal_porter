"""
Category mapping constants.

Lazy-loaded from MongoDB on first access to avoid module-level
MongoClient connections at import time (which blocks app startup
and leaks connections in test/CLI contexts).
"""
from src.utils.logging_config import setup_logger

logger = setup_logger(__name__)

# Sentinel to detect first access
_CATEGORY_MAPPING_CACHE = None


def get_category_mapping() -> dict:
    """
    Lazily load the category mapping from MongoDB with local file fallback.

    Returns the mapping on first call and caches it for subsequent calls.
    This replaces the previous module-level MongoClient instantiation that
    leaked connections and slowed imports.
    """
    global _CATEGORY_MAPPING_CACHE
    if _CATEGORY_MAPPING_CACHE is not None:
        return _CATEGORY_MAPPING_CACHE

    from pathlib import Path
    import json
    from pymongo import MongoClient
    from src.config import MongoConfig

    root_dir = Path(__file__).resolve().parent.parent
    empty_fallback = {
        "intent_to_actual_mapping": {},
        "actual_categorization_with_keywords": {},
        "colors": {},
    }

    try:
        client = MongoClient(MongoConfig.MONGO_URI, serverSelectionTimeoutMS=2000)
        db = client[MongoConfig.DB_NAME]
        # Artifact name is stored as 'category_mapping' without '.json' in MongoDB
        doc = db["hero_artifacts"].find_one(
            {"artifact_name": "category_mapping", "username": "system"}, {"_id": 0}
        )
        if not doc:
            # Fallback to any user's category mapping (e.g. single-tenant / personal setup)
            doc = db["hero_artifacts"].find_one(
                {"artifact_name": "category_mapping"}, {"_id": 0}
            )

        if doc and "data" in doc:
            _CATEGORY_MAPPING_CACHE = doc["data"]
            logger.info(
                f"Successfully loaded category mapping from MongoDB "
                f"(user: {doc.get('username', 'system')})."
            )
            return _CATEGORY_MAPPING_CACHE

        # Fallback to local files
        auth_file = root_dir / ".auth" / "category_mapping.json"
        example_file = root_dir / "data" / "category_mapping.example.json"

        for filepath in [auth_file, example_file]:
            if filepath.exists():
                try:
                    with open(filepath, "r") as f:
                        _CATEGORY_MAPPING_CACHE = json.load(f)
                    logger.info(
                        f"Loaded category mapping from local fallback file: {filepath}"
                    )
                    return _CATEGORY_MAPPING_CACHE
                except Exception as file_err:
                    logger.warning(
                        f"Error reading local category mapping fallback file "
                        f"{filepath}: {file_err}"
                    )

        logger.warning(
            "category_mapping artifact not found in MongoDB or local files. "
            "Using empty fallback."
        )
        _CATEGORY_MAPPING_CACHE = empty_fallback

    except Exception as e:
        logger.error(f"Error loading category mapping: {e}")
        _CATEGORY_MAPPING_CACHE = empty_fallback

    return _CATEGORY_MAPPING_CACHE


# Backward-compatible alias for callers that reference the module-level name.
# Accessing this property triggers lazy loading on first use.
class _LazyMapping:
    """Proxy that defers MongoDB access until a value is actually read."""
    def __getitem__(self, key):
        return get_category_mapping()[key]
    def __contains__(self, key):
        return key in get_category_mapping()
    def __iter__(self):
        return iter(get_category_mapping())
    def __len__(self):
        return len(get_category_mapping())
    def __bool__(self):
        return bool(get_category_mapping())
    def __eq__(self, other):
        return get_category_mapping() == other
    def get(self, key, default=None):
        return get_category_mapping().get(key, default)
    def keys(self):
        return get_category_mapping().keys()
    def values(self):
        return get_category_mapping().values()
    def items(self):
        return get_category_mapping().items()
    def __repr__(self):
        return repr(get_category_mapping())

loaded = False
ACTUAL_CATEGORY_MAPPING = _LazyMapping()
                    logger.warning(f"Error reading local category mapping fallback file {filepath}: {file_err}")

        if not loaded:
            logger.warning("category_mapping artifact not found in MongoDB or local files. Using empty fallback.")
            ACTUAL_CATEGORY_MAPPING = {"intent_to_actual_mapping": {}, "actual_categorization_with_keywords": {}, "colors": {}}
except Exception as e:
    logger.error(f"Error loading category mapping: {e}")
    ACTUAL_CATEGORY_MAPPING = {"intent_to_actual_mapping": {}, "actual_categorization_with_keywords": {}, "colors": {}}
