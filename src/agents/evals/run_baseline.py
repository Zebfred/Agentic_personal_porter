"""
Executable entry point to run evaluations and output baseline metrics.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from rich.console import Console

root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(root))

from src.agents.evals.model_comparison_harness import run_categorization_eval
from src.utils.path_utils import load_env_vars

console = Console()

def main():
    load_env_vars()
    
    results = run_categorization_eval()
    
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out_dir = os.path.join(root, "data", "evals")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "baseline_results.md")
    
    with open(out_file, "w") as f:
        f.write(f"# Agentic Personal Porter - Baseline Evaluation\n")
        f.write(f"**Date:** {current_date}\n\n")
        f.write("## Categorization Harness Results\n\n")
        f.write("| Provider | Model | Accuracy | Avg Latency |\n")
        f.write("|---|---|---|---|\n")
        for r in results:
            f.write(f"| {r['provider']} | {r['model']} | {r['accuracy']} | {r['avg_latency']} |\n")
            
    console.print(f"\n[bold green]Baseline results saved to {out_file}[/bold green]")

if __name__ == "__main__":
    main()
