import logging
import sys
from pathlib import Path

# Resolve project root (three levels up from src/utils/logging_config.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def setup_logger(name: str) -> logging.Logger:
    """
    Creates and returns a configured logger for the given module name.
    Logs are routed to both the console and a single 'porter.log' file in the project root.
    """
    logger = logging.getLogger(name)
    
    # Avoid adding multiple handlers if setup is called multiple times
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Formatter: Timestamp - LoggerName - Level - Message
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File Handler (project root)
        log_file = PROJECT_ROOT / "porter.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Prevent bubbling up to the root logger to avoid double printing
        logger.propagate = False
        
    return logger
