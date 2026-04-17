"""
Agentic Personal Porter — Application Factory

This module creates and configures the Flask application.
All route handlers live in src/routes/ as Flask Blueprints.
"""
import os
import sys
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Add project root to Python path so imports work when run directly
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load auth env vars BEFORE anything else reads them
root = Path(__file__).resolve().parent.parent
load_dotenv(root / ".auth" / ".env")

# --- Critical security checks ---
API_KEY = os.environ.get("PORTER_API_KEY")
if not API_KEY:
    raise ValueError(
        "CRITICAL SECURITY ERROR: PORTER_API_KEY environment variable is missing. "
        "It must be set in .auth/.env for secure authentication."
    )

JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError(
        "CRITICAL SECURITY ERROR: JWT_SECRET environment variable is missing. "
        "It must be set in .auth/.env for secure token generation."
    )


def _configure_logging():
    """Set up the APP_ROUTER logger with file and console handlers."""
    log_dir = root / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "app.log"

    logger = logging.getLogger("APP_ROUTER")
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=2)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    return logger


def create_app():
    """Application factory — creates, configures, and returns the Flask app."""
    logger = _configure_logging()

    app = Flask(__name__)

    # --- CORS ---
    allowed_origins_str = os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5000,http://127.0.0.1:5000,http://localhost:5090,http://127.0.0.1:5090"
    )
    cors_origins = [o.strip() for o in allowed_origins_str.split(",") if o.strip()]
    CORS(app, resources={r"/*": {"origins": cors_origins}})

    # --- Register Blueprints ---
    from src.routes.static_routes import static_bp
    from src.routes.auth_routes import auth_bp
    from src.routes.journal_routes import journal_bp
    from src.routes.chat_routes import chat_bp
    from src.routes.calendar_routes import calendar_bp
    from src.routes.inventory_routes import inventory_bp
    from src.routes.admin_routes import admin_bp

    # Static routes have no prefix — they serve /, /index.html, /js/*, etc.
    app.register_blueprint(static_bp)

    # Auth routes: /api/login
    app.register_blueprint(auth_bp, url_prefix='/api')

    # Journal routes carry their own /api/ prefix for save_log and logs,
    # but /process_journal stays at root for frontend backward compatibility
    app.register_blueprint(journal_bp)

    # Chat routes: /api/chat/porter
    app.register_blueprint(chat_bp, url_prefix='/api')

    # Calendar routes: /get_calendar_events at root (legacy frontend URL)
    app.register_blueprint(calendar_bp)

    # Inventory routes: /api/inventory, /api/artifacts/*, /api/graph_data
    app.register_blueprint(inventory_bp, url_prefix='/api')

    # Admin routes: /api/admin/*, /api/wake_infrastructure
    app.register_blueprint(admin_bp, url_prefix='/api')

    logger.info(f"Flask app created with {len(list(app.url_map.iter_rules()))} routes across 7 blueprints.")
    return app


# --- Entrypoint ---
app = create_app()

if __name__ == '__main__':
    logger = logging.getLogger("APP_ROUTER")
    logger.info("=" * 82)
    logger.warning("Starting the Agentic Personal Porter via Flask's built-in development server.")
    logger.warning("This server is not suitable for production deployments.")
    logger.info("For a production WSGI server, please execute: ./run_production.sh (which uses Gunicorn)")
    logger.info("=" * 82)

    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    logger.info(f"Server starting on port 5090 (Debug Mode: {debug_mode})...")

    app.run(debug=debug_mode, host='0.0.0.0', port=5090)
