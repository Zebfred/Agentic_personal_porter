#!/usr/bin/env python3
"""
Data Lineage Tracer — Cross-System Correlation ID Lookup.

Given a correlation ID, queries all data sources (MongoDB, Neo4j, ChromaDB)
to show everywhere that record landed. This is the primary debugging and
auditing tool for the Phase A lineage system.

Usage:
    python scripts/analyze_scripts/trace_lineage.py <correlation_id>
    python scripts/analyze_scripts/trace_lineage.py log-W27-2026-07-05-morning-Hero
    python scripts/analyze_scripts/trace_lineage.py --list          # List recent IDs
    python scripts/analyze_scripts/trace_lineage.py --list --limit 20
"""
import sys
import os
import argparse
from datetime import datetime

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
import atexit

console = Console()


def _cleanup_connections():
    """Explicitly close database connections to suppress ResourceWarnings."""
    try:
        from src.database.mongo_client.connection import MongoConnectionManager
        if hasattr(MongoConnectionManager, '_client') and MongoConnectionManager._client:
            MongoConnectionManager._client.close()
    except Exception:
        pass
    try:
        from src.database.neo4j_client.connection import close_driver
        close_driver()
    except Exception:
        pass


atexit.register(_cleanup_connections)


def trace_mongo(correlation_id: str) -> dict:
    """
    Search all MongoDB collections for documents containing the correlation ID.
    Returns a dict of {collection_name: [matching_docs]}.
    """
    from src.database.mongo_client.connection import MongoConnectionManager
    db = MongoConnectionManager.get_db()
    results = {}

    # 1. Journal time entries (nested structure — correlation_id lives inside chunk data)
    journal_col = db["journal_time_entries"]
    # Use dot-notation regex to search nested chunk fields
    pipeline = [
        {"$project": {"month_id": 1, "user_id": 1, "weeks": {"$objectToArray": "$weeks"}}},
        {"$unwind": "$weeks"},
        {"$project": {"month_id": 1, "user_id": 1, "week": "$weeks.k", "days": {"$objectToArray": "$weeks.v"}}},
        {"$unwind": "$days"},
        {"$project": {"month_id": 1, "user_id": 1, "week": 1, "day": "$days.k", "chunks": {"$objectToArray": "$days.v.chunks"}}},
        {"$unwind": "$chunks"},
        {"$match": {"chunks.v.correlation_id": correlation_id}},
        {"$project": {
            "month_id": 1, "user_id": 1, "week": 1, "day": 1,
            "time_chunk": "$chunks.k",
            "correlation_id": "$chunks.v.correlation_id",
            "processed_at": "$chunks.v.processed_at",
            "intention": "$chunks.v.intention",
            "actual": "$chunks.v.actual",
        }}
    ]
    try:
        journal_hits = list(journal_col.aggregate(pipeline))
        if journal_hits:
            results["journal_time_entries"] = journal_hits
    except Exception as e:
        results["journal_time_entries_error"] = str(e)

    # 2. Freeform journals
    freeform_col = db["freeform_journals"]
    freeform_hits = list(freeform_col.find(
        {"correlation_id": correlation_id},
        {"_id": 0, "date": 1, "user_id": 1, "correlation_id": 1, "updated_at": 1, "text": {"$substr": ["$text", 0, 120]}}
    ))
    if freeform_hits:
        results["freeform_journals"] = freeform_hits

    # 3. Weekly expectations
    weekly_col = db["weekly_expectations"]
    weekly_hits = list(weekly_col.find(
        {"correlation_id": correlation_id},
        {"_id": 0, "user_id": 1, "week_start_date": 1, "correlation_id": 1, "updated_at": 1, "expectation_text": {"$substr": ["$expectation_text", 0, 120]}}
    ))
    if weekly_hits:
        results["weekly_expectations"] = weekly_hits

    # 4. Calendar actual events
    actual_col = db["calendar_actual_events"]
    actual_hits = list(actual_col.find(
        {"correlation_id": correlation_id},
        {"_id": 1, "user_id": 1, "correlation_id": 1, "time_slot": 1}
    ))
    if actual_hits:
        # Convert ObjectId to string for display
        for hit in actual_hits:
            hit["_id"] = str(hit["_id"])
        results["calendar_actual_events"] = actual_hits

    # 5. Calendar unified events
    unified_col = db["calendar_unified_events"]
    unified_hits = list(unified_col.find(
        {"correlation_id": correlation_id},
        {"_id": 1, "user_id": 1, "correlation_id": 1, "time_slot": 1}
    ))
    if unified_hits:
        for hit in unified_hits:
            hit["_id"] = str(hit["_id"])
        results["calendar_unified_events"] = unified_hits

    # 6. Agent reflections
    reflections_col = db["agent_reflections"]
    reflection_hits = list(reflections_col.find(
        {"correlation_id": correlation_id},
        {"_id": 0, "day": 1, "user_id": 1, "correlation_id": 1, "created_at": 1}
    ))
    if reflection_hits:
        results["agent_reflections"] = reflection_hits

    return results


