"""
Orchestration Eval Harness — tests the First-Serving Porter's tool-routing
accuracy across multiple LLM models using mock tool stubs.

Mock tools have identical names, type signatures, and docstrings to the real
Porter tools but return static strings. This lets us inspect the LLM's
*tool call decisions* (which tool, what arguments) without hitting real DBs.

Metrics scored per model:
  - Tool Selection Accuracy: did the model pick the right tool? (binary)
  - Argument Accuracy: did it extract the right parameters? (fuzzy substring)
  - Latency: time from invocation to first tool call
  - Token Usage: estimated from response metadata
"""

import time
from typing import List, Dict, Any, Optional

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from src.utils.llm_factory import AgentLLMConfig
from src.agents.evals.trajectory_tests import get_routing_test_cases

from rich.console import Console

console = Console()

# ── Cost estimates per 1M tokens (USD) ────────────────────────────────
COST_PER_1M_TOKENS: Dict[str, Dict[str, float]] = {
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    "gemini-2.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-3.1-pro-preview": {"input": 2.00, "output": 12.00},
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
}

# ── Mock Tool Stubs ───────────────────────────────────────────────────
# These mirror the real tools in first_serving_porter.py exactly —
# same names, same docstrings — but return canned static responses.

@tool
def route_to_subagent(agent_name: str, task_description: str) -> str:
    """declare intent to route tasks to sub-agents, enabling transparency logging on the UI.
    agent_name MUST be one of: 'GTKY Librarian', 'Inventory Curator', 'Socratic Mirror'.
    task_description MUST be a detailed description of what the sub-agent should do.
    """
    return f"[MOCK] Routed to {agent_name}: '{task_description}'"

@tool
def update_artifact(artifact_name: str, new_content_summary: str) -> str:
    """declares intent to update a json artifact (like hero_origin.json or hero_ambition.json) with new content.
    The GTKY Identity Architect will receive this ping to queue a permanent file modification.
    """
    return f"[MOCK] Queued update for {artifact_name}: '{new_content_summary}'"

@tool
def scan_origin_story() -> str:
    """Use this to comprehensively scan the user's origin story for missing gaps (especially from their teenage and secondary education years).
    This tool returns 3 targeted interview questions you should ask the user to help fill in their timeline via the frontend UI.
    """
    return "[MOCK] Found 3 gaps: teenage years, college transition, first career move."

@tool
def weaviate_hybrid_search(query: str, pillar: str = "Daily Reflection") -> str:
    """Use this to fetch exact journal entries and calendar events mapped to the 9 life pillars.
    Pass in a robust query string and the specific pillar (e.g. 'Social Goal', 'Career Goal', 'Health Goal') to hybrid match.
    """
    return f"[MOCK] 5 results for '{query}' under pillar '{pillar}'."

@tool
def chroma_vibe_check(query: str) -> str:
    """Use this to conceptually verify large, philosophical trends or Origin Story metrics of the User.
    Pass in a natural language query exploring the overarching vibe/sentiment without strict keyword matching.
    """
    return f"[MOCK] Vibe check for '{query}': overall positive trend, 3 conceptual matches."

@tool
def fetch_unverified_audits() -> str:
    """Use this to pull any categorized events that the human has not verified yet.
    You will use this to generate the presentation bundle for the Verification Dashboard.
    """
    return "[MOCK] Found 7 unverified events awaiting human review."

@tool
def consult_time_keeper(date_iso: str) -> str:
    """Use this to consult the Temporal Specialist Agent (Time Keeper) regarding exact schedule realities.
    Pass in a strict ISO string (e.g., '2026-04-17') to get a summary of what actually happened on that day.
    """
    return f"[MOCK] Day summary for {date_iso}: 3 meetings, 2 focus blocks, 1 break."

MOCK_TOOLS = [
    route_to_subagent,
    update_artifact,
    scan_origin_story,
    weaviate_hybrid_search,
    chroma_vibe_check,
    fetch_unverified_audits,
    consult_time_keeper,
]

