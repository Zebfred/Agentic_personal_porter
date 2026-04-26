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

from src.routes.auth_middleware import require_api_key, require_role

admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger("APP_ROUTER")


@admin_bp.route('/admin/system_sync', methods=['POST'])
@require_api_key
@require_role('admin')
def admin_system_sync():
    """
    Triggers the system state sync pipeline to Neo4j.
    This fetches metrics and updates the System State calendar.
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
@require_role('admin')
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
@require_role('admin')
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
@require_role('admin')
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
@require_role('admin')
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
@require_role('admin')
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

@admin_bp.route('/admin/pulse', methods=['GET'])
@require_api_key
@require_role('admin')
def get_system_pulse():
    """
    Returns the system health metadata (Sync status, Vector DB stats, Graph DB topology).
    """
    try:
        from src.utils.pulse_service import PulseService
        pulse_data = PulseService.get_system_heartbeat()
        return jsonify(pulse_data)
    except Exception as e:
        logger.error(f"Error fetching system pulse: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/admin/impersonate', methods=['POST', 'OPTIONS'])
@require_api_key
@require_role('admin')
def impersonate_user():
    """
    Generates a shadow-state JWT token for an admin to impersonate a standard user.
    This allows admins to view the User Portal exactly as the target user sees it.
    """
    if request.method == 'OPTIONS':
        return '', 204
    try:
        data = request.get_json()
        target_email = data.get('target_email')
        
        if not target_email:
            return jsonify({"error": "target_email is required"}), 400
            
        from src.database.mongo_storage import SovereignMongoStorage
        import jwt
        import os
        from datetime import datetime, timezone, timedelta
        
        storage = SovereignMongoStorage()
        user_doc = storage.users_col.find_one({"email": target_email})
        
        if not user_doc:
            return jsonify({"error": f"User {target_email} not found in database"}), 404
            
        profile_data = user_doc.get("profile", {})
        jwt_secret = os.environ.get("JWT_SECRET", "default_dev_secret")
        
        # Generate an impersonation JWT
        expiration = datetime.now(timezone.utc) + timedelta(hours=2) # Shorter duration for impersonation
        internal_token = jwt.encode(
            {
                "role": "user", 
                "account_type": "hero",
                "email": target_email,
                "exp": expiration,
                "profile": profile_data,
                "is_impersonation": True,
                "impersonated_by": getattr(request, 'user_email', 'unknown_admin')
            },
            jwt_secret,
            algorithm="HS256"
        )
        
        logger.info(f"SECURITY AUDIT: Admin {getattr(request, 'user_email', 'unknown')} initiated impersonation of {target_email}")
        
        return jsonify({
            "token": internal_token, 
            "role": "user",
            "account_type": "hero",
            "message": f"Successfully impersonating {target_email}"
        })
    except Exception as e:
        logger.error(f"Error during impersonation: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
