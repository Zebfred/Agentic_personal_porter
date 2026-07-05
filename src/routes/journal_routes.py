"""
Journal and daily log routes.

Handles saving time-chunk logs, retrieving historical monthly data,
and triggering the daily AI reflection via LangGraph.
"""
import logging
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from src.routes.auth_middleware import require_api_key
from src.database.neo4j_client import log_to_neo4j
from src.database.mongo_storage import SovereignMongoStorage
from src.schemas.api_models import JournalLogBase, DailyReflectionRequestSchema
from src.agents.porter_manager import run_porter_reflection
from src.routes.calendar_routes import fetch_calendar_events_for_date
from src.database.mongo_client.connection import MongoConnectionManager
from src.config import MongoConfig
from src.database.mongo_client.uuid_manager import UUIDGenerator
from src.utils.correlation import generate_correlation_id, generate_freeform_correlation_id
from src.events.publisher import publish_journal_event

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

        # If flat format doesn't have sync_status, initialize it
        if "sync_status" not in log_data_dict:
            log_data_dict["sync_status"] = {"neo4j": False, "mongo_actuals": False, "unified": False}
        if "saga_status" not in log_data_dict:
            log_data_dict["saga_status"] = {
                "status": "RECEIVED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": f"Journal entry received for day {log_data_dict.get('day')} chunk {log_data_dict.get('timeChunk')}"
            }

        # 1. Save pristine Frontend log to MongoDB Landing Zone
        mongo_storage = SovereignMongoStorage()

        user_email = getattr(request, 'user_email', 'Hero')
        username = 'Hero'
        if user_email != 'Hero':
            user_doc = mongo_storage.get_user_by_email(user_email)
            username = user_doc.get("username", "Hero") if user_doc else "Hero"

        day_str = str(log_data_dict.get("day", "unknown_date"))
        time_chunk = str(log_data_dict.get("timeChunk", "unknown_time"))

        # Generate deterministic correlation ID for cross-system lineage
        correlation_id = generate_correlation_id(
            user_id=username,
            day_str=day_str,
            time_chunk=time_chunk,
            entry_type="log"
        )
        logger.info(f"[LINEAGE] Generated correlation_id: {correlation_id}")

        # 1. Save pristine Frontend log to MongoDB Landing Zone (with lineage)
        mongo_doc_id = mongo_storage.save_journal_entry(log_data_dict, user_id=username, correlation_id=correlation_id)

        # 2. Save the complete log as a distinct node to Neo4j Identity Graph
        db_confirmation = "Failed"
        try:
            db_confirmation = log_to_neo4j(log_data_dict, username, correlation_id=correlation_id)
            mongo_storage.update_journal_sync_status(mongo_doc_id, day_str, time_chunk, {
                "neo4j": True,
                "saga_status.status": "GRAPH_INJECTED",
                "saga_status.timestamp": datetime.now(timezone.utc).isoformat(),
                "saga_status.details": f"Injected to Neo4j successfully: {db_confirmation}"
            }, user_id=username)
        except Exception as e_neo:
            logger.warning(f"Failed to write to Neo4j: {e_neo}")
            mongo_storage.update_journal_sync_status(mongo_doc_id, day_str, time_chunk, {
                "neo4j": False,
                "neo4j_error": str(e_neo),
                "saga_status.status": "FAILED",
                "saga_status.details": f"Neo4j Injection Failed: {e_neo}"
            }, user_id=username)

        # 3. Mach 3 Rework: Write strictly to event_actuals and unified_events as ground truth
        try:
            db = MongoConnectionManager.get_db()
            actual_col = db[MongoConfig.ACTUAL_COLLECTION]
            unified_col = db[MongoConfig.UNIFIED_EVENTS_COLLECTION]

            synthetic_gcal_id = f"manual_log_{day_str}_{time_chunk}_{mongo_doc_id}"
            event_uuid = UUIDGenerator.generate_for_event(synthetic_gcal_id, username)

            intent_payload = {
                "title": log_data_dict.get("intention", "Weekly Expectation"),
                "description": log_data_dict.get("intention", "Weekly Expectation"),
            }

            actual_payload = {
                "title": log_data_dict.get("title", "Adventure Log Entry"),
                "category": log_data_dict.get("category", "General"),
                "energy_spent": int(log_data_dict.get("energy_spent", 60)),
                "status": "Verified Log",
                "matches_intent": log_data_dict.get("matchesIntent", False)
            }

            time_slot = {
                "start": day_str,
                "end": day_str
            }

            actual_col.update_one(
                {"_id": event_uuid},
                {"$set": {
                    "user_id": username,
                    "gcal_id": synthetic_gcal_id,
                    "time_slot": time_slot,
                    "actual": actual_payload,
                    "correlation_id": correlation_id,
                    "metadata": {
                        "source": "adventure_log",
                        "last_sync": datetime.now(timezone.utc).isoformat()
                    }
                }},
                upsert=True
            )

            unified_col.update_one(
                {"_id": event_uuid},
                {"$set": {
                    "user_id": username,
                    "time_slot": time_slot,
                    "intent": intent_payload,
                    "actual": actual_payload,
                    "correlation_id": correlation_id
                }},
                upsert=True
            )
            mongo_storage.update_journal_sync_status(mongo_doc_id, day_str, time_chunk, {"mongo_actuals": True, "unified": True}, user_id=username)
        except Exception as e_actual:
            logger.warning(f"Failed to write to actuals/unified: {e_actual}")
            mongo_storage.update_journal_sync_status(mongo_doc_id, day_str, time_chunk, {"mongo_actuals": False, "unified": False, "mongo_error": str(e_actual)}, user_id=username)

        # 4. Publish CDC event for async VectorDB embedding (hybrid mode)
        publish_journal_event(
            correlation_id=correlation_id,
            entry_type="log",
            payload=log_data_dict,
            user_id=username
        )

        return jsonify({
            "status": "success",
            "mongo_id": mongo_doc_id,
            "db_status": db_confirmation,
            "correlation_id": correlation_id
        })
    except Exception as e:
        logger.error(f"Error saving log: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@journal_bp.route('/api/planning/weekly', methods=['POST', 'OPTIONS'])
@require_api_key
def save_weekly_expectation():
    """
    Saves a Weekly Expectation mapping it to the (Week) node in Neo4j.
    """
    if request.method == 'OPTIONS':
        return '', 204
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        week_start_date = data.get("week_start_date")
        expectation_text = data.get("expectation_text")

        user_email = getattr(request, 'user_email', 'Hero')
        mongo_storage = SovereignMongoStorage()
        user_doc = mongo_storage.get_user_by_email(user_email)
        username = user_doc.get("username", "Hero") if user_doc else "Hero"

        if not week_start_date or not expectation_text:
            return jsonify({"error": "Missing week_start_date or expectation_text"}), 400

        updated_at = datetime.now(timezone.utc).isoformat()

        # Generate deterministic correlation ID for cross-system lineage
        correlation_id = generate_correlation_id(
            user_id=username,
            day_str=week_start_date,
            entry_type="weekly"
        )
        logger.info(f"[LINEAGE] Generated weekly correlation_id: {correlation_id}")

        # Save to MongoDB weekly_expectations
        db = MongoConnectionManager.get_db()
        week_col = db["weekly_expectations"]

        week_col.update_one(
            {"user_id": username, "week_start_date": week_start_date},
            {"$set": {
                "expectation_text": expectation_text,
                "updated_at": updated_at,
                "correlation_id": correlation_id
            }},
            upsert=True
        )

        # Inject to Neo4j (Week)-[:PLANNED_AS]->(Intention)
        neo4j_status = "Failed"
        try:
            from src.database.neo4j_client.connection import get_driver
            with get_driver().session() as session:
                query = """
                MERGE (u:Hero {id: $username})
                MERGE (w:Week {id: $week_start_date})
                MERGE (u)-[:EXPERIENCED]->(w)
                MERGE (i:Intention {type: "Weekly Expectation", week: $week_start_date})
                SET i.text = $expectation_text, i.updated_at = $timestamp, i.source_id = $correlation_id
                MERGE (w)-[:PLANNED_AS]->(i)
                """
                session.run(query, {
                    "username": username,
                    "week_start_date": week_start_date,
                    "expectation_text": expectation_text,
                    "timestamp": updated_at,
                    "correlation_id": correlation_id
                })
                neo4j_status = "Success"
        except Exception as neo_e:
            logger.warning(f"Failed to inject weekly expectation to Neo4j: {neo_e}")
            neo4j_status = f"Neo4j Error: {neo_e}"

        # Publish CDC event for async VectorDB embedding (hybrid mode)
        publish_journal_event(
            correlation_id=correlation_id,
            entry_type="weekly",
            payload={"expectation_text": expectation_text, "week_start_date": week_start_date},
            user_id=username
        )

        return jsonify({
            "status": "success",
            "neo4j_status": neo4j_status,
            "updated_at": updated_at
        })

    except Exception as e:
        logger.error(f"Error saving weekly expectation: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@journal_bp.route('/api/planning/weekly', methods=['GET'])
@require_api_key
def get_weekly_expectation():
    """
    Fetches the Weekly Expectation for a given week_start_date.
    """
    try:
        week_start_date = request.args.get("week_start_date")
        if not week_start_date:
            return jsonify({"error": "Missing week_start_date"}), 400

        user_email = getattr(request, 'user_email', 'Hero')
        mongo_storage = SovereignMongoStorage()
        user_doc = mongo_storage.get_user_by_email(user_email)
        username = user_doc.get("username", "Hero") if user_doc else "Hero"

        db = MongoConnectionManager.get_db()
        week_col = db["weekly_expectations"]
        doc = week_col.find_one({"user_id": username, "week_start_date": week_start_date})

        return jsonify({
            "status": "success",
            "data": {
                "expectation_text": doc.get("expectation_text", "") if doc else "",
                "updated_at": doc.get("updated_at") if doc else None
            }
        })
    except Exception as e:
        logger.error(f"Error fetching weekly expectation: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@journal_bp.route('/api/journal/freeform', methods=['POST', 'OPTIONS'])
@require_api_key
def save_freeform_journal():
    if request.method == 'OPTIONS':
        return '', 204
    try:
        data = request.get_json()
        date_str = data.get("date")
        text = data.get("text")
        if not date_str or text is None:
            return jsonify({"error": "Missing date or text"}), 400
        user_email = getattr(request, 'user_email', 'Hero')
        mongo_storage = SovereignMongoStorage()
        user_doc = mongo_storage.get_user_by_email(user_email)
        username = user_doc.get("username", "Hero") if user_doc else "Hero"

        # Generate freeform correlation ID with HH:MM:SS timestamp
        correlation_id = generate_freeform_correlation_id(
            user_id=username,
            day_str=date_str
        )
        logger.info(f"[LINEAGE] Generated freeform correlation_id: {correlation_id}")

        updated_at = mongo_storage.save_freeform_journal(date_str, text, username, correlation_id=correlation_id)

        # Publish CDC event for async VectorDB embedding (hybrid mode)
        publish_journal_event(
            correlation_id=correlation_id,
            entry_type="freeform",
            payload={"text": text, "date": date_str},
            user_id=username
        )

        return jsonify({"status": "success", "updated_at": updated_at, "correlation_id": correlation_id})
    except Exception as e:
        logger.error(f"Error saving freeform journal: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@journal_bp.route('/api/journal/freeform', methods=['GET'])
@require_api_key
def get_freeform_journal():
    try:
        date_str = request.args.get("date")
        if not date_str:
            return jsonify({"error": "Missing date"}), 400
        user_email = getattr(request, 'user_email', 'Hero')
        mongo_storage = SovereignMongoStorage()
        user_doc = mongo_storage.get_user_by_email(user_email)
        username = user_doc.get("username", "Hero") if user_doc else "Hero"
        doc = mongo_storage.get_freeform_journal(date_str, username)
        # convert datetime to string if it was saved prior to the isoformat change
        updated_at = doc.get("updated_at")
        if updated_at and not isinstance(updated_at, str):
            updated_at = updated_at.isoformat()
        return jsonify({"status": "success", "data": {"text": doc.get("text", ""), "updated_at": updated_at}})
    except Exception as e:
        logger.error(f"Error fetching freeform journal: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@journal_bp.route('/api/journal/history', methods=['GET'])
@require_api_key
def get_journal_history():
    """
    Fetches the combined history of recent freeform journals and weekly expectations.
    """
    try:
        user_email = getattr(request, 'user_email', 'Hero')
        mongo_storage = SovereignMongoStorage()
        user_doc = mongo_storage.get_user_by_email(user_email)
        username = user_doc.get("username", "Hero") if user_doc else "Hero"

        limit = int(request.args.get("limit", 10))
        correlation_id = request.args.get("correlation_id")

        history = mongo_storage.get_journal_and_expectation_history(username, limit=limit, correlation_id=correlation_id)

        # Convert datetime to string for json serialization if necessary
        for item in history:
            updated_at = item.get("updated_at")
            if updated_at and not isinstance(updated_at, str):
                item["updated_at"] = updated_at.isoformat()

        return jsonify({"status": "success", "data": history})
    except Exception as e:
        logger.error(f"Error fetching journal history: {e}", exc_info=True)
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
        user_email = getattr(request, 'user_email', 'Hero')
        user_doc = mongo_storage.get_user_by_email(user_email)
        username = user_doc.get("username", "Hero") if user_doc else "Hero"
        month_data = mongo_storage.get_monthly_log(month, user_id=username)

        return jsonify({
            "status": "success",
            "data": month_data
        })
    except Exception as e:
        logger.error(f"Error fetching monthly logs: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@journal_bp.route('/api/logs/year', methods=['GET', 'OPTIONS'])
@require_api_key
def get_yearly_logs_route():
    """
    Fetches all nested monthly journal entries for a given year.
    Query params:
        year: str format 'YYYY'
    """
    if request.method == 'OPTIONS':
        return '', 204
    try:
        year = request.args.get('year')
        if not year:
            return jsonify({"error": "Missing year parameter (format: YYYY)"}), 400

        mongo_storage = SovereignMongoStorage()
        user_email = getattr(request, 'user_email', 'Hero')
        user_doc = mongo_storage.get_user_by_email(user_email)
        username = user_doc.get("username", "Hero") if user_doc else "Hero"
        data = mongo_storage.get_yearly_logs(year, user_id=username)

        return jsonify({
            "status": "success",
            "data": data
        })
    except Exception as e:
        logger.error(f"Error fetching yearly logs: {e}", exc_info=True)
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
                    events = fetch_calendar_events_for_date(target_date, getattr(request, 'user_email', None))

                    if events:
                        event_titles = [e.get('summary', 'Untitled') for e in events]
                        calendar_context = f"\n\nCalendar Events for {day}: {', '.join(event_titles)}"
                        #enhanced_journal_entry = journal_entry + calendar_context
                        logger.info(f"Added {len(events)} calendar events to journal context")
            except Exception as cal_err:
                logger.warning(f"Calendar context failed: {cal_err}")

            # Run LangGraph reflection
            result_text = run_porter_reflection(enhanced_journal_entry, log_data)

            # Save Reflection to dedicated collection
            mongo_storage = SovereignMongoStorage()
            user_email = getattr(request, 'user_email', 'Hero')
            user_doc = mongo_storage.get_user_by_email(user_email)
            username = user_doc.get("username", "Hero") if user_doc else "Hero"
            
            reflection_id = mongo_storage.save_agent_reflection({
                "day": day,
                "user_id": username,
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
            logger.error(f"Backend Error during LangGraph execution: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    except Exception as e:
        logger.error(f"Error reading request data: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@journal_bp.route('/api/journal/reflection', methods=['GET', 'OPTIONS'])
@require_api_key
def get_daily_reflection():
    """
    Fetches the agent reflection for a specific day.
    """
    if request.method == 'OPTIONS':
        return '', 204
    try:
        date_str = request.args.get("date")
        if not date_str:
            return jsonify({"error": "Missing date parameter"}), 400

        user_email = getattr(request, 'user_email', 'Hero')
        mongo_storage = SovereignMongoStorage()
        user_doc = mongo_storage.get_user_by_email(user_email)
        username = user_doc.get("username", "Hero") if user_doc else "Hero"

        doc = mongo_storage.get_agent_reflection(date_str, username)

        return jsonify({"status": "success", "data": doc})
    except Exception as e:
        logger.error(f"Error fetching reflection: {e}", exc_info=True)
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
            cat_map = mongo.get_hero_artifact('category_mapping.json', "system")
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
                            mongo.save_hero_artifact('category_mapping.json', cat_map, "system")
                            logger.info(f"Appended '{event_title}' to {actual_target} General Bucket.")

            return jsonify({"status": "success", "message": f"Successfully mapped '{event_title}' to {new_pillar}."})

        else:
            return jsonify({"error": f"Unknown action: {action}"}), 400

    except Exception as e:
        logger.error(f"Error editing journal event: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@journal_bp.route('/api/journal/review_data', methods=['GET'])
@require_api_key
def get_journal_review_data():
    """
    Returns data for the Journal Review page: Intentions (Weekly & Hero) and Actual Events (Time Chunks).
    """
    try:
        date_str = request.args.get('date') # e.g. YYYY-MM-DD
        if not date_str:
            return jsonify({"error": "Missing date parameter"}), 400

        user_email = getattr(request, 'user_email', None)
        if not user_email:
            return jsonify({"error": "User email context not found"}), 400

        from src.database.mongo_storage import SovereignMongoStorage
        mongo = SovereignMongoStorage()

        # 1. Fetch Intentions (Weekly Planning and Hero Ambition)
        active_intentions = []
        weekly_plan = mongo.db['weekly_planning'].find_one({"user_id": user_email}, sort=[("week_start_date", -1)])
        if weekly_plan and weekly_plan.get("expectation_text"):
            active_intentions.append(f"Weekly Expectation: {weekly_plan['expectation_text']}")

        hero_ambition = mongo.get_hero_artifact("hero_ambition.json")
        if hero_ambition and isinstance(hero_ambition, dict):
            # Extract some high-level ambitions if available
            for k, v in hero_ambition.items():
                if isinstance(v, str):
                    active_intentions.append(f"{k.capitalize()}: {v}")
                elif isinstance(v, dict) and "description" in v:
                    active_intentions.append(f"{k.capitalize()}: {v['description']}")
                elif isinstance(v, list) and v and isinstance(v[0], str):
                    active_intentions.append(f"{k.capitalize()}: {', '.join(v)}")

        # If still empty, add a placeholder
        if not active_intentions:
            active_intentions.append("No stated weekly ambitions or Hero Intentions found.")

        # 2. Fetch Actual Events (Time Chunks from unified_events / event_actuals for the given date)
        observations = []

        query = {
            "user_id": user_email,
            "time_slot.start": {"$regex": f"^{date_str}"}
        }

        unified = list(mongo.db['unified_events'].find(query))
        actuals = list(mongo.db['event_actuals'].find(query))

        for event in unified:
            # Unified events could be intents or matched actuals
            title = event.get('intent', {}).get('title', 'Unknown')
            pillar = event.get('intent', {}).get('pillar_id', 'Uncategorized')
            duration = event.get('intent', {}).get('duration_minutes', 0)
            status = "Aligned"
            if pillar == "Uncategorized":
                status = "Fog of War"

            # If there's an actual component in the unified event
            if 'actual' in event:
                title = event['actual'].get('title', title)
                pillar = event['actual'].get('pillar_id', pillar)
                duration = event['actual'].get('duration_minutes', duration)
                if event['actual'].get('detour_type'):
                    status = "Valuable Detour" if event['actual']['detour_type'] == 'valuable' else "Detrimental Detour"

            observations.append({
                "title": title,
                "pillar": pillar,
                "duration": duration,
                "status": status
            })

        for event in actuals:
            title = event.get('actual', {}).get('title', 'Unknown')
            pillar = event.get('actual', {}).get('pillar_id', 'Uncategorized')
            duration = event.get('actual', {}).get('duration_minutes', 0)
            status = "Fog of War" if pillar == "Uncategorized" else "Valuable Detour"
            if event.get('actual', {}).get('detour_type') == 'detrimental':
                status = "Detrimental Detour"

            observations.append({
                "title": title,
                "pillar": pillar,
                "duration": duration,
                "status": status
            })

        return jsonify({
            "status": "success",
            "data": {
                "active_intentions": active_intentions,
                "observations": observations
            }
        })

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error fetching journal review data: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
