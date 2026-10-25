"""
Agentic Personal Porter — Application Factory

This module creates and configures the Flask application.
All route handlers live in src/routes/ as Flask Blueprints.
"""

import os
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask_cors import CORS

# --- Load environment variables ---
from src.utils.path_utils import load_env_vars

load_env_vars()

# --- Critical security checks ---
PORTER_API_KEY = os.environ.get("PORTER_API_KEY")
if not PORTER_API_KEY:
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
    from src.utils.path_utils import get_project_root

    log_dir = get_project_root() / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "app.log"

    logger = logging.getLogger("APP_ROUTER")
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")

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

    # ⚡ Bolt Optimization: Keep global Neo4j driver singleton alive across requests.
    allowed_origins_str = os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5000,http://127.0.0.1:5000,http://localhost:6010,http://127.0.0.1:6010",
    )
    cors_origins = [o.strip() for o in allowed_origins_str.split(",") if o.strip()]
    CORS(app, resources={r"/*": {"origins": cors_origins}})

    from src.routes.static_routes import static_bp
    from src.routes.auth_routes import auth_bp
    from src.routes.journal_routes import journal_bp
    from src.routes.chat_routes import chat_bp
    from src.routes.calendar_routes import calendar_bp
    from src.routes.inventory_routes import inventory_bp
    from src.routes.admin_routes import admin_bp
    from src.routes.user_routes import user_bp
    from src.routes.jira_routes import jira_bp

    app.register_blueprint(static_bp)
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(journal_bp)
    app.register_blueprint(chat_bp, url_prefix="/api")
    app.register_blueprint(calendar_bp)
    app.register_blueprint(inventory_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api")
    app.register_blueprint(user_bp, url_prefix="/api/user")
    app.register_blueprint(jira_bp, url_prefix="/api")

    logger.info(
        f"Flask app created with {len(list(app.url_map.iter_rules()))} routes across 9 blueprints."
    )
    return app


# --- Entrypoint ---
app = create_app()

if __name__ == "__main__":
    logger = logging.getLogger("APP_ROUTER")
    logger.info("=" * 82)
    logger.warning("Starting the Agentic Personal Porter via Flask's built-in development server.")
    logger.warning("This server is not suitable for production deployments.")
    logger.info(
        "For a production WSGI server, please execute: ./run_production.sh (which uses Gunicorn)"
    )
    logger.info("=" * 82)

    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    run_host = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
    logger.info(f"Server starting on {run_host}:5090 (Debug Mode: {debug_mode})...")

    app.run(debug=debug_mode, host=run_host, port=5090)
