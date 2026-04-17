"""
Inventory and artifact routes.

Handles Neo4j graph data retrieval, hero inventory,
and hero artifact CRUD (with MongoDB as source of truth).
"""
import os
import json
import logging
from pathlib import Path
from flask import Blueprint, request, jsonify

from src.routes.auth_middleware import require_api_key
from src.database.mongo_storage import SovereignMongoStorage

inventory_bp = Blueprint('inventory', __name__)
logger = logging.getLogger("APP_ROUTER")

# Project root for filesystem artifact fallback
project_root = Path(__file__).resolve().parent.parent.parent


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
        from src.database.neo4j_client import get_valuable_detours
        detours = get_valuable_detours(user_name=os.environ.get("HERO_NAME", "Hero"))

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


@inventory_bp.route('/artifacts/<artifact_name>', methods=['GET', 'POST', 'OPTIONS'])
@require_api_key
def manage_artifact(artifact_name):
    """
    Fetch or update a JSON artifact.
    """
    if request.method == 'OPTIONS':
        return '', 204

    allowed_artifacts = ['hero_origin.json', 'hero_ambition.json', 'hero_detriments.json']
    if artifact_name not in allowed_artifacts:
        return jsonify({"error": "Invalid artifact name"}), 400

    if artifact_name == 'hero_detriments.json':
        artifact_path = project_root / '.auth' / artifact_name
    else:
        artifact_path = project_root / 'data' / 'hero_artifacts' / artifact_name

    if request.method == 'GET':
        try:
            mongo_storage = SovereignMongoStorage()
            data = mongo_storage.get_hero_artifact(artifact_name)

            # If not in MongoDB yet, seed it from the filesystem
            if not data:
                if not artifact_path.exists():
                    return jsonify({"error": "Artifact not found"}), 404
                with open(artifact_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                mongo_storage.save_hero_artifact(artifact_name, data)

            return jsonify(data)
        except Exception as e:
            logger.error(f"Error fetching artifact {artifact_name}: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "No JSON data provided"}), 400

            # Keep flat-file synchronized as a fallback
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            with open(artifact_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)

            # Update Mongo as Source of Truth
            mongo_storage = SovereignMongoStorage()
            mongo_storage.save_hero_artifact(artifact_name, data)

            return jsonify({"status": "success", "message": f"{artifact_name} updated successfully in MongoDB"})
        except Exception as e:
            logger.error(f"Error saving artifact {artifact_name}: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500
