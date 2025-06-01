import pytest
from unittest.mock import patch, MagicMock
import logging

# Import errors that main.py specifically catches
from backend.src.spotify_client import SpotifyAuthError
from backend.src.spotify_data import SpotifyAPIError
# Import main function last to ensure mocks can be applied if necessary before it's defined
# from backend.main import main # Will be imported within test functions after mocks are set up

# Suppress all logging output during these tests to keep test results clean
@pytest.fixture(autouse=True)
def disable_logging():
    logging.disable(logging.CRITICAL + 1) # Disable all logging levels
    yield
    logging.disable(logging.NOTSET) # Re-enable logging after test

@pytest.fixture
def env_vars_dict():
    """Provides a dictionary of environment variables for tests."""
    return {
        "SPOTIFY_CLIENT_ID": "test_client_id",
        "SPOTIFY_CLIENT_SECRET": "test_client_secret",
        "SPOTIFY_REFRESH_TOKEN": "test_refresh_token",
        "DATABASE_URL": "postgresql://test_user:test_pass@test_host:5432/test_db"
    }

# Patch targets are now where the objects are defined, as main.py imports them from there.
@patch('backend.src.database.create_tables')
@patch('backend.src.database.insert_raw_data')
@patch('backend.src.database.get_db_engine')
@patch('backend.src.spotify_data.get_recently_played_tracks')
@patch('backend.src.spotify_client.SpotifyOAuthClient')
@patch('backend.src.config.get_env_variable')
def test_main_successful_run(
    mock_config_get_env_variable,
    mock_spotify_client_SpotifyOAuthClient,
    mock_spotify_data_get_recently_played_tracks,
    mock_database_get_db_engine,
    mock_database_insert_raw_data,
    mock_database_create_tables,
    env_vars_dict
):
    """Test a successful execution path of main()."""
    # Arrange
    mock_config_get_env_variable.side_effect = lambda var_name: env_vars_dict.get(var_name)
    mock_oauth_instance = mock_spotify_client_SpotifyOAuthClient.return_value
    mock_oauth_instance.get_access_token_from_refresh.return_value = "mock_access_token"

    mock_db_engine_instance = MagicMock()
    mock_database_get_db_engine.return_value = mock_db_engine_instance

    mock_spotify_data = {"items": [{"id": "123", "name": "Test Song"}]}
    mock_spotify_data_get_recently_played_tracks.return_value = mock_spotify_data

    import importlib
    from backend import main as main_module
    importlib.reload(main_module)
    main_module.main()

    # Assert
    mock_config_get_env_variable.assert_any_call("SPOTIFY_CLIENT_ID")
    mock_config_get_env_variable.assert_any_call("SPOTIFY_CLIENT_SECRET")
    mock_config_get_env_variable.assert_any_call("SPOTIFY_REFRESH_TOKEN")

    mock_spotify_client_SpotifyOAuthClient.assert_called_once_with("test_client_id", "test_client_secret", "test_refresh_token")
    mock_oauth_instance.get_access_token_from_refresh.assert_called_once()

    mock_database_get_db_engine.assert_called_once()
    # mock_database_create_tables.assert_called_once_with(mock_db_engine_instance) # If create_tables is active in main.py

    mock_spotify_data_get_recently_played_tracks.assert_called_once_with("mock_access_token", limit=50)
    mock_database_insert_raw_data.assert_called_once_with(mock_db_engine_instance, mock_spotify_data)


@patch('backend.src.config.get_env_variable', side_effect=ValueError("Missing SPOTIFY_CLIENT_ID"))
def test_main_handles_config_value_error(mock_config_get_env_variable_fails): # Mock name updated
    """Test main() handles ValueError from get_env_variable (config error)."""
    import importlib
    from backend import main as main_module
    importlib.reload(main_module)

    try:
        main_module.main()
    except Exception as e:
        pytest.fail(f"main() raised an unhandled exception on config error: {e}")
    mock_config_get_env_variable_fails.assert_any_call("SPOTIFY_CLIENT_ID")


@patch('backend.src.config.get_env_variable')
@patch('backend.src.spotify_client.SpotifyOAuthClient') # Patched where defined
def test_main_handles_spotify_auth_error(
    mock_spotify_client_SpotifyOAuthClient,
    mock_config_get_env_variable,
    env_vars_dict
):
    """Test main() handles SpotifyAuthError from SpotifyOAuthClient."""
    mock_config_get_env_variable.side_effect = lambda var_name: env_vars_dict.get(var_name)
    mock_oauth_instance = mock_spotify_client_SpotifyOAuthClient.return_value
    mock_oauth_instance.get_access_token_from_refresh.side_effect = SpotifyAuthError("Test Auth Error")

    import importlib
    from backend import main as main_module
    importlib.reload(main_module)
    try:
        main_module.main()
    except Exception as e:
        pytest.fail(f"main() raised an unhandled exception on SpotifyAuthError: {e}")

    mock_spotify_client_SpotifyOAuthClient.assert_called_once()
    mock_oauth_instance.get_access_token_from_refresh.assert_called_once()


