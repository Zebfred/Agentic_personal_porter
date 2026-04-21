"""
Static file serving routes.

Handles serving the frontend HTML pages and static assets (JS, CSS).
"""
from flask import Blueprint, send_from_directory, render_template

static_bp = Blueprint('static', __name__, template_folder='../../frontend')


# --- HTML Page Routes ---

@static_bp.route('/')
@static_bp.route('/index.html')
def index():
    return render_template('index.html')

@static_bp.route('/adventure_log')
@static_bp.route('/Adventure_Time_log.html')
def adventure_log():
    return render_template('Adventure_Time_log.html')

@static_bp.route('/adventure_calendar')
@static_bp.route('/adventure_calendar.html')
def adventure_calendar():
    return render_template('adventure_calendar.html')

@static_bp.route('/journal_review')
@static_bp.route('/journal_review.html')
def journal_review():
    return render_template('journal_review.html')

@static_bp.route('/oracle_predictions')
@static_bp.route('/Oracle_predictions.html')
def oracle_predictions():
    return render_template('Oracle_predictions.html')

@static_bp.route('/inventory')
@static_bp.route('/inventory.html')
def inventory():
    return render_template('inventory.html')

@static_bp.route('/artifacts')
@static_bp.route('/artifacts.html')
def artifacts():
    return render_template('artifacts.html')

@static_bp.route('/login')
@static_bp.route('/login.html')
def login_page():
    return render_template('login.html')

@static_bp.route('/graph_explorer')
@static_bp.route('/graph_explorer.html')
def graph_explorer():
    return render_template('graph_explorer.html')


# --- Static Asset Routes ---

@static_bp.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('../frontend/js', filename)

@static_bp.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory('../frontend/css', filename)
