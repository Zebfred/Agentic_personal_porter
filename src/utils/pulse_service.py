import os
from datetime import datetime, timezone

from src.utils.path_utils import load_env_vars
from src.database.mongo_storage import SovereignMongoStorage
from src.database.neo4j_client.connection import get_driver
from src.config import MongoConfig
import logging

logger = logging.getLogger(__name__)

class PulseService:
    @staticmethod
    def get_system_heartbeat():
        """
        Gathers system health metrics including Calendar Sync, Vector DB Sync,
        Graph DB status, MongoDB collection counts, Langsmith tracing status,
        and individual Agent health metrics.
        """
        # Ensure environment variables are loaded
        load_env_vars()
        
        try:
            storage = SovereignMongoStorage()
            cal_sync = storage.get_system_status("calendar_sync")
            vec_sync = storage.get_system_status("vector_db_sync")
            
            neo4j_node_count = 0
            neo4j_edge_count = 0
            latest_day_node = None
            
            try:
                driver = get_driver()
                with driver.session() as session:
                    node_res = session.execute_read(lambda tx: tx.run("MATCH (n) RETURN count(n) as c").single())
                    if node_res: neo4j_node_count = node_res["c"]

                    edge_res = session.execute_read(lambda tx: tx.run("MATCH ()-[r]->() RETURN count(r) as c").single())
                    if edge_res: neo4j_edge_count = edge_res["c"]

                    day_res = session.execute_read(lambda tx: tx.run("MATCH (d:Day) RETURN d.date as date ORDER BY d.date DESC LIMIT 1").single())
                    if day_res: latest_day_node = day_res["date"]
            except Exception as e:
                logger.error(f"Error querying Neo4j for Pulse: {e}")
                
            db = storage.db
            mongo_counts = {
                "raw_calendar_events": db[MongoConfig.RAW_COLLECTION].estimated_document_count(),
                "formatted_calendar_events": db[MongoConfig.FORMATTED_COLLECTION].estimated_document_count(),
                "daily_categorized_events": db[MongoConfig.DAILY_CATEGORIZED_EVENTS].estimated_document_count(),
                "calendar_events_timeseries": db[MongoConfig.RAW_TIMESERIES_COLLECTION].estimated_document_count(),
                "event_intentions": db[MongoConfig.INTENT_COLLECTION].estimated_document_count(),
                "event_actuals": db[MongoConfig.ACTUAL_COLLECTION].estimated_document_count(),
                "unified_events": db[MongoConfig.UNIFIED_EVENTS_COLLECTION].estimated_document_count(),
                "journal_entries": db['journal_entries'].estimated_document_count(),
                "agent_reflections": db['agent_reflections'].estimated_document_count()
            }

            # LangSmith / Environment Check
            langchain_project = os.getenv("LANGCHAIN_PROJECT", "porter_mach_3")
            env_status = {
                "LANGCHAIN_API_KEY_CONFIGURED": bool(os.getenv("LANGCHAIN_API_KEY") and os.getenv("LANGCHAIN_API_KEY") != "YOUR_API_KEY_HERE"),
                "LANGCHAIN_TRACING_V2": os.getenv("LANGCHAIN_TRACING_V2", "false"),
                "LANGCHAIN_PROJECT": langchain_project,
                "OPENAI_API_KEY_CONFIGURED": bool(os.getenv("OPENAI_API_KEY")),
                "HERO_NAME": os.getenv("HERO_NAME", "Hero")
            }
            
            # Pull Last 5 Traces from LangSmith
            recent_traces = []
            try:
                if env_status["LANGCHAIN_API_KEY_CONFIGURED"]:
                    from langsmith import Client
                    ls_client = Client()
                    runs = ls_client.list_runs(
                        project_name=langchain_project,
                        is_root=True,
                        limit=5
                    )
                    for r in runs:
                        recent_traces.append({
                            "name": r.name,
                            "status": "error" if r.error else "success",
                            "error": r.error,
                            "total_tokens": r.total_tokens,
                            "latency_seconds": (r.end_time - r.start_time).total_seconds() if r.end_time and r.start_time else None,
                            "start_time": r.start_time.isoformat() if r.start_time else None
                        })
            except Exception as ls_err:
                recent_traces.append({"error": f"Failed to fetch from LangSmith: {ls_err}"})
                
            # Agent Health Monitor
            try:
                from src.database.mongo_client.agent_health import AgentHeartbeatManager
                health_manager = AgentHeartbeatManager()
                agent_health = health_manager.get_all_agent_statuses()
            except Exception as hm_err:
                agent_health = {"error": f"Failed to fetch agent health: {hm_err}"}
            
            pulse_data = {
                "calendar_sync": cal_sync,
                "vector_db_sync": vec_sync,
                "graph_db": {
                    "node_count": neo4j_node_count,
                    "edge_count": neo4j_edge_count,
                    "latest_day_node": latest_day_node
                },
                "mongo_collections_counts": mongo_counts,
                "environment_and_observability": env_status,
                "langsmith_recent_traces": recent_traces,
                "agent_health": agent_health,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            return pulse_data

        except Exception as e:
            logger.error(f"Error compiling system heartbeat: {e}")
            raise e