def trace_neo4j(correlation_id: str) -> list:
    """
    Search Neo4j for nodes with a matching source_id property.
    Returns a list of matching nodes with their labels and key properties.
    """
    try:
        from src.database.neo4j_client.connection import get_driver
        driver = get_driver()
        with driver.session() as session:
            # Query for any node that has this source_id
            query = """
            MATCH (n)
            WHERE n.source_id = $correlation_id
            RETURN labels(n) AS labels, 
                   n.source_id AS source_id,
                   CASE 
                       WHEN 'Intention' IN labels(n) THEN n.description
                       WHEN 'Actual' IN labels(n) THEN n.activity
                       ELSE 'N/A'
                   END AS summary,
                   n.timestamp AS timestamp
            """
            result = session.run(query, correlation_id=correlation_id)
            return [dict(record) for record in result]
    except Exception as e:
        return [{"error": str(e)}]


def trace_chromadb(correlation_id: str) -> list:
    """
    Search ChromaDB for vectors with matching correlation_id metadata.
    """
    try:
        from src.database.vector_database.chromadb_client import ChromaExperimentalClient
        client = ChromaExperimentalClient()
        results = client.search_by_correlation_id(correlation_id)
        if results and isinstance(results, dict):
            return results.get("documents", [])
        return results if results else []
    except Exception as e:
        return [{"error": str(e)}]


def trace_weaviate(correlation_id: str) -> list:
    """
    Search Weaviate for vectors with matching correlation_id metadata.
    """
    try:
        from src.database.vector_database.weaviate_client import WeaviateExperimentalClient
        client = WeaviateExperimentalClient()
        results = client.search_by_correlation_id(correlation_id)
        if results and isinstance(results, dict):
            data = results.get("data", {}).get("Get", {}).get("MemoryObj", [])
            return data if data else []
        return results if results else []
    except Exception as e:
        return [{"error": str(e)}]


def list_recent_correlation_ids(limit: int = 10) -> list:
    """
    List the most recent correlation IDs found across MongoDB collections.
    Useful for discovering what IDs exist to trace.
    """
    from src.database.mongo_client.connection import MongoConnectionManager
    db = MongoConnectionManager.get_db()
    ids_found = []

    # Freeform journals (flat structure — easiest to query)
    freeform_col = db["freeform_journals"]
    for doc in freeform_col.find(
        {"correlation_id": {"$exists": True}},
        {"correlation_id": 1, "date": 1, "user_id": 1, "updated_at": 1, "_id": 0}
    ).sort("updated_at", -1).limit(limit):
        doc["source"] = "freeform_journals"
        ids_found.append(doc)

    # Weekly expectations
    weekly_col = db["weekly_expectations"]
    for doc in weekly_col.find(
        {"correlation_id": {"$exists": True}},
        {"correlation_id": 1, "week_start_date": 1, "user_id": 1, "updated_at": 1, "_id": 0}
    ).sort("updated_at", -1).limit(limit):
        doc["source"] = "weekly_expectations"
        ids_found.append(doc)

    # Journal time entries (nested — use aggregation)
    journal_col = db["journal_time_entries"]
    pipeline = [
        {"$project": {"weeks": {"$objectToArray": "$weeks"}, "user_id": 1}},
        {"$unwind": "$weeks"},
        {"$project": {"user_id": 1, "days": {"$objectToArray": "$weeks.v"}}},
        {"$unwind": "$days"},
        {"$project": {"user_id": 1, "day": "$days.k", "chunks": {"$objectToArray": "$days.v.chunks"}}},
        {"$unwind": "$chunks"},
        {"$match": {"chunks.v.correlation_id": {"$exists": True}}},
        {"$project": {
            "correlation_id": "$chunks.v.correlation_id",
            "user_id": 1,
            "day": 1,
            "time_chunk": "$chunks.k",
            "processed_at": "$chunks.v.processed_at",
        }},
        {"$sort": {"processed_at": -1}},
        {"$limit": limit}
    ]
    try:
        for doc in journal_col.aggregate(pipeline):
            doc["source"] = "journal_time_entries"
            doc.pop("_id", None)
            ids_found.append(doc)
    except Exception:
        pass

    # Sort all by most recent and deduplicate
    return ids_found[:limit]


