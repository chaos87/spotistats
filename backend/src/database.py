import os
import json # Added
import datetime # Added
import logging # Added
from typing import Optional # Added
from sqlalchemy import create_engine, select, func, case # Added case
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert as pg_insert # Added for ON CONFLICT
from sqlalchemy.exc import IntegrityError, SQLAlchemyError # Added SQLAlchemyError
from dotenv import load_dotenv

# Import Base and specific models used by functions in this file
from .models import Base, RecentlyPlayedTracksRaw, Artist, Album, Track, Listen, PodcastSeries, PodcastEpisode # Added Artist, Album, Track, Listen
from .exceptions import DatabaseError # Import custom DatabaseError
from .config import get_database_url_config # Import config function for DB URL

load_dotenv() # Ensure .env is loaded for DATABASE_URL. TODO: This might be redundant if config.py handles it.

logger = logging.getLogger(__name__) # Added logger

# def get_database_url(): # This function is now effectively in config.py as get_database_url_config
#     url = os.getenv("DATABASE_URL")
#     if not url:
#         # Fallback or error for local development if .env is not set up
#         print("Warning: DATABASE_URL not found in environment. Using default SQLite DB for local dev.")
#         return "sqlite:///./local_spotify_dashboard.db" # Example fallback
#     return url

def get_db_engine(db_url: Optional[str] = None):
    try:
        if db_url is None:
            db_url = get_database_url_config() # Use the function from config.py
        # db_url being None should be caught by get_database_url_config raising ConfigurationError
        # Set echo=True for debugging SQL queries locally if needed
        engine = create_engine(db_url, echo=os.getenv("SQLALCHEMY_ECHO", "False").lower() == "true")
        logger.debug("DB engine created successfully.", extra={"db_url": db_url})
        return engine
    except SQLAlchemyError as e: # Catch errors from create_engine itself
        logger.error("SQLAlchemyError creating DB engine.", exc_info=True, extra={"db_url": db_url, "error": str(e)})
        raise DatabaseError(f"Failed to create DB engine: {e}") from e
    except Exception as e: # Catch any other unexpected error like ConfigurationError not being caught by caller
        logger.error("Unexpected error creating DB engine.", exc_info=True, extra={"db_url": db_url, "error": str(e)})
        raise DatabaseError(f"Unexpected error creating DB engine: {e}") from e


def get_session(engine=None):
    try:
        if engine is None:
            engine = get_db_engine()
        # autoflush=False can be useful in some scenarios, autocommit=False is default
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        logger.debug("DB session factory created successfully.")
        return Session()
    except Exception as e: # Includes DatabaseError from get_db_engine
        logger.error("Error creating session factory.", exc_info=True, extra={"error": str(e)})
        # If get_db_engine raises DatabaseError, we just re-raise it.
        # Otherwise, wrap other potential errors from sessionmaker.
        if isinstance(e, DatabaseError):
            raise
        raise DatabaseError(f"Failed to create session: {e}") from e

def insert_raw_data(session, raw_json_data: dict) -> RecentlyPlayedTracksRaw:
    """Inserts raw JSON data into the database."""
    if not isinstance(raw_json_data, dict):
        # This is a programming error, so TypeError is appropriate.
        raise TypeError("raw_json_data must be a dictionary")
    try:
        db_record = RecentlyPlayedTracksRaw(data=raw_json_data)
        session.add(db_record)
        logger.debug("Raw data record added to session.", extra={"record_id": db_record.id if db_record.id else "pending_flush"})
        # The caller is responsible for session.commit() or session.rollback()
        return db_record
    except SQLAlchemyError as e:
        logger.error("SQLAlchemyError in insert_raw_data.", exc_info=True, extra={"error": str(e)})
        raise DatabaseError(f"Failed to insert raw data: {e}") from e

def init_db(engine=None): # pragma: no cover
    """Initializes the database by creating all tables."""
    try:
        if engine is None:
            engine = get_db_engine()
        Base.metadata.create_all(engine)
        logger.info("Database initialized (tables created if they didn't exist).", extra={"engine_url": str(engine.url)})
    except SQLAlchemyError as e: # Catch errors from create_all
        logger.error("SQLAlchemyError during DB initialization.", exc_info=True, extra={"error": str(e)})
        raise DatabaseError(f"Failed to initialize database: {e}") from e
    except DatabaseError as e: # Catch errors from get_db_engine
        logger.error("DatabaseError during DB initialization (from get_db_engine).", exc_info=True, extra={"error": str(e)})
        raise # Re-raise because it's already a DatabaseError
    except Exception as e:
        logger.error("Unexpected error during DB initialization.", exc_info=True, extra={"error": str(e)})
        raise DatabaseError(f"Unexpected error initializing database: {e}") from e


