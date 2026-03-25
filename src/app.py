import sys
from pathlib import Path

# Add project root to Python path so imports work when run directly
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, time, timedelta
from src.agents.crew_manager_mach2 import run_crew
from src.database.neo4j_client import log_to_neo4j
from src.database.mongo_storage import SovereignMongoStorage
from src.integrations.google_calendar import get_calendar_service
from src.agents.first_serving_porter import run_first_serving_porter
from functools import wraps
import os
import json
import jwt
import hmac
from dotenv import load_dotenv
from pydantic import ValidationError
from src.schemas.api_models import JournalRequestSchema, CalendarRequestSchema

import logging
from logging.handlers import RotatingFileHandler

# Load auth env vars
root = Path(__file__).resolve().parent.parent
load_dotenv(root / ".auth" / ".env")
API_KEY = os.environ.get("PORTER_API_KEY")
if not API_KEY:
    raise ValueError("CRITICAL SECURITY ERROR: PORTER_API_KEY environment variable is missing. It must be set in .auth/.env for secure authentication.")

JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("CRITICAL SECURITY ERROR: JWT_SECRET environment variable is missing. It must be set in .auth/.env for secure token generation.")

# Set up logging
log_dir = root / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "app.log"

logger = logging.getLogger("APP_ROUTER")
logger.setLevel(logging.INFO)
# Remove default handlers
if logger.hasHandlers():
    logger.handlers.clear()
file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
logger.addHandler(file_handler)
# Also log to console
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
logger.addHandler(console_handler)


app = Flask(__name__)
# Restrict CORS to specific local origins instead of '*'
cors_origins = [
    "http://localhost:5000",
    "http://127.0.0.1:5000", 
    "http://localhost:5090",
    "http://127.0.0.1:5090"
]
CORS(app, resources={r"/*": {"origins": cors_origins}})

from flask import make_response

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'OPTIONS':
            response = make_response()
            response.headers.add("Access-Control-Allow-Origin", request.headers.get("Origin", "*"))
            response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
            response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
            return response, 204
            
        supplied_key = request.headers.get("Authorization")
        if not supplied_key:
            return jsonify({"error": "Unauthorized: Missing Authorization header"}), 401
            
        token_str = supplied_key.replace("Bearer ", "")
        
        # Check if it's the raw API Key (used by background python scripts usually)
        if hmac.compare_digest(token_str, API_KEY):
            return f(*args, **kwargs)
            
        # Try checking if it's a valid JWT from the frontend login UI
        try:
            decoded = jwt.decode(token_str, JWT_SECRET, algorithms=["HS256"])
            if decoded.get("role") == "admin":
                return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Unauthorized: Token expired"}), 401
        except jwt.InvalidTokenError:
            pass
            
        return jsonify({"error": "Unauthorized: Invalid credentials"}), 401
    return decorated_function

# Serve front-end files
@app.route('/')
@app.route('/index.html')
def index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/adventure_log')
@app.route('/Adventure_Time_log.html')
def adventure_log():
    return send_from_directory('../frontend', 'Adventure_Time_log.html')

@app.route('/journal_review')
@app.route('/journal_review.html')
def journal_review():
    return send_from_directory('../frontend', 'journal_review.html')

@app.route('/oracle_predictions')
@app.route('/Oracle_predictions.html')
def oracle_predictions():
    return send_from_directory('../frontend', 'Oracle_predictions.html')

@app.route('/inventory')
@app.route('/inventory.html')
def inventory():
    return send_from_directory('../frontend', 'inventory.html')

@app.route('/artifacts')
@app.route('/artifacts.html')
def artifacts():
    return send_from_directory('../frontend', 'artifacts.html')

@app.route('/login')
@app.route('/login.html')
def login_page():
    return send_from_directory('../frontend', 'login.html')

# Serve static files (JS, CSS, etc.)
@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('../frontend/js', filename)

@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory('../frontend/css', filename)

# Initialize Google Calendar service (lazy initialization)
_calendar_service = None

def get_calendar_service_instance():
    """Get or create calendar service instance."""
    global _calendar_service
    if _calendar_service is None:
        _calendar_service = get_calendar_service()
    return _calendar_service


def fetch_calendar_events_for_date(target_date_str: str):
    """
    Helper function to fetch calendar events for a date.
    Can be used both by the route and internally.
    
    Args:
        target_date_str: Date in YYYY-MM-DD format
        
    Returns:
        List of event dictionaries or empty list if error
    """
    try:
        service = get_calendar_service_instance()
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        
        time_min = datetime.combine(target_date, time.min).isoformat() + 'Z'
        time_max = datetime.combine(target_date, time.max).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        return events
    except Exception as e:
        logger.error(f"Error fetching calendar events internally: {e}")
        return []

