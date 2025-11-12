import os
import datetime
from google_calendar_auth import get_calendar_service
from flask import Flask, request, jsonify
from flask_cors import CORS
from main import run_crew # Uncomment when API key is set
from neo4j_db import get_driver, create_user, get_user, log_to_neo4j
from auth import hash_password, check_password
from dotenv import load_dotenv, find_dotenv
load_dotenv()

app = Flask(__name__) 
# A secret key is needed for session management, which stores the OAuth token.
app.secret_key = os.getenv('FLASH_SECRET_KEY', 'a_default-dev-key')
CORS(app, supports_credentials=True) # supports_credentials=True is needed for sessions

# --- Database Connection ---
uri = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

if not all([uri, username, password]):
    raise ValueError("Missing one or more Neo4j environment variables.")

# --- Google Calendar Service ---
# We initialize this when the app starts. The very first time you run this,
# you will need to follow the authentication steps printed in your Flask terminal.
# After that, it should be automatic thanks to the token.pickle file.
print("--- Initializing Google Calendar Service ---")
gcal_service = get_calendar_service()
print("--- Google Calendar Service Initialized ---")

app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    hashed_password = hash_password(password)

    driver = get_driver()
    with driver.session() as db_session:
        user = db_session.execute_write(create_user, username, hashed_password)
    driver.close()

    if user:
        return jsonify({"message": "User created successfully"}), 201
    else:
        return jsonify({"error": "User already exists"}), 409

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    driver = get_driver()
    with driver.session() as db_session:
        user_node = db_session.execute_read(get_user, username)
    driver.close()

    if user_node and check_password(user_node['password'], password):
        session['user_id'] = user_node['username']
        return jsonify({"message": "Login successful", "user_id": user_node['username']}), 200
    else:
        return jsonify({"error": "Invalid username or password"}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Logout successful"}), 200

@app.route('/check_session', methods=['GET'])
def check_session():
    if 'user_id' in session:
        return jsonify({"logged_in": True, "user_id": session['user_id']})
    else:
        return jsonify({"logged_in": False})


# --- Main Application Route ---

@app.route('/get_calendar_events', methods=['GET'])
def get_events():
    """
    Fetches calendar events for a specific date provided as a query parameter.
    e.g., /get_calendar_events?date=2025-09-29
    """
    try:
        date_str = request.args.get('date')
        if not date_str:
            return jsonify({"error": "A 'date' query parameter is required."}), 400

        # Create a timezone-aware datetime object for the start and end of the day
        day = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        time_min = datetime.datetime.combine(day, datetime.time.min).isoformat() + 'Z'  # 'Z' denotes UTC
        time_max = datetime.datetime.combine(day, datetime.time.max).isoformat() + 'Z'

        print(f"Fetching events for date: {date_str}")
        events_result = gcal_service.events().list(
            calendarId='primary', timeMin=time_min, timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        
        # We'll just send back the titles (summaries) of the events.
        event_titles = [event['summary'] for event in events if 'summary' in event]
        
        print(f"Found {len(event_titles)} events.")
        return jsonify({"events": event_titles})

    except Exception as e:
        print(f"Error fetching calendar events: {e}")
        return jsonify({"error": "An unexpected error occurred while fetching calendar events."}), 500


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
            # Run the CrewAI workflow
            crew_result = run_crew(journal_entry)

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
            return jsonify({"reflection": result_text})
        
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
