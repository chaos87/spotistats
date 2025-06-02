import pytest
import requests
import requests_mock
import tenacity # Added import for tenacity
from backend.src.spotify_data import get_recently_played_tracks
from backend.src.exceptions import SpotifyAPIError # Ensure this is imported from exceptions


# Sample successful response from Spotify API
MOCK_SUCCESS_RESPONSE = {
    "items": [
        {
            "track": {
                "name": "Test Track 1",
                "id": "test_id_1"
            },
            "played_at": "2023-01-01T12:00:00Z"
        },
        {
            "track": {
                "name": "Test Track 2",
                "id": "test_id_2"
            },
            "played_at": "2023-01-01T12:05:00Z"
        }
    ],
    "limit": 2
}

# Another sample successful response with different data
MOCK_SUCCESS_RESPONSE_LIMIT_1 = {
    "items": [
        {
            "track": {
                "name": "Test Track Only",
                "id": "test_id_only"
            },
            "played_at": "2023-01-02T10:00:00Z"
        }
    ],
    "limit": 1
}


@pytest.fixture
def mock_spotify_api():
    with requests_mock.Mocker() as m:
        yield m

def test_get_recently_played_tracks_success(mock_spotify_api):
    """Test successful fetching of recently played tracks."""
    access_token = "fake_access_token"
    limit = 2
    mock_spotify_api.get(
        f"https://api.spotify.com/v1/me/player/recently-played?limit={limit}",
        json=MOCK_SUCCESS_RESPONSE,
        status_code=200,
        headers={'Authorization': f'Bearer {access_token}'}
    )

    response = get_recently_played_tracks(access_token, limit=limit)
    assert response == MOCK_SUCCESS_RESPONSE
    assert len(response["items"]) == limit
    assert mock_spotify_api.call_count == 1
    history = mock_spotify_api.request_history
    assert history[0].method == "GET"
    assert history[0].url == f"https://api.spotify.com/v1/me/player/recently-played?limit={limit}"
    assert history[0].headers["Authorization"] == f"Bearer {access_token}"

def test_get_recently_played_tracks_success_different_limit(mock_spotify_api):
    """Test successful fetching with a different limit."""
    access_token = "another_fake_token"
    limit = 1
    mock_spotify_api.get(
        f"https://api.spotify.com/v1/me/player/recently-played?limit={limit}",
        json=MOCK_SUCCESS_RESPONSE_LIMIT_1,
        status_code=200
    )

    response = get_recently_played_tracks(access_token, limit=limit)
    assert response == MOCK_SUCCESS_RESPONSE_LIMIT_1
    assert len(response["items"]) == limit

def test_get_recently_played_tracks_http_error(mock_spotify_api):
    """Test handling of HTTP errors from Spotify API."""
    access_token = "fake_access_token"
    limit = 5
    mock_spotify_api.get(
        f"https://api.spotify.com/v1/me/player/recently-played?limit={limit}",
        text="Internal Server Error",
        status_code=500
    )

    # The function is decorated with a retry. If all retries fail, tenacity.RetryError is raised.
    with pytest.raises(tenacity.RetryError) as excinfo:
        get_recently_played_tracks(access_token, limit=limit)

    # Verify the underlying error after retries are exhausted
    final_exception = excinfo.value.last_attempt.exception()
    assert isinstance(final_exception, SpotifyAPIError)
    assert "Spotify API request failed with status 500" in str(final_exception)

def test_get_recently_played_tracks_request_exception(mock_spotify_api):
    """Test handling of general request exceptions (e.g., network error)."""
    access_token = "fake_access_token"
    limit = 10
    mock_spotify_api.get(
        f"https://api.spotify.com/v1/me/player/recently-played?limit={limit}",
        exc=requests.exceptions.Timeout("Connection timed out") # This is a retryable exception
    )

    # The function is decorated. Expect tenacity.RetryError.
    with pytest.raises(tenacity.RetryError) as excinfo:
        get_recently_played_tracks(access_token, limit=limit)

    final_exception = excinfo.value.last_attempt.exception()
    assert isinstance(final_exception, SpotifyAPIError)
    assert "Spotify API request failed: Connection timed out" in str(final_exception)


def test_get_recently_played_tracks_invalid_limit_too_low():
    """Test that an invalid limit (too low) raises ValueError."""
    access_token = "fake_access_token"
    with pytest.raises(ValueError) as excinfo:
        get_recently_played_tracks(access_token, limit=0)
    assert "Limit must be between 1 and 50" in str(excinfo.value)

def test_get_recently_played_tracks_invalid_limit_too_high():
    """Test that an invalid limit (too high) raises ValueError."""
    access_token = "fake_access_token"
    with pytest.raises(ValueError) as excinfo:
        get_recently_played_tracks(access_token, limit=51)
    assert "Limit must be between 1 and 50" in str(excinfo.value)

# To run these tests, navigate to the `backend` directory and run:
# poetry run pytest
# Ensure `requests_mock` and `pytest` are in `pyproject.toml` dev dependencies.
# Example pyproject.toml section:
# [tool.poetry.group.dev.dependencies]
# pytest = "^7.0"
# requests-mock = "^1.9"
