import sys
import os
from pathlib import Path
import time
import logging

# Ensure concise logging for the test
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.append(str(root))

from dotenv import load_dotenv
load_dotenv(root / ".auth" / ".env")

from src.integrations.gcp_compute_client import GCPComputeClient

def run_tests():
    print("==================================================")
    print("🚀 GCP Compute Client Verification Test")
    print("==================================================")
    
    print("\n[1] Initializing GCP Compute Client (Using Application Default Credentials)...")
    client = GCPComputeClient()
    
    if not client.service:
        print("❌ FAILED: Could not initialize Google Cloud Credentials.")
        print("    Ensure you have run `gcloud auth application-default login` natively on your machine.")
        return

    instance_name = os.environ.get("GCP_COMPUTE_INSTANCE", "ollama-vector-host")
    print(f"\n[2] Polling instantaneous status of {instance_name}...")
    status = client.get_instance_status(instance_name)
    print(f"    Current Status:  => [ {status} ] <=")
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == "wake":
            print(f"\n[3] INITIATING WAKE SEQUENCE for {instance_name}...")
            success = client.wake_instance(instance_name, block_until_running=True)
            print(f"    Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
            
        elif command == "sleep":
            print(f"\n[3] INITIATING SLEEP SEQUENCE for {instance_name}...")
            success = client.sleep_instance(instance_name)
            print(f"    Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
            print("    (Sleeping takes a few seconds to reflect on GCP...)")
            for i in range(5):
                time.sleep(2)
                sys.stdout.write(".")
                sys.stdout.flush()
            print()
            print(f"    Final Status Check: {client.get_instance_status(instance_name)}")
    else:
        print("\n==================================================")
        print("ℹ️ ACTIVE TESTING INSTRUCTIONS:")
        print("To safely test the state-change triggers, run this script with an argument:")
        print("    Wake Test:  conda run -n agentic_porter python helper_scripts/test_gcp_compute.py wake")
        print("    Sleep Test: conda run -n agentic_porter python helper_scripts/test_gcp_compute.py sleep")
        print("==================================================")

if __name__ == "__main__":
    run_tests()
