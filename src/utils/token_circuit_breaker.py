"""FinOps Token & Request-Density Circuit Breaker for First-Serving Porter (T108)."""

from collections import deque
from collections.abc import Callable
from datetime import datetime, timezone
import logging
import time
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from src.config import MongoConfig
from src.database.mongo_client.connection import MongoConnectionManager

logger = logging.getLogger(__name__)


class TokenLimitExceededError(Exception):
    """Raised when an LLM breaches cumulative token or sliding-window density caps."""


def _extract_token_count(response: LLMResult) -> int:
    """Extract total token usage across OpenAI/Groq llm_output, LangChain usage_metadata, or fallback."""
    llm_output = getattr(response, "llm_output", None)
    if isinstance(llm_output, dict):
        usage = llm_output.get("token_usage") or llm_output.get("usage_metadata")
        if isinstance(usage, dict):
            total = int(usage.get("total_tokens", 0) or 0)
            if total > 0:
                return total

    total_meta = 0
    fallback_chars = 0
    for gen_list in getattr(response, "generations", None) or []:
        for gen in gen_list:
            msg = getattr(gen, "message", None)
            meta = getattr(msg, "usage_metadata", None) if msg is not None else None
            if isinstance(meta, dict):
                total_meta += int(meta.get("total_tokens", 0) or 0)
            text = getattr(gen, "text", "") or ""
            fallback_chars += len(str(text))

    if total_meta > 0:
        return total_meta
    return max(1, fallback_chars // 4) if fallback_chars > 0 else 0


class TokenCircuitBreakerHandler(BaseCallbackHandler):
    """Halts runaway agent loops via cumulative budget + sliding-window density caps."""

    def __init__(
        self,
        max_tokens: int = 25000,
        *,
        max_tokens_per_minute: int = 30000,
        max_requests_per_minute: int = 20,
        window_seconds: float = 60.0,
        user_email: str = "system@localhost",
        session_id: str | None = None,
        clock_fn: Callable[[], float] | None = None,
    ) -> None:
        self.max_tokens = max_tokens
        self.max_tokens_per_minute = max_tokens_per_minute
        self.max_requests_per_minute = max_requests_per_minute
        self.window_seconds = window_seconds
        self.user_email = user_email
        self.session_id = session_id or "default"
        self._clock: Callable[[], float] = clock_fn or time.monotonic
        self.total_tokens_spent = 0
        self.successful_requests = 0
        self.tripped = False
        self._window_events: deque[tuple[float, int]] = deque()

    def _prune_window(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._window_events and self._window_events[0][0] < cutoff:
            self._window_events.popleft()

    def _record_trip_event(self, reason: str, window_tokens: int, window_reqs: int) -> None:
        """Persist a sanitized FinOps circuit-breaker trip into happenings (non-fatal)."""
        try:
            db = MongoConnectionManager.get_db()
            db[MongoConfig.FIRST_SERVING_HAPPENINGS_COLLECTION].insert_one(
                {
                    "session_id": self.session_id,
                    "user_email": self.user_email,
                    "timestamp": datetime.now(timezone.utc),
                    "event": "circuit_breaker_tripped",
                    "tool_name": "TokenCircuitBreakerHandler",
                    "reason": reason,
                    "total_tokens_spent": self.total_tokens_spent,
                    "window_tokens": window_tokens,
                    "window_requests": window_reqs,
                }
            )
        except Exception as exc:
            logger.warning("Could not persist circuit-breaker trip event: %s", exc)

    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any) -> None:
        """Enforce request-rate density BEFORE dispatching another LLM call."""
        _ = (serialized, prompts, kwargs)
        now = self._clock()
        self._prune_window(now)
        if len(self._window_events) >= self.max_requests_per_minute:
            window_tokens = sum(t for _, t in self._window_events)
            self.tripped = True
            reason = (
                f"Request-density limit exceeded: {len(self._window_events)} reqs "
                f"in {int(self.window_seconds)}s (max {self.max_requests_per_minute})."
            )
            self._record_trip_event(reason, window_tokens, len(self._window_events))
            raise TokenLimitExceededError(reason)

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Track cumulative & sliding-window token spend and trip on breach."""
        _ = kwargs
        tokens = _extract_token_count(response)
        now = self._clock()
        self._prune_window(now)
        self.total_tokens_spent += tokens
        self.successful_requests += 1
        self._window_events.append((now, tokens))

        window_tokens = sum(t for _, t in self._window_events)
        window_reqs = len(self._window_events)
        logger.debug(
            "LLM call complete: tokens=%d total=%d window_tokens=%d window_reqs=%d",
            tokens,
            self.total_tokens_spent,
            window_tokens,
            window_reqs,
        )

        if self.total_tokens_spent > self.max_tokens:
            self.tripped = True
            reason = (
                f"Agent trapped in hallucination loop. Exceeded API safety cap of "
                f"{self.max_tokens} tokens (used {self.total_tokens_spent})."
            )
            self._record_trip_event(reason, window_tokens, window_reqs)
            raise TokenLimitExceededError(reason)

        if window_tokens > self.max_tokens_per_minute:
            self.tripped = True
            reason = (
                f"Token-density limit exceeded: {window_tokens} tokens in "
                f"{int(self.window_seconds)}s (max {self.max_tokens_per_minute})."
            )
            self._record_trip_event(reason, window_tokens, window_reqs)
            raise TokenLimitExceededError(reason)

    def snapshot(self) -> dict[str, Any]:
        """Return current breaker telemetry for observability and testing."""
        self._prune_window(self._clock())
        return {
            "user_email": self.user_email,
            "session_id": self.session_id,
            "total_tokens_spent": self.total_tokens_spent,
            "successful_requests": self.successful_requests,
            "window_tokens": sum(t for _, t in self._window_events),
            "window_requests": len(self._window_events),
            "max_tokens": self.max_tokens,
            "max_tokens_per_minute": self.max_tokens_per_minute,
            "max_requests_per_minute": self.max_requests_per_minute,
            "tripped": self.tripped,
        }

    def reset(self) -> None:
        """Reset breaker counters for a fresh discrete run."""
        self.total_tokens_spent = 0
        self.successful_requests = 0
        self.tripped = False
        self._window_events.clear()
