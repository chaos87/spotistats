import unittest
from unittest.mock import patch, MagicMock
import logging

# Suppress logging during tests to keep a clean test output
logging.disable(logging.CRITICAL)

class TestMainExecution(unittest.TestCase):

    @patch('backend.main.load_spotify_config')
    @patch('backend.main.SpotifyOAuthClient')
    def test_main_runs_successfully_with_mocks(self, MockSpotifyOAuthClient, mock_load_spotify_config):
        # Arrange
        # Mock config loading
        mock_load_spotify_config.return_value = ("test_id", "test_secret", "test_token")

        # Mock Spotify client behavior
        mock_spotify_instance = MockSpotifyOAuthClient.return_value
        mock_spotify_instance.get_access_token_from_refresh.return_value = "mocked_access_token"

        # Act & Assert: Ensure main() runs without throwing an unhandled exception
        try:
            # Import main function here to ensure mocks are applied before main is defined
            from backend.main import main
            main()
        except Exception as e:
            self.fail(f"main() raised an exception unexpectedly: {e}")

        # Assert that the config loader was called
        mock_load_spotify_config.assert_called_once()
        # Assert that the Spotify client was instantiated with the correct config
        MockSpotifyOAuthClient.assert_called_once_with(
            client_id="test_id",
            client_secret="test_secret",
            refresh_token="test_token"
        )
        # Assert that get_access_token_from_refresh was called
        mock_spotify_instance.get_access_token_from_refresh.assert_called_once()

    @patch('backend.main.load_spotify_config')
    def test_main_handles_config_value_error(self, mock_load_spotify_config):
        # Arrange
        mock_load_spotify_config.side_effect = ValueError("Missing SPOTIFY_CLIENT_ID")

        # Act & Assert
        # We expect a ValueError to be caught and logged, not to crash the program.
        try:
            # Import main function here
            from backend.main import main
            main()
        except Exception as e: # Should not raise an unhandled exception
            self.fail(f"main() raised an unhandled exception on config error: {e}")

        mock_load_spotify_config.assert_called_once()


    @patch('backend.main.load_spotify_config')
    @patch('backend.main.SpotifyOAuthClient')
    def test_main_handles_spotify_client_exception(self, MockSpotifyOAuthClient, mock_load_spotify_config):
        # Arrange
        mock_load_spotify_config.return_value = ("test_id", "test_secret", "test_token")
        mock_spotify_instance = MockSpotifyOAuthClient.return_value
        mock_spotify_instance.get_access_token_from_refresh.side_effect = Exception("Spotify API error")

        # Act & Assert
        try:
            # Import main function here
            from backend.main import main
            main()
        except Exception as e: # Should not raise an unhandled exception
            self.fail(f"main() raised an unhandled exception on Spotify client error: {e}")

        mock_load_spotify_config.assert_called_once()
        MockSpotifyOAuthClient.assert_called_once()
        mock_spotify_instance.get_access_token_from_refresh.assert_called_once()

if __name__ == '__main__':
    unittest.main()
