"""Tenant-scoped observability & provenance monitoring for First-Serving Porter (T108)."""

import datetime
import logging
import re
from typing import Any
import uuid

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from pymongo import ASCENDING, DESCENDING

from src.config import MongoConfig
from src.database.mongo_client.connection import MongoConnectionManager

logger = logging.getLogger(__name__)

_CID_PATTERN = re.compile(r"\[CID:([^\]]+)\]|correlation_id[\"']?\s*[:=]\s*[\"']?([a-zA-Z0-9\-_]+)")

TRACE_PROJECTION: dict[str, int] = {
    "_id": 0,
    "session_id": 1,
    "user_email": 1,
    "timestamp": 1,
    "event": 1,
    "token_usage": 1,  # nosec B105 - MongoDB field projection flag, not a secret
    "correlation_id": 1,
}

HAPPENING_PROJECTION: dict[str, int] = {
    "_id": 0,
    "session_id": 1,
    "user_email": 1,
    "timestamp": 1,
    "event": 1,
    "tool_name": 1,
    "reason": 1,
    "correlation_id": 1,
    "provenance": 1,
}


def ensure_observability_indexes(db: Any) -> None:
    """Ensure DESCENDING compound tenant indexes on traces & happenings collections."""
    try:
        db[MongoConfig.FIRST_SERVING_TRACES_COLLECTION].create_index(
            [("user_email", ASCENDING), ("timestamp", DESCENDING)],
            name="idx_traces_tenant_ts_desc",
        )
        db[MongoConfig.FIRST_SERVING_HAPPENINGS_COLLECTION].create_index(
            [("user_email", ASCENDING), ("timestamp", DESCENDING)],
            name="idx_happenings_tenant_ts_desc",
        )
    except Exception as exc:
        logger.warning("Observability index init skipped: %s", exc)


def fetch_recent_traces(db: Any, user_email: str, *, limit: int = 25) -> list[dict[str, Any]]:
    """Fetch projected recent trace records scoped strictly to user_email."""
    docs = (
        db[MongoConfig.FIRST_SERVING_TRACES_COLLECTION]
        .find({"user_email": user_email}, TRACE_PROJECTION)
        .sort("timestamp", DESCENDING)
        .limit(limit)
    )
    return [_serialize_doc(d) for d in docs]


def fetch_recent_happenings(db: Any, user_email: str, *, limit: int = 25) -> list[dict[str, Any]]:
    """Fetch projected recent tool/circuit-breaker happenings scoped strictly to user_email."""
    docs = (
        db[MongoConfig.FIRST_SERVING_HAPPENINGS_COLLECTION]
        .find({"user_email": user_email}, HAPPENING_PROJECTION)
        .sort("timestamp", DESCENDING)
        .limit(limit)
    )
    return [_serialize_doc(d) for d in docs]


def _serialize_doc(doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(doc)
    ts = out.get("timestamp")
    if isinstance(ts, datetime.datetime):
        out["timestamp"] = ts.isoformat()
    return out


class FirstServingMonitoringHandler(BaseCallbackHandler):
    """Logs tenant-scoped LLM traces, token usage, tool calls, and CID provenance."""

    def __init__(
        self,
        session_id: str | None = None,
        correlation_id: str | None = None,
        user_email: str = "system@localhost",
    ) -> None:
        self.session_id = session_id or str(uuid.uuid4())
        self.correlation_id = correlation_id
        self.user_email = user_email
        self.db = MongoConnectionManager.get_db()
        ensure_observability_indexes(self.db)
        self.traces_collection = self.db[MongoConfig.FIRST_SERVING_TRACES_COLLECTION]
        self.happenings_collection = self.db[MongoConfig.FIRST_SERVING_HAPPENINGS_COLLECTION]

    def _base_doc(self, event: str) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "session_id": self.session_id,
            "user_email": self.user_email,
            "timestamp": datetime.datetime.now(datetime.timezone.utc),
            "event": event,
        }
        if self.correlation_id:
            doc["correlation_id"] = self.correlation_id
        return doc

    def on_chat_model_start(
        self, serialized: dict[str, Any], messages: list[list[Any]], **kwargs: Any
    ) -> None:
        """Log chat model start into first_serving_traces."""
        _ = (serialized, kwargs)
        try:
            doc = self._base_doc("chat_model_start")
            doc["messages"] = [[getattr(m, "content", str(m)) for m in ml] for ml in messages]
            self.traces_collection.insert_one(doc)
        except Exception as exc:
            logger.error("Failed to log chat model start: %s", exc)

    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any) -> None:
        """Log prompt start into first_serving_traces."""
        _ = (serialized, kwargs)
        try:
            doc = self._base_doc("llm_start")
            doc["prompts"] = prompts
            self.traces_collection.insert_one(doc)
        except Exception as exc:
            logger.error("Failed to log LLM start: %s", exc)

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Log LLM completion and token usage into first_serving_traces."""
        _ = kwargs
        try:
            tokens = 0
            if isinstance(response.llm_output, dict):
                usage = response.llm_output.get("token_usage") or {}
                if isinstance(usage, dict):
                    tokens = int(usage.get("total_tokens", 0) or 0)
            generated = [
                g.text for gl in (getattr(response, "generations", None) or []) for g in gl
            ]
            doc = self._base_doc("llm_end")
            doc["token_usage"] = tokens
            doc["generated_texts"] = generated
            self.traces_collection.insert_one(doc)
        except Exception as exc:
            logger.error("Failed to log LLM end: %s", exc)

    def on_tool_start(self, serialized: dict[str, Any], input_str: str, **kwargs: Any) -> None:
        """Log tool invocation into first_serving_porter_happenings."""
        _ = kwargs
        try:
            doc = self._base_doc("tool_start")
            doc["tool_name"] = serialized.get("name", "UnknownTool")
            doc["tool_input"] = input_str
            self.happenings_collection.insert_one(doc)
        except Exception as exc:
            logger.error("Failed to log tool start: %s", exc)

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Log tool completion and extracted CID provenance into happenings."""
        try:
            tool_name = str(kwargs.get("name", "UnknownTool"))
            extracted = [
                m[0] or m[1]
                for m in (_CID_PATTERN.findall(output) if isinstance(output, str) else [])
                if (m[0] or m[1])
            ]
            doc = self._base_doc("tool_end")
            doc["tool_name"] = tool_name
            doc["tool_output"] = output
            if extracted:
                doc["provenance"] = {
                    "extracted_correlation_ids": extracted,
                    "description": f"Agent used {tool_name} referencing CID(s): {', '.join(extracted)}",
                }
            self.happenings_collection.insert_one(doc)
        except Exception as exc:
            logger.error("Failed to log tool end: %s", exc)
