import unittest
from unittest.mock import patch, MagicMock
from backend.src.spotify_client import SpotifyOAuthClient

class TestSpotifyOAuthClient(unittest.TestCase):
    def setUp(self):
        self.client_id = "test_client_id"
        self.client_secret = "test_client_secret"
        self.refresh_token = "test_refresh_token"
        self.client = SpotifyOAuthClient(
            self.client_id, self.client_secret, self.refresh_token
        )

    @patch("requests.post")
    def test_get_access_token_from_refresh_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "new_access_token"}
        mock_post.return_value = mock_response

        access_token = self.client.get_access_token_from_refresh()

        self.assertEqual(access_token, "new_access_token")
        mock_post.assert_called_once_with(
            SpotifyOAuthClient.TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
            headers=self.client._get_auth_headers(),
        )

    @patch("requests.post")
    def test_get_access_token_from_refresh_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        with self.assertRaises(Exception):
            self.client.get_access_token_from_refresh()

    @patch("requests.post")
    def test_get_initial_refresh_token_manual_flow_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "initial_access_token",
            "refresh_token": "initial_refresh_token",
        }
        mock_post.return_value = mock_response

        auth_code = "test_auth_code"
        redirect_uri = "http://localhost/callback"
        access_token, refresh_token = (
            self.client.get_initial_refresh_token_manual_flow(
                auth_code, redirect_uri
            )
        )

        self.assertEqual(access_token, "initial_access_token")
        self.assertEqual(refresh_token, "initial_refresh_token")
        self.assertEqual(self.client.refresh_token, "initial_refresh_token")
        mock_post.assert_called_once_with(
            SpotifyOAuthClient.TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": redirect_uri,
            },
            headers=self.client._get_auth_headers(),
        )

    @patch("requests.post")
    def test_get_initial_refresh_token_manual_flow_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        with self.assertRaises(Exception):
            self.client.get_initial_refresh_token_manual_flow(
                "test_auth_code", "http://localhost/callback"
            )

if __name__ == "__main__":
    unittest.main()
