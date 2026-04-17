import logging
from typing import Any, Dict, List
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)

class TokenLimitExceededError(Exception):
    """Exception explicitly raised when an LLM breaches the token tracking budget."""
    pass

class TokenCircuitBreakerHandler(BaseCallbackHandler):
    """
    A unified Custom Callback Handler to brutally sever an agent run if it begins an infinite hallucinated loop.
    Monitors all LLM tool calls/responses mapping token expenditure.
    """
    def __init__(self, max_tokens: int = 25000):
        self.max_tokens = max_tokens
        self.total_tokens_spent = 0
        self.successful_requests = 0

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Runs when the LLM begins execution."""
        pass

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Runs when the LLM finishes execution."""
        # Note: Depending on the provider (OpenAI vs Groq), token_usage keys might differ slightly.
        # This parses Groq/OpenAI generic output structure.
        if response.llm_output is not None and "token_usage" in response.llm_output:
            usage = response.llm_output["token_usage"]
            if isinstance(usage, dict):
                tokens = usage.get("total_tokens", 0)
                self.total_tokens_spent += tokens
                self.successful_requests += 1

                logger.debug(f"LLM Call Finished. Cost: {tokens}. Total Run Cost: {self.total_tokens_spent}")

                if self.total_tokens_spent > self.max_tokens:
                    logger.error(f"[CIRCUIT BROKEN] Agent exceeded {self.max_tokens} tokens! Total used: {self.total_tokens_spent}. Force halting the run loop.")
                    raise TokenLimitExceededError(f"Agent trapped in hallucination loop. Exceeded API safety cap of {self.max_tokens} tokens.")
        
    def reset(self):
        """Allows resetting the breaker for sequential discrete runs."""
        self.total_tokens_spent = 0
        self.successful_requests = 0
