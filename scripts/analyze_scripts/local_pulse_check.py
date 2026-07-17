from src.utils.logging_config import setup_logger
logger = setup_logger(__name__)
import json
from datetime import datetime

# Setup path so we can import from src

from src.utils.path_utils import load_env_vars

def run_pulse_check():
    """
    Runs the system pulse check locally and writes the output to a log file.
    """
    logger.info("--- Starting Local Pulse Check ---")

    # Ensure environment variables are loaded
    load_env_vars()
    try:
        from src.utils.pulse_service import PulseService
        pulse_data = PulseService.get_system_heartbeat()

        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return super().default(obj)

        # Write to log file
        from src.utils.path_utils import get_project_root
        log_dir = get_project_root() / "scripts/analyze_scripts/logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = log_dir / f"pulse_status_{timestamp_str}.log"

        with open(log_filename, "w") as f:
            f.write(json.dumps(pulse_data, indent=4, cls=DateTimeEncoder))

        logger.info("Pulse Check Complete.")
        logger.info(f"Log saved to: {log_filename}")

    except Exception as e:
        logger.info(f"Error running pulse check: {e}")

if __name__ == "__main__":
    run_pulse_check()
