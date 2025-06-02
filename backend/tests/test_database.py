import pytest
import os # Added
import datetime # Added
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, JSON, Integer, TEXT
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import ARRAY

from backend.src.database import (
    get_db_engine,
    insert_raw_data,
    init_db,
    Base
)
from backend.src.models import RecentlyPlayedTracksRaw, Artist, Track
# Removed: from backend.src.config import get_env_variable

TEST_DATABASE_URL_SQLITE = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def sqlite_engine():
    engine = create_engine(TEST_DATABASE_URL_SQLITE)
    original_artist_genres_type = Artist.genres.property.columns[0].type
    original_track_markets_type = Track.available_markets.property.columns[0].type
    original_raw_data_type = RecentlyPlayedTracksRaw.data.property.columns[0].type
    Artist.genres.property.columns[0].type = JSON()
    Track.available_markets.property.columns[0].type = JSON()
    RecentlyPlayedTracksRaw.data.property.columns[0].type = JSON()
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    Artist.genres.property.columns[0].type = original_artist_genres_type
    Track.available_markets.property.columns[0].type = original_track_markets_type
    RecentlyPlayedTracksRaw.data.property.columns[0].type = original_raw_data_type

@pytest.fixture
def mock_db_session(sqlite_engine):
    Session = sessionmaker(bind=sqlite_engine)
    session = Session()
    yield session
    session.close()

# --- Tests for get_db_engine ---
@patch('os.getenv') # Corrected patch target
@patch('backend.src.database.create_engine')
def test_get_db_engine_success(mock_create_engine, mock_os_getenv): # Renamed mock
    mock_db_url = "postgresql://user:pass@host:port/dbname"
    # Simulate os.getenv calls: first for DATABASE_URL, then for SQLALCHEMY_ECHO
    mock_os_getenv.side_effect = [mock_db_url, "False"]

    mock_engine_instance = MagicMock()
    mock_create_engine.return_value = mock_engine_instance

    engine = get_db_engine()

    mock_os_getenv.assert_any_call("DATABASE_URL") # Check DATABASE_URL call
    mock_os_getenv.assert_any_call("SQLALCHEMY_ECHO", "False") # Check SQLALCHEMY_ECHO call
    mock_create_engine.assert_called_once_with(mock_db_url, echo=False)
    mock_engine_instance.connect.assert_called_once()
    assert engine == mock_engine_instance

@patch('os.getenv') # Corrected patch target
def test_get_db_engine_missing_url(mock_os_getenv): # Renamed mock
    # Simulate os.getenv returning None for DATABASE_URL, then a value for SQLALCHEMY_ECHO
    mock_os_getenv.side_effect = [None, "False"]
    # The function get_database_url now prints a warning and returns a fallback SQLite URL
    # So, get_db_engine should not raise ValueError directly if DATABASE_URL is None,
    # but rather attempt to use the fallback.
    # Let's adjust the test to reflect that get_db_engine proceeds with fallback.
    with patch('backend.src.database.create_engine') as mock_create_engine_fallback:
        mock_engine_instance_fallback = MagicMock()
        mock_create_engine_fallback.return_value = mock_engine_instance_fallback

        engine = get_db_engine() # Should now use fallback

        mock_os_getenv.assert_any_call("DATABASE_URL")
        # It will use the fallback "sqlite:///./local_spotify_dashboard.db"
        expected_fallback_url = "sqlite:///./local_spotify_dashboard.db"
        mock_create_engine_fallback.assert_called_once_with(expected_fallback_url, echo=False)
        mock_engine_instance_fallback.connect.assert_called_once()
        assert engine == mock_engine_instance_fallback

@patch('os.getenv') # Corrected patch target
@patch('backend.src.database.create_engine')
def test_get_db_engine_connection_error(mock_create_engine, mock_os_getenv): # Renamed mock
    mock_db_url = "postgresql://user:pass@host:port/dbname"
    mock_os_getenv.side_effect = [mock_db_url, "False"]

    mock_engine_instance = MagicMock()
    mock_engine_instance.connect.side_effect = SQLAlchemyError("Connection failed")
    mock_create_engine.return_value = mock_engine_instance

    with pytest.raises(SQLAlchemyError, match="Connection failed"):
        get_db_engine()

