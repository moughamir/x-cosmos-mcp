import logging
import sys

def setup_logging(level=logging.INFO):
    """Set up logging for the application."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )