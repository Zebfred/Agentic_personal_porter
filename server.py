from flask import Flask, request, jsonify
from flask_cors import CORS
from main import run_crew
from neo4j_db import log_to_neo4j

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

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
