import os
import time
from typing import Optional
import google.auth
from googleapiclient import discovery
import logging

logger = logging.getLogger(__name__)

class GCPComputeClient:
    """
    Lightweight wrapper around Google Compute Engine API to manage instance lifecycles.
    Uses Application Default Credentials (ADC) to authenticate seamlessly between local and Cloud Run.
    """
    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or os.environ.get("GCP_PROJECT_ID", "")
        try:
            self.credentials, self.default_project_id = google.auth.default()
            # Fall back to ADC-discovered project if neither arg nor env var provided
            if not self.project_id:
                self.project_id = self.default_project_id or ""
            self.service = discovery.build('compute', 'v1', credentials=self.credentials, cache_discovery=False)
        except Exception as e:
            logger.error(f"Failed to initialize GCP Credentials. Ensure Application Default Credentials are set. {e}")
            self.service = None
        self._auth_failed = False

    def get_instance_status(self, instance: str, zone: str = "us-central1-a") -> str:
        """ Returns the exact status of the VM (e.g. RUNNING, TERMINATED). Returns 'UNKNOWN' on error. """
        if not self.service:
            return "UNKNOWN"
        try:
            request = self.service.instances().get(project=self.project_id, zone=zone, instance=instance)
            response = request.execute()
            status = response.get('status', 'UNKNOWN')
            return status
        except Exception as e:
            if "Reauthentication is needed" in str(e) or "RefreshError" in str(type(e).__name__):
                if not self._auth_failed:
                    logger.error(f"GCP Reauthentication is needed. Please run `gcloud auth application-default login` to reauthenticate.")
                    self._auth_failed = True
            else:
                logger.error(f"Error checking status for {instance}: {e}")
            return "UNKNOWN"

    def wake_instance(self, instance: str, zone: str = "us-central1-a", block_until_running: bool = False):
        """ 
        Issues a start command if the instance is terminated.
        If block_until_running is True, halts execution until GCP confirms the instance is fully RUNNING. 
        """
        if not self.service:
            return False

        status = self.get_instance_status(instance, zone)
        if status == "RUNNING":
            logger.info(f"Instance {instance} is already RUNNING.")
            return True

        if status == "TERMINATED":
            logger.info(f"Instance {instance} is TERMINATED. Issuing Start command...")
            try:
                request = self.service.instances().start(project=self.project_id, zone=zone, instance=instance)
                response = request.execute()
                
                if block_until_running:
                    logger.info("Blocking until instance reports RUNNING...")
                    retries = 0
                    while retries < 15: # roughly 30 seconds wait
                        time.sleep(2)
                        if self.get_instance_status(instance, zone) == "RUNNING":
                            logger.info(f"{instance} is fully online.")
                            return True
                        retries += 1
                    logger.warning("Timeout waiting for instance to reach RUNNING state.")
                    return False
                return True
            except Exception as e:
                logger.error(f"Failed to start instance {instance}: {e}")
                return False
        
        logger.warning(f"Instance {instance} is in transitional state: {status}. Doing nothing.")
        return False

    def sleep_instance(self, instance: str, zone: str = "us-central1-a"):
        """ Issues a stop command to aggressively save infrastructure costs. """
        if not self.service:
            return False
            
        status = self.get_instance_status(instance, zone)
        if status == "RUNNING":
            logger.info(f"Instance {instance} is RUNNING. Issuing Stop command...")
            try:
                request = self.service.instances().stop(project=self.project_id, zone=zone, instance=instance)
                request.execute()
                return True
            except Exception as e:
                logger.error(f"Failed to stop instance {instance}: {e}")
                return False
        
        logger.info(f"Instance {instance} is already in state: {status}. No stop command needed.")
        return True
