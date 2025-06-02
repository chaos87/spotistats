import datetime
import logging # Added
from typing import Tuple, Dict, Any, Optional
from backend.src.models import Artist, Album, Track, Listen, PodcastSeries, PodcastEpisode # Assuming models.py is in backend.src

logger = logging.getLogger(__name__) # Added

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
        logger.warning("Unknown release_date_precision.", extra={"date_str": date_str, "precision": precision})
        return None # Unknown precision
    except ValueError as e: # Handles cases where date_str doesn't match format
        logger.warning("Could not parse release_date.",
                       extra={"date_str": date_str, "precision": precision, "error": str(e)})
        return None

class SpotifyItemNormalizer:
    def _normalize_track_data(self, track_data: dict, played_at_datetime: datetime.datetime) -> Tuple[Artist, Album, Track, Listen]:
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
            genres=primary_artist_data.get('genres', []) # Assuming genres might not exist
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
            primary_artist_id=artist.artist_id
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
            album_id=album.album_id,
            available_markets=track_data.get('available_markets', []),
            last_played_at=played_at_datetime # This seems to be a listen-specific field
        )

        # Listen for track
        listen = Listen(
            played_at=played_at_datetime,
            item_type='track',
            track_id=track.track_id,
            artist_id=artist.artist_id,
            album_id=album.album_id,
            episode_id=None
        )
        return artist, album, track, listen

    def normalize_episode_item(self, item: dict) -> Tuple[PodcastSeries, PodcastEpisode, Listen]:
        episode_data = item['track'] # The 'track' field contains episode details
        show_data = episode_data['show']
        played_at_datetime = datetime.datetime.fromisoformat(item['played_at'].replace('Z', '+00:00'))


        series_image_url = None
        if show_data.get('images') and len(show_data['images']) > 0:
            series_image_url = show_data['images'][0].get('url')

        series = PodcastSeries(
            series_id=show_data['id'],
            name=show_data['name'],
            publisher=show_data.get('publisher'),
            description=show_data.get('description'),
            image_url=series_image_url,
            spotify_url=show_data.get('external_urls', {}).get('spotify')
        )

        release_date_obj = None
        if episode_data.get('release_date') and episode_data.get('release_date_precision'):
            release_date_obj = parse_release_date(episode_data['release_date'], episode_data['release_date_precision'])

        episode = PodcastEpisode(
            episode_id=episode_data['id'],
            name=episode_data['name'],
            description=episode_data.get('description'),
            duration_ms=episode_data.get('duration_ms'),
            explicit=episode_data.get('explicit'),
            release_date=release_date_obj,
            spotify_url=episode_data.get('external_urls', {}).get('spotify'),
            series_id=series.series_id
        )

        listen = Listen(
            played_at=played_at_datetime,
            item_type='episode',
            episode_id=episode.episode_id,
            track_id=None,
            artist_id=None,
            album_id=None
        )
        return series, episode, listen

    def normalize_item(self, item: dict) -> Optional[Dict[str, Any]]:
        track_data = item.get('track')
        item_name_for_log = track_data.get('name', 'N/A') if track_data else 'N/A'
        item_id_for_log = track_data.get('id', 'N/A') if track_data else 'N/A'

        if not track_data:
            logger.warning("Item missing 'track' data, cannot normalize.", extra={"item_data": item})
            return None # Or raise an error, depending on desired handling

        played_at_str = item.get('played_at')
        if not played_at_str:
            logger.warning("Item missing 'played_at' data, cannot normalize.",
                           extra={"item_name": item_name_for_log, "item_id": item_id_for_log})
            return None # Or raise

        try:
            played_at_datetime = datetime.datetime.fromisoformat(played_at_str.replace('Z', '+00:00'))
        except ValueError:
            logger.warning("Could not parse 'played_at' timestamp during normalization.",
                           extra={"played_at_raw": played_at_str, "item_name": item_name_for_log, "item_id": item_id_for_log})
            return None


        item_type = track_data.get('type')

        if item_type == 'track':
            artist, album, track, listen = self._normalize_track_data(track_data, played_at_datetime)
            return {
                'type': 'track',
                'artist': artist,
                'album': album,
                'track': track,
                'listen': listen
            }
        elif item_type == 'episode':
            # The normalize_episode_item expects the full item for 'played_at'
            series, episode, listen = self.normalize_episode_item(item)
            return {
                'type': 'episode',
                'series': series,
                'episode': episode,
                'listen': listen
            }
        else:
            logger.warning("Unknown item type encountered during normalization.",
                           extra={"item_type": item_type, "item_name": item_name_for_log, "item_id": item_id_for_log})
            return None
