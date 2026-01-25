from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, time, timedelta
from main import run_crew
from neo4j_db import log_to_neo4j
from google_calendar_authentication_helper import get_calendar_service

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

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
        journal_entry = data['journal_entry']
        print(f"Received journal entry: {journal_entry}")  # Debugging log
        log_data = data.get('log_data')
        print(f"Received log data: {log_data}")  # Debugging log
        
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

            # BEFORE any error can happen
            print("\n--- DEBUGGING CREWAI OUTPUT ---")
            print(f"Type of crew_result: {type(crew_result)}")
            print(f"Raw crew_result object: {crew_result}")
            if crew_result:
                print(f"Attributes of crew_result: {dir(crew_result)}")
            print("--- END IMMEDIATE DEBUGGING ---\n")

            # Safely extract the reflection text
            result_text = "Could not retrieve a reflection."
            if crew_result and hasattr(crew_result, 'tasks_output') and crew_result.tasks_output:
                last_task = crew_result.tasks_output[-1]
                if hasattr(last_task, 'raw') and last_task.raw:
                    result_text = last_task.raw
                else:
                    result_text = str(last_task)
            elif crew_result: # Fallback if tasks_output is missing or empty
                result_text = str(crew_result)

            # Add reflection to the log data for the database
            log_data['reflection'] = result_text

            # 5. Save the complete log to Neo4j
            db_confirmation = log_to_neo4j(log_data)
            print(f"Neo4j Confirmation: {db_confirmation}")

            # 6. Return the successful result to the front-end
            # Note: app.js expects "result" key, not "reflection"
            return jsonify({"result": result_text})
        
        except Exception as e:
            # This will now catch the 'NoneType' error and give us a detailed traceback
            print(f"\n!!! AN ERROR OCCURRED DURING CREW EXECUTION OR DATA PROCESSING !!!")
            import traceback
            traceback.print_exc() # This prints the full error stack trace
            print(f"Error details: {e}\n")
            return jsonify({"error": "An error occurred while processing the AI reflection."}), 500

    except Exception as e:
        # This outer block catches errors in getting the initial JSON data
        print(f"An error occurred reading the request data: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500


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
    app.run(host='0.0.0.0', port=5000)
