import sys
from pathlib import Path

# Add project root to Python path so imports work when run directly
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, time, timedelta
from src.main import run_crew
from src.database.neo4j_db import log_to_neo4j
from src.integrations.google_calendar import get_calendar_service


app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

# Serve front-end files
@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/inventory')
def inventory():
    return send_from_directory('../frontend', 'inventory.html')

# Serve static files (JS, CSS, etc.)
@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('../frontend/js', filename)

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
        print(f"Error fetching calendar events internally: {e}")
        return []

@app.route('/process_journal', methods=['POST'])
def process_journal():
    """
    Receives a journal entry and full log data, gets an AI reflection,
    saves the complete log to Neo4j, and returns the reflection.
    """
    try:
        data = request.get_json()
        journal_entry = data.get('journal_entry')
        log_data = data.get('log_data')
        
        print(f"Received journal entry: {journal_entry[:100] if journal_entry else 'None'}...")
        print(f"Received log data for day: {log_data.get('day') if log_data else 'None'}")
        
        if not journal_entry or not log_data:
            # --- MORE DESCRIPTIVE 400 ERROR ---
            error_message = "Incomplete data. "
            if not journal_entry:
                error_message += "'journal_entry' is missing. "
            if not log_data:
                error_message += "'log_data' is missing. Check app.js payload construction."
            print(f"Returning 400 error: {error_message}")
            return jsonify({"error": error_message}), 400
        
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
                        print(f"Added {len(events)} calendar events to journal context")
            except Exception as cal_error:
                # Calendar fetch failed, but continue without it
                print(f"Could not fetch calendar events (non-critical): {cal_error}")
            
            # Run the CrewAI workflow with enhanced context
            crew_result = run_crew(enhanced_journal_entry)

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

            # Save the complete log to Neo4j
            db_confirmation = log_to_neo4j(log_data)
            print(f"Neo4j Confirmation: {db_confirmation}")

            # Return the successful result to the front-end
            # Note: app.js expects "result" key, not "reflection"
            return jsonify({
                "result": result_text,
                "db_status": db_confirmation
            })
        
        except Exception as e:
            # Log error with traceback for debugging
            print(f"Backend Error during CrewAI execution: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    except Exception as e:
        # This outer block catches errors in getting the initial JSON data
        print(f"Error reading request data: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/get_calendar_events', methods=['GET'])
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
        # Get date parameter or use today
        date_str = request.args.get('date')
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        # Validate date format
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({"error": f"Invalid date format. Use YYYY-MM-DD. Got: {date_str}"}), 400
        
        print(f"Fetching calendar events for date: {date_str}")
        
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
        
        print(f"Found {len(formatted_events)} events for {date_str}")
        
        return jsonify({
            "date": date_str,
            "events": formatted_events,
            "count": len(formatted_events)
        })
        
    except Exception as e:
        print(f"Error fetching calendar events: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An unexpected error occurred while fetching calendar events: {str(e)}"}), 500


if __name__ == '__main__':
    print("Agentic Personal Porter Server starting on port 5000...")
    app.run(debug=True, host='0.0.0.0', port=5000)