# ── Porter System Prompt (mirrors first_serving_porter.py) ────────────
PORTER_SYSTEM_PROMPT = """I. Role Identity
You are the First_Serving Porter, the Chief of Staff and primary orchestrator of the Agentic Porter Ecosystem. Your sole mission is to serve as the bridge between the User's Hero Intent (stored in the Neo4j Identity Graph) and the Ground Truth (actual time and action data).

II. Operational Context
You operate under the Sovereign Data Protocol. This means:
- You enforce a Strict Managerial protocol. You do not do heavy data scraping yourself, you delegate to the Audit Inspector and Time Keeper tools.
- The User's Origin Story and Core Principles are the ultimate source of truth.
- You must never make a recommendation that contradicts these nodes without explicit User sign-off.
- You have real-time access to Two Vector Databases:
    1. Weaviate (Hybrid Keyword database storing Journal/Calendar stats tagged by Pillars)
    2. Chroma (Conceptual database storing unstructured 'Vibe' notes and deep reflections).

III. Current Protocol Context
Hero Name: EvalUser
Active Intentions: Establish performance baselines, achieve Mach4 usability
Active Principles: Data sovereignty, minimal friction, honest self-assessment

IV. Artifact References
Ambition Snapshot: Write a book by end of year, build Agentic Porter to production
Core Detriments: Analysis paralysis, over-engineering before baseline usability
"""

def _get_rate_limit_sleep(provider: str) -> float:
    """Returns sleep duration between cases to respect rate limits.

    ReAct agents make multiple LLM calls per test case (reasoning + tool call
    + response), so we need more headroom than single-shot prompts.
    """
    if provider == "groq":
        return 3.0
    # Vertex AI / Google GenAI — ReAct agents are multi-call per case
    return 5.0

def _estimate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """Estimates cost of a single invocation in USD."""
    rates = COST_PER_1M_TOKENS.get(model_name)
    if not rates:
        return 0.0
    return (input_tokens / 1_000_000) * rates["input"] + \
           (output_tokens / 1_000_000) * rates["output"]

def _extract_tool_calls(messages: List[Any]) -> List[Dict[str, Any]]:
    """Extracts tool call information from the message sequence.

    Returns:
        List of dicts with 'tool_name' and 'tool_args' keys.
    """
    calls = []
    for msg in messages:
        if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                calls.append({
                    "tool_name": tc.get("name", ""),
                    "tool_args": tc.get("args", {}),
                })
    return calls

def _check_tool_selection(
    tool_calls: List[Dict[str, Any]],
    expected_tool: str,
) -> bool:
    """Checks if the expected tool was called.

    For multi-step cases (expected_tool == '__multi__'), any 2+ tool calls pass.
    """
    if expected_tool == "__multi__":
        return len(tool_calls) >= 2

    return any(tc["tool_name"] == expected_tool for tc in tool_calls)

def _check_argument_accuracy(
    tool_calls: List[Dict[str, Any]],
    expected_args: Dict[str, str],
) -> bool:
    """Checks if expected argument substrings appear in tool call args.

    Each expected_args key is an argument name, and the value is a substring
    that must appear in the actual argument value (case-insensitive).
    Returns True if all expected args are satisfied by at least one tool call.
    """
    if not expected_args:
        return True  # No args to check

    for arg_name, expected_substr in expected_args.items():
        found = False
        for tc in tool_calls:
            actual_value = str(tc["tool_args"].get(arg_name, "")).lower()
            if expected_substr.lower() in actual_value:
                found = True
                break
        if not found:
            return False

    return True

