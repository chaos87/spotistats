import requests
import logging
from backend.src.exceptions import SpotifyAPIError # Import from exceptions.py
from .utils import api_retry_decorator # Import the decorator

# Configure logging - This will be removed as setup_logging in main.py handles it.
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# class SpotifyAPIError(Exception): # This is now defined in exceptions.py
#     """Custom exception for Spotify API errors."""
#     pass

@api_retry_decorator
def get_recently_played_tracks(access_token: str, limit: int = 50, after: int = None) -> dict:
    """
    Fetches the user's recently played tracks from the Spotify API.

    Args:
        access_token: The Spotify API access token.
        limit: The number of items to return (max 50).

    Returns:
        A dictionary containing the raw JSON response from the API.

    Raises:
        SpotifyAPIError: If the API request fails.
    """
    if not 1 <= limit <= 50:
        raise ValueError("Limit must be between 1 and 50.")

    url = "https://api.spotify.com/v1/me/player/recently-played"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    params = { # Ensure all relevant params are passed through
        "limit": limit
    }
    if after:
        params["after"] = after

    try:
        logger.debug("Fetching recently played tracks from Spotify.",
                     extra={"url": url, "limit": limit, "after": after})
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)

        num_items = len(response.json().get('items', []))
        logger.info(f"Successfully fetched recently played items from Spotify.",
                    extra={"item_count": num_items, "limit_param": limit, "after_param": after})
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        logger.error("HTTP error occurred while fetching recently played tracks.",
                     exc_info=True, # Add exc_info for stack trace
                     extra={"url": url, "status_code": response.status_code, "response_text": response.text, "error": str(http_err)})
        raise SpotifyAPIError(f"Spotify API request failed with status {response.status_code}: {response.text}") from http_err
    except requests.exceptions.RequestException as req_err:
        logger.error("Request exception occurred while fetching recently played tracks.",
                     exc_info=True, # Add exc_info for stack trace
                     extra={"url": url, "error": str(req_err)})
        raise SpotifyAPIError(f"Spotify API request failed: {req_err}") from req_err

if __name__ == '__main__':
    # This is a placeholder for testing.
    # In a real scenario, the access token would be obtained through the OAuth flow.
    # You would need to replace 'YOUR_ACCESS_TOKEN' with a valid token.
    # print("This script is intended to be imported, not run directly for fetching data without a token.")
    # For manual testing, you can try:
    # try:
    #     # Replace with a valid access token obtained from Spotify
    #     # Ensure the token has the 'user-read-recently-played' scope
    #     test_token = "YOUR_ACCESS_TOKEN" # IMPORTANT: Replace with a real token for testing
    #     if test_token == "YOUR_ACCESS_TOKEN":
    #          print("Please replace 'YOUR_ACCESS_TOKEN' with a valid Spotify access token to test.")
    #     else:
    #         played_tracks = get_recently_played_tracks(test_token, limit=10)
    #         print("Fetched recently played tracks:")
    #         for i, item in enumerate(played_tracks.get('items', [])):
    #             track_name = item.get('track', {}).get('name')
    #             played_at = item.get('played_at')
    #             print(f"{i+1}. {track_name} (Played at: {played_at})")
    # except SpotifyAPIError as e:
    #     print(f"Error fetching tracks: {e}")
    # except ValueError as e:
    #     print(f"Input error: {e}")
    pass
