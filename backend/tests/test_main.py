import pytest
from unittest.mock import patch, MagicMock, ANY # Import ANY for logging message check
import logging
import datetime

# Import errors that main.py specifically catches
from backend.src.spotify_client import SpotifyAuthError
from backend.src.spotify_data import SpotifyAPIError
# Import models for type hinting in normalizer mock if needed
from backend.src.models import Artist, Album, Track, Listen


@pytest.fixture(autouse=True)
def disable_logging_for_tests():
    logging.disable(logging.CRITICAL + 1)
    yield
    logging.disable(logging.NOTSET)


# Common setup for mocks that allow execution to proceed deep into process_spotify_data
def setup_happy_path_mocks(
    mock_get_db_engine, mock_get_spotify_credentials, mock_spotify_oauth_client,
    mock_get_session, mock_get_max_played_at, mock_get_recently_played,
    max_played_at_return=None,
    recently_played_return={"items": []},
    access_token="mock_access_token"
    ):

    if mock_get_spotify_credentials:
        mock_get_spotify_credentials.return_value = ("test_client_id", "test_client_secret", "test_refresh_token")

    if mock_spotify_oauth_client:
        mock_oauth_instance = mock_spotify_oauth_client.return_value
        mock_oauth_instance.get_access_token_from_refresh.return_value = access_token

    if mock_get_db_engine:
        mock_db_engine_instance = MagicMock()
        mock_get_db_engine.return_value = mock_db_engine_instance

    if mock_get_session:
        mock_session_instance = MagicMock()
        mock_session_instance.name = "mock_session_instance"
        mock_get_session.return_value = mock_session_instance

    if mock_get_max_played_at:
        mock_get_max_played_at.return_value = max_played_at_return

    if mock_get_recently_played:
        mock_get_recently_played.return_value = recently_played_return


@patch('backend.main.SpotifyItemNormalizer')
@patch('backend.main.get_session')
@patch('backend.main.get_max_played_at')
@patch('backend.main.upsert_artist')
@patch('backend.main.upsert_album')
@patch('backend.main.upsert_track')
@patch('backend.main.insert_listen')
@patch('backend.main.get_recently_played_tracks')
@patch('backend.main.SpotifyOAuthClient')
@patch('backend.main.get_spotify_credentials')
@patch('backend.main.get_db_engine')
def test_main_successful_run(
    mock_get_db_engine, mock_get_spotify_credentials, mock_spotify_oauth_client,
    mock_get_recently_played, mock_insert_listen, mock_upsert_track, mock_upsert_album,
    mock_upsert_artist, mock_get_max_played_at, mock_get_session, mock_normalizer_class
):
    now_dt = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    now_iso = now_dt.isoformat().replace('+00:00', 'Z')

    spotify_item_good = {
        "track": {
            "id": "track_id_1", "name": "Test Track 1", "type": "track",
            "artists": [{"id": "artist_id_1", "name": "Test Artist 1", "external_urls": {"spotify":"art_url"}}],
            "album": {"id": "album_id_1", "name": "Test Album 1", "images": [{"url": "img_url"}], "external_urls": {"spotify":"alb_url"}, "release_date":"2023-01-01", "release_date_precision":"day"},
        }, "played_at": now_iso
    }

    setup_happy_path_mocks(
        mock_get_db_engine, mock_get_spotify_credentials, mock_spotify_oauth_client,
        mock_get_session, mock_get_max_played_at, mock_get_recently_played,
        max_played_at_return=None,
        recently_played_return={"items": [spotify_item_good]}
    )

    mock_normalizer_instance = mock_normalizer_class.return_value
    mock_listen_obj = MagicMock(spec=Listen)
    mock_artist_obj = MagicMock(spec=Artist, artist_id="artist_id_1")
    mock_album_obj = MagicMock(spec=Album, album_id="album_id_1")
    mock_track_obj = MagicMock(spec=Track, track_id="track_id_1", name="Test Track 1")

    # Mock return value for normalize_item for a track
    mock_normalizer_instance.normalize_item.return_value = {
        'type': 'track',
        'artist': mock_artist_obj,
        'album': mock_album_obj,
        'track': mock_track_obj,
        'listen': mock_listen_obj
    }

    mock_upsert_artist.return_value = {"artist_id": "artist_id_1"}
    mock_upsert_album.return_value = {"album_id": "album_id_1"}
    mock_upsert_track.return_value = {"track_id": "track_id_1"}
    mock_insert_listen.return_value = mock_listen_obj

    from backend.main import process_spotify_data
    process_spotify_data()

    mock_get_spotify_credentials.assert_called_once()
    mock_spotify_oauth_client.assert_called_once_with("test_client_id", "test_client_secret", "test_refresh_token")
    mock_spotify_oauth_client.return_value.get_access_token_from_refresh.assert_called_once()

    mock_get_db_engine.assert_called_once()
    mock_get_session.assert_called_once_with(mock_get_db_engine.return_value)
    mock_get_max_played_at.assert_called_once_with(mock_get_session.return_value)

    expected_after_param = None
    mock_get_recently_played.assert_called_once_with("mock_access_token", limit=50, after=expected_after_param)

    mock_normalizer_class.assert_called_once()
    # normalize_item now takes only the item
    mock_normalizer_instance.normalize_item.assert_called_once_with(spotify_item_good)

    mock_upsert_artist.assert_called_once()
    mock_upsert_album.assert_called_once()
    mock_upsert_track.assert_called_once()
    mock_insert_listen.assert_called_once_with(mock_get_session.return_value, mock_listen_obj)

    mock_get_session.return_value.commit.assert_called_once()
    mock_get_session.return_value.close.assert_called_once()


