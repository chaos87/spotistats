import os
from dotenv import load_dotenv
import logging
from .exceptions import ConfigurationError

# Configure logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
#basicConfig should only be called once. main.py might also call it.
#Let's ensure logger is available if needed.
logger = logging.getLogger(__name__)

# Load .env file from the 'backend' directory (assuming this file is in backend/src)
# Adjust the path if your .env file is located elsewhere relative to this config file.
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')

if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    # logging.info(f"Loaded .env file from {dotenv_path}")
else:
    # This is not necessarily an error if running in a deployed environment
    # where env vars are set directly.
    # logging.info(f".env file not found at {dotenv_path}. Relying on system environment variables.")
    pass


def get_env_variable(var_name: str, is_critical: bool = True) -> str | None:
    """
    Retrieves an environment variable.
    If is_critical is True (default) and the variable is not found, raises ConfigurationError.
    If is_critical is False and the variable is not found, returns None.
    """
    value = os.getenv(var_name) # os.getenv is equivalent to os.environ.get
    if value is None and is_critical:
        logger.error(f"Missing critical environment variable: {var_name}")
        raise ConfigurationError(f"Missing critical environment variable: {var_name}")
    return value

def get_spotify_credentials():
    """Retrieves Spotify API credentials from environment variables."""
    client_id = get_env_variable("SPOTIFY_CLIENT_ID")
    client_secret = get_env_variable("SPOTIFY_CLIENT_SECRET")
    refresh_token = get_env_variable("SPOTIFY_REFRESH_TOKEN")
    # All are critical, get_env_variable will raise error if any is missing.
    return client_id, client_secret, refresh_token

def get_database_url_config(): # Renamed to avoid clash if moved from database.py
    """Retrieves the database URL from environment variables."""
    db_url = get_env_variable("DATABASE_URL")
    # Critical, get_env_variable will raise error if missing.
    return db_url

# Example usage (optional, for direct testing of this file)
if __name__ == '__main__': # pragma: no cover
    logger.info("Testing config.py...")
    try:
        # Test critical variable
        db_url = get_database_url_config()
        if db_url: # Should always be true if no error
             logger.info(f"DATABASE_URL (partial for display): {db_url[:db_url.find('@') if '@' in db_url else 20]}...")
    except ConfigurationError as e:
        logger.error(e)
        logger.info("Please ensure DATABASE_URL is set in backend/.env or system environment.")

    try:
        # Test multiple critical variables
        client_id, client_secret, refresh_token = get_spotify_credentials()
        if client_id and client_secret and refresh_token : # Should always be true if no error
            logger.info(f"SPOTIFY_CLIENT_ID: {client_id}")
            logger.info(f"SPOTIFY_CLIENT_SECRET: {'*' * len(client_secret if client_secret else '')}")
            logger.info(f"SPOTIFY_REFRESH_TOKEN: {'*' * len(refresh_token if refresh_token else '')}")
    except ConfigurationError as e:
        logger.error(e)
        logger.info("Please ensure SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and SPOTIFY_REFRESH_TOKEN are set.")

    try:
        # Test non-critical variable
        non_critical_var = get_env_variable("NON_EXISTENT_VAR_FOR_TESTING", is_critical=False)
        if non_critical_var is None:
            logger.info("NON_EXISTENT_VAR_FOR_TESTING is None, as expected (non-critical).")
        else:
            logger.warning(f"NON_EXISTENT_VAR_FOR_TESTING has a value: {non_critical_var}, which is unexpected for this test.")
    except ConfigurationError: # Should not happen for non-critical
        logger.error("ConfigurationError was raised for a non-critical variable, which is unexpected.")
