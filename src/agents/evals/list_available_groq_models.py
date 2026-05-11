"""
Helper script to dynamically list available models from Groq and Vertex AI.
"""

import os
import sys
import requests
from pathlib import Path
from rich.console import Console

console = Console()

def list_groq_models():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        console.print("[red]GROQ_API_KEY is not set. Cannot list Groq models.[/red]")
        return
        
    try:
        response = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        response.raise_for_status()
        models = response.json().get("data", [])
        
        console.print("\n[bold green]Available Groq Models:[/bold green]")
        for m in sorted(models, key=lambda x: x["id"]):
            console.print(f"- {m['id']}")
            
    except Exception as e:
        console.print(f"[red]Error fetching Groq models: {e}[/red]")

def list_vertex_models():
    project = os.getenv("PROJECT_ID")
    location = os.getenv("GCP_LOCATION", "us-central1")
    
    if not project:
        console.print("[red]PROJECT_ID is not set. Assuming default authentication.[/red]")
        
    try:
        import google.auth
        import google.auth.transport.requests
        
        credentials, project_id = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        
        access_token = credentials.token
        
        project = project or project_id
        
        url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/google/models"
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        
        models = response.json().get("models", [])
        console.print("\n[bold blue]Available Google Vertex AI Foundation Models (Filtered):[/bold blue]")
        
        # Filter for models we commonly care about to avoid listing hundreds of variants
        gemini_models = [m["name"].split("/")[-1] for m in models if any(x in m["name"].lower() for x in ["gemini", "claude", "llama"])]
        
        for m in sorted(set(gemini_models)):
            console.print(f"- {m}")

    except Exception as e:
        console.print(f"[red]Error fetching Vertex models. Are you authenticated via gcloud? Error: {e}[/red]")

if __name__ == "__main__":
    from src.utils.path_utils import load_env_vars
    load_env_vars()
    
    console.print("[bold]Fetching dynamically available models...[/bold]")
    list_groq_models()
    list_vertex_models()
