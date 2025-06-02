import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, JSON, Integer # Import JSON and Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Import the functions and classes to be tested
# Assuming tests are run from the 'backend' directory or PYTHONPATH is set appropriately
from backend.src.database import (
    get_db_engine,
    insert_raw_data,
    init_db, # Changed from create_tables
    RecentlyPlayedTracksRaw,
    Base
)
from backend.src.config import get_env_variable # For mocking

# Use a fixed in-memory SQLite database for most tests for speed and isolation.
# For functions that absolutely need PostgreSQL features (like JSONB),
# those might need a separate integration test setup or more complex mocking.
TEST_DATABASE_URL_SQLITE = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def sqlite_engine():
    """Creates an in-memory SQLite engine for testing and creates tables."""
    engine = create_engine(TEST_DATABASE_URL_SQLITE)

    # Original types
    original_data_type = RecentlyPlayedTracksRaw.data.property.columns[0].type
    original_id_type = RecentlyPlayedTracksRaw.id.property.columns[0].type

    # Temporarily change types for SQLite compatibility
    RecentlyPlayedTracksRaw.data.property.columns[0].type = JSON()
    RecentlyPlayedTracksRaw.id.property.columns[0].type = Integer()

    Base.metadata.create_all(engine) # Create tables for this engine instance
    yield engine
    Base.metadata.drop_all(engine) # Clean up tables after test

    # Restore original types
    RecentlyPlayedTracksRaw.data.property.columns[0].type = original_data_type
    RecentlyPlayedTracksRaw.id.property.columns[0].type = original_id_type

@pytest.fixture
def mock_db_session(sqlite_engine):
    """Creates a session from the SQLite engine."""
    Session = sessionmaker(bind=sqlite_engine)
    session = Session()
    yield session
    session.close()

# --- Tests for get_db_engine ---
@patch('backend.src.database.get_env_variable')
@patch('backend.src.database.create_engine')
def test_get_db_engine_success(mock_create_engine, mock_get_env_var):
    """Test get_db_engine successfully creates an engine with URL from env."""
    mock_db_url = "postgresql://user:pass@host:port/dbname"
    mock_get_env_var.return_value = mock_db_url

    # Mock the engine and its connect method
    mock_engine_instance = MagicMock()
    mock_create_engine.return_value = mock_engine_instance

    engine = get_db_engine()

    mock_get_env_var.assert_called_once_with("DATABASE_URL")
    mock_create_engine.assert_called_once_with(mock_db_url)
    mock_engine_instance.connect.assert_called_once() # Check connection test
    assert engine == mock_engine_instance

@patch('backend.src.database.get_env_variable')
def test_get_db_engine_missing_url(mock_get_env_var):
    """Test get_db_engine raises ValueError if DATABASE_URL is not set."""
    mock_get_env_var.return_value = None
    with pytest.raises(ValueError, match="DATABASE_URL environment variable not set"):
        get_db_engine()

@patch('backend.src.database.get_env_variable')
@patch('backend.src.database.create_engine')
def test_get_db_engine_connection_error(mock_create_engine, mock_get_env_var):
    """Test get_db_engine raises error if connection fails."""
    mock_db_url = "postgresql://user:pass@host:port/dbname"
    mock_get_env_var.return_value = mock_db_url

    mock_engine_instance = MagicMock()
    mock_engine_instance.connect.side_effect = SQLAlchemyError("Connection failed")
    mock_create_engine.return_value = mock_engine_instance

    with pytest.raises(SQLAlchemyError, match="Connection failed"):
        get_db_engine()