@patch('backend.main.get_spotify_credentials', side_effect=ValueError("Simulated Config Error"))
def test_main_handles_config_value_error(mock_get_credentials_fails):
    from backend.main import process_spotify_data
    try:
        process_spotify_data()
    except Exception as e:
        pytest.fail(f"process_spotify_data() raised an unhandled exception on config error: {e}")
    mock_get_credentials_fails.assert_called_once()


@patch('backend.main.get_spotify_credentials')
@patch('backend.main.SpotifyOAuthClient')
def test_main_handles_spotify_auth_error(
    mock_spotify_oauth_client,
    mock_get_credentials
):
    mock_get_credentials.return_value = ("test_id", "test_secret", "test_refresh")
    mock_oauth_instance = mock_spotify_oauth_client.return_value
    mock_oauth_instance.get_access_token_from_refresh.side_effect = SpotifyAuthError("Simulated Auth Error")

    with patch('backend.main.get_db_engine', return_value=MagicMock()), \
         patch('backend.main.get_session', return_value=MagicMock()) as mock_session:
        from backend.main import process_spotify_data
        try:
            process_spotify_data()
        except Exception as e:
            pytest.fail(f"process_spotify_data() raised an unhandled exception on SpotifyAuthError: {e}")

        mock_get_credentials.assert_called_once()
        mock_spotify_oauth_client.assert_called_once()
        mock_oauth_instance.get_access_token_from_refresh.assert_called_once()
        if mock_session.called:
             mock_session.return_value.close.assert_called_once()


@patch('backend.main.get_db_engine')
@patch('backend.main.get_session')
@patch('backend.main.get_spotify_credentials')
@patch('backend.main.SpotifyOAuthClient')
@patch('backend.main.get_recently_played_tracks', side_effect=SpotifyAPIError("Simulated API Error"))
def test_main_handles_spotify_api_error(
    mock_get_recently_played,
    mock_spotify_oauth_client,
    mock_get_spotify_credentials,
    mock_get_session,
    mock_get_db_engine
):
    mock_get_spotify_credentials.return_value = ("test_id", "test_client_secret", "test_refresh_token")
    mock_oauth_instance = mock_spotify_oauth_client.return_value
    mock_oauth_instance.get_access_token_from_refresh.return_value = "mock_access_token"

    mock_db_engine_instance = MagicMock()
    mock_get_db_engine.return_value = mock_db_engine_instance
    mock_session_instance = MagicMock()
    mock_get_session.return_value = mock_session_instance

    with patch('backend.main.get_max_played_at', return_value=None):
        from backend.main import process_spotify_data
        try:
            process_spotify_data()
        except Exception as e:
            pytest.fail(f"process_spotify_data() raised an unhandled exception on SpotifyAPIError: {e}")

    mock_get_recently_played.assert_called_once()
    mock_get_session.return_value.rollback.assert_called_once()
    mock_get_session.return_value.close.assert_called_once()


