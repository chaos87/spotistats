import logging
from backend.src.spotify_client import SpotifyOAuthClient
from backend.src.config import load_spotify_config

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("Backend service starting...")
    try:
        # Load Spotify configuration
        client_id, client_secret, refresh_token = load_spotify_config()
        logger.info("Spotify configuration loaded successfully.")

        # Instantiate SpotifyOAuthClient
        spotify_client = SpotifyOAuthClient(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token
        )
        logger.info("SpotifyOAuthClient instantiated.")

        # Get new access token
        logger.info("Attempting to retrieve a new access token...")
        access_token = spotify_client.get_access_token_from_refresh()
        logger.info(f"Successfully retrieved new access token: {access_token[:20]}...") # Print only a portion for security

    except ValueError as ve:
        logger.error(f"Configuration error: {ve}")
    except Exception as e:
        logger.error(f"An error occurred in main: {e}")
        # In a real application, you might want to handle this more gracefully
        # or re-raise the exception after logging.

if __name__ == "__main__":
    # This part is for local testing.
    # In a real deployment, you might not have a .env file or might rely on
    # environment variables set in the deployment environment.
    # For local testing, ensure you have a backend/.env file with your credentials.
    logger.info("Running main.py directly for local testing...")

    # Temporarily set dummy env vars if .env is not present or vars are missing for local run
    # This is to prevent outright crashing if run in an environment without .env
    # A more robust solution for testing might involve command-line args or a dedicated test script.
    import os
    if not (os.getenv("SPOTIFY_CLIENT_ID") and os.getenv("SPOTIFY_CLIENT_SECRET") and os.getenv("SPOTIFY_REFRESH_TOKEN")):
        logger.warning("One or more Spotify environment variables are not set.")
        logger.warning("Attempting to run with dummy values for demonstration purposes ONLY.")
        logger.warning("This will likely fail when calling the Spotify API.")
        if not os.getenv("SPOTIFY_CLIENT_ID"):
            os.environ["SPOTIFY_CLIENT_ID"] = "dummy_client_id"
        if not os.getenv("SPOTIFY_CLIENT_SECRET"):
            os.environ["SPOTIFY_CLIENT_SECRET"] = "dummy_client_secret"
        if not os.getenv("SPOTIFY_REFRESH_TOKEN"):
            os.environ["SPOTIFY_REFRESH_TOKEN"] = "dummy_refresh_token"

    main()
