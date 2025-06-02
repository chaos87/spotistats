import sys
import os
import logging

print(f"Initial sys.path: {sys.path}")

# Attempt to import python_json_logger BEFORE sys.path modification
try:
    from python_json_logger import jsonlogger
    print("Successfully imported python_json_logger.jsonlogger (BEFORE sys.path mod)")
except ModuleNotFoundError as e:
    print(f"Failed to import python_json_logger.jsonlogger (BEFORE sys.path mod): {e}")
    # This would be very telling if it fails here too
    # To ensure script halts if this critical test fails
    if 'python_json_logger' not in sys.modules:
        raise
    else:
        print("python_json_logger was in sys.modules despite ModuleNotFoundError? This is odd.")


# Now, simulate PYTHONPATH=/app by adding the parent directory of 'backend/' to sys.path
app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if app_path not in sys.path:
    sys.path.insert(0, app_path)
    print(f"Manually prepended app_path: {app_path} to sys.path.")

print(f"sys.path for further import attempts: {sys.path}")

# Try importing again, just to see (should already be in sys.modules if first import worked)
try:
    from python_json_logger import jsonlogger # This should use the already imported module
    print("Successfully imported python_json_logger.jsonlogger (AFTER sys.path mod)")
except ModuleNotFoundError as e:
    print(f"Failed to import python_json_logger.jsonlogger (AFTER sys.path mod): {e}")
    # If it succeeded before but fails now, this is the key
    if 'python_json_logger' not in sys.modules: # Check if it truly disappeared
        raise
    else:
        print("python_json_logger was in sys.modules, but ModuleNotFoundError on re-import? Very odd.")


# Then try the logging_config import
try:
    from backend.src.logging_config import setup_logging # This imports python_json_logger again internally
    print("Successfully imported setup_logging from backend.src.logging_config")
    setup_logging()
    print("Successfully ran setup_logging()")

    logger = logging.getLogger(__name__)
    logger.info("Test info from test_import.py using configured logger.")
    print("Test info log sent via configured logger.")

except ModuleNotFoundError as e:
    print(f"ModuleNotFoundError during logging_config import or setup: {e}")
    # If the error is "No module named 'python_json_logger'", this is the spot.
    raise
except Exception as e:
    print(f"An unexpected error occurred with logging_config or setup_logging: {e}")
    raise

print("Script completed successfully.")
