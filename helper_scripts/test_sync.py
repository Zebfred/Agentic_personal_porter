import sys
import os
import logging
import argparse

logging.basicConfig(level=logging.DEBUG)

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root)

print("Starting script test...")
try:
    from src.orchestrators.sync_calendar_to_graph import run_sync_pipeline
    print("Imported run_sync_pipeline")
    
    parser = argparse.ArgumentParser(description="Test calendar sync pipeline.")
    parser.add_argument('--user', type=str, help='Target user email to sync (optional).', default=None)
    args = parser.parse_args()
    
    print(f"Running pipeline for user: {args.user if args.user else 'All users'}")
    run_sync_pipeline(target_user_email=args.user)
    print("Finished run_sync_pipeline")
except Exception as e:
    import traceback
    traceback.print_exc()