@patch('backend.src.config.get_env_variable')
@patch('backend.src.spotify_client.SpotifyOAuthClient')
@patch('backend.src.spotify_data.get_recently_played_tracks', side_effect=SpotifyAPIError("Test API Error"))
@patch('backend.src.database.get_db_engine')
def test_main_handles_spotify_api_error(
    mock_database_get_db_engine,
    mock_spotify_data_get_recently_played_tracks,
    mock_spotify_client_SpotifyOAuthClient,
    mock_config_get_env_variable,
    env_vars_dict
):
    """Test main() handles SpotifyAPIError from get_recently_played_tracks."""
    mock_config_get_env_variable.side_effect = lambda var_name: env_vars_dict.get(var_name)
    mock_oauth_instance = mock_spotify_client_SpotifyOAuthClient.return_value
    mock_oauth_instance.get_access_token_from_refresh.return_value = "mock_access_token"

    import importlib
    from backend import main as main_module
    importlib.reload(main_module)
    try:
        main_module.main()
    except Exception as e:
        pytest.fail(f"main() raised an unhandled exception on SpotifyAPIError: {e}")

    mock_spotify_data_get_recently_played_tracks.assert_called_once()


@patch('backend.src.config.get_env_variable')
@patch('backend.src.spotify_client.SpotifyOAuthClient')
@patch('backend.src.spotify_data.get_recently_played_tracks')
@patch('backend.src.database.get_db_engine', side_effect=Exception("Test DB Connection Error"))
def test_main_handles_db_engine_error(
    mock_database_get_db_engine,
    mock_spotify_data_get_recently_played_tracks,
    mock_spotify_client_SpotifyOAuthClient,
    mock_config_get_env_variable,
    env_vars_dict
):
    """Test main() handles errors during database engine initialization."""
    mock_config_get_env_variable.side_effect = lambda var_name: env_vars_dict.get(var_name)
    mock_oauth_instance = mock_spotify_client_SpotifyOAuthClient.return_value
    mock_oauth_instance.get_access_token_from_refresh.return_value = "mock_access_token"

    import importlib
    from backend import main as main_module
    importlib.reload(main_module)
    try:
        main_module.main()
    except Exception as e:
        pytest.fail(f"main() raised an unhandled exception on DB engine error: {e}")

    mock_database_get_db_engine.assert_called_once()


@patch('backend.src.config.get_env_variable')
@patch('backend.src.spotify_client.SpotifyOAuthClient')
@patch('backend.src.spotify_data.get_recently_played_tracks')
@patch('backend.src.database.get_db_engine')
@patch('backend.src.database.insert_raw_data', side_effect=Exception("Test DB Insert Error"))
def test_main_handles_db_insert_error(
    mock_database_insert_raw_data,
    mock_database_get_db_engine,
    mock_spotify_data_get_recently_played_tracks,
    mock_spotify_client_SpotifyOAuthClient,
    mock_config_get_env_variable,
    env_vars_dict
):
    """Test main() handles errors during database insertion."""
    mock_config_get_env_variable.side_effect = lambda var_name: env_vars_dict.get(var_name)
    mock_oauth_instance = mock_spotify_client_SpotifyOAuthClient.return_value
    mock_oauth_instance.get_access_token_from_refresh.return_value = "mock_access_token"

    mock_db_engine_instance = MagicMock()
    mock_database_get_db_engine.return_value = mock_db_engine_instance

    mock_spotify_data = {"items": [{"id": "123", "name": "Test Song"}]}
    mock_spotify_data_get_recently_played_tracks.return_value = mock_spotify_data

    import importlib
    from backend import main as main_module
    importlib.reload(main_module)
    try:
        main_module.main()
    except Exception as e:
        pytest.fail(f"main() raised an unhandled exception on DB insert error: {e}")

    mock_database_insert_raw_data.assert_called_once_with(mock_db_engine_instance, mock_spotify_data)

@patch('backend.src.config.get_env_variable')
@patch('backend.src.spotify_client.SpotifyOAuthClient')
@patch('backend.src.spotify_data.get_recently_played_tracks')
@patch('backend.src.database.get_db_engine')
@patch('backend.src.database.insert_raw_data')
def test_main_no_items_fetched(
    mock_database_insert_raw_data,
    mock_database_get_db_engine,
    mock_spotify_data_get_recently_played_tracks,
    mock_spotify_client_SpotifyOAuthClient,
    mock_config_get_env_variable,
    env_vars_dict
):
    """Test main() when no items are fetched from Spotify (should exit gracefully)."""
    mock_config_get_env_variable.side_effect = lambda var_name: env_vars_dict.get(var_name)
    mock_oauth_instance = mock_spotify_client_SpotifyOAuthClient.return_value
    mock_oauth_instance.get_access_token_from_refresh.return_value = "mock_access_token"

    mock_db_engine_instance = MagicMock()
    mock_database_get_db_engine.return_value = mock_db_engine_instance

    # Simulate Spotify returning no items
    mock_spotify_data_get_recently_played_tracks.return_value = {"items": []}

    import importlib
    from backend import main as main_module
    importlib.reload(main_module)
    main_module.main() # Should run without error and not call insert_raw_data

    mock_spotify_data_get_recently_played_tracks.assert_called_once_with("mock_access_token", limit=50)
    mock_database_insert_raw_data.assert_not_called() # Crucial check
