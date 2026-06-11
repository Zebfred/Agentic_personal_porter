#!/usr/bin/env python3
"""
CLI runner for the orchestration (tool-routing) evaluation harness.

Usage:
    python src/agents/evals/run_orchestration_eval.py
    python src/agents/evals/run_orchestration_eval.py --model gemini-2.5-pro
    python src/agents/evals/run_orchestration_eval.py --groq-only
    python src/agents/evals/run_orchestration_eval.py --all
"""

import argparse
from pathlib import Path
from datetime import datetime

from src.utils.path_utils import load_env_vars
from src.utils.llm_factory import AgentLLMConfig
from src.agents.evals.orchestration_harness import run_orchestration_eval
from rich.console import Console
from rich.table import Table

console = Console()

def _build_model_list(
    include_gemini: bool = True,
    include_groq: bool = False,
) -> list[AgentLLMConfig]:
    """Builds the list of models to evaluate."""
    models = []
    if include_gemini:
        models.extend([
            AgentLLMConfig(provider="google_genai", model="gemini-2.5-pro"),
            AgentLLMConfig(provider="google_genai", model="gemini-2.5-flash"),
        ])
    if include_groq:
        models.extend([
            AgentLLMConfig(provider="groq", model="llama-3.1-8b-instant"),
            AgentLLMConfig(provider="groq", model="llama-3.3-70b-versatile"),
        ])
    return models

def _write_results_markdown(results: list[dict], output_path: Path) -> None:
    """Writes evaluation results to a markdown report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# Orchestration Eval Results",
        "",
        f"**Generated**: {timestamp}",
        "**Test Type**: Single-turn tool-routing accuracy",
        "**Agent**: First-Serving Porter (ReAct with 7 mock tools)",
        "",
        "## Summary",
        "",
        "| Provider | Model | Tool Accuracy | Arg Accuracy | Avg Latency |",
        "|---|---|---|---|---|",
    ]

    for r in results:
        lines.append(
            f"| {r['provider']} | {r['model']} | {r['tool_accuracy']} "
            f"| {r['arg_accuracy']} | {r['avg_latency']} |"
        )

    lines.append("")
    lines.append("## Detailed Results")
    lines.append("")

    for r in results:
        lines.append(f"### {r['provider']} / {r['model']}")
        lines.append("")
        lines.append(
            "| ID | Profile | Expected Tool | Actual Tool(s) | Tool ✓ | Args ✓ | Latency |"
        )
        lines.append("|---|---|---|---|---|---|---|")

        for detail in r.get("case_details", []):
            actual = ", ".join(detail.get("actual_tools", ["-"]))
            if not actual:
                actual = "—"
            tool_mark = "✓" if detail.get("tool_ok") else "✗"
            arg_mark = "✓" if detail.get("arg_ok") else "✗"
            error = detail.get("error", "")
            latency_str = f"{detail.get('latency', 0)}s"
            if error:
                actual = f"ERROR: {error[:50]}"

            lines.append(
                f"| {detail['id']} | {detail['profile']} "
                f"| {detail['expected_tool']} | {actual} "
                f"| {tool_mark} | {arg_mark} | {latency_str} |"
            )

        lines.append("")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    console.print(f"\n[green]Results written to {output_path}[/green]")

def main():
    parser = argparse.ArgumentParser(
        description="Run orchestration (tool-routing) evaluation."
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Test a single model by name (e.g. gemini-2.5-pro)",
    )
    parser.add_argument(
        "--groq-only",
        action="store_true",
        help="Only test Groq models",
    )
    parser.add_argument(
        "--gemini-only",
        action="store_true",
        help="Only test Gemini models (default)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Test all models (Gemini + Groq)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path for results markdown",
    )
    args = parser.parse_args()

    load_env_vars()

    # Determine which models to include
    include_gemini = True
    include_groq = False

    if args.all:
        include_groq = True
    elif args.groq_only:
        include_gemini = False
        include_groq = True

    models = _build_model_list(
        include_gemini=include_gemini,
        include_groq=include_groq,
    )

    console.print("\n[bold]━━━ Orchestration Eval Harness ━━━[/bold]")
    console.print(f"Models: {len(models)}")
    console.print(f"Mode: {'single model' if args.model else 'full sweep'}\n")

    results = run_orchestration_eval(
        models=models,
        single_model=args.model,
    )

    # Print summary table
    table = Table(title="Orchestration Eval Summary")
    table.add_column("Provider", style="cyan")
    table.add_column("Model", style="magenta")
    table.add_column("Tool Accuracy", style="green")
    table.add_column("Arg Accuracy", style="yellow")
    table.add_column("Avg Latency", style="blue")

    for r in results:
        table.add_row(
            r["provider"], r["model"],
            r["tool_accuracy"], r["arg_accuracy"],
            r["avg_latency"],
        )

    console.print(table)

    # Write markdown report
    output_path = Path(args.output) if args.output else (root / "data" / "evals" / "orchestration_results.md")
    _write_results_markdown(results, output_path)

if __name__ == "__main__":
    main()
