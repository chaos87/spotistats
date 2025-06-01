import unittest
from unittest.mock import patch
from backend.src.config import load_spotify_config
import os

class TestConfig(unittest.TestCase):

    @patch.dict(os.environ, {
        "SPOTIFY_CLIENT_ID": "test_id",
        "SPOTIFY_CLIENT_SECRET": "test_secret",
        "SPOTIFY_REFRESH_TOKEN": "test_token"
    })
    def test_load_spotify_config_success(self):
        client_id, client_secret, refresh_token = load_spotify_config()
        self.assertEqual(client_id, "test_id")
        self.assertEqual(client_secret, "test_secret")
        self.assertEqual(refresh_token, "test_token")

    @patch.dict(os.environ, {}, clear=True)
    def test_load_spotify_config_missing_all(self):
        with self.assertRaises(ValueError) as context:
            load_spotify_config()
        self.assertIn("SPOTIFY_CLIENT_ID", str(context.exception))
        self.assertIn("SPOTIFY_CLIENT_SECRET", str(context.exception))
        self.assertIn("SPOTIFY_REFRESH_TOKEN", str(context.exception))

    @patch.dict(os.environ, {"SPOTIFY_CLIENT_SECRET": "test_secret", "SPOTIFY_REFRESH_TOKEN": "test_token"}, clear=True)
    def test_load_spotify_config_missing_client_id(self):
        with self.assertRaises(ValueError) as context:
            load_spotify_config()
        self.assertIn("SPOTIFY_CLIENT_ID", str(context.exception))
        self.assertNotIn("SPOTIFY_CLIENT_SECRET", str(context.exception))
        self.assertNotIn("SPOTIFY_REFRESH_TOKEN", str(context.exception))

    @patch.dict(os.environ, {"SPOTIFY_CLIENT_ID": "test_id", "SPOTIFY_REFRESH_TOKEN": "test_token"}, clear=True)
    def test_load_spotify_config_missing_client_secret(self):
        with self.assertRaises(ValueError) as context:
            load_spotify_config()
        self.assertNotIn("SPOTIFY_CLIENT_ID", str(context.exception))
        self.assertIn("SPOTIFY_CLIENT_SECRET", str(context.exception))
        self.assertNotIn("SPOTIFY_REFRESH_TOKEN", str(context.exception))

    @patch.dict(os.environ, {"SPOTIFY_CLIENT_ID": "test_id", "SPOTIFY_CLIENT_SECRET": "test_secret"}, clear=True)
    def test_load_spotify_config_missing_refresh_token(self):
        with self.assertRaises(ValueError) as context:
            load_spotify_config()
        self.assertNotIn("SPOTIFY_CLIENT_ID", str(context.exception))
        self.assertNotIn("SPOTIFY_CLIENT_SECRET", str(context.exception))
        self.assertIn("SPOTIFY_REFRESH_TOKEN", str(context.exception))

    @patch('backend.src.config.load_dotenv') # Mock load_dotenv to avoid looking for a .env file
    @patch.dict(os.environ, {
        "SPOTIFY_CLIENT_ID": "env_id",
        "SPOTIFY_CLIENT_SECRET": "env_secret",
        "SPOTIFY_REFRESH_TOKEN": "env_token"
    })
    def test_load_spotify_config_prioritizes_env_vars_over_dotenv(self, mock_load_dotenv):
        # Create a dummy .env file that would be loaded by load_dotenv if not for the mock
        # This test ensures that even if .env file has different values, actual env vars take precedence.
        with patch('builtins.open', unittest.mock.mock_open(read_data='SPOTIFY_CLIENT_ID="dotenv_id"\nSPOTIFY_CLIENT_SECRET="dotenv_secret"\nSPOTIFY_REFRESH_TOKEN="dotenv_token"')):
            client_id, client_secret, refresh_token = load_spotify_config()
            self.assertEqual(client_id, "env_id")
            self.assertEqual(client_secret, "env_secret")
            self.assertEqual(refresh_token, "env_token")
            mock_load_dotenv.assert_called_once()


if __name__ == "__main__":
    unittest.main()
