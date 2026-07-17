import logging
import re
import uuid
import datetime
from typing import Any, Dict, List, Optional
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from src.database.mongo_client.connection import MongoConnectionManager

logger = logging.getLogger(__name__)

# Pattern to extract correlation IDs from tool output text
_CID_PATTERN = re.compile(r"\[CID:([^\]]+)\]|correlation_id[\"']?\s*[:=]\s*[\"']?([a-zA-Z0-9\-_]+)")


class FirstServingMonitoringHandler(BaseCallbackHandler):
    """
    A unified Custom Callback Handler to actively log inputs, state metrics, token usage 
    and behavioral heuristics (tool calls) to MongoDB collections.
    
    Supports provenance tracking: when a correlation_id is provided (or extracted from
    tool outputs), it logs the full lineage chain from Frontend -> Mongo -> VectorDB -> Agent.
    """
    def __init__(self, session_id: Optional[str] = None, correlation_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.correlation_id = correlation_id
        self.db = MongoConnectionManager.get_db()
        self.traces_collection = self.db["first_serving_traces"]
        self.happenings_collection = self.db["first_serving_porter_happenings"]

    def on_chat_model_start(
        self, serialized: Dict[str, Any], messages: List[List[Any]], **kwargs: Any
    ) -> None:
        """Runs when a chat model begins execution."""
        try:
            # Safely extract message content
            msgs = []
            for m_list in messages:
                msgs.append([getattr(m, "content", str(m)) for m in m_list])

            doc = {
                "session_id": self.session_id,
                "timestamp": datetime.datetime.now(datetime.timezone.utc),
                "event": "chat_model_start",
                "messages": msgs,
            }
            if self.correlation_id:
                doc["correlation_id"] = self.correlation_id

            self.traces_collection.insert_one(doc)
        except Exception as e:
            logger.error(f"Failed to log chat model start to trace collection: {e}")

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Runs when the LLM begins execution."""
        try:
            doc = {
                "session_id": self.session_id,
                "timestamp": datetime.datetime.now(datetime.timezone.utc),
                "event": "llm_start",
                "prompts": prompts,
            }
            if self.correlation_id:
                doc["correlation_id"] = self.correlation_id

            self.traces_collection.insert_one(doc)
        except Exception as e:
            logger.error(f"Failed to log LLM start to trace collection: {e}")

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Runs when the LLM finishes execution."""
        try:
            tokens = 0
            if response.llm_output is not None and "token_usage" in response.llm_output:
                usage = response.llm_output["token_usage"]
                if isinstance(usage, dict):
                    tokens = usage.get("total_tokens", 0)

            # Extract generated string if available
            generated_texts = []
            if getattr(response, "generations", None):
                for generation_list in response.generations:
                    for generation in generation_list:
                        generated_texts.append(generation.text)

            doc = {
                "session_id": self.session_id,
                "timestamp": datetime.datetime.now(datetime.timezone.utc),
                "event": "llm_end",
                "token_usage": tokens,
                "generated_texts": generated_texts
            }
            if self.correlation_id:
                doc["correlation_id"] = self.correlation_id

            self.traces_collection.insert_one(doc)
        except Exception as e:
            logger.error(f"Failed to log LLM end to trace collection: {e}")

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """Runs when an agent invokes a tool."""
        try:
            tool_name = serialized.get("name", "UnknownTool")
            doc = {
                "session_id": self.session_id,
                "timestamp": datetime.datetime.now(datetime.timezone.utc),
                "event": "tool_start",
                "tool_name": tool_name,
                "tool_input": input_str
            }
            if self.correlation_id:
                doc["correlation_id"] = self.correlation_id

            self.happenings_collection.insert_one(doc)
        except Exception as e:
            logger.error(f"Failed to log tool start to happenings collection: {e}")

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """
        Runs when an agent tool completes.
        Extracts correlation IDs from tool output for provenance logging.
        """
        try:
            tool_name = kwargs.get("name", "UnknownTool")

            # Extract correlation IDs from the tool output text
            extracted_cids = []
            if isinstance(output, str):
                matches = _CID_PATTERN.findall(output)
                for m in matches:
                    cid = m[0] or m[1]  # Either [CID:x] group or key=value group
                    if cid:
                        extracted_cids.append(cid)

            doc = {
                "session_id": self.session_id,
                "timestamp": datetime.datetime.now(datetime.timezone.utc),
                "event": "tool_end",
                "tool_name": tool_name,
                "tool_output": output
            }
            if self.correlation_id:
                doc["correlation_id"] = self.correlation_id

            # Log provenance when correlation IDs are found in tool output
            if extracted_cids:
                doc["provenance"] = {
                    "extracted_correlation_ids": extracted_cids,
                    "description": (
                        f"Agent used {tool_name} and retrieved data originating from "
                        f"correlation_id(s): {', '.join(extracted_cids)}"
                    )
                }
                logger.info(
                    f"[PROVENANCE] {tool_name} returned data from CID(s): {', '.join(extracted_cids)}"
                )

            self.happenings_collection.insert_one(doc)
        except Exception as e:
            logger.error(f"Failed to log tool end to happenings collection: {e}")

