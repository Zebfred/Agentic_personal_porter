import time
import logging
from typing import Callable, Dict, Optional
from functools import wraps

from src.database.mongo_storage import SovereignMongoStorage

logger = logging.getLogger(__name__)

class FinOpsTracer:
    """
    A telemetry wrapper for LangGraph/ADK agent executions to monitor FinOps (API spend) and performance.
    Saves traces to the MongoDB first_serving_traces collection.
    """
    def __init__(self, agent_name: str, username: str = "Hero"):
        self.agent_name = agent_name
        self.username = username
        self.storage = SovereignMongoStorage()
        self.start_time = None

    def start_trace(self):
        self.start_time = time.time()
        logger.info(f"[FinOps] Trace started for agent: {self.agent_name}")

    def end_trace(self, status: str = "success", token_count: int = 0, error_msg: Optional[str] = None, extra_metadata: Optional[Dict] = None):
        if not self.start_time:
            logger.warning("[FinOps] end_trace called before start_trace")
            return

        duration_ms = int((time.time() - self.start_time) * 1000)

        trace_data = {
            "agent_name": self.agent_name,
            "username": self.username,
            "duration_ms": duration_ms,
            "token_count": token_count,
            "status": status,
        }

        if error_msg:
            trace_data["error_msg"] = error_msg

        if extra_metadata:
            trace_data["metadata"] = extra_metadata

        try:
            trace_id = self.storage.save_telemetry_trace(trace_data)
            logger.info(f"[FinOps] Trace saved for {self.agent_name} (Status: {status}, Tokens: {token_count}, Time: {duration_ms}ms) -> ID: {trace_id}")
        except Exception as e:
            logger.error(f"[FinOps] Failed to save trace for {self.agent_name}: {e}")

def with_finops_trace(agent_name: str):
    """
    Decorator to automatically wrap a function with FinOps telemetry.
    Assumes the function either returns normally (success) or raises an Exception (failure).
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract username from kwargs if present, else default
            username = kwargs.get("username", "Hero")
            if not username and args and isinstance(args[0], dict):
                username = args[0].get("username", "Hero")

            tracer = FinOpsTracer(agent_name=agent_name, username=username)
            tracer.start_trace()

            try:
                result = func(*args, **kwargs)
                tracer.end_trace(status="success")
                return result
            except Exception as e:
                tracer.end_trace(status="failure", error_msg=str(e))
                raise e
        return wrapper
    return decorator
