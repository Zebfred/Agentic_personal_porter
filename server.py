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
        journal_entry_text = data.get('journal_entry') 
        log_data = data.get('log_data')
        
        if not journal_entry_text or not log_data:
            return jsonify({'error': "Incomplete data provided: requires 'journal_entry_text' and 'log_data'"}), 400
        
        # Log the journal entry
        #journal_entry = data['journal_entry']
        
        # Runs the CrewAI workflow to get the reflection for the journal text
        crew_result = run_crew(journal_entry_text)



        # v4: Access the .raw attribute from the LAST task's output
        # The result is often a list of outputs, we want the final one.
        result_text = "Could not retrieve a reflection."
        
        # Safely access the nested raw output from the last task
        try:
            if crew_result and hasattr(crew_result, 'tasks_output') and crew_result.tasks_output:
                last_task = crew_result.tasks_output[-1]
                if hasattr(last_task, 'raw') and last_task.raw:
                    result_text = last_task.raw
                else: # Fallback if .raw is missing or empty
                    result_text = str(last_task)
            elif crew_result: # Fallback if tasks_output is missing or empty
                result_text = str(crew_result)
        except Exception as e:
            print(f"Error extracting reflection from crew_result: {e}")
            result_text = "Error parsing AI response object."
        #the generated reflection to the log_data dictionary
        log_data['reflection'] = result_text    

        # Log the journal entry
        #journal_entry = data['journal_entry']

        # Save the entire, complete log entry to our Neo4j database
        db_confirmation = log_to_neo4j(log_data)
        print(f"Neo4j Confirmation: {db_confirmation}")

        # --- Enhanced Debugging ---
        print("--- DEBUGGING CREWAI OUTPUT ---")
        print(f"Type of crew_result: {type(crew_result)}")
        print(f"Raw crew_result object: {crew_result}")
        print(f"Attributes of crew_result: {dir(crew_result)}")
        #print(f"Type of result_text: {type(result_text)}")
        #print(f"Raw result_text object: {result_text}")
        #print(f"Attributes of result_text_object: {dir(result_text)}")
        # --- End Debugging ---

        
        # --- Enhanced Debugging for Return Value ---
        print("--- DEBUGGING RETURN VALUE ---")
        print(f"Type of result_text before jsonify: {type(result_text)}")
        print(f"Content of result_text: {result_text}")
        print(f"Attributes of result_text_object: {dir(result_text)}")
        # --- End Debugging ---    

        # Send the reflection text back to the front-end to be displayed
        return jsonify({'reflection': result_text})

    except Exception as e:
        # Log the error for debugging
        print(f"An error occurred: {e}")
        # Return a generic error message
        return jsonify({'error': 'An internal server error occurred.'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
