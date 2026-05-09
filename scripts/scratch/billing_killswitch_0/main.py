import base64
import json
import os
import logging
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variable for the project ID
PROJECT_ID = os.environ.get('GCP_PROJECT')

def stop_billing(data, context):
    """
    Cloud Function to handle budget alerts from Pub/Sub.
    When triggered, it checks if the budget has been exceeded (or reached the 100% threshold).
    If it has, it disables the Vertex AI API (aiplatform.googleapis.com) to stop further LLM costs.
    """
    pubsub_data = base64.b64decode(data['data']).decode('utf-8')
    pubsub_json = json.loads(pubsub_data)
    cost_amount = pubsub_json.get('costAmount')
    budget_amount = pubsub_json.get('budgetAmount')
    
    if cost_amount is None or budget_amount is None:
        logger.error(f"No costAmount or budgetAmount in pubsub data: {pubsub_data}")
        return
        
    if cost_amount <= budget_amount:
        logger.info(f"Cost {cost_amount} <= Budget {budget_amount}. No action required.")
        return

    logger.warning(f"🚨 BUDGET EXCEEDED! Cost {cost_amount} > Budget {budget_amount}.")
    
    _disable_vertex_api()

def _disable_vertex_api():
    """Disables the Vertex AI API for the current project using the Service Usage API."""
    if not PROJECT_ID:
        logger.error("GCP_PROJECT environment variable not set. Cannot disable API.")
        return
        
    try:
        credentials = GoogleCredentials.get_application_default()
        service = discovery.build('serviceusage', 'v1', credentials=credentials)
        
        # We target the specific Vertex AI API endpoint
        service_name = f'projects/{PROJECT_ID}/services/aiplatform.googleapis.com'
        
        logger.info(f"Issuing request to disable {service_name}...")
        request = service.services().disable(name=service_name)
        response = request.execute()
        
        logger.info(f"✅ Successfully disabled Vertex AI API: {response}")
    except Exception as e:
        logger.error(f"❌ Failed to disable Vertex AI API: {e}")
        raise e