@patch('backend.main.logger.error') # Changed from logging.error to logger.error
@patch('backend.main.get_db_engine', side_effect=Exception("Simulated DB Connection Error"))
@patch('backend.main.get_spotify_credentials') # Added this mock
def test_main_handles_db_engine_error(mock_get_spotify_credentials, mock_get_db_engine_fails, mock_logger_error): # Renamed mock_logging_error and added new mock
    mock_get_spotify_credentials.return_value = ("test_id", "test_secret", "test_refresh") # Mock successful credential retrieval
    from backend.main import process_spotify_data

    process_spotify_data() # No try-except block here in the test

    mock_get_db_engine_fails.assert_called_once()
    mock_logger_error.assert_called_once()
    # Optional: More specific check on what was logged
    args, kwargs = mock_logger_error.call_args
    # Example: Check if the log message contains part of the error and exc_info=True
    # This depends on the exact log message format in main.py
    # The first argument to logger.error is the message string.
    # In main.py, it's "Database error encountered." or "An unexpected error occurred..."
    # The actual exception is in exc_info=True or passed as a string in the message.
    # The check `assert "Simulated DB Connection Error" in str(args[0])` might fail if the message is generic.
    # The check `exc_info=True` is more robust for this case.
    # The actual message logged by main.py for a get_db_engine failure (which raises DatabaseError) is:
    # logger.error("Database error encountered.", exc_info=True)
    # If get_db_engine raises a generic Exception, it's:
    # logger.error("An unexpected error occurred during data processing.", exc_info=True)
    # Since we mock get_db_engine to raise Exception("Simulated DB Connection Error"),
    # it will be caught by the generic `except Exception as e:`
    assert "An unexpected error occurred" in args[0] # Check the generic message
    assert kwargs.get('exc_info') is True # Check that exc_info was passed


@patch('backend.main.SpotifyItemNormalizer')
@patch('backend.main.get_session')
@patch('backend.main.get_max_played_at')
@patch('backend.main.upsert_artist')
@patch('backend.main.upsert_album')
@patch('backend.main.upsert_track')
@patch('backend.main.insert_listen', side_effect=Exception("Simulated DB Insert Error"))
@patch('backend.main.get_recently_played_tracks')
@patch('backend.main.SpotifyOAuthClient')
@patch('backend.main.get_spotify_credentials')
@patch('backend.main.get_db_engine')
def test_main_handles_db_insert_error(
    mock_get_db_engine, mock_get_spotify_credentials, mock_spotify_oauth_client,
    mock_get_recently_played, mock_insert_listen_fails, mock_upsert_track,
    mock_upsert_album, mock_upsert_artist, mock_get_max_played_at,
    mock_get_session, mock_normalizer_class
):
    now_dt = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    now_iso = now_dt.isoformat().replace('+00:00', 'Z')
    spotify_item_good = {"track": {"id":"trk1", "type":"track", "name":"Test"}, "played_at": now_iso}

    setup_happy_path_mocks(
        mock_get_db_engine, mock_get_spotify_credentials, mock_spotify_oauth_client,
        mock_get_session, mock_get_max_played_at, mock_get_recently_played,
        max_played_at_return=None,
        recently_played_return={"items": [spotify_item_good]}
    )

    mock_normalizer_instance = mock_normalizer_class.return_value
    mock_listen_obj = MagicMock(spec=Listen)
    mock_artist_obj = MagicMock(spec=Artist, artist_id="some_id_artist")
    mock_album_obj = MagicMock(spec=Album, album_id="some_id_album")
    mock_track_obj = MagicMock(spec=Track, track_id="some_id_track", name="Test Track 1")

    # Mock return value for normalize_item for a track
    mock_normalizer_instance.normalize_item.return_value = {
        'type': 'track',
        'artist': mock_artist_obj,
        'album': mock_album_obj,
        'track': mock_track_obj,
        'listen': mock_listen_obj
    }
    mock_upsert_artist.return_value = {"artist_id": "some_id"}
    mock_upsert_album.return_value = {"album_id": "some_id"}
    mock_upsert_track.return_value = {"track_id": "some_id"}

    from backend.main import process_spotify_data
    try:
        process_spotify_data()
    except Exception as e:
        pytest.fail(f"process_spotify_data() raised an unhandled exception on DB insert error: {e}")

    mock_insert_listen_fails.assert_called_once()
    mock_get_session.return_value.rollback.assert_called_once()
    mock_get_session.return_value.close.assert_called_once()


@patch('backend.main.get_session')
@patch('backend.main.get_max_played_at')
@patch('backend.main.insert_listen')
@patch('backend.main.get_recently_played_tracks')
@patch('backend.main.SpotifyOAuthClient')
@patch('backend.main.get_spotify_credentials')
@patch('backend.main.get_db_engine')
def test_main_no_items_fetched(
    mock_get_db_engine, mock_get_spotify_credentials, mock_spotify_oauth_client,
    mock_get_recently_played, mock_insert_listen, mock_get_max_played_at,
    mock_get_session
):
    setup_happy_path_mocks(
        mock_get_db_engine, mock_get_spotify_credentials, mock_spotify_oauth_client,
        mock_get_session, mock_get_max_played_at, mock_get_recently_played,
        max_played_at_return=None,
        recently_played_return={"items": []}
    )

    from backend.main import process_spotify_data
    process_spotify_data()

    mock_get_recently_played.assert_called_once_with("mock_access_token", limit=50, after=None)
    mock_insert_listen.assert_not_called()
    mock_get_session.return_value.commit.assert_not_called()
    mock_get_session.return_value.close.assert_called_once()
