import logging
from sqlalchemy import create_engine, Column, BigInteger, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Dict, Any

# Assuming config.py exists in the same directory or is accessible in PYTHONPATH
# and has a function get_env_variable("DATABASE_URL") or similar.
# For now, let's make a placeholder for where config would be imported from.
# from .config import get_env_variable # Placeholder if config.py is in the same directory
# If config.py is in backend/src, then:
from backend.src.config import get_env_variable # Corrected import path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

Base = declarative_base()

class RecentlyPlayedTracksRaw(Base):
    __tablename__ = 'recently_played_tracks_raw'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    data = Column(JSONB, nullable=False)
    ingestion_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<RecentlyPlayedTracksRaw(id={self.id}, ingestion_timestamp='{self.ingestion_timestamp}')>"

def get_db_engine(database_url: str = None):
    """
    Creates and returns a SQLAlchemy engine instance.
    Reads DATABASE_URL from environment variables if not provided.
    """
    if database_url is None:
        database_url = get_env_variable("DATABASE_URL")
    if not database_url:
        logging.error("DATABASE_URL environment variable not set.")
        raise ValueError("DATABASE_URL environment variable not set.")

    logging.info("Creating database engine.")
    try:
        engine = create_engine(database_url)
        # Test connection
        with engine.connect() as connection:
            logging.info("Database connection successful.")
        return engine
    except Exception as e:
        logging.error(f"Error creating database engine or connecting: {e}")
        raise

def insert_raw_data(engine, raw_json_data: Dict[str, Any]) -> None:
    """
    Inserts raw JSON data into the recently_played_tracks_raw table.

    Args:
        engine: The SQLAlchemy engine instance.
        raw_json_data: A dictionary containing the JSON data from Spotify.
    """
    if not isinstance(raw_json_data, dict):
        logging.error("raw_json_data must be a dictionary.")
        raise TypeError("raw_json_data must be a dictionary.")

    DBSession = sessionmaker(bind=engine)
    session: Session = DBSession()

    try:
        new_raw_record = RecentlyPlayedTracksRaw(data=raw_json_data)
        session.add(new_raw_record)
        session.commit()
        logging.info(f"Successfully inserted raw data record with ID: {new_raw_record.id}")
    except Exception as e:
        session.rollback()
        logging.error(f"Error inserting raw data: {e}")
        raise
    finally:
        session.close()

# Example of how to create tables (typically run once, not in the main script flow)
def create_tables(engine):
    """Creates all tables defined by Base metadata (if they don't exist)."""
    try:
        Base.metadata.create_all(engine)
        logging.info("Tables created successfully (if they didn't exist).")
    except Exception as e:
        logging.error(f"Error creating tables: {e}")
        raise

if __name__ == '__main__':
    # This block is for demonstration and manual testing.
    # It requires a .env file with DATABASE_URL.

    # Create a .env file in the backend directory with:
    # DATABASE_URL="postgresql://user:password@host:port/database"

    print("Running database.py for demonstration...")

    try:
        # 1. Get engine (ensure .env is set up for this to work)
        # You might need to run this from the root of the project or adjust PYTHONPATH
        # for 'from backend.src.config import get_env_variable' to work.
        # If running directly within backend/src, use 'from config import get_env_variable'
        # For this subtask, assume it's run in an environment where backend.src.config is findable.

        # To make this runnable for demo, we might need to temporarily adjust path or use a direct import.
        # For now, let's assume get_env_variable can be called.
        # If config.py is:
        # backend/
        #   src/
        #     config.py
        #     database.py
        # then `from .config import get_env_variable` or `from config import get_env_variable`
        # would work if database.py is run as `python -m backend.src.database` from project root.
        # The `from backend.src.config import get_env_variable` is for when other modules import this.

        # Let's simulate getting the URL for direct script execution for now
        import os
        from dotenv import load_dotenv

        # Load .env from the parent directory relative to src (i.e., from 'backend/')
        dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path)
            print(f"Loaded .env file from {dotenv_path}")
        else:
            print(f".env file not found at {dotenv_path}, ensure it exists with DATABASE_URL.")
            # Fallback to os.environ.get if .env is not in the expected place for direct run

        db_url_for_demo = os.environ.get("DATABASE_URL")

        if not db_url_for_demo:
            print("DATABASE_URL not found in environment for demo. Please set it in backend/.env")
        else:
            print(f"Using DATABASE_URL: {db_url_for_demo[:db_url_for_demo.find('@')]}...") # Avoid printing password

            engine = get_db_engine(db_url_for_demo)

            # 2. Create tables (optional, run once if tables don't exist)
            # Make sure your PostgreSQL server is running and accessible.
            print("Attempting to create tables (if they don't exist)...")
            create_tables(engine)

            # 3. Insert some dummy raw data
            print("Attempting to insert dummy raw data...")
            sample_data = {
                "items": [{"track": {"name": "Demo Track"}, "played_at": "2023-01-01T00:00:00Z"}],
                "limit": 1
            }
            insert_raw_data(engine, sample_data)
            print("Dummy raw data insertion attempt complete.")

            # 4. Query to verify (optional)
            DBSession = sessionmaker(bind=engine)
            session = DBSession()
            records = session.query(RecentlyPlayedTracksRaw).order_by(RecentlyPlayedTracksRaw.id.desc()).limit(5).all()
            print(f"Found {len(records)} records in recently_played_tracks_raw (showing max 5 most recent):")
            for rec in records:
                print(rec)
            session.close()

    except ValueError as ve:
        print(f"Configuration Error: {ve}")
    except ImportError as ie:
        print(f"Import Error: {ie}. Make sure you are in the correct directory or PYTHONPATH is set.")
        print("If running this file directly, ensure backend/src/config.py exists and is importable.")
    except Exception as e:
        print(f"An error occurred during demonstration: {e}")
