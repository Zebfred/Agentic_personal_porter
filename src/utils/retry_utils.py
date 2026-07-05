import logging
from typing import Any, Callable, TypeVar, Coroutine
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception,
    RetryCallState
)
from src.utils.token_circuit_breaker import TokenLimitExceededError

logger = logging.getLogger(__name__)

T = TypeVar("T")

def is_retryable_exception(exception: BaseException) -> bool:
    """
    Determine if the given exception should trigger a retry.
    We do NOT retry TokenLimitExceededError because it implies an infinite logic loop.
    We DO retry 429s, timeout errors, or general API faults.
    """
    if isinstance(exception, TokenLimitExceededError):
        logger.error(f"[RETRY ABORTED] Token circuit breaker tripped. Not retrying.")
        return False
    
    err_str = str(exception).lower()
    
    # Identify typical rate limit / transient errors
    if "429" in err_str or "too many requests" in err_str or "rate limit" in err_str or "resource exhausted" in err_str:
        return True
        
    # Default to True for generic exceptions just in case it's a transient network fault
    return True

def before_sleep_log(retry_state: RetryCallState):
    """Callback to log before sleeping for a retry."""
    ex = retry_state.outcome.exception()
    logger.warning(
        f"[API RETRY] Network or Rate Limit error encountered. "
        f"Attempt {retry_state.attempt_number} failed. Retrying in {retry_state.next_action.sleep}s... "
        f"Error: {ex}"
    )

# Decorator for ASYNC functions (like run_adk)
def with_llm_retry(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
    """Decorator to apply exponential backoff retries to async LLM calls."""
    decorator = retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        retry=retry_if_exception(is_retryable_exception),
        before_sleep=before_sleep_log,
        reraise=True
    )
    return decorator(func)

# Helper function for SYNC executions (like chain.invoke)
def invoke_with_retry(callable_fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Helper to execute synchronous functions (like .invoke()) with exponential backoff retries."""
    
    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        retry=retry_if_exception(is_retryable_exception),
        before_sleep=before_sleep_log,
        reraise=True
    )
    def _execute():
        return callable_fn(*args, **kwargs)
        
    return _execute()
