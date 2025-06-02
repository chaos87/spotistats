import os
import logging
import datetime # Renamed from datetime to datetime_module for clarity if needed, but direct use is fine
from sqlalchemy.orm import Session # Explicitly import Session
from backend.src.database import get_db_engine, init_db, get_session, get_max_played_at, upsert_artist, upsert_album, upsert_track, insert_listen
from backend.src.models import Artist, Album, Track, Listen # Models for type hinting and use
from backend.src.normalizer import SpotifyMusicNormalizer
# Assuming these modules/functions exist from previous/other subtasks or will be created:
# from backend.src.config import get_spotify_credentials
# from backend.src.spotify_client import SpotifyOAuthClient
# from backend.src.spotify_data import get_recently_played_tracks

# Placeholder for actual functions - replace with real imports when available
def get_spotify_credentials():
    logging.warning("Using placeholder get_spotify_credentials()")
    return "dummy_client_id", "dummy_client_secret", "dummy_refresh_token"

class SpotifyOAuthClient:
    def __init__(self, client_id, client_secret, refresh_token):
        logging.warning(f"Using placeholder SpotifyOAuthClient with {client_id[:5]}...")
        self.access_token = "DUMMY_ACCESS_TOKEN_FOR_SUBTASK_MAIN_PY"
    def get_access_token_from_refresh(self):
        logging.warning("Using placeholder get_access_token_from_refresh()")
        return self.access_token

def get_recently_played_tracks(access_token, limit=50, after=None):
    logging.warning(f"Using placeholder get_recently_played_tracks() with token {access_token[:5]}..., limit {limit}, after {after}")
    # Simulate some data, including one item older than a potential max_played_at
    # and one non-track item, and one that would be a duplicate if max_played_at is 2023-01-15 10:25
    return {
        "items": [
            {
                "track": {
                    "id": "track_id_1", "name": "Test Track 1", "type": "track",
                    "artists": [{"id": "artist_id_1", "name": "Test Artist 1", "external_urls": {"spotify":"artist_url_1"}}],
                    "album": {"id": "album_id_1", "name": "Test Album 1", "images": [{"url": "img_url_1"}], "external_urls": {"spotify":"album_url_1"}, "release_date":"2023-01-01", "release_date_precision":"day"},
                    "duration_ms": 180000, "explicit": False, "popularity": 50, "external_urls": {"spotify":"track_url_1"}
                },
                "played_at": "2023-01-15T10:30:00Z" # New
            },
            {
                "track": {
                    "id": "track_id_2", "name": "Test Track 2", "type": "track",
                    "artists": [{"id": "artist_id_2", "name": "Test Artist 2", "external_urls": {"spotify":"artist_url_2"}}],
                    "album": {"id": "album_id_2", "name": "Test Album 2", "images": [{"url": "img_url_2"}], "external_urls": {"spotify":"album_url_2"}, "release_date":"2023-01-02", "release_date_precision":"day"},
                    "duration_ms": 200000, "explicit": True, "popularity": 60, "external_urls": {"spotify":"track_url_2"}
                },
                "played_at": "2023-01-15T09:00:00Z" # Old, if max_played_at is 2023-01-15 10:00:00Z
            },
            {
                "track": {"id": "episode_id_1", "name": "Test Episode 1", "type": "episode"},
                "played_at": "2023-01-15T11:00:00Z" # New, but not a track
            },
             { # Duplicate if max_played_at is just before this, to test insert_listen duplicate handling
                "track": {
                    "id": "track_id_3", "name": "Test Track 3 Duplicate", "type": "track",
                    "artists": [{"id": "artist_id_3", "name": "Test Artist 3", "external_urls": {"spotify":"artist_url_3"}}],
                    "album": {"id": "album_id_3", "name": "Test Album 3", "images": [{"url": "img_url_3"}], "external_urls": {"spotify":"album_url_3"}, "release_date":"2023-01-03", "release_date_precision":"day"},
                    "duration_ms": 220000, "explicit": False, "popularity": 70, "external_urls": {"spotify":"track_url_3"}
                },
                "played_at": "2023-01-15T10:25:00Z"
            }
        ],
        "next": None # Or a URL to fetch more
    }


# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

