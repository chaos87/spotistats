import requests
import logging
import base64

logger = logging.getLogger(__name__)

class SpotifyOAuthClient:
    TOKEN_URL = "https://accounts.spotify.com/api/token"

    def __init__(self, client_id, client_secret, refresh_token=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token

    def get_access_token_from_refresh(self):
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }
        headers = self._get_auth_headers()

        response = requests.post(self.TOKEN_URL, data=payload, headers=headers)
        self._handle_response_error(response)

        data = response.json()
        if "access_token" not in data:
            logger.error("Access token not in response: %s", data)
            raise Exception("Access token not in response")
        return data["access_token"]

    def get_initial_refresh_token_manual_flow(self, auth_code, redirect_uri):
        payload = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": redirect_uri,
        }
        headers = self._get_auth_headers()

        response = requests.post(self.TOKEN_URL, data=payload, headers=headers)
        self._handle_response_error(response)

        data = response.json()
        if "access_token" not in data or "refresh_token" not in data:
            logger.error("Access token or refresh token not in response: %s", data)
            raise Exception("Access token or refresh token not in response")

        self.refresh_token = data["refresh_token"]
        return data["access_token"], data["refresh_token"]

    def _get_auth_headers(self):
        auth_str = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_str.encode("utf-8")
        auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")
        return {"Authorization": f"Basic {auth_base64}"}

    def _handle_response_error(self, response):
        if response.status_code != 200:
            logger.error(
                "Error getting token: %s - %s",
                response.status_code,
                response.text,
            )
            response.raise_for_status()