@app.route('/process_journal', methods=['POST', 'OPTIONS'])
@require_api_key
def process_journal():
    """
    Receives a journal entry and full log data, gets an AI reflection,
    saves the complete log to Neo4j, and returns the reflection.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
        
        try:
            validated_data = JournalRequestSchema(**data)
            journal_entry = validated_data.journal_entry
            log_data = validated_data.log_data.model_dump() if hasattr(validated_data.log_data, 'model_dump') else validated_data.log_data.dict()
        except ValidationError as e:
            logger.error(f"Validation Error: {e}")
            return jsonify({"error": f"Invalid data format: {str(e)}"}), 400
            
        logger.info("Received journal entry request (content redacted for PII)...")
        logger.info(f"Received log data for day: {log_data.get('day')}")
        
        try:
            # Enhance journal entry with calendar context if available
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
                        enhanced_journal_entry = journal_entry + calendar_context
                        logger.info(f"Added {len(events)} calendar events to journal context")
            except Exception as cal_error:
                # Calendar fetch failed, but continue without it
                logger.warning(f"Could not fetch calendar events (non-critical): {cal_error}")
            
            # Run the CrewAI workflow with enhanced context
            crew_result = run_crew(enhanced_journal_entry, log_data)

            # Extract the reflection text (simplified from iteration file)
            if crew_result and hasattr(crew_result, 'tasks_output') and crew_result.tasks_output:
                last_task = crew_result.tasks_output[-1]
                result_text = last_task.raw if hasattr(last_task, 'raw') and last_task.raw else str(last_task)
            elif crew_result and hasattr(crew_result, 'raw'):
                result_text = crew_result.raw
            else:
                result_text = str(crew_result) if crew_result else "Could not retrieve a reflection."

            # Add reflection to the log data for the database
            log_data['reflection'] = result_text

            # 1. Save pristine Frontend log to MongoDB Landing Zone
            mongo_storage = SovereignMongoStorage()
            mongo_doc_id = mongo_storage.save_journal_entry(log_data)
            logger.info(f"MongoDB Journal Saved: {mongo_doc_id}")

            # 2. Save the complete log as a distinct node to Neo4j Identity Graph
            db_confirmation = log_to_neo4j(log_data)
            logger.info(f"Neo4j Confirmation: {db_confirmation}")

            # Return the successful result to the front-end
            # Note: app.js expects "result" key, not "reflection"
            return jsonify({
                "result": result_text,
                "db_status": db_confirmation
            })
        
        except Exception as e:
            # Log error with traceback for debugging
            logger.error(f"Backend Error during CrewAI execution: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    except Exception as e:
        # This outer block catches errors in getting the initial JSON data
        logger.error(f"Error reading request data: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat/porter', methods=['POST', 'OPTIONS'])
@require_api_key
def chat_porter():
    """
    Handles chat interaction with the First-Serving Porter agent.
    """
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"error": "Message required"}), 400
            
        user_msg = data['message']
        logger.info("Received Porter chat message.")
        
        result = run_first_serving_porter(user_msg)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in First-Serving Porter chat: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    """
    Validates the provided password against the PORTER_API_KEY.
    If valid, returns a JWT token valid for 24 hours.
    """
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        data = request.get_json()
        if not data or 'password' not in data:
            return jsonify({"error": "Password required"}), 400
            
        if hmac.compare_digest(data['password'], API_KEY):
            # Generate JWT Token valid for 24 hours
            expiration = datetime.utcnow() + timedelta(hours=24)
            token = jwt.encode(
                {"role": "admin", "exp": expiration},
                JWT_SECRET,
                algorithm="HS256"
            )
            return jsonify({"token": token, "message": "Login successful"})
        else:
            return jsonify({"error": "Invalid password"}), 401
            
    except Exception as e:
        logger.error(f"Error during login: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/inventory', methods=['GET'])
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

@app.route('/api/artifacts/<artifact_name>', methods=['GET', 'POST', 'OPTIONS'])
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


@app.route('/get_calendar_events', methods=['GET'])
@require_api_key
def get_calendar_events():
    """
    Fetches calendar events for a specific date.
    
    Query parameters:
        date: Date in YYYY-MM-DD format (defaults to today if not provided)
    
    Returns:
        JSON with events array, each event containing:
        - title: Event title/summary
        - start: Start time (ISO format)
        - end: End time (ISO format)
        - description: Event description (if available)
    """
    try:
        try:
            req = CalendarRequestSchema(date=request.args.get('date'))
        except ValidationError as e:
            return jsonify({"error": f"Invalid query parameters: {str(e)}"}), 400

        date_str = req.date
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        # Validate date format strictly
        try:
            if len(date_str) != 10:
                raise ValueError("Strict length check failed")
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({"error": "Invalid date format. Use strict YYYY-MM-DD."}), 400
        
        logger.info(f"Fetching calendar events for date: {date_str}")
        
        # Fetch events using helper function
        try:
            events = fetch_calendar_events_for_date(date_str)
        except FileNotFoundError as e:
            return jsonify({"error": f"Google Calendar credentials not found: {e}"}), 500
        except Exception as e:
            return jsonify({"error": f"Failed to fetch calendar events: {e}"}), 500
        
        # Format events for front-end
        formatted_events = []
        for event in events:
            # Get start and end times
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            formatted_events.append({
                'title': event.get('summary', 'No Title'),
                'start': start,
                'end': end,
                'description': event.get('description', ''),
                'location': event.get('location', ''),
                'id': event.get('id', '')
            })
        
        logger.info(f"Found {len(formatted_events)} events for {date_str}")
        
        return jsonify({
            "date": date_str,
            "events": formatted_events,
            "count": len(formatted_events)
        })
        
    except Exception as e:
        logger.error(f"Error fetching calendar events: {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred while fetching calendar events: {str(e)}"}), 500

@app.route('/api/admin/sync_calendar', methods=['POST'])
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

@app.route('/api/admin/inject_foundation', methods=['POST'])
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


if __name__ == '__main__':
    logger.info("==================================================================================")
    logger.warning("Starting the Agentic Personal Porter via Flask's built-in development server.")
    logger.warning("This server is not suitable for production deployments.")
    logger.info("For a production WSGI server, please execute: ./run_production.sh (which uses Gunicorn)")
    logger.info("==================================================================================")
    logger.info("Server starting on port 5090...")
    app.run(debug=True, host='0.0.0.0', port=5090)