def get_max_played_at(session) -> Optional[datetime.datetime]:
    """Retrieves the maximum 'played_at' timestamp from the Listen table."""
    try:
        max_ts = session.execute(select(func.max(Listen.played_at))).scalar_one_or_none()
        if max_ts and max_ts.tzinfo is None:
            max_ts = max_ts.replace(tzinfo=datetime.timezone.utc)
        logger.debug("Retrieved max_played_at.", extra={"max_played_at": str(max_ts) if max_ts else None})
        return max_ts
    except SQLAlchemyError as e:
        logger.error("SQLAlchemyError in get_max_played_at.", exc_info=True, extra={"error": str(e)})
        raise DatabaseError(f"Failed to get max played_at: {e}") from e

def upsert_artist(session, artist_obj: Artist) -> dict:
    """Upserts an artist record into the database."""

    genres_val = artist_obj.genres
    if session.bind.dialect.name == 'sqlite':
        if isinstance(genres_val, list):
            genres_to_insert = json.dumps(genres_val)
        elif genres_val is None: # Handle None explicitly for SQLite
            genres_to_insert = json.dumps([])
        else: # Already a string or other type, pass through (or error if not expected)
            genres_to_insert = genres_val
    else: # For PostgreSQL or other dialects
        genres_to_insert = genres_val if genres_val is not None else []

    try:
        stmt = pg_insert(Artist).values(
            artist_id=artist_obj.artist_id, name=artist_obj.name,
            spotify_url=artist_obj.spotify_url, image_url=artist_obj.image_url,
            genres=genres_to_insert  # Use the processed value
        ).on_conflict_do_update(
            index_elements=[Artist.artist_id],
            set_=dict(
                name=artist_obj.name, spotify_url=artist_obj.spotify_url,
                image_url=artist_obj.image_url, genres=genres_to_insert  # Use the processed value
            )
        ).returning(Artist.artist_id, Artist.name, Artist.spotify_url, Artist.image_url, Artist.genres)
        result_row = session.execute(stmt).fetchone()
        logger.debug("Upserted artist successfully.", extra={"artist_id": artist_obj.artist_id, "returned_data_is_none": result_row is None})
        return result_row._asdict() if result_row else None
    except SQLAlchemyError as e:
        logger.error("SQLAlchemyError in upsert_artist.", exc_info=True, extra={"artist_id": artist_obj.artist_id, "error": str(e)})
        raise DatabaseError(f"Failed to upsert artist {artist_obj.artist_id}: {e}") from e

def upsert_album(session, album_obj: Album) -> dict:
    """Upserts an album record into the database."""
    try:
        stmt = pg_insert(Album).values(
            album_id=album_obj.album_id, name=album_obj.name,
            release_date=album_obj.release_date, album_type=album_obj.album_type,
            spotify_url=album_obj.spotify_url, image_url=album_obj.image_url,
            primary_artist_id=album_obj.primary_artist_id
        ).on_conflict_do_update(
            index_elements=[Album.album_id],
            set_=dict(
                name=album_obj.name, release_date=album_obj.release_date,
                album_type=album_obj.album_type, spotify_url=album_obj.spotify_url,
                image_url=album_obj.image_url, primary_artist_id=album_obj.primary_artist_id
            )
        ).returning(Album.album_id, Album.name, Album.release_date, Album.album_type, Album.spotify_url, Album.image_url, Album.primary_artist_id)
        result_row = session.execute(stmt).fetchone()
        logger.debug("Upserted album successfully.", extra={"album_id": album_obj.album_id, "returned_data_is_none": result_row is None})
        return result_row._asdict() if result_row else None
    except SQLAlchemyError as e:
        logger.error("SQLAlchemyError in upsert_album.", exc_info=True, extra={"album_id": album_obj.album_id, "error": str(e)})
        raise DatabaseError(f"Failed to upsert album {album_obj.album_id}: {e}") from e

def upsert_track(session, track_obj: Track) -> dict:
    """Upserts a track record into the database."""

    markets_val = track_obj.available_markets
    if session.bind.dialect.name == 'sqlite':
        if isinstance(markets_val, list):
            markets_to_insert = json.dumps(markets_val)
        elif markets_val is None:
            markets_to_insert = json.dumps([])
        else:
            markets_to_insert = markets_val
    else: # For PostgreSQL or other dialects
        markets_to_insert = markets_val if markets_val is not None else []

    try:
        stmt = pg_insert(Track).values(
            track_id=track_obj.track_id, name=track_obj.name,
            duration_ms=track_obj.duration_ms, explicit=track_obj.explicit,
            popularity=track_obj.popularity, preview_url=track_obj.preview_url,
            spotify_url=track_obj.spotify_url, album_id=track_obj.album_id,
            available_markets=markets_to_insert,  # Use the processed value
            last_played_at=track_obj.last_played_at
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[Track.track_id],
            set_={
                'name': stmt.excluded.name,
                'duration_ms': stmt.excluded.duration_ms,
                'explicit': stmt.excluded.explicit,
                'popularity': stmt.excluded.popularity,
                'preview_url': stmt.excluded.preview_url,
                'spotify_url': stmt.excluded.spotify_url,
                'album_id': stmt.excluded.album_id,
                'available_markets': stmt.excluded.available_markets, # Use stmt.excluded here
                'last_played_at': case(
                    (stmt.excluded.last_played_at > Track.last_played_at, stmt.excluded.last_played_at),
                    else_=Track.last_played_at
                )
            }
        ).returning(Track.track_id, Track.name, Track.duration_ms, Track.explicit, Track.popularity, Track.preview_url, Track.spotify_url, Track.album_id, Track.available_markets, Track.last_played_at)
        result_row = session.execute(stmt).fetchone()
        logger.debug("Upserted track successfully.", extra={"track_id": track_obj.track_id, "returned_data_is_none": result_row is None})
        return result_row._asdict() if result_row else None
    except SQLAlchemyError as e:
        logger.error("SQLAlchemyError in upsert_track.", exc_info=True, extra={"track_id": track_obj.track_id, "error": str(e)})
        raise DatabaseError(f"Failed to upsert track {track_obj.track_id}: {e}") from e


