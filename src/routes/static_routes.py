"""
Static file serving routes.

Handles serving the frontend HTML pages and static assets (JS, CSS).
"""
from flask import Blueprint, send_from_directory

static_bp = Blueprint('static', __name__)


# --- HTML Page Routes ---

@static_bp.route('/')
@static_bp.route('/index.html')
def index():
    return send_from_directory('../frontend', 'index.html')

@static_bp.route('/adventure_log')
@static_bp.route('/Adventure_Time_log.html')
def adventure_log():
    return send_from_directory('../frontend', 'Adventure_Time_log.html')

@static_bp.route('/adventure_calendar')
@static_bp.route('/adventure_calendar.html')
def adventure_calendar():
    return send_from_directory('../frontend', 'adventure_calendar.html')

@static_bp.route('/journal_review')
@static_bp.route('/journal_review.html')
def journal_review():
    return send_from_directory('../frontend', 'journal_review.html')

@static_bp.route('/oracle_predictions')
@static_bp.route('/Oracle_predictions.html')
def oracle_predictions():
    return send_from_directory('../frontend', 'Oracle_predictions.html')

@static_bp.route('/inventory')
@static_bp.route('/inventory.html')
def inventory():
    return send_from_directory('../frontend', 'inventory.html')

@static_bp.route('/artifacts')
@static_bp.route('/artifacts.html')
def artifacts():
    return send_from_directory('../frontend', 'artifacts.html')

@static_bp.route('/login')
@static_bp.route('/login.html')
def login_page():
    return send_from_directory('../frontend', 'login.html')

@static_bp.route('/graph_explorer')
@static_bp.route('/graph_explorer.html')
def graph_explorer():
    return send_from_directory('../frontend', 'graph_explorer.html')


# --- Static Asset Routes ---

@static_bp.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('../frontend/js', filename)

@static_bp.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory('../frontend/css', filename)
