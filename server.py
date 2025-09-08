from flask import Flask, request, jsonify
from flask_cors import CORS
from main import run_crew

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

@app.route('/process_journal', methods=['POST'])
def process_journal():
    try:
        data = request.get_json()
        if not data or 'journal_entry' not in data:
            return jsonify({'error': 'Missing journal_entry in request body'}), 400

        journal_entry = data['journal_entry']

        # Kick off the CrewAI process
        result = run_crew(journal_entry)

        # Return the result from the crew
        return jsonify({'result': result})

    except Exception as e:
        # Log the error for debugging
        print(f"An error occurred: {e}")
        # Return a generic error message
        return jsonify({'error': 'An internal server error occurred.'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
