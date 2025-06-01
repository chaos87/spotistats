import pytest
from unittest.mock import patch
import os

# Ensure imports are correct for the project structure
# Assuming tests are run from the 'backend' directory or PYTHONPATH is set
from backend.src.config import get_env_variable

@pytest.fixture(autouse=True)
def manage_env_vars():
    """Fixture to save and restore environment variables for each test."""
    original_environ = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_environ)

def test_get_env_variable_success():
    """Test successful retrieval of an environment variable."""
    test_key = "TEST_VAR"
    test_value = "test_value"
    with patch.dict(os.environ, {test_key: test_value}, clear=True):
        assert get_env_variable(test_key) == test_value

def test_get_env_variable_missing_no_default():
    """Test that ValueError is raised for a missing variable with no default."""
    test_key = "MISSING_TEST_VAR"
    # Ensure the variable is not in the environment for this test
    if test_key in os.environ:
        del os.environ[test_key]

    with pytest.raises(ValueError, match=f"Environment variable '{test_key}' not found."):
        get_env_variable(test_key)

def test_get_env_variable_missing_with_default():
    """Test retrieval of a default value when a variable is missing."""
    test_key = "MISSING_TEST_VAR_WITH_DEFAULT"
    default_val = "default_value"
    # Ensure the variable is not in the environment for this test
    if test_key in os.environ:
        del os.environ[test_key]

    assert get_env_variable(test_key, default_value=default_val) == default_val

def test_get_env_variable_empty_string_value():
    """Test retrieval of an environment variable that is an empty string."""
    test_key = "EMPTY_TEST_VAR"
    test_value = ""
    with patch.dict(os.environ, {test_key: test_value}, clear=True):
        assert get_env_variable(test_key) == test_value

def test_get_spotify_credentials_loaded():
    """Test that Spotify specific credentials can be loaded."""
    spotify_vars = {
        "SPOTIFY_CLIENT_ID": "spotify_client_id_123",
        "SPOTIFY_CLIENT_SECRET": "spotify_client_secret_xyz",
        "SPOTIFY_REFRESH_TOKEN": "spotify_refresh_token_abc"
    }
    with patch.dict(os.environ, spotify_vars, clear=True):
        assert get_env_variable("SPOTIFY_CLIENT_ID") == spotify_vars["SPOTIFY_CLIENT_ID"]
        assert get_env_variable("SPOTIFY_CLIENT_SECRET") == spotify_vars["SPOTIFY_CLIENT_SECRET"]
        assert get_env_variable("SPOTIFY_REFRESH_TOKEN") == spotify_vars["SPOTIFY_REFRESH_TOKEN"]

def test_get_database_url_loaded():
    """Test that DATABASE_URL can be loaded."""
    db_url = "postgresql://user:pass@host:port/db"
    with patch.dict(os.environ, {"DATABASE_URL": db_url}, clear=True):
        assert get_env_variable("DATABASE_URL") == db_url

@patch('dotenv.load_dotenv') # Mock load_dotenv where it's originally from
def test_dotenv_loading_is_attempted(mock_load_dotenv):
    """
    Test that load_dotenv is called when config.py is imported/reloaded.
    This doesn't test get_env_variable directly but the setup in config.py.
    Requires re-importing config or a more complex setup to test properly.
    For simplicity, we assume load_dotenv in config.py works if called.
    This test primarily ensures that our mocking of load_dotenv in other tests
    for get_env_variable doesn't hide the fact that config.py *tries* to load .env.
    """
    # config.py is imported at the top of this test file.
    # load_dotenv in config.py should have been called upon initial import.
    # However, Pytest's collection and execution model might make this tricky.
    # A more robust way would be to unload and reload the module, or test
    # the side effect of load_dotenv (e.g., os.environ being populated from a dummy .env).

    # For now, we'll rely on the fact that load_dotenv is called at the module level
    # in config.py. A simple check is that the mock was called.
    # If config.py was imported before this test runs (likely), load_dotenv was already called.
    # To make it explicit for this test:
    import importlib
    from backend.src import config # Assuming config.py is in backend/src

    # Patch os.path.exists to ensure the condition for calling load_dotenv is met
    # And then reload the config module to trigger its top-level code
    with patch('os.path.exists', return_value=True):
        importlib.reload(config)

    mock_load_dotenv.assert_called() # load_dotenv in config.py should be called

# Note: The original test_config.py used unittest.
# This version uses pytest style for consistency with other new tests like test_database.py.
# Pytest can run unittest-style tests too, but pytest style is generally more concise.
