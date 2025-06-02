import datetime
from backend.src.models import Artist, Album, Track, Listen # Assuming models.py is in backend.src

def parse_release_date(date_str: str, precision: str) -> datetime.date | None:
    if not date_str:
        return None
    try:
        if precision == 'day':
            return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        elif precision == 'month':
            # For month precision, Spotify provides YYYY-MM. strptime needs a day.
            # So, parse as YYYY-MM, then replace day with 1.
            dt_obj = datetime.datetime.strptime(date_str, '%Y-%m')
            return dt_obj.date().replace(day=1)
        elif precision == 'year':
            # For year precision, Spotify provides YYYY. strptime needs month/day.
            # So, parse as YYYY, then replace month and day with 1.
            dt_obj = datetime.datetime.strptime(date_str, '%Y')
            return dt_obj.date().replace(month=1, day=1)
        return None # Unknown precision
    except ValueError: # Handles cases where date_str doesn't match format
        return None

class SpotifyMusicNormalizer:
    def normalize_track_item(self, spotify_item: dict, played_at_datetime: datetime.datetime) -> tuple[Artist, Album, Track, Listen] | None:
        track_data = spotify_item.get('track')
        if not track_data or track_data.get('type') != 'track':
            return None

        # Primary Artist
        primary_artist_data = track_data['artists'][0] if track_data.get('artists') and len(track_data['artists']) > 0 else {}

        artist_image_url = None
        # Try to get image from album data if present
        if track_data.get('album') and track_data['album'].get('images'):
            album_images = track_data['album']['images']
            if album_images and len(album_images) > 0:
                artist_image_url = album_images[0].get('url')

        artist = Artist(
            artist_id=primary_artist_data.get('id'),
            name=primary_artist_data.get('name'),
            spotify_url=primary_artist_data.get('external_urls', {}).get('spotify'),
            image_url=artist_image_url,
            genres=primary_artist_data.get('genres', [])
        )

        # Album
        album_data = track_data.get('album', {})
        album_image_url = None
        if album_data.get('images'):
            album_images_list = album_data['images']
            if album_images_list and len(album_images_list) > 0:
                album_image_url = album_images_list[0].get('url')

        release_date_obj = None
        if album_data.get('release_date') and album_data.get('release_date_precision'):
            release_date_obj = parse_release_date(album_data['release_date'], album_data['release_date_precision'])

        album = Album(
            album_id=album_data.get('id'),
            name=album_data.get('name'),
            release_date=release_date_obj,
            album_type=album_data.get('album_type'),
            spotify_url=album_data.get('external_urls', {}).get('spotify'),
            image_url=album_image_url,
            primary_artist_id=artist.artist_id # This will be None if artist_id is None
        )

        # Track
        track = Track(
            track_id=track_data.get('id'),
            name=track_data.get('name'),
            duration_ms=track_data.get('duration_ms'),
            explicit=track_data.get('explicit'),
            popularity=track_data.get('popularity'),
            preview_url=track_data.get('preview_url'),
            spotify_url=track_data.get('external_urls', {}).get('spotify'),
            album_id=album.album_id, # This will be None if album_id is None
            available_markets=track_data.get('available_markets', []),
            last_played_at=played_at_datetime
        )

        # Listen
        listen = Listen(
            played_at=played_at_datetime,
            item_type='track', # Hardcoded as per requirement
            track_id=track.track_id, # Will be None if track_id is None
            artist_id=artist.artist_id, # Will be None if artist_id is None
            album_id=album.album_id,   # Will be None if album_id is None
            episode_id=None # Hardcoded as per requirement
        )

        return artist, album, track, listen
