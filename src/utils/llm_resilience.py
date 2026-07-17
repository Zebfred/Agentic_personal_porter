"""
Centralized LLM Resilience Factory — Three-Tier Fallback with Circuit Breaking.

Provides a single function to create a LangChain ChatModel with:
  Tier 1: Groq Llama 3.3 70b (fast, rate-limited)
  Tier 2: Gemini 2.5 Flash (fast, high TPM)
  Tier 3: Gemini 2.5 Pro (expensive, unlimited)

Usage:
    from src.utils.llm_resilience import get_resilient_llm
    llm = get_resilient_llm(task="categorizer")
"""
import logging
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel

from src.utils.llm_factory import AgentLLMConfig
from src.utils.token_circuit_breaker import TokenCircuitBreakerHandler

logger = logging.getLogger(__name__)

# Default model configurations for the three tiers
TIER_1_CONFIG = AgentLLMConfig(
    provider="groq",
    model="llama-3.3-70b-versatile",
    temperature=0.0,
    max_tokens=4096
)

TIER_2_CONFIG = AgentLLMConfig(
    provider="google_genai",
    model="gemini-2.5-flash",
    temperature=0.0,
    max_tokens=4096
)

TIER_3_CONFIG = AgentLLMConfig(
    provider="google_genai",
    model="gemini-2.5-pro",
    temperature=0.0,
    max_tokens=4096
)


def get_resilient_llm(
    task: str = "default",
    temperature: float = 0.0,
    max_tokens: int = 4096,
    token_budget: int = 25000,
    verbose: bool = False,
    callbacks: Optional[list] = None,
) -> BaseChatModel:
    """
    Returns a three-tier fallback LLM with token circuit breaking.

    When Tier 1 (Groq) returns a 429 or fails, LangChain automatically
    falls through to Tier 2 (Gemini Flash), then Tier 3 (Gemini Pro).

    Args:
        task: Descriptive name for logging (e.g. 'categorizer', 'reflection').
        temperature: Sampling temperature.
        max_tokens: Maximum output tokens.
        token_budget: Max total tokens before circuit breaker trips.
        verbose: Enable verbose LangChain logging.
        callbacks: Additional LangChain callbacks to attach.

    Returns:
        A BaseChatModel with three-tier fallback + circuit breaking.
    """
    # Build circuit breaker callback
    circuit_breaker = TokenCircuitBreakerHandler(max_tokens=token_budget)
    all_callbacks = [circuit_breaker]
    if callbacks:
        all_callbacks.extend(callbacks)

    # Override temperature/max_tokens on each tier
    tier_1 = TIER_1_CONFIG.model_copy(update={"temperature": temperature, "max_tokens": max_tokens})
    tier_2 = TIER_2_CONFIG.model_copy(update={"temperature": temperature, "max_tokens": max_tokens})
    tier_3 = TIER_3_CONFIG.model_copy(update={"temperature": temperature, "max_tokens": max_tokens})

    try:
        primary = tier_1.get_chat_model(verbose=verbose, callbacks=all_callbacks)
        fallback_flash = tier_2.get_chat_model(verbose=verbose, callbacks=all_callbacks)
        fallback_pro = tier_3.get_chat_model(verbose=verbose, callbacks=all_callbacks)

        resilient_llm = primary.with_fallbacks([fallback_flash, fallback_pro])

        logger.info(
            f"[LLM RESILIENCE] Built 3-tier chain for '{task}': "
            f"{tier_1.model} -> {tier_2.model} -> {tier_3.model} "
            f"(budget={token_budget} tokens)"
        )
        return resilient_llm

    except Exception as e:
        logger.error(f"[LLM RESILIENCE] Failed to build primary chain for '{task}': {e}")
        # Emergency fallback — try just Gemini Flash directly
        logger.warning(f"[LLM RESILIENCE] Falling back to Gemini Flash only for '{task}'")
        return tier_2.get_chat_model(verbose=verbose, callbacks=all_callbacks)
