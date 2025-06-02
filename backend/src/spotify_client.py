import requests
import logging
import base64
from .exceptions import SpotifyAuthError, SpotifyAPIError # Import from exceptions.py
from .utils import api_retry_decorator # Import the decorator

# class SpotifyAuthError(Exception): # Moved to exceptions.py
#     """Custom exception for Spotify authentication errors."""
#     pass

# class SpotifyAPIError(Exception): # Moved to exceptions.py
#     """Custom exception for Spotify API errors (non-auth related)."""
#     pass

logger = logging.getLogger(__name__)

class SpotifyOAuthClient:
    TOKEN_URL = "https://accounts.spotify.com/api/token"

    def __init__(self, client_id, client_secret, refresh_token=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token

    @api_retry_decorator
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
            logger.error("Access token not in response during refresh.",
                         extra={"response_data": data, "token_url": self.TOKEN_URL})
            raise SpotifyAuthError("Access token not found in response during token refresh.")
        logger.debug("Successfully obtained access token via refresh token flow.") # This log might be hit multiple times if retried
        return data["access_token"]

    @api_retry_decorator
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
            logger.error("Access token or refresh token not in response during initial auth.",
                         extra={"response_data": data, "token_url": self.TOKEN_URL})
            raise SpotifyAuthError("Access token or refresh token not found in response during initial authorization.")

        self.refresh_token = data["refresh_token"]
        logger.debug("Successfully obtained initial access and refresh token.",
                     extra={"redirect_uri": redirect_uri})
        return data["access_token"], data["refresh_token"]

    def _get_auth_headers(self):
        auth_str = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_str.encode("utf-8")
        auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")
        return {"Authorization": f"Basic {auth_base64}"}

    def _handle_response_error(self, response):
        if response.status_code != 200:
            logger.error("Error response from Spotify token endpoint.",
                         extra={"status_code": response.status_code,
                                "response_text": response.text,
                                "token_url": self.TOKEN_URL})
            if response.status_code in [400, 401, 403]: # Added 400 for bad request (e.g. invalid refresh token)
                # Specific error for auth-related issues that are client's fault or token issues
                raise SpotifyAuthError(f"Authentication or token request failed ({response.status_code}): {response.text}")
            else:
                # For other server-side errors or unexpected issues, could be a more generic API error or rely on requests' own.
                # For now, re-raising HTTPError for non-auth specific Spotify errors.
                # Alternatively, wrap in SpotifyAPIError.
                try:
                    response.raise_for_status() # This will raise requests.exceptions.HTTPError
                except requests.exceptions.HTTPError as e:
                    raise SpotifyAPIError(f"Spotify API request failed: {e}") from e