def run_orchestration_eval(
    models: Optional[List[AgentLLMConfig]] = None,
    single_model: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Runs the orchestration eval across configured models.

    Args:
        models: Optional list of AgentLLMConfig to test. If None, uses defaults.
        single_model: If provided, only test the model matching this name.

    Returns:
        List of result dicts with accuracy, latency, and cost per model.
    """
    test_cases = get_routing_test_cases()

    if models is None:
        models = [
            AgentLLMConfig(provider="google_genai", model="gemini-2.5-pro"),
            AgentLLMConfig(provider="google_genai", model="gemini-2.5-flash"),
        ]

    if single_model:
        models = [m for m in models if m.model == single_model]
        if not models:
            console.print(f"[red]No model found matching '{single_model}'[/red]")
            return []

    results_summary: List[Dict[str, Any]] = []

    for config in models:
        console.print(
            f"\n[bold blue]━━━ Orchestration Eval: "
            f"{config.provider} / {config.model} ━━━[/bold blue]"
        )

        try:
            llm = config.get_chat_model(verbose=False)
            agent = create_react_agent(
                llm,
                tools=MOCK_TOOLS,
                prompt=PORTER_SYSTEM_PROMPT,
            )
        except Exception as e:
            console.print(f"[red]Failed to initialize: {e}[/red]")
            results_summary.append({
                "model": config.model,
                "provider": config.provider,
                "tool_accuracy": "INIT_FAIL",
                "arg_accuracy": "INIT_FAIL",
                "avg_latency": "N/A",
                "total_cost_usd": "N/A",
                "error": str(e),
            })
            continue

        tool_correct = 0
        arg_correct = 0
        total_latency = 0.0
        case_details: List[Dict[str, Any]] = []
        sleep_interval = _get_rate_limit_sleep(config.provider)

        for case in test_cases:
            # Retry with exponential backoff for 429 rate limit errors
            max_retries = 3
            result = None
            last_error = None

            for attempt in range(max_retries):
                start = time.time()
                try:
                    result = agent.invoke(
                        {"messages": [HumanMessage(content=case["input_text"])]},
                    )
                    elapsed = time.time() - start
                    last_error = None
                    break  # Success — exit retry loop

                except Exception as e:
                    elapsed = time.time() - start
                    error_str = str(e)
                    last_error = error_str

                    # Check if it's a rate limit error
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                        backoff = 10 * (2 ** attempt)  # 10s, 20s, 40s
                        console.print(
                            f"  [yellow]⏳ {case['id']} 429 rate limit "
                            f"(attempt {attempt + 1}/{max_retries}), "
                            f"backing off {backoff}s...[/yellow]"
                        )
                        time.sleep(backoff)
                        continue
                    else:
                        # Non-rate-limit error — don't retry
                        break

            if result is not None and last_error is None:
                # Successful invocation
                total_latency += elapsed
                messages = result.get("messages", [])
                tool_calls = _extract_tool_calls(messages)

                # Score tool selection
                tool_ok = _check_tool_selection(tool_calls, case["expected_tool"])
                if tool_ok:
                    tool_correct += 1

                # Score argument accuracy
                arg_ok = _check_argument_accuracy(tool_calls, case["expected_args"])
                if arg_ok:
                    arg_correct += 1

                # Format what the model actually called
                actual_tools = [tc["tool_name"] for tc in tool_calls]
                actual_args_summary = {
                    tc["tool_name"]: tc["tool_args"] for tc in tool_calls
                }

                status_icon = "[green]✓[/green]" if (tool_ok and arg_ok) else "[red]✗[/red]"
                console.print(
                    f"  {status_icon} {case['id']} ({elapsed:.2f}s) "
                    f"tool={'✓' if tool_ok else '✗'} "
                    f"args={'✓' if arg_ok else '✗'} "
                    f"→ called: {actual_tools}"
                )

                case_details.append({
                    "id": case["id"],
                    "profile": case["profile"],
                    "expected_tool": case["expected_tool"],
                    "actual_tools": actual_tools,
                    "actual_args": actual_args_summary,
                    "tool_ok": tool_ok,
                    "arg_ok": arg_ok,
                    "latency": round(elapsed, 2),
                })
            else:
                # All retries failed or non-429 error
                total_latency += elapsed
                error_msg = (last_error or "Unknown error")[:120]
                console.print(
                    f"  [red]✗ {case['id']} error ({elapsed:.2f}s): {error_msg}[/red]"
                )
                case_details.append({
                    "id": case["id"],
                    "profile": case["profile"],
                    "expected_tool": case["expected_tool"],
                    "actual_tools": [],
                    "tool_ok": False,
                    "arg_ok": False,
                    "latency": round(elapsed, 2),
                    "error": error_msg,
                })

            time.sleep(sleep_interval)

        num_cases = len(test_cases)
        avg_latency = total_latency / num_cases if num_cases else 0

        results_summary.append({
            "model": config.model,
            "provider": config.provider,
            "tool_accuracy": f"{tool_correct}/{num_cases}",
            "arg_accuracy": f"{arg_correct}/{num_cases}",
            "avg_latency": f"{avg_latency:.2f}s",
            "total_cost_usd": "N/A",  # ReAct agent doesn't expose token counts easily
            "case_details": case_details,
        })

        console.print(
            f"\n  [bold]Summary: tool={tool_correct}/{num_cases} "
            f"args={arg_correct}/{num_cases} "
            f"avg_latency={avg_latency:.2f}s[/bold]"
        )

    return results_summary
