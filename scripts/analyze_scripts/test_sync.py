import logging
from src.utils.logging_config import setup_logger
logger = setup_logger(__name__)
import os
import argparse

logging.basicConfig(level=logging.DEBUG)

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

logger.info("Starting script test...")
try:
    from src.orchestrators.sync_calendar_to_graph import run_sync_pipeline
    logger.info("Imported run_sync_pipeline")

    parser = argparse.ArgumentParser(description="Test calendar sync pipeline.")
    parser.add_argument('--user', type=str, help='Target user email to sync (optional).', default=None)
    args = parser.parse_args()

    logger.info(f"Running pipeline for user: {args.user if args.user else 'All users'}")
    run_sync_pipeline(target_user_email=args.user)
    logger.info("Finished run_sync_pipeline")
except Exception:
    import traceback
    traceback.print_exc()
