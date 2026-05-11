import logging
from src.utils.logging_config import setup_logger
logger = setup_logger(__name__)
import sys
import os
from pathlib import Path
import time
import logging

# Ensure concise logging for the test
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from src.utils.path_utils import load_env_vars
load_env_vars()

from src.integrations.gcp_compute_client import GCPComputeClient

def run_tests():
    logger.info("==================================================")
    logger.info("🚀 GCP Compute Client Verification Test")
    logger.info("==================================================")
    
    logger.info("\n[1] Initializing GCP Compute Client (Using Application Default Credentials)...")
    client = GCPComputeClient()
    
    if not client.service:
        logger.info("❌ FAILED: Could not initialize Google Cloud Credentials.")
        logger.info("    Ensure you have run `gcloud auth application-default login` natively on your machine.")
        return

    instance_name = os.environ.get("GCP_COMPUTE_INSTANCE", "ollama-vector-host")
    logger.info(f"\n[2] Polling instantaneous status of {instance_name}...")
    status = client.get_instance_status(instance_name)
    logger.info(f"    Current Status:  => [ {status} ] <=")
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == "wake":
            logger.info(f"\n[3] INITIATING WAKE SEQUENCE for {instance_name}...")
            success = client.wake_instance(instance_name, block_until_running=True)
            logger.info(f"    Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
            
        elif command == "sleep":
            logger.info(f"\n[3] INITIATING SLEEP SEQUENCE for {instance_name}...")
            success = client.sleep_instance(instance_name)
            logger.info(f"    Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
            logger.info("    (Sleeping takes a few seconds to reflect on GCP...)")
            for i in range(5):
                time.sleep(2)
                sys.stdout.write(".")
                sys.stdout.flush()
            logger.info()
            logger.info(f"    Final Status Check: {client.get_instance_status(instance_name)}")
    else:
        logger.info("\n==================================================")
        logger.info("ℹ️ ACTIVE TESTING INSTRUCTIONS:")
        logger.info("To safely test the state-change triggers, run this script with an argument:")
        logger.info("    Wake Test:  conda run -n agentic_porter python helper_scripts/test_gcp_compute.py wake")
        logger.info("    Sleep Test: conda run -n agentic_porter python helper_scripts/test_gcp_compute.py sleep")
        logger.info("==================================================")

if __name__ == "__main__":
    run_tests()
