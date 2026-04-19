import logging
import uuid
import datetime
from typing import Any, Dict, List, Optional
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from src.database.mongo_client.connection import MongoConnectionManager

logger = logging.getLogger(__name__)

class FirstServingMonitoringHandler(BaseCallbackHandler):
    """
    A unified Custom Callback Handler to actively log inputs, state metrics, token usage 
    and behavioral heuristics (tool calls) to MongoDB collections.
    """
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
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

            self.traces_collection.insert_one({
                "session_id": self.session_id,
                "timestamp": datetime.datetime.utcnow(),
                "event": "chat_model_start",
                "messages": msgs,
            })
        except Exception as e:
            logger.error(f"Failed to log chat model start to trace collection: {e}")

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Runs when the LLM begins execution."""
        try:
            self.traces_collection.insert_one({
                "session_id": self.session_id,
                "timestamp": datetime.datetime.utcnow(),
                "event": "llm_start",
                "prompts": prompts,
            })
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

            self.traces_collection.insert_one({
                "session_id": self.session_id,
                "timestamp": datetime.datetime.utcnow(),
                "event": "llm_end",
                "token_usage": tokens,
                "generated_texts": generated_texts
            })
        except Exception as e:
            logger.error(f"Failed to log LLM end to trace collection: {e}")

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """Runs when an agent invokes a tool."""
        try:
            tool_name = serialized.get("name", "UnknownTool")
            self.happenings_collection.insert_one({
                "session_id": self.session_id,
                "timestamp": datetime.datetime.utcnow(),
                "event": "tool_start",
                "tool_name": tool_name,
                "tool_input": input_str
            })
        except Exception as e:
            logger.error(f"Failed to log tool start to happenings collection: {e}")

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Runs when an agent tool completes."""
        try:
            # We also get tool name dynamically via kwargs if needed via 'name'
            tool_name = kwargs.get("name", "UnknownTool")
            self.happenings_collection.insert_one({
                "session_id": self.session_id,
                "timestamp": datetime.datetime.utcnow(),
                "event": "tool_end",
                "tool_name": tool_name,
                "tool_output": output
            })
        except Exception as e:
            logger.error(f"Failed to log tool end to happenings collection: {e}")
