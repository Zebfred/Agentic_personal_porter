"""
Runs identical test cases across multiple LLM providers (via AgentLLMConfig)
to evaluate latency, accuracy, and token usage for the categorizer node.

Updated 2026-05-10: Added Tier 1 Gemini API models and cost tracking.
"""

import re
import time
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.utils.llm_factory import AgentLLMConfig
from src.agents.porter_manager import CategorizationResult
from src.agents.evals.trajectory_tests import get_categorization_test_cases
from langchain_core.prompts import ChatPromptTemplate
from rich.console import Console
from rich.table import Table

console = Console()

# ── Cost estimates per 1M tokens (USD) ────────────────────────────────
# Source: Vertex AI pricing page, May 2026
COST_PER_1M_TOKENS: Dict[str, Dict[str, float]] = {
    # Gemini API models (per-token pricing) — GA
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    "gemini-2.5-pro": {"input": 1.25, "output": 5.00},
    # Gemini API models (per-token pricing) — Preview (3.x)
    "gemini-3-flash-preview": {"input": 0.50, "output": 3.00},
    "gemini-3.1-flash-lite": {"input": 0.25, "output": 1.50},
    "gemini-3.1-pro-preview": {"input": 2.00, "output": 12.00},
    # Groq models (free tier / paid tier varies, estimate conservatively)
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
}

# ── Model Definitions ──────────────────────────────────────────────────
# Primary source: scratch/verified_candidates.json (built by script 04).
# Fallback: hardcoded GA-only models known to work.

MODELS_TIER1_GEMINI: List[AgentLLMConfig] = [
    AgentLLMConfig(provider="vertex", model="gemini-2.5-flash"),
    AgentLLMConfig(provider="vertex", model="gemini-2.5-pro"),
]

MODELS_BASELINE_GROQ: List[AgentLLMConfig] = [
    AgentLLMConfig(provider="groq", model="llama-3.1-8b-instant"),
    AgentLLMConfig(provider="groq", model="llama-3.3-70b-versatile"),
]

def _load_verified_candidates() -> Optional[List[AgentLLMConfig]]:
    """Load model list from verified_candidates.json if it exists.

    Returns:
        List of AgentLLMConfig from the verified file, or None if not found.
    """
    import json
    candidates_path = root / "scratch" / "verified_candidates.json"
    if not candidates_path.exists():
        return None

    try:
        with open(candidates_path) as f:
            data = json.load(f)

        configs = []
        for entry in data.get("harness_config", []):
            configs.append(AgentLLMConfig(
                provider=entry["provider"],
                model=entry["model"],
            ))

        if configs:
            console.print(
                f"[dim]Loaded {len(configs)} verified models from "
                f"{candidates_path.name}[/dim]"
            )
        return configs if configs else None

    except Exception as e:
        console.print(f"[yellow]Warning: Could not load verified candidates: {e}[/yellow]")
        return None

def _estimate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """Estimates the cost of a single invocation in USD."""
    rates = COST_PER_1M_TOKENS.get(model_name)
    if not rates:
        return 0.0
    input_cost = (input_tokens / 1_000_000) * rates["input"]
    output_cost = (output_tokens / 1_000_000) * rates["output"]
    return input_cost + output_cost

def _get_rate_limit_sleep(provider: str) -> float:
    """Returns the sleep interval between calls to respect rate limits.

    Args:
        provider: The LLM provider name.

    Returns:
        Sleep duration in seconds.
    """
    if provider == "groq":
        # Groq free tier limits to ~30 RPM
        return 2.5
    # Vertex AI — use 3s delay to avoid 429 RESOURCE_EXHAUSTED
    return 3.0

