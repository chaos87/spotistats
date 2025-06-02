import os
import logging
import datetime
from sqlalchemy.orm import Session
from backend.src.database import get_db_engine, init_db, get_session, get_max_played_at, upsert_artist, upsert_album, upsert_track, insert_listen
from backend.src.models import Artist, Album, Track, Listen
from backend.src.normalizer import SpotifyMusicNormalizer
# Placeholder functions will remain as they are for this refactoring
# from backend.src.config import get_spotify_credentials
# from backend.src.spotify_client import SpotifyOAuthClient
# from backend.src.spotify_data import get_recently_played_tracks

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
    # Example data from previous version
    return {
        "items": [
            {
                "track": {
                    "id": "track_id_1", "name": "Test Track 1", "type": "track",
                    "artists": [{"id": "artist_id_1", "name": "Test Artist 1", "external_urls": {"spotify":"artist_url_1"}}],
                    "album": {"id": "album_id_1", "name": "Test Album 1", "images": [{"url": "img_url_1"}], "external_urls": {"spotify":"album_url_1"}, "release_date":"2023-01-01", "release_date_precision":"day"},
                }, "played_at": "2023-01-15T10:30:00Z"
            },
            {
                "track": {"id": "episode_id_1", "name": "Test Episode 1", "type": "episode"},
                "played_at": "2023-01-15T11:00:00Z"
            }
        ], "next": None
    }

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

def process_spotify_data():
    engine = None  # Initialize before try block
    db_session = None  # Initialize before try block

    try:
        engine = get_db_engine()
        # Optional: init_db(engine) # Typically called once manually, not every run.
        db_session = get_session(engine)

        # 1. Get Spotify Access Token
        client_id, client_secret, refresh_token = get_spotify_credentials()
        spotify_client = SpotifyOAuthClient(client_id, client_secret, refresh_token)
        access_token = spotify_client.get_access_token_from_refresh()

        if not access_token:
            logging.error("Failed to get Spotify access token.")
            # No return here, finally will still execute if db_session is None
            # If db_session was created before this error, finally should handle it.
            # However, if this error is critical, might want to ensure db_session is not used.
            # For now, assume if access_token fails, we might not want to proceed to DB operations.
            # A 'return' here would skip the main logic but still hit 'finally'.
            return

        logging.info("Successfully obtained Spotify access token.")

        # 2. Get max_played_at from DB
        max_played_at_db = get_max_played_at(db_session)
        logging.info(f"Max played_at from DB: {max_played_at_db}")

        after_param = None
        if max_played_at_db:
            after_param = int(max_played_at_db.timestamp() * 1000)

        # 3. Fetch recently played tracks from Spotify
        spotify_items_response = get_recently_played_tracks(access_token, limit=50, after=after_param)

        if not spotify_items_response or 'items' not in spotify_items_response:
            logging.warning("No items found in Spotify response or bad response.")
            # No 'return' here needed explicitly, flow will go to 'finally'.
            # If db_session exists, it will be closed. If items are empty, commit won't happen.
        else: # Only process if items exist
            spotify_items = spotify_items_response['items']
            logging.info(f"Fetched {len(spotify_items)} items from Spotify.")

            normalizer = SpotifyMusicNormalizer()
            new_listens_count = 0
            processed_items_count = 0

            for item in reversed(spotify_items):
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

                    db_artist_dict = upsert_artist(db_session, artist_model_obj)
                    db_album_dict = upsert_album(db_session, album_model_obj)
                    db_track_dict = upsert_track(db_session, track_model_obj)

                    if not (db_artist_dict and db_album_dict and db_track_dict):
                        # This is a critical error for a specific item, might indicate bad data from normalizer or DB issue
                        # For now, log error and continue with other items rather than full rollback of batch
                        logging.error(f"Failed to upsert artist/album/track for listen: {track_model_obj.name if track_model_obj else 'N/A'} played at {played_at_dt}. Skipping this listen.")
                        continue # Skip this listen

                    listen_model_obj.artist_id = db_artist_dict['artist_id']
                    listen_model_obj.album_id = db_album_dict['album_id']
                    listen_model_obj.track_id = db_track_dict['track_id']

                    db_listen = insert_listen(db_session, listen_model_obj)

                    if db_listen:
                        new_listens_count += 1
                        logging.info(f"Queued for commit: Listen for track '{track_model_obj.name}' played at {played_at_dt}")
                    else:
                        logging.warning(f"Failed to queue listen for track '{track_model_obj.name}' (likely duplicate played_at: {played_at_dt})")
                else:
                    logging.debug(f"Skipping item of type '{item_type}': {track_info.get('name', 'N/A')}")

            if new_listens_count > 0 : # Only commit if new listens were successfully processed and added
                db_session.commit()
                logging.info(f"Successfully committed {new_listens_count} new listens to the database. Total items processed (newer than max_played_at): {processed_items_count}.")
            elif processed_items_count > 0 and new_listens_count == 0:
                 logging.info(f"Processed {processed_items_count} items, but no new listens were added (e.g. all duplicates or normalization issues). No commit performed.")
            else: # No items processed after filtering, no new listens
                logging.info("No new items to process or commit.")

    except Exception as e:
        logging.error(f"An error occurred during data processing: {e}", exc_info=True)
        if db_session:
            try:
                db_session.rollback()
                logging.info("Database session rolled back due to error.")
            except Exception as rb_e:
                logging.error(f"Error during session rollback: {rb_e}", exc_info=True)
    finally:
        if db_session:
            try:
                db_session.close()
                logging.info("Database session closed.")
            except Exception as cl_e:
                logging.error(f"Error during session close: {cl_e}", exc_info=True)

if __name__ == '__main__':
    logging.info("Starting Spotify data processing script.")
    process_spotify_data()
    logging.info("Spotify data processing script finished.")
