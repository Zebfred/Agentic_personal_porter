import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

# Setup path so we can import from src
root = Path(__file__).resolve().parent.parent
sys.path.append(str(root))

from src.utils.path_utils import load_env_vars
from src.database.mongo_storage import SovereignMongoStorage
from src.database.neo4j_client.connection import get_driver

def run_pulse_check():
    """
    Runs the system pulse check locally and writes the output to a log file.
    """
    print("--- Starting Local Pulse Check ---")
    
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
        log_dir = root / "helper_scripts" / "logs"
        log_dir.mkdir(exist_ok=True)
        
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = log_dir / f"pulse_status_{timestamp_str}.log"
        
        with open(log_filename, "w") as f:
            f.write(json.dumps(pulse_data, indent=4, cls=DateTimeEncoder))
            
        print(f"Pulse Check Complete.")
        print(f"Log saved to: {log_filename}")
        
    except Exception as e:
        print(f"Error running pulse check: {e}")

if __name__ == "__main__":
    run_pulse_check()
