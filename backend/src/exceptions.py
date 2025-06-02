class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass

class ConfigurationError(Exception):
    """Custom exception for configuration errors."""
    pass

class SpotifyAuthError(Exception):
    """Custom exception for Spotify authentication errors."""
    pass

class SpotifyAPIError(Exception):
    """Custom exception for Spotify API errors (non-auth related)."""
    pass
