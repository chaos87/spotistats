import logging
import os
# Corrected import path for JsonFormatter based on deprecation warning
from pythonjsonlogger.json import JsonFormatter

def setup_logging():
    logger = logging.getLogger() # Get root logger
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()

    try:
        log_level = logging.getLevelName(log_level_name)
        # Check if getLevelName returned a number (level) or string (level name)
        if not isinstance(log_level, int):
            # Fallback for invalid level names
            log_level = logging.INFO
            logging.getLogger(__name__).warning(
                f"Invalid LOG_LEVEL '{log_level_name}'. Defaulting to INFO."
            )
    except ValueError: # Should not happen with getLevelName, but as a safeguard
        log_level = logging.INFO
        logging.getLogger(__name__).warning(
            f"Invalid LOG_LEVEL '{log_level_name}'. Defaulting to INFO."
        )

    logger.setLevel(log_level)

    # Remove existing handlers if any (e.g., from a previous basicConfig call)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close() # Close handler before removing

    log_handler = logging.StreamHandler()
    # Use a more detailed fmt string as per the example in the prompt
    # Use the directly imported JsonFormatter
    formatter = JsonFormatter(
        fmt='%(asctime)s %(levelname)s %(name)s %(module)s %(funcName)s %(lineno)d %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S%z',
        rename_fields={'levelname': 'level'} # common practice to rename for some log systems
    )
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)

    # Reduce verbosity of noisy loggers
    noisy_loggers = ["sqlalchemy.engine", "urllib3.connectionpool", "requests.packages.urllib3.connectionpool"]
    for noisy_logger_name in noisy_loggers:
        noisy_logger_instance = logging.getLogger(noisy_logger_name)
        noisy_logger_instance.setLevel(logging.WARNING)

    # Test log to confirm setup (will be logged by the root logger)
    logging.getLogger(__name__).info("Structured JSON logging configured.")
