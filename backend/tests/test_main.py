import pytest
from unittest.mock import patch, MagicMock
import logging

# Import errors that main.py specifically catches
from backend.src.spotify_client import SpotifyAuthError
from backend.src.spotify_data import SpotifyAPIError
# Import main function last to ensure mocks can be applied if necessary before it's defined
# from backend.main import process_spotify_data will be imported after mocks for some tests

# Suppress all logging output during these tests to keep test results clean
@pytest.fixture(autouse=True)
def disable_logging():
    logging.disable(logging.CRITICAL + 1) # Disable all logging levels
    yield
    logging.disable(logging.NOTSET) # Re-enable logging after test

@pytest.fixture
def env_vars_dict():
    """Provides a dictionary of environment variables for tests.
       Note: These are less relevant now as process_spotify_data uses placeholder functions
       for credentials internally, but kept for structure if tests evolve.
    """
    return {
        "SPOTIFY_CLIENT_ID": "test_client_id",
        "SPOTIFY_CLIENT_SECRET": "test_client_secret",
        "SPOTIFY_REFRESH_TOKEN": "test_refresh_token",
        "DATABASE_URL": "postgresql://test_user:test_pass@test_host:5432/test_db"
    }

# Patch targets are now for dependencies of process_spotify_data as defined/imported in main.py
# Assuming main.py has its own placeholder get_spotify_credentials, SpotifyOAuthClient, get_recently_played_tracks
# And imports database functions like get_db_engine, get_max_played_at, upsert_*, insert_listen
@patch('backend.main.get_session') # process_spotify_data gets session from get_session
@patch('backend.main.get_max_played_at')
@patch('backend.main.upsert_artist')
@patch('backend.main.upsert_album')
@patch('backend.main.upsert_track')
@patch('backend.main.insert_listen')
@patch('backend.main.get_recently_played_tracks')
@patch('backend.main.SpotifyOAuthClient') # Patches the placeholder in main.py
@patch('backend.main.get_spotify_credentials') # Patches the placeholder in main.py
@patch('backend.main.get_db_engine') # Patches from where process_spotify_data imports it
def test_main_successful_run(
    mock_get_db_engine, # Corresponds to backend.main.get_db_engine
    mock_get_spotify_credentials, # Corresponds to backend.main.get_spotify_credentials
    mock_spotify_oauth_client, # Corresponds to backend.main.SpotifyOAuthClient
    mock_get_recently_played,
    mock_insert_listen,
    mock_upsert_track,
    mock_upsert_album,
    mock_upsert_artist,
    mock_get_max_played_at,
    mock_get_session # Corresponds to backend.main.get_session
):
    """Test a successful execution path of process_spotify_data()."""
    # Arrange
    # Mock for get_spotify_credentials placeholder
    mock_get_spotify_credentials.return_value = ("test_client_id", "test_client_secret", "test_refresh_token")

    # Mock for SpotifyOAuthClient placeholder
    mock_oauth_instance = mock_spotify_oauth_client.return_value
    mock_oauth_instance.get_access_token_from_refresh.return_value = "mock_access_token"

    # Mock for get_db_engine
    mock_db_engine_instance = MagicMock()
    mock_get_db_engine.return_value = mock_db_engine_instance

    # Mock for get_session
    mock_session_instance = MagicMock()
    mock_get_session.return_value = mock_session_instance

    # Mock for get_max_played_at
    mock_get_max_played_at.return_value = None # Simulate no previous listens

    # Mock for get_recently_played_tracks placeholder
    # Example: one valid track item, newer than max_played_at (which is None)
    # Datetime must be timezone aware for fromisoformat
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
    mock_spotify_data = {"items": [{
        "track": {
            "id": "track_id_1", "name": "Test Track 1", "type": "track",
            "artists": [{"id": "artist_id_1", "name": "Test Artist 1", "external_urls": {"spotify":"art_url"}}],
            "album": {"id": "album_id_1", "name": "Test Album 1", "images": [{"url": "img_url"}], "external_urls": {"spotify":"alb_url"}, "release_date":"2023-01-01", "release_date_precision":"day"},
            "duration_ms": 180000, "explicit": False, "popularity": 50, "external_urls": {"spotify":"track_url"}
        },
        "played_at": now_iso
    }]}
    mock_get_recently_played.return_value = mock_spotify_data

    # Mocks for DB operations (upsert/insert)
    mock_upsert_artist.return_value = {"artist_id": "artist_id_1"}
    mock_upsert_album.return_value = {"album_id": "album_id_1"}
    mock_upsert_track.return_value = {"track_id": "track_id_1"}
    mock_insert_listen.return_value = MagicMock() # Simulate successful listen insertion

    # Dynamically import the main module to use the patched versions
    import importlib
    from backend import main as main_module
    importlib.reload(main_module) # Reload to apply mocks if main was imported before

    main_module.process_spotify_data()

    # Assert
    mock_get_spotify_credentials.assert_called_once()
    mock_spotify_oauth_client.assert_called_once_with("test_client_id", "test_client_secret", "test_refresh_token")
    mock_oauth_instance.get_access_token_from_refresh.assert_called_once()

    mock_get_db_engine.assert_called_once()
    mock_get_session.assert_called_once_with(mock_db_engine_instance)
    mock_get_max_played_at.assert_called_once_with(mock_session_instance)

    # after_param for get_recently_played_tracks should be None since max_played_at is None
    mock_get_recently_played.assert_called_once_with("mock_access_token", limit=50, after=None)

    # Check if DB operations were called (assuming one valid item processed)
    mock_upsert_artist.assert_called_once()
    mock_upsert_album.assert_called_once()
    mock_upsert_track.assert_called_once()
    mock_insert_listen.assert_called_once()

    mock_session_instance.commit.assert_called_once() # Check for commit
    mock_session_instance.close.assert_called_once() # Check for session close


