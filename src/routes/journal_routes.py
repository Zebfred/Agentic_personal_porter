"""
Journal and daily log routes.

Handles saving time-chunk logs, retrieving historical monthly data,
and triggering the daily AI reflection via CrewAI.
"""
import os
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from src.routes.auth_middleware import require_api_key
from src.database.neo4j_client import log_to_neo4j
from src.database.mongo_storage import SovereignMongoStorage
from src.schemas.api_models import JournalLogBase, DailyReflectionRequestSchema
from src.agents.crew_manager_mach3 import run_crew
from src.routes.calendar_routes import fetch_calendar_events_for_date

journal_bp = Blueprint('journal', __name__)
logger = logging.getLogger("APP_ROUTER")


@journal_bp.route('/api/save_log', methods=['POST', 'OPTIONS'])
@require_api_key
def save_log():
    """
    Saves a log entry to MongoDB and Neo4j without triggering AI reflection.
    """
    if request.method == 'OPTIONS':
        return '', 204
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        try:
            validated_data = JournalLogBase(**data)
            log_data_dict = validated_data.model_dump() if hasattr(validated_data, 'model_dump') else validated_data.dict()
        except ValidationError as e:
            logger.error(f"Validation Error in save_log: {e}")
            return jsonify({"error": f"Invalid data format: {str(e)}"}), 400

        # 1. Save pristine Frontend log to MongoDB Landing Zone
        mongo_storage = SovereignMongoStorage()
        mongo_doc_id = mongo_storage.save_journal_entry(log_data_dict)

        # 2. Save the complete log as a distinct node to Neo4j Identity Graph
        db_confirmation = log_to_neo4j(log_data_dict)

        return jsonify({
            "status": "success",
            "mongo_id": mongo_doc_id,
            "db_status": db_confirmation
        })
    except Exception as e:
        logger.error(f"Error saving log: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@journal_bp.route('/api/logs', methods=['GET', 'OPTIONS'])
@require_api_key
def get_historical_logs():
    """
    Fetches the nested monthly journal entries for the UI calendar.
    Query params:
        month: str format 'YYYY-MM'
    """
    if request.method == 'OPTIONS':
        return '', 204
    try:
        month = request.args.get('month')
        if not month:
            return jsonify({"error": "Missing month parameter (format: YYYY-MM)"}), 400

        mongo_storage = SovereignMongoStorage()
        user_id = os.environ.get("HERO_NAME", "Hero")
        month_data = mongo_storage.get_monthly_log(month, user_id=user_id)

        return jsonify({
            "status": "success",
            "data": month_data
        })
    except Exception as e:
        logger.error(f"Error fetching monthly logs: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@journal_bp.route('/process_journal', methods=['POST', 'OPTIONS'])
@require_api_key
def process_journal():
    """
    Generates a daily reflection based on the day's logs.
    Saves the reflection to a dedicated collection.
    """
    if request.method == 'OPTIONS':
        return '', 204
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        try:
            validated_data = DailyReflectionRequestSchema(**data)
            journal_entry = validated_data.journal_entry
            log_data = validated_data.log_data.model_dump() if hasattr(validated_data.log_data, 'model_dump') else validated_data.log_data.dict()
            day = log_data.get('day', 'Unknown')
        except ValidationError as e:
            logger.error(f"Validation Error: {e}")
            return jsonify({"error": f"Invalid data format: {str(e)}"}), 400

        logger.info(f"Generating daily reflection for {day}...")

        try:
            # Enhance journal entry with calendar context
            enhanced_journal_entry = journal_entry

            # Try to fetch calendar events for the day
            try:
                day = log_data.get('day')
                if day:
                    # Convert day name to date (approximate - use current week)
                    today = datetime.now()
                    day_map = {
                        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                        'friday': 4, 'saturday': 5, 'sunday': 6
                    }
                    day_index = day_map.get(day.lower(), 0)
                    current_day_index = today.weekday()
                    days_diff = day_index - current_day_index
                    target_date = (today + timedelta(days=days_diff)).strftime('%Y-%m-%d')

                    # Fetch calendar events using helper function
                    events = fetch_calendar_events_for_date(target_date)

                    if events:
                        event_titles = [e.get('summary', 'Untitled') for e in events]
                        calendar_context = f"\n\nCalendar Events for {day}: {', '.join(event_titles)}"
                        #enhanced_journal_entry = journal_entry + calendar_context
                        logger.info(f"Added {len(events)} calendar events to journal context")
            except Exception as cal_err:
                logger.warning(f"Calendar context failed: {cal_err}")

            # Run CrewAI reflection
            result_text = run_crew(enhanced_journal_entry, log_data)

            # Save Reflection to dedicated collection
            mongo_storage = SovereignMongoStorage()
            reflection_id = mongo_storage.save_agent_reflection({
                "day": day,
                "user_id": os.environ.get("HERO_NAME", "Hero"),
                "reflection_text": result_text,
                "metadata": {
                    "source": "daily_recon",
                    "timestamp": datetime.now().isoformat()
                }
            })

            return jsonify({
                "result": result_text,
                "reflection_id": reflection_id
            })

        except Exception as e:
            logger.error(f"Backend Error during CrewAI execution: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    except Exception as e:
        logger.error(f"Error reading request data: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@journal_bp.route('/api/journal/edit_event', methods=['POST', 'OPTIONS'])
@require_api_key
def edit_journal_event():
    """
    Allows the human-in-the-loop to aggressively edit the raw timeline logs.
    Includes deleting nonsense events, or rigorously mapping misclassified events.
    If mapped, natively upgrades category_mapping.json to learn from the human.
    """
    if request.method == 'OPTIONS':
        return '', 204
    try:
        data = request.get_json()
        if not data or 'gcal_id' not in data or 'action' not in data:
            return jsonify({"error": "Missing required fields (gcal_id, action)"}), 400

        action = data['action']
        gcal_id = data['gcal_id']
        mongo = SovereignMongoStorage()

        if action == 'delete':
            mongo.raw_col.delete_one({"gcal_id": gcal_id})
            mongo.formatted_col.delete_one({"gcal_id": gcal_id})
            return jsonify({"status": "success", "message": "Event permanently deleted from Mongo."})

        elif action == 'reclassify':
            new_pillar = data.get('new_pillar')
            event_title = data.get('summary')
            
            if not new_pillar or not event_title:
                return jsonify({"error": "reclassify requires 'new_pillar' and 'summary'."}), 400

            # 1. Update the actual event
            mongo.formatted_col.update_one(
                {"gcal_id": gcal_id}, 
                {"$set": {"pillar": new_pillar, "classification_verified": True}}
            )

            # 2. Append to Knowledge Base (category_mapping.json -> MongoDB)
            cat_map = mongo.get_hero_artifact('category_mapping.json')
            if cat_map:
                intent_map = cat_map.get('intent_to_actual_mapping', {})
                actual_target = intent_map.get(new_pillar)
                
                # If they used the raw name directly e.g. "Leisures_related"
                if not actual_target and new_pillar in cat_map.get('actual_categorization_with_keywords', {}):
                    actual_target = new_pillar
                
                if actual_target:
                    target_bucket = cat_map['actual_categorization_with_keywords'].get(actual_target, {})
                    if 'General' in target_bucket:
                        # Append the raw event title dynamically to train the system
                        if event_title not in target_bucket['General']:
                            target_bucket['General'].append(event_title.lower())
                            mongo.save_hero_artifact('category_mapping.json', cat_map)
                            logger.info(f"Appended '{event_title}' to {actual_target} General Bucket.")

            return jsonify({"status": "success", "message": f"Successfully mapped '{event_title}' to {new_pillar}."})
            
        else:
            return jsonify({"error": f"Unknown action: {action}"}), 400

    except Exception as e:
        logger.error(f"Error editing journal event: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