def render_trace(correlation_id: str):
    """
    Main rendering function — queries all sources and prints a rich table.
    """
    console.print(Panel(
        f"[bold cyan]Tracing Correlation ID:[/bold cyan] [yellow]{correlation_id}[/yellow]",
        title="🔍 Data Lineage Tracer",
        border_style="cyan"
    ))

    # --- MongoDB ---
    console.print("\n[bold green]📦 MongoDB[/bold green]")
    mongo_results = trace_mongo(correlation_id)
    if not mongo_results:
        console.print("  [dim]No records found in any MongoDB collection.[/dim]")
    else:
        for collection, docs in mongo_results.items():
            if collection.endswith("_error"):
                console.print(f"  [red]⚠ {collection}: {docs}[/red]")
                continue
            table = Table(title=f"  {collection}", box=box.SIMPLE, show_lines=True)
            if docs:
                for key in docs[0].keys():
                    table.add_column(str(key), style="cyan", overflow="fold")
                for doc in docs:
                    table.add_row(*[str(v)[:80] for v in doc.values()])
            console.print(table)

    # --- Neo4j ---
    console.print("\n[bold blue]🔗 Neo4j[/bold blue]")
    neo4j_results = trace_neo4j(correlation_id)
    if not neo4j_results:
        console.print("  [dim]No nodes found with this source_id.[/dim]")
    elif "error" in neo4j_results[0]:
        console.print(f"  [red]⚠ Neo4j error: {neo4j_results[0]['error']}[/red]")
    else:
        table = Table(title="  Neo4j Nodes", box=box.SIMPLE, show_lines=True)
        table.add_column("Labels", style="blue")
        table.add_column("Summary", style="white")
        table.add_column("Timestamp", style="dim")
        for node in neo4j_results:
            labels = ", ".join(node.get("labels", []))
            table.add_row(labels, str(node.get("summary", "")), str(node.get("timestamp", "")))
        console.print(table)

    # --- ChromaDB (Phase B — populated by CDC workers) ---
    console.print("\n[bold magenta]🧠 ChromaDB[/bold magenta] [dim](Phase B — CDC workers)[/dim]")
    chroma_results = trace_chromadb(correlation_id)
    if not chroma_results:
        console.print("  [dim]No vectors found with this correlation_id.[/dim]")
    elif isinstance(chroma_results[0], dict) and "error" in chroma_results[0]:
        console.print(f"  [red]⚠ ChromaDB error: {chroma_results[0]['error']}[/red]")
    else:
        console.print(f"  Found [bold]{len(chroma_results)}[/bold] vector(s)")
        for i, doc in enumerate(chroma_results[:5]):
            console.print(f"    [{i+1}] {str(doc)[:120]}...")

    # --- Weaviate (Phase B — populated by CDC workers) ---
    console.print("\n[bold yellow]🌐 Weaviate[/bold yellow] [dim](Phase B — CDC workers)[/dim]")
    weaviate_results = trace_weaviate(correlation_id)
    if not weaviate_results:
        console.print("  [dim]No vectors found with this correlation_id.[/dim]")
    elif isinstance(weaviate_results[0], dict) and "error" in weaviate_results[0]:
        console.print(f"  [red]⚠ Weaviate error: {weaviate_results[0]['error']}[/red]")
    else:
        console.print(f"  Found [bold]{len(weaviate_results)}[/bold] vector(s)")
        for i, doc in enumerate(weaviate_results[:5]):
            text_preview = str(doc.get('text', doc))[:120]
            console.print(f"    [{i+1}] {text_preview}...")

    # --- Summary ---
    total = sum(len(v) for v in mongo_results.values() if isinstance(v, list))
    total += len([n for n in neo4j_results if "error" not in n])
    total += len(chroma_results) if chroma_results and not (isinstance(chroma_results[0], dict) and "error" in chroma_results[0]) else 0
    total += len(weaviate_results) if weaviate_results and not (isinstance(weaviate_results[0], dict) and "error" in weaviate_results[0]) else 0

    console.print(Panel(
        f"[bold]Total records found: {total}[/bold]",
        title="📊 Lineage Summary",
        border_style="green" if total > 0 else "red"
    ))


def render_list(limit: int):
    """List recent correlation IDs across all collections."""
    console.print(Panel(
        f"[bold cyan]Listing {limit} most recent Correlation IDs[/bold cyan]",
        title="📋 Recent Correlation IDs",
        border_style="cyan"
    ))
    
    ids = list_recent_correlation_ids(limit)
    if not ids:
        console.print("[dim]No correlation IDs found yet. Save a journal entry to generate one.[/dim]")
        return

    table = Table(box=box.ROUNDED, show_lines=True)
    table.add_column("Correlation ID", style="yellow", min_width=40)
    table.add_column("Source", style="cyan")
    table.add_column("User", style="green")
    table.add_column("Date/Context", style="white")

    for item in ids:
        cid = item.get("correlation_id", "N/A")
        source = item.get("source", "unknown")
        user = item.get("user_id", "N/A")
        context = item.get("day", item.get("date", item.get("week_start_date", "N/A")))
        if item.get("time_chunk"):
            context += f" / {item['time_chunk']}"
        table.add_row(cid, source, user, context)

    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="Trace a correlation ID across all data sources (Mongo, Neo4j, ChromaDB).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/analyze_scripts/trace_lineage.py log-W27-2026-07-05-morning-Hero
    python scripts/analyze_scripts/trace_lineage.py --list
    python scripts/analyze_scripts/trace_lineage.py --list --limit 20
        """
    )
    parser.add_argument("correlation_id", nargs="?", help="The correlation ID to trace")
    parser.add_argument("--list", action="store_true", help="List recent correlation IDs")
    parser.add_argument("--limit", type=int, default=10, help="Number of recent IDs to show (default: 10)")

    args = parser.parse_args()

    if args.list:
        render_list(args.limit)
    elif args.correlation_id:
        render_trace(args.correlation_id)
    else:
        parser.print_help()
        console.print("\n[yellow]Tip:[/yellow] Run with --list to discover existing correlation IDs")


if __name__ == "__main__":
    main()
