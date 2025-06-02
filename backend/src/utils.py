import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, retry_if_exception_type
from requests.exceptions import RequestException, ConnectionError, Timeout
from sqlalchemy.exc import OperationalError # For DB connection retries

# Assuming exceptions are consolidated in backend.src.exceptions
from backend.src.exceptions import SpotifyAuthError, SpotifyAPIError

# Configure a logger for this module (utils.py)
logger = logging.getLogger(__name__)

def is_retryable_api_exception(e: Exception) -> bool:
    """Determines if an API exception is retryable."""
    if isinstance(e, SpotifyAuthError): # Do not retry auth errors (401, 403 specifically handled in spotify_client)
        logger.debug(f"Non-retryable: SpotifyAuthError encountered: {e}")
        return False

    # Check for basic network issues first
    if isinstance(e, (ConnectionError, Timeout)):
        logger.warning(f"Retrying due to network error: {type(e).__name__} - {e}")
        return True

    # Check for SpotifyAPIError which might wrap HTTPError from requests
    # SpotifyAPIError in spotify_client._handle_response_error is now raised for non-400,401,403 client/server errors.
    # And specifically for 5xx errors from requests.raise_for_status()
    if isinstance(e, SpotifyAPIError):
        # If SpotifyAPIError directly wraps a requests.exceptions.RequestException, check its response
        if hasattr(e, '__cause__') and isinstance(e.__cause__, RequestException):
            original_request_exc = e.__cause__
            if original_request_exc.response is not None:
                status_code = original_request_exc.response.status_code
                if status_code == 429: # Rate limiting
                    logger.warning(f"Retrying due to Spotify API rate limit (429): {e}")
                    # TODO: Implement handling of 'Retry-After' header if available.
                    # Tenacity's wait_exponential doesn't inherently support this.
                    # A custom wait function would be needed.
                    return True
                if status_code >= 500 and status_code <= 599: # Server-side errors
                    logger.warning(f"Retrying due to Spotify API server-side error ({status_code}): {e}")
                    return True
        # If it's a SpotifyAPIError not directly wrapping a RequestException with a response,
        # it might be a custom one. For now, assume these are not retryable unless specified.
        logger.debug(f"Non-retryable SpotifyAPIError (not a 429 or 5xx): {e}")
        return False

    # Fallback for direct RequestException instances not wrapped by SpotifyAPIError (should be less common now)
    if isinstance(e, RequestException) and e.response is not None:
        status_code = e.response.status_code
        if status_code == 429:
            logger.warning(f"Retrying due to direct RequestException rate limit (429): {e}")
            return True
        if status_code >= 500 and status_code <= 599:
            logger.warning(f"Retrying due to direct RequestException server-side error ({status_code}): {e}")
            return True

    logger.debug(f"Non-retryable API exception: {type(e).__name__} - {e}")
    return False

api_retry_decorator = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10), # Exponential backoff: 2s, 4s, 8s...
    retry=retry_if_exception(is_retryable_api_exception),
    before_sleep=lambda retry_state: logger.info(
        f"Retrying API call: {retry_state.fn.__name__}, attempt #{retry_state.attempt_number} "
        f"after {retry_state.seconds_since_start:.2f}s. Last exception: {retry_state.outcome.exception()}",
        extra={
            "retry_fn_name": retry_state.fn.__name__,
            "retry_attempt_number": retry_state.attempt_number,
            "retry_seconds_since_start": f"{retry_state.seconds_since_start:.2f}",
            "retry_last_exception_type": type(retry_state.outcome.exception()).__name__ if retry_state.outcome else None,
            "retry_last_exception": str(retry_state.outcome.exception()) if retry_state.outcome else None,
        }
    )
)

# Define a retry decorator for database connection attempts
# OperationalError is a broad category; might include issues like "too many connections"
# or temporary network problems to the DB server.
db_retry_decorator = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(OperationalError), # Retry only on OperationalError for DB
    before_sleep=lambda retry_state: logger.info(
        f"Retrying DB operation: {retry_state.fn.__name__}, attempt #{retry_state.attempt_number} "
        f"after {retry_state.seconds_since_start:.2f}s. Last exception: {retry_state.outcome.exception()}",
        extra={
            "retry_fn_name": retry_state.fn.__name__,
            "retry_attempt_number": retry_state.attempt_number,
            "retry_seconds_since_start": f"{retry_state.seconds_since_start:.2f}",
            "retry_last_exception_type": type(retry_state.outcome.exception()).__name__ if retry_state.outcome else None,
            "retry_last_exception": str(retry_state.outcome.exception()) if retry_state.outcome else None,
        }
    )
)
