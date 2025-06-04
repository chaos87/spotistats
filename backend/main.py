# At the top of main.py
from backend.src.logging_config import setup_logging
setup_logging() # Call this early

import logging # Keep this for using logging.getLogger() later
import os
import datetime
from sqlalchemy.orm import Session
from backend.src.database import (
    get_db_engine, init_db, get_session, get_max_played_at,
    upsert_artist, upsert_album, upsert_track, insert_listen,
    upsert_podcast_series, upsert_podcast_episode
)
from backend.src.models import Artist, Album, Track, Listen, PodcastSeries, PodcastEpisode
from backend.src.normalizer import SpotifyItemNormalizer
from backend.src.exceptions import DatabaseError, ConfigurationError, SpotifyAuthError, SpotifyAPIError # Updated import
# For this subtask, we'll use the placeholder functions in main.py for Spotify operations,
# so ConfigurationError for Spotify credentials won't be hit from config.py yet.
from backend.src.config import get_spotify_credentials
from backend.src.spotify_client import SpotifyOAuthClient
from backend.src.spotify_data import get_recently_played_tracks

# Remove: logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
logger = logging.getLogger(__name__) # Standard way to get logger per module

def process_spotify_data():
    logger.info("Starting Spotify data processing.") # Example of using the logger
    engine = None
    db_session = None

    try:
        # Config related calls first (though get_spotify_credentials is a placeholder here)
        client_id, client_secret, refresh_token = get_spotify_credentials()

        # Database setup
        engine = get_db_engine() # Can raise DatabaseError (wrapping ConfigurationError or SQLAlchemyError)
        # init_db(engine) # Typically called once manually. If called, can also raise DatabaseError.
        db_session = get_session(engine) # Can raise DatabaseError

        # Spotify client setup and token fetch
        spotify_client = SpotifyOAuthClient(client_id, client_secret, refresh_token) # Placeholder
        access_token = spotify_client.get_access_token_from_refresh() # Placeholder, real one can raise SpotifyAuthError

        if not access_token:
            # This specific check might be redundant if get_access_token_from_refresh always raises on failure.
            # However, keeping it if a None return is possible for some auth flows.
            logger.error("Failed to get Spotify access token (access_token is None).")
            # Depending on desired behavior, this could be a specific custom error too.
            # For now, it will be caught by generic Exception or lead to issues in get_recently_played_tracks.
            # If this is considered a critical auth failure, could raise SpotifyAuthError here.
            raise SpotifyAuthError("Access token was not obtained (is None).")


        logger.info("Successfully obtained Spotify access token.")

        # Main data processing logic
        max_played_at_db = get_max_played_at(db_session)
        logger.info("Max played_at from DB.", extra={"max_played_at": str(max_played_at_db) if max_played_at_db else None})

        after_param = None
        if max_played_at_db:
            after_param = int(max_played_at_db.timestamp() * 1000)

        # 3. Fetch recently played tracks from Spotify
        spotify_items_response = get_recently_played_tracks(access_token, limit=50, after=after_param)

        if not spotify_items_response or 'items' not in spotify_items_response:
            logger.warning("No items found in Spotify response or bad response.", extra={"response": spotify_items_response})
            # No 'return' here needed explicitly, flow will go to 'finally'.
            # If db_session exists, it will be closed. If items are empty, commit won't happen.
        else: # Only process if items exist
            spotify_items = spotify_items_response['items']
            logger.info(f"Fetched items from Spotify.", extra={"item_count": len(spotify_items)})

            normalizer = SpotifyItemNormalizer() # Updated class name
            new_listens_count = 0
            processed_items_count = 0

            for item in reversed(spotify_items): # Process oldest first to maintain played_at order for duplicates
                track_info = item.get('track', {})
                item_name = track_info.get('name', 'N/A')
                item_id = track_info.get('id', 'N/A')
                played_at_raw = item.get('played_at')

                if not track_info or not played_at_raw:
                    logger.warning("Skipping item due to missing 'track' or 'played_at'.", extra={"item_data": item})
                    continue

                # Check if played_at is newer than max_played_at_db before normalization
                try:
                    played_at_dt = datetime.datetime.fromisoformat(played_at_raw.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning("Could not parse played_at timestamp. Skipping item.",
                                   extra={"played_at_raw": played_at_raw, "item_id": item_id, "item_name": item_name})
                    continue

                if max_played_at_db is not None and played_at_dt <= max_played_at_db:
                    logger.debug("Skipping item as it's not newer than max_played_at_db.",
                                 extra={"played_at": str(played_at_dt), "max_db": str(max_played_at_db), "item_id": item_id})
                    continue

                processed_items_count += 1
                logger.debug("Processing item.", extra={"item_id": item_id, "item_name": item_name, "played_at": str(played_at_dt)})

                normalized_item_data = normalizer.normalize_item(item)

                if not normalized_item_data:
                    logger.warning("Normalization failed for item.",
                                   extra={"item_name": item_name, "item_id": item_id, "played_at_raw": played_at_raw})
                    continue

                item_type = normalized_item_data['type']
                listen_model_obj = normalized_item_data['listen'] # Common listen object

                if item_type == 'track':
                    artist_model_obj = normalized_item_data['artist']
                    album_model_obj = normalized_item_data['album']
                    track_model_obj = normalized_item_data['track']

                    db_artist_dict = upsert_artist(db_session, artist_model_obj)
                    db_album_dict = upsert_album(db_session, album_model_obj)
                    db_track_dict = upsert_track(db_session, track_model_obj)

                    if not (db_artist_dict and db_album_dict and db_track_dict):
                        logger.error("Failed to upsert artist/album/track for listen.",
                                     extra={"track_name": track_model_obj.name if track_model_obj else 'N/A',
                                            "played_at": str(listen_model_obj.played_at)})
                        continue

                    listen_model_obj.artist_id = db_artist_dict['artist_id']
                    listen_model_obj.album_id = db_album_dict['album_id']
                    listen_model_obj.track_id = db_track_dict['track_id']

                    db_listen = insert_listen(db_session, listen_model_obj)
                    if db_listen:
                        new_listens_count += 1
                        logger.info("Queued for commit: Listen for track.",
                                    extra={"track_name": track_model_obj.name, "played_at": str(listen_model_obj.played_at)})
                    else:
                        # This case is handled by insert_listen logging a warning for duplicates
                        pass # insert_listen already logged the warning

                elif item_type == 'episode':
                    series_model_obj = normalized_item_data['series']
                    episode_model_obj = normalized_item_data['episode']

                    upsert_podcast_series(db_session, series_model_obj)
                    upsert_podcast_episode(db_session, episode_model_obj)

                    db_listen = insert_listen(db_session, listen_model_obj)
                    if db_listen:
                        new_listens_count += 1
                        logger.info("Queued for commit: Listen for episode.",
                                    extra={"episode_name": episode_model_obj.name, "played_at": str(listen_model_obj.played_at)})
                    else:
                        # insert_listen already logged the warning
                        pass
                else:
                    logger.warning("Unknown item type from normalizer.",
                                   extra={"item_type": item_type, "item_name": item_name, "item_id": item_id})

            if new_listens_count > 0:
                db_session.commit() # Can raise DatabaseError (wrapping SQLAlchemyError)
                logger.info(f"Successfully committed new listens to the database.",
                            extra={"new_listen_count": new_listens_count, "processed_item_count": processed_items_count})
            elif processed_items_count > 0 and new_listens_count == 0:
                 logger.info("Processed items, but no new listens were added (e.g. all duplicates or normalization issues). No commit performed.",
                             extra={"processed_item_count": processed_items_count})
            else: # No items processed after filtering, no new listens
                logger.info("No new items to process or commit.")

    except ConfigurationError as e:
        logger.error("Configuration error encountered.", exc_info=True) # exc_info=True adds stack trace
        if db_session:
            try:
                db_session.rollback()
                logger.info("Database session rolled back due to ConfigurationError (though unlikely to be active).")
            except Exception as rb_e:
                logger.error("Error during session rollback after ConfigurationError.", exc_info=True, extra={"rollback_error": str(rb_e)})
    except DatabaseError as e:
        logger.error("Database error encountered.", exc_info=True)
        if db_session:
            try:
                db_session.rollback()
                logger.info("Database session rolled back due to DatabaseError.")
            except Exception as rb_e: # Catch potential error during rollback
                logger.error("Error during session rollback after DatabaseError.", exc_info=True, extra={"rollback_error": str(rb_e)})
    except SpotifyAuthError as e:
        logger.error("Spotify authentication error encountered.", exc_info=True)
        if db_session:
            try:
                db_session.rollback()
                logger.info("Database session rolled back due to SpotifyAuthError.")
            except Exception as rb_e:
                logger.error("Error during session rollback after SpotifyAuthError.", exc_info=True, extra={"rollback_error": str(rb_e)})
    except SpotifyAPIError as e:
        logger.error("Spotify API error encountered.", exc_info=True)
        if db_session:
            try:
                db_session.rollback()
                logger.info("Database session rolled back due to SpotifyAPIError.")
            except Exception as rb_e:
                logger.error("Error during session rollback after SpotifyAPIError.", exc_info=True, extra={"rollback_error": str(rb_e)})
    except Exception as e: # Generic catch-all for unexpected errors
        logger.error("An unexpected error occurred during data processing.", exc_info=True)
        if db_session:
            try:
                db_session.rollback()
                logger.info("Database session rolled back due to unexpected error.")
            except Exception as rb_e:
                logger.error("Error during session rollback after unexpected error.", exc_info=True, extra={"rollback_error": str(rb_e)})
    finally:
        if db_session:
            try:
                db_session.close()
                logger.info("Database session closed.")
            except Exception as cl_e: # Catch error during close
                logger.error("Error during session close.", exc_info=True, extra={"close_error": str(cl_e)})

if __name__ == '__main__':
    # setup_logging() is already called at the top of the script.
    # No need to get a new logger here if we use the one defined at module level for these script-level logs.
    # However, if process_spotify_data() was in another module, it would define its own logger.
    # For consistency, ensure all logs use a logger instance.
    script_logger = logging.getLogger(__name__) # Or just use 'logger' if it's meant to be the same.
    script_logger.info("Spotify data processing script started via __main__.")
    process_spotify_data()
    script_logger.info("Spotify data processing script finished via __main__.")