def process_spotify_data():
    engine = get_db_engine()
    # Optional: init_db(engine) # Typically called once manually, not every run.

    db_session = get_session(engine) # Use get_session which returns a Session instance

    try:
        # 1. Get Spotify Access Token
        client_id, client_secret, refresh_token = get_spotify_credentials()
        spotify_client = SpotifyOAuthClient(client_id, client_secret, refresh_token)
        access_token = spotify_client.get_access_token_from_refresh()

        if not access_token:
            logging.error("Failed to get Spotify access token.")
            return
        logging.info("Successfully obtained Spotify access token.")

        # 2. Get max_played_at from DB
        max_played_at_db = get_max_played_at(db_session)
        logging.info(f"Max played_at from DB: {max_played_at_db}")

        # Convert max_played_at_db to Unix timestamp in milliseconds if it exists for 'after' parameter
        after_param = None
        if max_played_at_db:
            # Spotify API 'after' is Unix timestamp in milliseconds
            after_param = int(max_played_at_db.timestamp() * 1000)


        # 3. Fetch recently played tracks from Spotify
        # Pass 'after_param' to get_recently_played_tracks if your implementation supports it
        spotify_items_response = get_recently_played_tracks(access_token, limit=50, after=after_param)

        if not spotify_items_response or 'items' not in spotify_items_response:
            logging.warning("No items found in Spotify response or bad response.")
            db_session.close() # Close session before returning
            return

        spotify_items = spotify_items_response['items']
        logging.info(f"Fetched {len(spotify_items)} items from Spotify.")

        normalizer = SpotifyMusicNormalizer()
        new_listens_count = 0
        processed_items_count = 0

        for item in reversed(spotify_items): # Process oldest first to maintain order for played_at
            played_at_str = item.get('played_at')
            track_info = item.get('track')

            if not played_at_str or not track_info:
                logging.warning(f"Skipping item due to missing played_at or track info: Item details: {item}")
                continue

            try:
                played_at_dt = datetime.datetime.fromisoformat(played_at_str.replace('Z', '+00:00'))
            except ValueError:
                logging.warning(f"Could not parse played_at timestamp: {played_at_str}")
                continue

            # Primary filtering: ensure we only process items newer than what's in DB
            if max_played_at_db is not None and played_at_dt <= max_played_at_db:
                logging.debug(f"Skipping item played at {played_at_dt} as it's not newer than max_played_at_db {max_played_at_db}")
                continue

            processed_items_count +=1
            item_type = track_info.get('type')
            if item_type == 'track':
                normalized_data = normalizer.normalize_track_item(item, played_at_dt)
                if normalized_data is None:
                    logging.warning(f"Normalization failed for track: {track_info.get('name', 'N/A')}. Item: {item}")
                    continue

                artist_model_obj, album_model_obj, track_model_obj, listen_model_obj = normalized_data

                # Perform UPSERT operations
                # These functions currently return dicts.
                db_artist_dict = upsert_artist(db_session, artist_model_obj)
                db_album_dict = upsert_album(db_session, album_model_obj)
                db_track_dict = upsert_track(db_session, track_model_obj)

                if not (db_artist_dict and db_album_dict and db_track_dict):
                    logging.error(f"Failed to upsert artist/album/track for listen at {played_at_dt}. Rolling back.")
                    # This error is critical, implies something wrong with data or DB operation logic for main entities
                    db_session.rollback()
                    db_session.close()
                    return # Stop further processing

                # Update listen_obj with IDs from the DB if they were different or generated.
                # In this setup, IDs are from Spotify, so this step is more for FK integrity confirmation.
                # If the upsert functions returned ORM objects, you'd use those.
                # Since they return dicts, and normalizer already sets IDs:
                listen_model_obj.artist_id = db_artist_dict['artist_id']
                listen_model_obj.album_id = db_album_dict['album_id']
                listen_model_obj.track_id = db_track_dict['track_id']

                db_listen = insert_listen(db_session, listen_model_obj)

                if db_listen:
                    new_listens_count += 1
                    logging.info(f"Queued for commit: Listen for track '{track_model_obj.name}' played at {played_at_dt}")
                else:
                    # This is expected for duplicates based on played_at unique constraint
                    logging.warning(f"Failed to queue listen for track '{track_model_obj.name}' (likely duplicate played_at: {played_at_dt})")
            else:
                logging.debug(f"Skipping item of type '{item_type}': {track_info.get('name', 'N/A')}")

        if processed_items_count > 0 or new_listens_count > 0 : # only commit if there was something to do
            db_session.commit()
            logging.info(f"Successfully committed {new_listens_count} new listens to the database. Total items processed after filtering: {processed_items_count}.")
        else:
            logging.info("No new items to process or commit.")

    except Exception as e:
        logging.error(f"An error occurred during data processing: {e}", exc_info=True)
        if db_session:
            db_session.rollback()
    finally:
        if db_session:
            db_session.close()
            logging.info("Database session closed.")

if __name__ == '__main__':
    logging.info("Starting Spotify data processing script.")
    # To run this directly for testing (ensure DB is accessible and ENV VARS are set):
    # 1. Make sure your .env file has DATABASE_URL
    # 2. python -m backend.main (if running from project root)
    # Note: The placeholder functions for Spotify interaction will be used.

    # Example of how one might initialize DB if needed (manual step)
    # choice = input("Initialize database? (yes/no): ")
    # if choice.lower() == 'yes':
    #     try:
    #         confirm = input("This will create tables. Are you sure? (yes/no): ")
    #         if confirm.lower() == 'yes':
    #             init_db_engine = get_db_engine()
    #             init_db(init_db_engine) # Initialize database tables
    #             logging.info("Database initialization requested.")
    #         else:
    #             logging.info("Database initialization cancelled by user.")
    #     except Exception as e:
    #         logging.error(f"Error during manual DB initialization: {e}")

    process_spotify_data()
    logging.info("Spotify data processing script finished.")
