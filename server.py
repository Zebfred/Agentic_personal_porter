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
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        journal_entry = data.get('journal_entry') 
        log_data = data.get('log_data')
        
        # Validation
        if not journal_entry or not isinstance(journal_entry, str):
            return jsonify({"error": "'journal_entry' is missing or invalid."}), 400

        if not log_data or not isinstance(log_data, dict):
             return jsonify({"error": "'log_data' is missing or invalid."}), 400

        required_fields = ['day', 'timeChunk', 'intention', 'actual', 'feeling', 'brainFog', 'isValuableDetour', 'inventoryNote']
        missing_fields = [field for field in required_fields if field not in log_data]
        if missing_fields:
            return jsonify({"error": f"Missing fields in log_data: {', '.join(missing_fields)}"}), 400

        # Removed sensitive logging of journal_entry and log_data
        
        try:
            # Run the CrewAI workflow
            crew_result = run_crew(journal_entry)

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
            # Log error securely (avoid printing full traceback to stdout in production if possible, but keeping minimal info)
            print(f"An error occurred during crew execution: {str(e)}")
            return jsonify({"error": "An error occurred while processing the AI reflection."}), 500

    except Exception as e:
        # This outer block catches errors in getting the initial JSON data
        print(f"An error occurred reading the request data: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
