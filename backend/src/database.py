import os
import datetime # Added
import logging # Added
from typing import Optional # Added
from sqlalchemy import create_engine, select, func # Added select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert as pg_insert # Added for ON CONFLICT
from sqlalchemy.exc import IntegrityError # Added
from dotenv import load_dotenv

# Import Base and specific models used by functions in this file
from backend.src.models import Base, RecentlyPlayedTracksRaw, Artist, Album, Track, Listen # Added Artist, Album, Track, Listen

load_dotenv() # Ensure .env is loaded for DATABASE_URL

logger = logging.getLogger(__name__) # Added logger

def get_database_url():
    url = os.getenv("DATABASE_URL")
    if not url:
        # Fallback or error for local development if .env is not set up
        print("Warning: DATABASE_URL not found in environment. Using default SQLite DB for local dev.")
        return "sqlite:///./local_spotify_dashboard.db" # Example fallback
    return url

def get_db_engine(db_url=None):
    if db_url is None:
        db_url = get_database_url()
    if not db_url: # Should not happen if get_database_url has a fallback or raises error
        raise ValueError("Database URL is not set.")
    # Set echo=True for debugging SQL queries locally if needed
    return create_engine(db_url, echo=os.getenv("SQLALCHEMY_ECHO", "False").lower() == "true")

def get_session(engine=None):
    if engine is None:
        engine = get_db_engine()
    # autoflush=False can be useful in some scenarios, autocommit=False is default
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return Session()

# This function assumes a session is passed to it and the caller handles commit/rollback
def insert_raw_data(session, raw_json_data: dict) -> RecentlyPlayedTracksRaw:
    if not isinstance(raw_json_data, dict):
        raise TypeError("raw_json_data must be a dictionary")
    # Creates an instance of RecentlyPlayedTracksRaw and adds it to the session.
    # The caller is responsible for committing the session.
    db_record = RecentlyPlayedTracksRaw(data=raw_json_data)
    session.add(db_record)
    return db_record # Return the instance if it's useful to the caller

# A general function to initialize the database (create all tables defined in models.py)
# This should be called explicitly, e.g., in main.py or a setup script, not automatically on import.
def init_db(engine=None): # pragma: no cover
    if engine is None:
        engine = get_db_engine()
    # Base.metadata.create_all(engine) will create tables based on models imported from backend.src.models
    Base.metadata.create_all(engine)
    print("Database initialized (tables created if they didn't exist).")


def get_max_played_at(session) -> Optional[datetime.datetime]:
    max_ts = session.execute(select(func.max(Listen.played_at))).scalar_one_or_none()
    return max_ts

def upsert_artist(session, artist_obj: Artist) -> dict: # Return type changed to dict for now
    # Ensure artist_obj.genres is a list, even if None from model, pg_insert expects list for ARRAY
    genres = artist_obj.genres if artist_obj.genres is not None else []

    stmt = pg_insert(Artist).values(
        artist_id=artist_obj.artist_id,
        name=artist_obj.name,
        spotify_url=artist_obj.spotify_url,
        image_url=artist_obj.image_url,
        genres=genres
    ).on_conflict_do_update(
        index_elements=[Artist.artist_id],
        set_=dict(
            name=artist_obj.name,
            spotify_url=artist_obj.spotify_url,
            image_url=artist_obj.image_url,
            genres=genres # Use the potentially corrected genres list
        )
    ).returning(Artist.artist_id, Artist.name, Artist.spotify_url, Artist.image_url, Artist.genres) # Specify columns

    result_row = session.execute(stmt).fetchone()
    return result_row._asdict() if result_row else None

def upsert_album(session, album_obj: Album) -> dict: # Return type changed to dict
    stmt = pg_insert(Album).values(
        album_id=album_obj.album_id,
        name=album_obj.name,
        release_date=album_obj.release_date,
        album_type=album_obj.album_type,
        spotify_url=album_obj.spotify_url,
        image_url=album_obj.image_url,
        primary_artist_id=album_obj.primary_artist_id
    ).on_conflict_do_update(
        index_elements=[Album.album_id],
        set_=dict(
            name=album_obj.name,
            release_date=album_obj.release_date,
            album_type=album_obj.album_type,
            spotify_url=album_obj.spotify_url,
            image_url=album_obj.image_url,
            primary_artist_id=album_obj.primary_artist_id
        )
    ).returning(Album.album_id, Album.name, Album.release_date, Album.album_type, Album.spotify_url, Album.image_url, Album.primary_artist_id)
    result_row = session.execute(stmt).fetchone()
    return result_row._asdict() if result_row else None

def upsert_track(session, track_obj: Track) -> dict: # Return type changed to dict
    # Ensure available_markets is a list
    available_markets = track_obj.available_markets if track_obj.available_markets is not None else []

    stmt = pg_insert(Track).values(
        track_id=track_obj.track_id,
        name=track_obj.name,
        duration_ms=track_obj.duration_ms,
        explicit=track_obj.explicit,
        popularity=track_obj.popularity,
        preview_url=track_obj.preview_url,
        spotify_url=track_obj.spotify_url,
        album_id=track_obj.album_id,
        available_markets=available_markets,
        last_played_at=track_obj.last_played_at
    ).on_conflict_do_update(
        index_elements=[Track.track_id],
        set_=dict(
            name=track_obj.name,
            duration_ms=track_obj.duration_ms,
            explicit=track_obj.explicit,
            popularity=track_obj.popularity,
            preview_url=track_obj.preview_url,
            spotify_url=track_obj.spotify_url,
            album_id=track_obj.album_id,
            available_markets=available_markets, # Use potentially corrected list
            last_played_at=track_obj.last_played_at
        )
    ).returning(Track.track_id, Track.name, Track.duration_ms, Track.explicit, Track.popularity, Track.preview_url, Track.spotify_url, Track.album_id, Track.available_markets, Track.last_played_at)
    result_row = session.execute(stmt).fetchone()
    return result_row._asdict() if result_row else None


def insert_listen(session, listen_obj: Listen) -> Optional[Listen]:
    try:
        session.add(listen_obj)
        session.flush()
        return listen_obj
    except IntegrityError:
        # Caller should handle rollback for the whole transaction
        logger.warning(f"IntegrityError: Could not insert listen record for item played at {listen_obj.played_at}. Might be a duplicate.", exc_info=False) # exc_info=False to reduce noise for expected errors
        return None
