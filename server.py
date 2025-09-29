import os
import datetime
from flask import Flask, request, jsonify, session
from flask_cors import CORS
# from main import run_crew # Uncomment when API key is set
from neo4j_db import get_driver, create_user, get_user, log_to_neo4j
from auth import hash_password, check_password

app = Flask(__name__)
# A static secret key is required for session management.
# In a production environment, this should be a more complex key
# and stored securely, e.g., in an environment variable.
app.secret_key = 'a_really_secret_key_that_should_be_changed'
CORS(app, supports_credentials=True) # supports_credentials=True is needed for sessions

# --- Authentication Routes ---

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    hashed_password = hash_password(password)

    driver = get_driver()
    with driver.session() as db_session:
        user = db_session.write_transaction(create_user, username, hashed_password)
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
        user_node = db_session.read_transaction(get_user, username)
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

@app.route('/process_journal', methods=['POST'])
def process_journal():
    if 'user_id' not in session:
        return jsonify({"error": "User not logged in"}), 401

    user_id = session['user_id']

    try:
        data = request.get_json()
        journal_entry = data.get('journal_entry')
        log_data = data.get('log_data')
        
        if not journal_entry or not log_data:
            return jsonify({"error": "Incomplete data provided"}), 400
        
        # NOTE: The following section requires a valid GROQ_API_KEY in your .env file.
        # Uncomment the 'from main import run_crew' at the top of the file and
        # the following lines to enable the AI reflection feature.
        # -----------------------------------------------------------------
        # crew_result = run_crew(journal_entry)

        # result_text = "Could not retrieve a reflection."
        # if crew_result and hasattr(crew_result, 'tasks_output') and crew_result.tasks_output:
        #     last_task = crew_result.tasks_output[-1]
        #     result_text = last_task.raw if hasattr(last_task, 'raw') and last_task.raw else str(last_task)
        # elif crew_result:
        #     result_text = str(crew_result)
        # -----------------------------------------------------------------

        # Mocked result for placeholder. Replace with the actual crew_result logic above.
        result_text = "AI reflection is currently disabled. Configure your API key to enable it."

        log_data['reflection'] = result_text

        # Save the complete log to Neo4j, now with user_id
        db_confirmation = log_to_neo4j(log_data, user_id)
        print(f"Neo4j Confirmation: {db_confirmation}")

        return jsonify({"reflection": result_text})

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "An internal server error occurred."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)