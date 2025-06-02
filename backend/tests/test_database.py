import pytest
import os
import datetime
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
@patch('os.getenv')
@patch('backend.src.database.create_engine')
def test_get_db_engine_success(mock_create_engine, mock_os_getenv):
    mock_db_url = "postgresql://user:pass@host:port/dbname"
    mock_os_getenv.side_effect = [mock_db_url, "False"]

    mock_engine_instance = MagicMock()
    mock_create_engine.return_value = mock_engine_instance

    engine = get_db_engine()

    mock_os_getenv.assert_any_call("DATABASE_URL")
    mock_os_getenv.assert_any_call("SQLALCHEMY_ECHO", "False")
    mock_create_engine.assert_called_once_with(mock_db_url, echo=False)
    assert engine == mock_engine_instance

@patch('os.getenv')
def test_get_db_engine_missing_url(mock_os_getenv):
    mock_os_getenv.side_effect = [None, "False"]
    with patch('backend.src.database.create_engine') as mock_create_engine_fallback:
        mock_engine_instance_fallback = MagicMock()
        mock_create_engine_fallback.return_value = mock_engine_instance_fallback

        engine = get_db_engine()

        mock_os_getenv.assert_any_call("DATABASE_URL")
        expected_fallback_url = "sqlite:///./local_spotify_dashboard.db"
        mock_create_engine_fallback.assert_called_once_with(expected_fallback_url, echo=False)
        # mock_engine_instance_fallback.connect.assert_called_once() # Removed this line
        assert engine == mock_engine_instance_fallback

# TODO: This test needs redesigning to test connection errors at a more appropriate stage (e.g., during session usage),
# as get_db_engine itself does not establish a connection.
# @patch('os.getenv')
# @patch('backend.src.database.create_engine')
# def test_get_db_engine_connection_error(mock_create_engine, mock_os_getenv):
#     mock_db_url = "postgresql://user:pass@host:port/dbname"
#     mock_os_getenv.side_effect = [mock_db_url, "False"]

#     mock_engine_instance = MagicMock()
#     mock_engine_instance.connect.side_effect = SQLAlchemyError("Connection failed")
#     mock_create_engine.return_value = mock_engine_instance

#     with pytest.raises(SQLAlchemyError, match="Connection failed"):
#         get_db_engine()

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
def test_insert_raw_data_success(mock_db_session):
    sample_data = {"key": "value", "items": [{"id": 1, "name": "Test Song"}]}
    insert_raw_data(mock_db_session, sample_data)
    mock_db_session.commit()

    record = mock_db_session.query(RecentlyPlayedTracksRaw).first()
    assert record is not None
    assert record.data == sample_data
    assert record.id is not None
    assert record.ingestion_timestamp is not None

def test_insert_raw_data_multiple_records(mock_db_session):
    sample_data1 = {"event": "play", "track_id": "track1"}
    sample_data2 = {"event": "pause", "track_id": "track2"}
    insert_raw_data(mock_db_session, sample_data1)
    insert_raw_data(mock_db_session, sample_data2)
    mock_db_session.commit()

    records = mock_db_session.query(RecentlyPlayedTracksRaw).order_by(RecentlyPlayedTracksRaw.id).all()
    assert len(records) == 2
    assert records[0].data == sample_data1
    assert records[1].data == sample_data2

def test_insert_raw_data_type_error(mock_db_session):
    with pytest.raises(TypeError, match="raw_json_data must be a dictionary"):
        insert_raw_data(mock_db_session, "not_a_dict")

@patch('backend.src.database.sessionmaker')
def test_insert_raw_data_commit_error(mock_sessionmaker_dont_use, sqlite_engine):
    mock_session_instance = MagicMock()
    mock_session_instance.add.side_effect = SQLAlchemyError("Add failed")

    sample_data = {"key": "value"}
    with pytest.raises(SQLAlchemyError, match="Add failed"):
        insert_raw_data(mock_session_instance, sample_data)

    mock_session_instance.add.assert_called_once()
    assert not mock_session_instance.commit.called
    assert not mock_session_instance.rollback.called


# --- Test RecentlyPlayedTracksRaw model representation ---
def test_recently_played_tracks_raw_repr():
    ts = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
    record = RecentlyPlayedTracksRaw(id=1, data={"test": "data"}, ingestion_timestamp=ts)
    expected_repr = f"<RecentlyPlayedTracksRaw(id=1, ingestion_timestamp={ts!r})>"
    assert repr(record) == expected_repr

# To run these tests:
# Ensure pytest is installed (it's a dev dependency in pyproject.toml)
# From the `backend` directory, run: `poetry run pytest -v`
# Or, if PYTHONPATH is set to include the project root: `pytest backend/tests/test_database.py`
