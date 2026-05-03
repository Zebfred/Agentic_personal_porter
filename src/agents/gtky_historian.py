import logging
from typing import List, Dict
from src.agents.gtky_base_classifier import GTKYBaseClassifier

# Configure logging to monitor our "Historian"
logger = logging.getLogger(__name__)

class GTKYHistorian(GTKYBaseClassifier):
    """
    The GTKY Historian is responsible for methodically classifying
    historical Google Calendar events and generating "Golden Objects"
    based on the user's Origin Story and Ambitions.
    """
    
    def classify_historical_batch(self, historical_events: List[Dict], username: str = "system") -> List[Dict]:
        """
        Processes a batch of historical raw events, bundles them with Hero Context,
        and uses LLM classification to mint "Golden Objects".
        """
        return self._classify_batch(
            events=historical_events,
            username=username,
            agent_role="Historian",
            time_context="historical",
            log_emoji="📜"
        )
