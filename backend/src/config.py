import os
from dotenv import load_dotenv

def load_spotify_config():
    """
    Loads Spotify API configuration from environment variables.

    Raises:
        ValueError: If any of the required environment variables are missing.

    Returns:
        tuple: A tuple containing SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and SPOTIFY_REFRESH_TOKEN.
    """
    load_dotenv()  # Load environment variables from .env file if it exists

    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    refresh_token = os.getenv("SPOTIFY_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        missing_vars = []
        if not client_id:
            missing_vars.append("SPOTIFY_CLIENT_ID")
        if not client_secret:
            missing_vars.append("SPOTIFY_CLIENT_SECRET")
        if not refresh_token:
            missing_vars.append("SPOTIFY_REFRESH_TOKEN")
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    return client_id, client_secret, refresh_token

if __name__ == '__main__':
    # Example usage:
    try:
        spotify_client_id, spotify_client_secret, spotify_refresh_token = load_spotify_config()
        print("Spotify Config Loaded Successfully:")
        print(f"  Client ID: {spotify_client_id}")
        print(f"  Client Secret: {spotify_client_secret}")
        print(f"  Refresh Token: {spotify_refresh_token}")
    except ValueError as e:
        print(f"Error loading Spotify config: {e}")
