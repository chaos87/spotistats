import logging
from backend.src.config import get_env_variable
from backend.src.spotify_client import SpotifyOAuthClient, SpotifyAuthError
from backend.src.spotify_data import get_recently_played_tracks, SpotifyAPIError
from backend.src.database import get_db_engine, insert_raw_data, create_tables # Added create_tables for potential one-off setup

# Configure basic logging
# More advanced structured logging can be added later as per Module 2.5
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler() # Ensure logs go to stdout/stderr for Cloud Run
    ]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting backend data ingestion process...")

    try:
        # --- 1. Load Configuration & Initialize Spotify Client ---
        logger.info("Loading configuration and initializing Spotify client...")
        client_id = get_env_variable("SPOTIFY_CLIENT_ID")
        client_secret = get_env_variable("SPOTIFY_CLIENT_SECRET")
        refresh_token = get_env_variable("SPOTIFY_REFRESH_TOKEN")

        spotify_client = SpotifyOAuthClient(client_id, client_secret, refresh_token)
        access_token = spotify_client.get_access_token_from_refresh()
        logger.info("Successfully obtained Spotify access token.")

        # --- 2. Initialize Database Engine ---
        # (Optional: Create tables if they don't exist - useful for first run or dev)
        # In a production Cloud Run, you'd typically run migrations/table creation separately.
        # For this project structure, it's included but can be commented out if DB is pre-configured.
        try:
            db_engine = get_db_engine() # Reads DATABASE_URL from config
            logger.info("Database engine initialized.")
            # Uncomment the line below if you want the script to attempt table creation on startup.
            # create_tables(db_engine)
            # logger.info("Checked/created database tables if they didn't exist.")
        except Exception as e:
            logger.error(f"Failed to initialize database engine or create tables: {e}", exc_info=True)
            # Depending on retry strategy, might re-raise or exit
            raise


        # --- 3. Fetch Recently Played Tracks from Spotify ---
        logger.info("Fetching recently played tracks from Spotify...")
        # Default limit is 50 as per spotify_data.py, can be overridden here if needed.
        raw_spotify_data = get_recently_played_tracks(access_token, limit=50)
        items_fetched = len(raw_spotify_data.get("items", []))
        logger.info(f"Fetched {items_fetched} items from Spotify API.")

        if not raw_spotify_data.get("items"):
            logger.info("No new items found in recently played tracks from Spotify. Nothing to insert.")
            logger.info("Backend data ingestion process completed successfully (no new data).")
            return # Exit if no items

        # --- 4. Insert Raw Data into Database ---
        logger.info("Inserting raw Spotify data into the database...")
        insert_raw_data(db_engine, raw_spotify_data)
        logger.info("Successfully inserted raw Spotify data into 'recently_played_tracks_raw' table.")

        logger.info("Backend data ingestion process completed successfully.")

    except SpotifyAuthError as e:
        logger.error(f"Spotify authentication error: {e}", exc_info=True)
        # Potentially send alert or exit with specific code
    except SpotifyAPIError as e:
        logger.error(f"Spotify API error: {e}", exc_info=True)
    except ValueError as e: # For config errors or other value issues
        logger.error(f"Configuration or value error: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred during the ingestion process: {e}", exc_info=True)
        # Exit with a generic error code or re-raise if appropriate for orchestrator
    finally:
        logger.info("Backend data ingestion process finished.")


if __name__ == '__main__':
    # This allows the script to be run directly for testing or local execution.
    # For Cloud Run, the entry point will typically be just calling main().
    # Ensure .env file is present in the `backend` directory with all required variables:
    # SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN, DATABASE_URL
    main()