# --- Tests for init_db (formerly create_tables) ---
def test_create_tables_via_init_db(sqlite_engine):
    from sqlalchemy import inspect
    inspector = inspect(sqlite_engine)
    assert RecentlyPlayedTracksRaw.__tablename__ in inspector.get_table_names()
    assert Artist.__tablename__ in inspector.get_table_names()
    assert Track.__tablename__ in inspector.get_table_names()
    try:
        init_db(sqlite_engine)
    except Exception as e:
        pytest.fail(f"init_db raised an exception {e} when run on existing tables.")

# --- Tests for insert_raw_data ---
def test_insert_raw_data_success(mock_db_session): # Changed sqlite_engine to mock_db_session
    sample_data = {"key": "value", "items": [{"id": 1, "name": "Test Song"}]}
    insert_raw_data(mock_db_session, sample_data) # Use session
    # No commit needed here as insert_raw_data only adds to session. Caller should commit.
    # For verification, we'd need to commit if this test was standalone for the commit part.
    # However, insert_raw_data itself doesn't commit. It returns the object.
    # To test DB state, we need a commit. Let's assume the test implies checking post-commit state.
    mock_db_session.commit()

    record = mock_db_session.query(RecentlyPlayedTracksRaw).first()
    assert record is not None
    assert record.data == sample_data
    assert record.id is not None
    assert record.ingestion_timestamp is not None

def test_insert_raw_data_multiple_records(mock_db_session): # Changed sqlite_engine to mock_db_session
    sample_data1 = {"event": "play", "track_id": "track1"}
    sample_data2 = {"event": "pause", "track_id": "track2"}
    insert_raw_data(mock_db_session, sample_data1) # Use session
    insert_raw_data(mock_db_session, sample_data2) # Use session
    mock_db_session.commit()

    records = mock_db_session.query(RecentlyPlayedTracksRaw).order_by(RecentlyPlayedTracksRaw.id).all()
    assert len(records) == 2
    assert records[0].data == sample_data1
    assert records[1].data == sample_data2

# Added mock_db_session as argument
def test_insert_raw_data_type_error(mock_db_session): # Changed sqlite_engine to mock_db_session
    with pytest.raises(TypeError, match="raw_json_data must be a dictionary"):
        insert_raw_data(mock_db_session, "not_a_dict") # Use session

@patch('backend.src.database.sessionmaker') # This mock setup seems specific to an older version of insert_raw_data
def test_insert_raw_data_commit_error(mock_sessionmaker_dont_use, sqlite_engine):
    # The current insert_raw_data(session, data) does not create its own session nor commit.
    # So this test needs to be re-thought or removed if it's testing an old behavior.
    # If we want to test that insert_raw_data works correctly and then a *subsequent* commit fails,
    # the test structure would be different.
    # For now, let's assume insert_raw_data could raise if session.add fails, though typically it won't.
    # The original test seems to imply insert_raw_data handles session creation/commit itself.
    # Given insert_raw_data(session, data), the commit error test should be at the caller level.
    # Let's adapt it to check if session.add by insert_raw_data fails (less likely).

    mock_session_instance = MagicMock()
    # Simulate error on session.add if that's what we want to test for insert_raw_data internal robustness
    mock_session_instance.add.side_effect = SQLAlchemyError("Add failed")

    sample_data = {"key": "value"}
    with pytest.raises(SQLAlchemyError, match="Add failed"):
        insert_raw_data(mock_session_instance, sample_data) # Use the mock session directly

    mock_session_instance.add.assert_called_once()
    # No commit or rollback should be called by insert_raw_data itself.
    assert not mock_session_instance.commit.called
    assert not mock_session_instance.rollback.called


# --- Test RecentlyPlayedTracksRaw model representation ---
def test_recently_played_tracks_raw_repr():
    ts = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc) # Corrected
    record = RecentlyPlayedTracksRaw(id=1, data={"test": "data"}, ingestion_timestamp=ts)
    expected_repr = f"<RecentlyPlayedTracksRaw(id=1, ingestion_timestamp={ts!r})>" # Corrected
    assert repr(record) == expected_repr

# To run these tests:
# Ensure pytest is installed (it's a dev dependency in pyproject.toml)
# From the `backend` directory, run: `poetry run pytest -v`
# Or, if PYTHONPATH is set to include the project root: `pytest backend/tests/test_database.py`