def run_categorization_eval(
    include_gemini: bool = True,
    include_groq: bool = True,
    use_verified: bool = True,
) -> List[Dict[str, Any]]:
    """Runs the categorization evaluation across configured models.

    Args:
        include_gemini: Whether to include Tier 1 Gemini API models.
        include_groq: Whether to include baseline Groq models.
        use_verified: If True, loads from verified_candidates.json first.

    Returns:
        A list of result dictionaries with accuracy, latency, and cost.
    """
    test_cases = get_categorization_test_cases()

    models_to_test: List[AgentLLMConfig] = []

    # Try loading from verified candidates first
    if use_verified:
        verified = _load_verified_candidates()
        if verified:
            # Apply provider filters if specified
            for cfg in verified:
                if cfg.provider == "groq" and not include_groq:
                    continue
                if cfg.provider in ("vertex", "google_genai") and not include_gemini:
                    continue
                models_to_test.append(cfg)

    # Fallback to hardcoded lists if no verified candidates loaded
    if not models_to_test:
        console.print("[dim]Using hardcoded model lists (no verified candidates)[/dim]")
        if include_groq:
            models_to_test.extend(MODELS_BASELINE_GROQ)
        if include_gemini:
            models_to_test.extend(MODELS_TIER1_GEMINI)

    if not models_to_test:
        console.print("[red]No models selected for evaluation.[/red]")
        return []

    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are 'The Categorizer'. You are no longer a deep contextual "
            "philosophical coach. Your sole responsibility is to evaluate daily "
            "events and definitively map them to exactly one of the designated "
            "9 Hero Pillars (e.g. Health, Wealth, Core). Fast, objective, and strict.\n\n"
            "Goal: Perform strict, low-latency categorization of Intention vs. "
            "Actual events across the 9 Core Pillars."
        )),
        ("user", (
            "1. Analyze the following FRONTEND PAYLOAD quickly submitted by {username}:\n"
            "'{journal_entry}'\n\n"
            "2. Contextualize it against his last 5 Calendar Events:\n{actuals_str}\n\n"
            "3. Identify EXACTLY which of the 9 Hero pillars this combination represents: "
            "(1. Core Identity, 2. Mind, 3. Body/Health, 4. Heart/Social, 5. Wealth/Career, "
            "6. Community, 7. Leisure, 8. Spirit, 9. Duty).\n"
            "Expected output: A single structured JSON block."
        ))
    ])

    results_summary: List[Dict[str, Any]] = []

    for config in models_to_test:
        console.print(
            f"\n[bold blue]━━━ Evaluating: {config.provider} / {config.model} ━━━[/bold blue]"
        )

        try:
            llm = config.get_chat_model().with_structured_output(CategorizationResult)
            chain = prompt | llm
        except Exception as e:
            console.print(f"[red]Failed to initialize model: {e}[/red]")
            results_summary.append({
                "model": config.model,
                "provider": config.provider,
                "accuracy": "INIT_FAIL",
                "avg_latency": "N/A",
                "total_cost_usd": "N/A",
                "error": str(e),
            })
            continue

        success_count = 0
        total_latency = 0.0
        total_input_tokens = 0
        total_output_tokens = 0
        errors: List[str] = []
        sleep_interval = _get_rate_limit_sleep(config.provider)

        for case in test_cases:
            start_time = time.time()
            try:
                res = chain.invoke({
                    "username": "Hero",
                    "journal_entry": case["journal_entry"],
                    "actuals_str": case["actuals_str"]
                })
                end_time = time.time()
                latency = end_time - start_time
                total_latency += latency

                # Attempt to extract token counts from response metadata
                # LangChain models expose this via response_metadata on the raw AIMessage
                if hasattr(res, 'response_metadata'):
                    meta = res.response_metadata
                    total_input_tokens += meta.get('usage', {}).get('prompt_tokens', 0)
                    total_output_tokens += meta.get('usage', {}).get('completion_tokens', 0)

                # Check accuracy — normalize by stripping the number prefix.
                # Expected format: "3. Body/Health" or "Body/Health"
                # Model may return: \"Body/Health\" or \"3. Body/Health\"
                expected_raw = case["expected_pillar"].lower().strip()
                got_raw = res.Pillar.lower().strip()

                # Strip leading "N. " prefix from both (e.g., "3. body/health" → "body/health")
                expected_norm = re.sub(r'^\d+\.\s*', '', expected_raw)
                got_norm = re.sub(r'^\d+\.\s*', '', got_raw)

                is_correct = expected_norm == got_norm or expected_norm in got_norm or got_norm in expected_norm
                if is_correct:
                    success_count += 1
                    console.print(
                        f"  [green]✓ {case['id']} passed ({latency:.2f}s) "
                        f"→ {res.Pillar} [Confidence: {res.Confidence_Score}][/green]"
                    )
                else:
                    console.print(
                        f"  [red]✗ {case['id']} failed ({latency:.2f}s) "
                        f"→ Expected: {case['expected_pillar']}, Got: {res.Pillar}[/red]"
                    )

            except Exception as e:
                end_time = time.time()
                latency = end_time - start_time
                total_latency += latency
                error_msg = str(e)[:80]
                errors.append(f"{case['id']}: {error_msg}")
                console.print(f"  [red]✗ {case['id']} error ({latency:.2f}s): {error_msg}[/red]")

            time.sleep(sleep_interval)

        # Calculate totals
        num_cases = len(test_cases)
        avg_latency = total_latency / num_cases if num_cases else 0
        total_cost = _estimate_cost(config.model, total_input_tokens, total_output_tokens)

        results_summary.append({
            "model": config.model,
            "provider": config.provider,
            "accuracy": f"{success_count}/{num_cases}",
            "avg_latency": f"{avg_latency:.2f}s",
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_cost_usd": f"${total_cost:.6f}",
            "errors": errors if errors else None,
        })

    return results_summary

if __name__ == "__main__":
    from src.utils.path_utils import load_env_vars
    load_env_vars()

    console.print("\n[bold]Starting Categorization Evaluation Harness...[/bold]\n")
    results = run_categorization_eval()

    table = Table(title="Model Evaluation Summary")
    table.add_column("Provider", style="cyan")
    table.add_column("Model", style="magenta")
    table.add_column("Accuracy", style="green")
    table.add_column("Avg Latency", style="yellow")
    table.add_column("Tokens (In/Out)", style="blue")
    table.add_column("Est. Cost", style="red")

    for r in results:
        tokens = f"{r.get('total_input_tokens', '?')}/{r.get('total_output_tokens', '?')}"
        table.add_row(
            r["provider"], r["model"], r["accuracy"],
            r["avg_latency"], tokens, r["total_cost_usd"]
        )

    console.print(table)
