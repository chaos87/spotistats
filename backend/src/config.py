import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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


def get_env_variable(var_name: str, default_value: str = None) -> str:
    """
    Retrieves an environment variable.
    Raises an error if the variable is not found and no default is given.
    """
    value = os.environ.get(var_name)
    if value is None:
        if default_value is None:
            logging.error(f"Environment variable '{var_name}' not found.")
            raise ValueError(f"Environment variable '{var_name}' not found.")
        return default_value
    return value

# Example usage (optional, for direct testing of this file)
if __name__ == '__main__':
    print("Testing config.py...")
    try:
        db_url = get_env_variable("DATABASE_URL")
        print(f"DATABASE_URL (partial): {db_url[:db_url.find('@')]}...") # Avoid printing password
    except ValueError as e:
        print(e)
        print("Please ensure DATABASE_URL is set in backend/.env or system environment.")

    try:
        client_id = get_env_variable("SPOTIFY_CLIENT_ID")
        print(f"SPOTIFY_CLIENT_ID: {client_id}")
    except ValueError as e:
        print(e)
        print("Please ensure SPOTIFY_CLIENT_ID is set in backend/.env or system environment.")