# --- Tests for init_db (formerly create_tables) ---
def test_create_tables_via_init_db(sqlite_engine): # Renamed function
    """Test that init_db runs without error and tables are created.""" # Updated docstring
    # The fixture sqlite_engine already calls Base.metadata.create_all(engine)
    # So we just check if the table exists using inspect
    from sqlalchemy import inspect
    inspector = inspect(sqlite_engine)
    assert RecentlyPlayedTracksRaw.__tablename__ in inspector.get_table_names()

    # We can also try to run it again to ensure it's idempotent
    try:
        init_db(sqlite_engine) # Changed to init_db
    except Exception as e:
        pytest.fail(f"init_db raised an exception {e} when run on existing tables.") # Updated fail message


# --- Tests for insert_raw_data ---
def test_insert_raw_data_success(sqlite_engine, mock_db_session):
    """Test successful insertion of raw data."""
    sample_data = {"key": "value", "items": [{"id": 1, "name": "Test Song"}]}

    insert_raw_data(sqlite_engine, sample_data)

    # Verify data in the database using the session from the fixture
    record = mock_db_session.query(RecentlyPlayedTracksRaw).first()
    assert record is not None
    assert record.data == sample_data # For SQLite JSON type, dict comparison should work
    assert record.id is not None
    assert record.ingestion_timestamp is not None

def test_insert_raw_data_multiple_records(sqlite_engine, mock_db_session):
    """Test inserting multiple records successfully."""
    sample_data1 = {"event": "play", "track_id": "track1"}
    sample_data2 = {"event": "pause", "track_id": "track2"}

    insert_raw_data(sqlite_engine, sample_data1)
    insert_raw_data(sqlite_engine, sample_data2)

    records = mock_db_session.query(RecentlyPlayedTracksRaw).order_by(RecentlyPlayedTracksRaw.id).all()
    assert len(records) == 2
    assert records[0].data == sample_data1
    assert records[1].data == sample_data2

def test_insert_raw_data_type_error(sqlite_engine):
    """Test insert_raw_data raises TypeError if raw_json_data is not a dict."""
    with pytest.raises(TypeError, match="raw_json_data must be a dictionary"):
        insert_raw_data(sqlite_engine, "not_a_dict")

@patch('backend.src.database.sessionmaker')
def test_insert_raw_data_commit_error(mock_sessionmaker, sqlite_engine):
    """Test insert_raw_data handles SQLAlchemyError during commit and rolls back."""
    mock_session_instance = MagicMock()
    mock_session_instance.commit.side_effect = SQLAlchemyError("Commit failed")
    mock_session_instance.rollback = MagicMock() # Ensure rollback is mockable
    mock_session_instance.close = MagicMock() # Ensure close is mockable

    # Configure the mock sessionmaker to return our mock_session_instance
    # sessionmaker() returns a class, then call it to get session_instance
    mock_session_factory = MagicMock(return_value=mock_session_instance)
    mock_sessionmaker.return_value = mock_session_factory

    sample_data = {"key": "value"}

    with pytest.raises(SQLAlchemyError, match="Commit failed"):
        insert_raw_data(sqlite_engine, sample_data)

    mock_session_instance.add.assert_called_once()
    mock_session_instance.commit.assert_called_once()
    mock_session_instance.rollback.assert_called_once() # Crucial check
    mock_session_instance.close.assert_called_once()


# --- Test RecentlyPlayedTracksRaw model representation ---
def test_recently_played_tracks_raw_repr():
    """Test the __repr__ method of the model."""
    record = RecentlyPlayedTracksRaw(id=1, data={"test": "data"}, ingestion_timestamp="2023-01-01T12:00:00Z")
    # Note: ingestion_timestamp would normally be a datetime object if queried from DB
    # For direct instantiation, the string is fine for repr testing.
    expected_repr = "<RecentlyPlayedTracksRaw(id=1, ingestion_timestamp='2023-01-01T12:00:00Z')>"
    assert repr(record) == expected_repr

# To run these tests:
# Ensure pytest is installed (it's a dev dependency in pyproject.toml)
# From the `backend` directory, run: `poetry run pytest -v`
# Or, if PYTHONPATH is set to include the project root: `pytest backend/tests/test_database.py`
