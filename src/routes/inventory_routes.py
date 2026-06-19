"""
Inventory and artifact routes.

Handles Neo4j graph data retrieval, hero inventory,
and hero artifact CRUD (with MongoDB as source of truth).
"""
import logging
from flask import Blueprint, request, jsonify

from src.routes.auth_middleware import require_api_key
from src.database.mongo_storage import SovereignMongoStorage
from src.utils.path_utils import get_project_root

inventory_bp = Blueprint('inventory', __name__)
logger = logging.getLogger("APP_ROUTER")

# Project root for filesystem artifact fallback
project_root = get_project_root()

@inventory_bp.route('/graph_data', methods=['GET'])
@require_api_key
def get_graph_data():
    """
    Fetches the simplified graph topology for visualization.
    """
    try:
        from src.database.neo4j_client.read_operations import get_full_graph_topology
        limit = request.args.get('limit', default=500, type=int)
        graph_data = get_full_graph_topology(limit=limit)
        return jsonify(graph_data)
    except Exception as e:
        logger.error(f"Error fetching graph data: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@inventory_bp.route('/inventory', methods=['GET'])
@require_api_key
def get_inventory():
    """
    Fetches the 'Valuable Detours' and skills acquired by the user from Neo4j.
    """
    try:
        from src.database.neo4j_client import get_all_detours
        from src.database.mongo_storage import SovereignMongoStorage
        
        user_email = getattr(request, 'user_email', 'Hero')
        if user_email != 'Hero':
            mongo_storage = SovereignMongoStorage()
            user_doc = mongo_storage.get_user_by_email(user_email)
            username = user_doc.get("username", "Hero") if user_doc else "Hero"
        else:
            username = 'Hero'
            
        detours = get_all_detours(username=username)

        response_data = {
            "valuable_detours": detours,
            "quests": [],
            "skills": [],
            "equipment": [],
            "stats": {"level": 5, "strength": 10, "intelligence": 15, "charisma": 12},
            "finances": {"gold": 1500, "investment_growth": "+5%"}
        }
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error fetching inventory: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@inventory_bp.route('/artifacts/scan', methods=['GET'])
@require_api_key
def scan_artifacts():
    """
    Triggers the Identity Architect to scan hero_origin.json for chronological gaps.
    """
    try:
        from src.agents.gtky_identity_architect import GTKYIdentityArchitect
        mongo_storage = SovereignMongoStorage()
        user_doc = mongo_storage.get_user_by_email(request.user_email)
        username = user_doc.get("username", "system") if user_doc else "system"
        
        architect = GTKYIdentityArchitect(username=username)
        scan_results = architect.scan_for_missing_origin()
        return jsonify({"status": "success", "results": scan_results})
    except Exception as e:
        logger.error(f"Error scanning artifacts: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@inventory_bp.route('/artifacts/<artifact_name>', methods=['GET', 'POST', 'OPTIONS'])
@require_api_key
def manage_artifact(artifact_name):
    """
    Fetch or update a JSON artifact.
    """
    if request.method == 'OPTIONS':
        return '', 204

    allowed_artifacts = ['hero_origin.json', 'hero_ambition.json', 'hero_detriments.json', 'category_mapping.json']
    if artifact_name not in allowed_artifacts:
        return jsonify({"error": "Invalid artifact name"}), 400

    if artifact_name in ['hero_detriments.json', 'category_mapping.json']:
        artifact_path = project_root / '.auth' / artifact_name
    else:
        artifact_path = project_root / 'data' / 'hero_artifacts' / artifact_name

    if request.method == 'GET':
        try:
            mongo_storage = SovereignMongoStorage()
            user_doc = mongo_storage.get_user_by_email(request.user_email)
            username = user_doc.get("username", "unknown") if user_doc else "unknown"

            data = mongo_storage.get_hero_artifact(artifact_name, username)

            # If not in MongoDB yet, return an empty template based on the file name
            if not data:
                if 'hero_origin' in artifact_name:
                    data = {
                        "origin_story": {
                            "epochs": [
                                {
                                    "name": "Update your hero origin! Proper Instructions coming soon.",
                                    "timeframe": "TBD",
                                    "experiences": [],
                                    "experience candidate": []
                                }
                            ]
                        }
                    }
                else:
                    data = {
                        "message": f"Update your {artifact_name.replace('.json', '')}! Proper Instructions coming soon.",
                        "data": {}
                    }
                
                # Save the new template for the user so it persists
                mongo_storage.save_hero_artifact(artifact_name, data, username)

            return jsonify(data)
        except Exception as e:
            logger.error(f"Error fetching artifact {artifact_name}: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "No JSON data provided"}), 400

            mongo_storage = SovereignMongoStorage()
            user_doc = mongo_storage.get_user_by_email(request.user_email)
            username = user_doc.get("username", "unknown") if user_doc else "unknown"

            # Update Mongo as Source of Truth
            mongo_storage.save_hero_artifact(artifact_name, data, username)

            return jsonify({"status": "success", "message": f"{artifact_name} updated successfully in MongoDB for user {username}"})
        except Exception as e:
            logger.error(f"Error saving artifact {artifact_name}: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500
