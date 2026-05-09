"""
Runs identical test cases across multiple LLM providers (via AgentLLMConfig)
to evaluate latency, accuracy, and token usage for the categorizer node.
"""

import time
import sys
import os
from pathlib import Path

root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(root))

from src.utils.llm_factory import AgentLLMConfig
from src.agents.porter_manager import CategorizationResult
from src.agents.evals.trajectory_tests import get_categorization_test_cases
from langchain_core.prompts import ChatPromptTemplate
from rich.console import Console
from rich.table import Table

console = Console()

def run_categorization_eval():
    test_cases = get_categorization_test_cases()
    
    # Define models to compare
    models_to_test = [
        AgentLLMConfig(provider="groq", model="llama-3.1-8b-instant"),
        AgentLLMConfig(provider="groq", model="llama-3.3-70b-versatile"),
        AgentLLMConfig(provider="vertex", model="gemini-1.5-flash-002")
    ]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are 'The Categorizer'. You are no longer a deep contextual philosophical coach. Your sole responsibility is to evaluate daily events and definitively map them to exactly one of the designated 9 Hero Pillars (e.g. Health, Wealth, Core). Fast, objective, and strict.\n\nGoal: Perform strict, low-latency categorization of Intention vs. Actual events across the 9 Core Pillars."),
        ("user", "1. Analyze the following FRONTEND PAYLOAD quickly submitted by {username}:\n'{journal_entry}'\n\n2. Contextualize it against his last 5 Calendar Events:\n{actuals_str}\n\n3. Identify EXACTLY which of the 9 Hero pillars this combination represents: (1. Core Identity, 2. Mind, 3. Body/Health, 4. Heart/Social, 5. Wealth/Career, 6. Community, 7. Leisure, 8. Spirit, 9. Duty).\nExpected output: A single structured JSON block.")
    ])

    results_summary = []
    
    for config in models_to_test:
        console.print(f"\n[bold blue]Evaluating Model: {config.provider} / {config.model}[/bold blue]")
        try:
            llm = config.get_chat_model().with_structured_output(CategorizationResult)
            chain = prompt | llm
        except Exception as e:
            console.print(f"[red]Failed to initialize model: {e}[/red]")
            continue
            
        success_count = 0
        total_latency = 0
        
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
                
                is_correct = case["expected_pillar"] in res.Pillar
                if is_correct:
                    success_count += 1
                    console.print(f"  [green]✓ {case['id']} passed ({latency:.2f}s) - {res.Pillar}[/green]")
                else:
                    console.print(f"  [red]✗ {case['id']} failed ({latency:.2f}s) - Expected: {case['expected_pillar']}, Got: {res.Pillar}[/red]")
            except Exception as e:
                console.print(f"  [red]✗ {case['id']} error: {e}[/red]")
                
            # Sleep to respect Groq rate limits
            time.sleep(2.5)
                
        results_summary.append({
            "model": config.model,
            "provider": config.provider,
            "accuracy": f"{success_count}/{len(test_cases)}",
            "avg_latency": f"{(total_latency / len(test_cases)):.2f}s"
        })
        
    return results_summary

if __name__ == "__main__":
    console.print("\n[bold]Starting Categorization Evaluation Harness...[/bold]\n")
    results = run_categorization_eval()
    
    table = Table(title="Model Evaluation Summary")
    table.add_column("Provider", style="cyan")
    table.add_column("Model", style="magenta")
    table.add_column("Accuracy", style="green")
    table.add_column("Avg Latency", style="yellow")
    
    for r in results:
        table.add_row(r["provider"], r["model"], r["accuracy"], r["avg_latency"])
        
    console.print(table)
