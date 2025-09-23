from flask import Flask, request, jsonify
from flask_cors import CORS
from main import run_crew

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

@app.route('/process_journal', methods=['POST'])
def process_journal():
    try:
        data = request.get_json()
        journal_entry = data.get('journal_entry') 
        
        if not journal_entry:
            return jsonify({'error': 'Missing journal_entry in request body'}), 400
        
        #if not data or 'journal_entry' not in data:
        #    return jsonify({'error': 'Missing journal_entry in request body'}), 400

        journal_entry = data['journal_entry']

        # Kick off CrewAI workflow process
        crew_result = run_crew(journal_entry)

        # --- Enhanced Debugging ---
        #print("--- DEBUGGING CREWAI OUTPUT ---")
        #print(f"Type of crew_result: {type(crew_result)}")
        #print(f"Raw crew_result object: {crew_result}")
        #print(f"Attributes of crew_result: {dir(crew_result)}")
        # --- End Debugging ---

        # Final Correction v3: Access the .raw attribute from the LAST task's output
        # The result is often a list of outputs, we want the final one.
        if crew_result and crew_result.tasks_output:
            result_text = crew_result.tasks_output[-1].raw
        else:
            # Fallback in case the structure is different
            result_text = str(crew_result)

        # --- Enhanced Debugging for Return Value ---
        #print("--- DEBUGGING RETURN VALUE ---")
        #print(f"Type of result_text before jsonify: {type(result_text)}")
        #print(f"Content of result_text: {result_text}")
        # --- End Debugging ---    

        # Return the plain txt from the crew as JSON
        return jsonify({'result': result_text})

    except Exception as e:
        # Log the error for debugging
        print(f"An error occurred: {e}")
        # Return a generic error message
        return jsonify({'error': 'An internal server error occurred.'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