# This test needs to be re-evaluated based on how process_spotify_data handles config errors.
# If get_spotify_credentials (placeholder in main.py) raises an error, that's what we'd catch.
@patch('backend.main.get_spotify_credentials', side_effect=ValueError("Missing SPOTIFY_CLIENT_ID"))
def test_main_handles_config_value_error(mock_get_credentials_fails):
    """Test process_spotify_data() handles ValueError from get_spotify_credentials."""
    import importlib
    from backend import main as main_module
    importlib.reload(main_module)

    try:
        main_module.process_spotify_data()
    except Exception as e:
        pytest.fail(f"process_spotify_data() raised an unhandled exception on config error: {e}")
    mock_get_credentials_fails.assert_called_once()


@patch('backend.main.get_spotify_credentials')
@patch('backend.main.SpotifyOAuthClient')
def test_main_handles_spotify_auth_error(
    mock_spotify_oauth_client,
    mock_get_credentials
):
    """Test process_spotify_data() handles SpotifyAuthError."""
    mock_get_credentials.return_value = ("test_id", "test_secret", "test_refresh")
    mock_oauth_instance = mock_spotify_oauth_client.return_value
    mock_oauth_instance.get_access_token_from_refresh.side_effect = SpotifyAuthError("Test Auth Error")

    import importlib
    from backend import main as main_module
    importlib.reload(main_module)
    try:
        main_module.process_spotify_data()
    except Exception as e:
        pytest.fail(f"process_spotify_data() raised an unhandled exception on SpotifyAuthError: {e}")

    mock_spotify_oauth_client.assert_called_once()
    mock_oauth_instance.get_access_token_from_refresh.assert_called_once()


@patch('backend.main.get_spotify_credentials')
@patch('backend.main.SpotifyOAuthClient')
@patch('backend.main.get_recently_played_tracks', side_effect=SpotifyAPIError("Test API Error"))
@patch('backend.main.get_db_engine') # For get_session call
@patch('backend.main.get_session')   # To provide a session for finally block
def test_main_handles_spotify_api_error(
    mock_get_session, # Added
    mock_get_db_engine, # Added
    mock_get_recently_played,
    mock_spotify_oauth_client,
    mock_get_credentials
):
    """Test process_spotify_data() handles SpotifyAPIError."""
    mock_get_credentials.return_value = ("test_id", "test_secret", "test_refresh")
    mock_oauth_instance = mock_spotify_oauth_client.return_value
    mock_oauth_instance.get_access_token_from_refresh.return_value = "mock_access_token"

    # Mock get_db_engine and get_session for the try/finally block
    mock_db_engine_instance = MagicMock()
    mock_get_db_engine.return_value = mock_db_engine_instance
    mock_session_instance = MagicMock()
    mock_get_session.return_value = mock_session_instance


    import importlib
    from backend import main as main_module
    importlib.reload(main_module)
    try:
        main_module.process_spotify_data()
    except Exception as e:
        pytest.fail(f"process_spotify_data() raised an unhandled exception on SpotifyAPIError: {e}")

    mock_get_recently_played.assert_called_once()
    mock_session_instance.rollback.assert_called_once() # Should rollback on error
    mock_session_instance.close.assert_called_once()


@patch('backend.main.get_db_engine', side_effect=Exception("Test DB Connection Error"))
def test_main_handles_db_engine_error(
    mock_get_db_engine
):
    """Test process_spotify_data() handles errors during DB engine init (via get_session)."""
    # Credentials and Spotify client mocks are not strictly needed if error is at get_db_engine
    import importlib
    from backend import main as main_module
    importlib.reload(main_module)
    try:
        main_module.process_spotify_data()
    except Exception as e:
        pytest.fail(f"process_spotify_data() raised an unhandled exception on DB engine error: {e}")

    # process_spotify_data calls get_db_engine via get_session.
    # If get_db_engine itself is patched to error, this should be hit.
    mock_get_db_engine.assert_called_once()