def insert_listen(session, listen_obj: Listen) -> Optional[Listen]:
    """Inserts a listen record. Returns the object if successful, None if IntegrityError (duplicate)."""
    try:
        session.add(listen_obj)
        session.flush() # Use flush to catch IntegrityError here, commit is handled by caller
        logger.debug("Listen record flushed to session.", extra={"played_at": str(listen_obj.played_at), "item_id": listen_obj.track_id or listen_obj.episode_id})
        return listen_obj
    except IntegrityError:
        # This is an expected error for duplicate listens, log and return None.
        # The caller (process_spotify_data) handles rollback for the whole transaction.
        logger.warning("IntegrityError (likely duplicate) for listen. Skipping.",
                       exc_info=False, # Keep exc_info False for this specific, common case to reduce noise
                       extra={"played_at": str(listen_obj.played_at),
                              "item_id": listen_obj.track_id or listen_obj.episode_id})
        return None # Explicitly return None for handled IntegrityError
    except SQLAlchemyError as e:
        # For other SQLAlchemy errors, wrap in DatabaseError and re-raise.
        logger.error("SQLAlchemyError in insert_listen.", exc_info=True,
                       extra={"played_at": str(listen_obj.played_at),
                              "item_id": listen_obj.track_id or listen_obj.episode_id,
                              "error": str(e)})
        raise DatabaseError(f"Failed to insert listen for item played at {listen_obj.played_at}: {e}") from e

def upsert_podcast_series(session, series_obj: PodcastSeries) -> Optional[PodcastSeries]:
    """Upserts a podcast series record (on conflict do nothing)."""
    try:
        stmt = pg_insert(PodcastSeries).values(
            series_id=series_obj.series_id, name=series_obj.name,
            publisher=series_obj.publisher, description=series_obj.description,
            image_url=series_obj.image_url, spotify_url=series_obj.spotify_url
        ).on_conflict_do_nothing(
            index_elements=[PodcastSeries.series_id]
        )
        session.execute(stmt)
        # For "ON CONFLICT DO NOTHING", execute doesn't return the row directly via RETURNING
        # in the same way as DO UPDATE. We return the input object assuming success.
        # A select could confirm, but adds overhead. This matches existing behavior.
        logger.debug("Upserted podcast series (on conflict do nothing).", extra={"series_id": series_obj.series_id})
        return series_obj
    except SQLAlchemyError as e:
        logger.error("SQLAlchemyError in upsert_podcast_series.", exc_info=True, extra={"series_id": series_obj.series_id, "error": str(e)})
        raise DatabaseError(f"Failed to upsert podcast series {series_obj.series_id}: {e}") from e

def upsert_podcast_episode(session, episode_obj: PodcastEpisode) -> Optional[PodcastEpisode]:
    """Upserts a podcast episode record (on conflict do nothing)."""
    try:
        stmt = pg_insert(PodcastEpisode).values(
            episode_id=episode_obj.episode_id, name=episode_obj.name,
            description=episode_obj.description, duration_ms=episode_obj.duration_ms,
            explicit=episode_obj.explicit, release_date=episode_obj.release_date,
            spotify_url=episode_obj.spotify_url, series_id=episode_obj.series_id
        ).on_conflict_do_nothing(
            index_elements=[PodcastEpisode.episode_id]
        )
        session.execute(stmt)
        # Similar to series, return input object assuming success.
        logger.debug("Upserted podcast episode (on conflict do nothing).", extra={"episode_id": episode_obj.episode_id})
        return episode_obj
    except SQLAlchemyError as e:
        logger.error("SQLAlchemyError in upsert_podcast_episode.", exc_info=True, extra={"episode_id": episode_obj.episode_id, "error": str(e)})
        raise DatabaseError(f"Failed to upsert podcast episode {episode_obj.episode_id}: {e}") from e
