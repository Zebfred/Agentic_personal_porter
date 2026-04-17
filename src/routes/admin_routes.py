"""
Admin routes.

Protected endpoints for triggering background operations:
- Calendar sync to Neo4j
- Vector database batch sync
- Hero Foundation injection
- Infrastructure warm-up
"""
import logging
from flask import Blueprint, request, jsonify

from src.routes.auth_middleware import require_api_key

admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger("APP_ROUTER")


@admin_bp.route('/admin/sync_calendar', methods=['POST'])
@require_api_key
def admin_sync_calendar():
    """
    Triggers the Google Calendar sync pipeline to Neo4j.
    """
    try:
        from src.orchestrators.sync_calendar_to_graph import run_sync_pipeline
        run_sync_pipeline()
        return jsonify({"message": "Calendar sync completed successfully."})
    except Exception as e:
        logger.error(f"Error syncing calendar: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/wake_infrastructure', methods=['POST', 'OPTIONS'])
@require_api_key
def wake_infrastructure():
    """
    Called by the frontend to silently warm up internal cloud infrastructure (like the Spot BGE-M3 instance)
    so inference engines are running by the time the user chats.
    """
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from src.integrations.gcp_compute_client import GCPComputeClient
        client = GCPComputeClient()
        success = client.wake_instance(instance="ollama-vector-host", zone="us-central1-a", block_until_running=False)
        return jsonify({"status": "acknowledged", "woke_instance": success})
    except Exception as e:
        logger.error(f"Error executing wake pulse: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/admin/vector_sync', methods=['POST'])
@require_api_key
def admin_vector_sync():
    """
    Triggers the isolated batch synchronization into ChromaDB and Weaviate.
    """
    try:
        from src.orchestrators.vector_batch_sync_all import execute_sync
        execute_sync(sync_trigger_time="CRON")
        return jsonify({"message": "Vector DB batch synchronization completed."})
    except Exception as e:
        logger.error(f"Error during vector batch sync: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/admin/inject_foundation', methods=['POST'])
@require_api_key
def admin_inject_foundation():
    """
    Triggers the Hero Foundation (Origin/Ambition) injection to Neo4j.
    """
    try:
        from src.database.inject_hero_foundation import inject_hero_data
        inject_hero_data()
        return jsonify({"message": "Hero foundation injected successfully."})
    except Exception as e:
        logger.error(f"Error injecting foundation: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/admin/unverified_audits', methods=['GET'])
@require_api_key
def get_unverified_audits():
    """
    Fetches the unverified records queue for the Verification Dashboard.
    """
    try:
        from src.agents.audit_inspector import AuditInspector
        inspector = AuditInspector()
        records = inspector.batch_unverified_records()
        return jsonify({"status": "success", "records": records})
    except Exception as e:
        logger.error(f"Error fetching unverified audits: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/admin/verified_history', methods=['GET'])
@require_api_key
def get_verified_history():
    """
    Fetches the deeply confirmed historical audits for the Verification Dashboard.
    """
    try:
        from src.agents.audit_inspector import AuditInspector
        inspector = AuditInspector()
        records = inspector.get_recently_verified_records(limit=10)
        return jsonify({"status": "success", "records": records})
    except Exception as e:
        logger.error(f"Error fetching verified history: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/admin/approve_audits', methods=['POST'])
@require_api_key
def approve_audits():
    """
    Batch approves a list of record gcal_ids.
    """
    try:
        data = request.json
        gcal_ids = data.get('gcal_ids', [])
        if not gcal_ids:
            return jsonify({"status": "error", "message": "No gcal_ids provided."}), 400
            
        from src.agents.audit_inspector import AuditInspector
        inspector = AuditInspector()
        modified = inspector.approve_batch(gcal_ids)
        return jsonify({"status": "success", "modified_count": modified})
    except Exception as e:
        logger.error(f"Error approving audits: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