# This test needs significant rework as process_spotify_data has more complex DB interaction
# For instance, it calls multiple db functions (get_max_played_at, upserts, insert_listen)
# Patching just one (like insert_listen) might not fully test error handling for all DB errors.
@patch('backend.main.get_spotify_credentials')
@patch('backend.main.SpotifyOAuthClient')
@patch('backend.main.get_recently_played_tracks')
@patch('backend.main.get_db_engine')
@patch('backend.main.get_session')
@patch('backend.main.get_max_played_at') # Add this
@patch('backend.main.insert_listen', side_effect=Exception("Test DB Insert Error")) # Example: error on insert_listen
def test_main_handles_db_insert_error(
    mock_insert_listen_fails,
    mock_get_max_played_at, # Add this
    mock_get_session,
    mock_get_db_engine,
    mock_get_recently_played,
    mock_spotify_oauth_client,
    mock_get_credentials
):
    """Test process_spotify_data() handles errors during a database operation like insert_listen."""
    mock_get_credentials.return_value = ("test_id", "test_secret", "test_refresh")
    mock_oauth_instance = mock_spotify_oauth_client.return_value
    mock_oauth_instance.get_access_token_from_refresh.return_value = "mock_access_token"

    mock_db_engine_instance = MagicMock()
    mock_get_db_engine.return_value = mock_db_engine_instance
    mock_session_instance = MagicMock()
    mock_get_session.return_value = mock_session_instance

    mock_get_max_played_at.return_value = None # Simulate no previous listens

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
    mock_spotify_data = {"items": [{"track": {"id":"trk1", "type":"track", "name":"Test"}, "played_at": now_iso}]} # Simplified
    mock_get_recently_played.return_value = mock_spotify_data

    # Mock normalizer to return something, so flow reaches insert_listen
    with patch('backend.main.SpotifyMusicNormalizer') as mock_normalizer_class:
        mock_norm_instance = MagicMock()
        # Simulate successful normalization returning mock model instances
        mock_norm_instance.normalize_track_item.return_value = (MagicMock(), MagicMock(), MagicMock(), MagicMock())
        mock_normalizer_class.return_value = mock_norm_instance

        # Mock upserts to not fail before insert_listen
        with patch('backend.main.upsert_artist', return_value=MagicMock()), \
             patch('backend.main.upsert_album', return_value=MagicMock()), \
             patch('backend.main.upsert_track', return_value=MagicMock()):

            import importlib
            from backend import main as main_module
            importlib.reload(main_module)
            try:
                main_module.process_spotify_data()
            except Exception as e:
                pytest.fail(f"process_spotify_data() raised an unhandled exception on DB insert error: {e}")

    mock_insert_listen_fails.assert_called_once()
    mock_session_instance.rollback.assert_called_once()
    mock_session_instance.close.assert_called_once()


@patch('backend.main.get_spotify_credentials')
@patch('backend.main.SpotifyOAuthClient')
@patch('backend.main.get_recently_played_tracks')
@patch('backend.main.get_db_engine') # For get_session call
@patch('backend.main.get_session')   # To provide a session for finally block
@patch('backend.main.insert_listen') # To check it's not called
@patch('backend.main.get_max_played_at')
def test_main_no_items_fetched(
    mock_get_max_played_at, # Added
    mock_insert_listen, # Added
    mock_get_session, # Added
    mock_get_db_engine, # Added
    mock_get_recently_played,
    mock_spotify_oauth_client,
    mock_get_credentials
):
    """Test process_spotify_data() when no items are fetched (should exit gracefully)."""
    mock_get_credentials.return_value = ("test_id", "test_secret", "test_refresh")
    mock_oauth_instance = mock_spotify_oauth_client.return_value
    mock_oauth_instance.get_access_token_from_refresh.return_value = "mock_access_token"

    mock_db_engine_instance = MagicMock()
    mock_get_db_engine.return_value = mock_db_engine_instance
    mock_session_instance = MagicMock() # Mock session for the finally block
    mock_get_session.return_value = mock_session_instance

    mock_get_max_played_at.return_value = None # No previous history

    mock_get_recently_played.return_value = {"items": []} # Simulate Spotify returning no items

    import importlib
    import datetime # Required for isoformat if not already imported at top
    from backend import main as main_module
    importlib.reload(main_module)

    main_module.process_spotify_data()

    mock_get_recently_played.assert_called_once_with("mock_access_token", limit=50, after=None)
    mock_insert_listen.assert_not_called()
    # Should not commit if no items processed, but will call close
    mock_session_instance.commit.assert_not_called()
    mock_session_instance.close.assert_called_once()

[Error creating import for 'datetime': cannot import name 'datetime' from 'backend.main']
