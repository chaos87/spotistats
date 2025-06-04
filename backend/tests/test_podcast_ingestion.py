import unittest
from unittest.mock import patch, MagicMock
import datetime
import os

from sqlalchemy import create_engine, text, JSON # Added JSON
from sqlalchemy.orm import sessionmaker

# Models and db functions
from backend.src.models import Base, Artist, Album, Track, Listen, PodcastSeries, PodcastEpisode, RecentlyPlayedTracksRaw # Added RecentlyPlayedTracksRaw
from backend.src.database import (
    get_max_played_at, upsert_artist, upsert_album, upsert_track,
    upsert_podcast_series, upsert_podcast_episode, insert_listen
) # Removed init_db as it's not used directly in tests after setup
# Main processing function
from backend.main import process_spotify_data # Removed get_spotify_credentials, SpotifyOAuthClient as they are mocked

# Normalizer
from backend.src.normalizer import SpotifyItemNormalizer


# Helper to create a timezone-aware datetime object
def make_played_at_dt(iso_string):
    # Ensures the datetime object is timezone-aware, matching how they are stored from Spotify.
    return datetime.datetime.fromisoformat(iso_string.replace('Z', '+00:00'))

# Sample data for mocking Spotify API responses - Copied from original
SAMPLE_TRACK_ITEM_NEW = {
    "track": {
        "id": "track_id_new", "name": "New Test Track", "type": "track", "duration_ms": 180000, "explicit": False,
        "artists": [{"id": "artist_id_new", "name": "New Test Artist", "external_urls": {"spotify":"new_artist_url"}, "genres": ["new genre"]}],
        "album": {"id": "album_id_new", "name": "New Test Album", "images": [{"url": "new_img_url"}], "external_urls": {"spotify":"new_album_url"}, "release_date":"2024-01-01", "release_date_precision":"day", "album_type": "album"},
        "external_urls": {"spotify":"new_track_url"}, "available_markets": ["US"]
    }, "played_at": "2024-03-01T10:00:00Z"
}
SAMPLE_EPISODE_ITEM_NEW = {
    "track": {
        "id": "ep_id_new", "name": "New Test Episode", "type": "episode", "duration_ms": 1800000, "explicit": False,
        "show": {"id": "show_id_new", "name": "New Test Show", "publisher": "New Publisher", "description": "A new show.", "images":[{"url":"new_show_img"}], "external_urls":{"spotify":"new_show_url"}},
        "external_urls": {"spotify":"new_ep_url"}, "release_date": "2024-02-01", "release_date_precision": "day"
    }, "played_at": "2024-03-01T11:00:00Z"
}
SAMPLE_TRACK_ITEM_EXISTING_LISTEN = {
    "track": {
        "id": "track_id_existing_listen", "name": "Existing Listen Track", "type": "track", "duration_ms": 190000, "explicit": True,
        "artists": [{"id": "artist_id_existing_listen", "name": "Existing Listen Artist", "external_urls": {"spotify":"existing_listen_artist_url"}, "genres": ["existing genre"]}], # Added genres for consistency
        "album": {"id": "album_id_existing_listen", "name": "Existing Listen Album", "images": [{"url": "existing_listen_img"}], "external_urls": {"spotify":"existing_listen_album_url"}, "release_date":"2023-01-01", "release_date_precision":"day", "album_type": "album"}, # Added album_type
        "external_urls": {"spotify":"existing_listen_track_url"}, "available_markets": ["US"] # Added available_markets
    }, "played_at": "2023-02-01T10:00:00Z"
}
SAMPLE_EPISODE_ITEM_EXISTING_LISTEN = {
     "track": {
        "id": "ep_id_existing_listen", "name": "Existing Listen Episode", "type": "episode", "duration_ms": 1900000, "explicit": False,
        "show": {"id": "show_id_existing_listen", "name": "Existing Listen Show", "publisher": "Existing Publisher", "description": "An old show.", "images":[{"url":"old_show_img"}], "external_urls":{"spotify":"old_show_url"}},
        "external_urls": {"spotify":"old_ep_url"}, "release_date": "2023-01-15", "release_date_precision": "day"
    }, "played_at": "2023-02-01T11:00:00Z"
}


class TestPodcastIngestion(unittest.TestCase):
    engine = None
    SessionLocal = None # Renamed from Session to SessionLocal to avoid confusion with self.session
    TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

    # Store original types for SQLite compatibility monkeypatching
    original_artist_genres_type = None
    original_track_markets_type = None
    original_raw_data_type = None


    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(cls.TEST_SQLALCHEMY_DATABASE_URL)

        # Apply type overrides for SQLite compatibility
        cls.original_artist_genres_type = Artist.genres.property.columns[0].type
        Artist.genres.property.columns[0].type = JSON()

        cls.original_track_markets_type = Track.available_markets.property.columns[0].type
        Track.available_markets.property.columns[0].type = JSON()

        # Assuming RecentlyPlayedTracksRaw is used or might be created by schema, ensure its type is compatible too
        if hasattr(RecentlyPlayedTracksRaw, 'data'): # Check if the model and column exist
             cls.original_raw_data_type = RecentlyPlayedTracksRaw.data.property.columns[0].type
             RecentlyPlayedTracksRaw.data.property.columns[0].type = JSON()

        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine) # Drop all tables

        # Restore original types
        if cls.original_artist_genres_type:
            Artist.genres.property.columns[0].type = cls.original_artist_genres_type
        if cls.original_track_markets_type:
            Track.available_markets.property.columns[0].type = cls.original_track_markets_type
        if cls.original_raw_data_type and hasattr(RecentlyPlayedTracksRaw, 'data'):
            RecentlyPlayedTracksRaw.data.property.columns[0].type = cls.original_raw_data_type

        if cls.engine:
            cls.engine.dispose()

    def setUp(self):
        self.session = self.SessionLocal()
        # Clean tables before each test method
        for table in reversed(Base.metadata.sorted_tables):
            self.session.execute(table.delete())
        self.session.commit()

        self.normalizer = SpotifyItemNormalizer()

        # Pre-populate existing track listen
        # Note: For SQLite, ON CONFLICT DO UPDATE behaves like DO NOTHING if not supported,
        # or specific handling is needed. PG-specific upsert logic in database.py might need adjustment or mocking for SQLite.
        # For this test, we assume upsert functions are compatible or we are testing the flow around them.
        # The `pg_insert` functions in database.py are specific to PostgreSQL.
        # We will mock these database functions to simulate their behavior without PG dependency.

        # Instead of direct DB calls here, we'll rely on process_spotify_data to populate
        # and test against that. For initial max_played_at, we can insert directly.

        # Pre-insert existing listens to establish a baseline max_played_at
        existing_artist = Artist(artist_id="artist_id_existing_listen", name="Existing Listen Artist", genres=["existing genre"])
        existing_album = Album(album_id="album_id_existing_listen", name="Existing Listen Album", primary_artist_id="artist_id_existing_listen", album_type="album")
        existing_track = Track(track_id="track_id_existing_listen", name="Existing Listen Track", album_id="album_id_existing_listen", available_markets=["US"])

        existing_series = PodcastSeries(series_id="show_id_existing_listen", name="Existing Listen Show", publisher="Existing Publisher")
        existing_episode = PodcastEpisode(episode_id="ep_id_existing_listen", name="Existing Listen Episode", series_id="show_id_existing_listen")

        self.session.add_all([existing_artist, existing_album, existing_track, existing_series, existing_episode])
        self.session.commit()

        listen_track_existing = Listen(
            played_at=make_played_at_dt(SAMPLE_TRACK_ITEM_EXISTING_LISTEN['played_at']),
            item_type='track',
            track_id=existing_track.track_id,
            artist_id=existing_artist.artist_id,
            album_id=existing_album.album_id
        )
        listen_episode_existing = Listen(
            played_at=make_played_at_dt(SAMPLE_EPISODE_ITEM_EXISTING_LISTEN['played_at']),
            item_type='episode',
            episode_id=existing_episode.episode_id
        )
        self.session.add_all([listen_track_existing, listen_episode_existing])
        self.session.commit()

        self.initial_max_played_at = get_max_played_at(self.session)
        # Ensure the retrieved time is UTC aware for comparison, as SQLite might not store TZ info
        if self.initial_max_played_at and self.initial_max_played_at.tzinfo is None:
            self.initial_max_played_at = self.initial_max_played_at.replace(tzinfo=datetime.timezone.utc)

        self.assertEqual(self.initial_max_played_at, make_played_at_dt(SAMPLE_EPISODE_ITEM_EXISTING_LISTEN['played_at']))


    def tearDown(self):
        self.session.rollback()
        self.session.close()

    @patch('backend.main.get_spotify_credentials')
    @patch('backend.main.SpotifyOAuthClient')
    @patch('backend.main.get_recently_played_tracks')
    # Patch get_db_engine within main.py to return our in-memory SQLite engine
    @patch('backend.main.get_db_engine')
    def test_ingestion_mixed_new_and_existing_items(
        self, mock_get_main_db_engine, mock_get_recently_played,
        mock_spotify_oauth_client, mock_get_creds
    ):
        # Configure the mock for get_db_engine to return the test engine
        mock_get_main_db_engine.return_value = self.engine

        mock_get_creds.return_value = ("id", "secret", "refresh")
        mock_spotify_oauth_client.return_value.get_access_token_from_refresh.return_value = "test_access_token"

        mock_get_recently_played.return_value = {
            "items": [
                SAMPLE_EPISODE_ITEM_NEW,
                SAMPLE_TRACK_ITEM_NEW,
            ],
            "next": None
        }

        process_spotify_data()

        retrieved_listens = self.session.query(Listen).order_by(Listen.played_at).all()
        self.assertEqual(len(retrieved_listens), 4) # 2 initial + 2 new

        # Make retrieved datetimes UTC aware for comparison
        aware_listens_played_at = []
        for l_obj in retrieved_listens:
            if l_obj.played_at and l_obj.played_at.tzinfo is None:
                aware_listens_played_at.append(l_obj.played_at.replace(tzinfo=datetime.timezone.utc))
            else:
                aware_listens_played_at.append(l_obj.played_at)

        self.assertEqual(aware_listens_played_at[0], make_played_at_dt(SAMPLE_TRACK_ITEM_EXISTING_LISTEN['played_at']))
        self.assertEqual(aware_listens_played_at[1], make_played_at_dt(SAMPLE_EPISODE_ITEM_EXISTING_LISTEN['played_at']))
        self.assertEqual(aware_listens_played_at[2], make_played_at_dt(SAMPLE_TRACK_ITEM_NEW['played_at']))
        self.assertEqual(aware_listens_played_at[3], make_played_at_dt(SAMPLE_EPISODE_ITEM_NEW['played_at']))

        # new_max_played_at is already aware due to changes in get_max_played_at
        new_max_played_at = get_max_played_at(self.session)
        self.assertEqual(new_max_played_at, make_played_at_dt(SAMPLE_EPISODE_ITEM_NEW['played_at']))

        # Detailed verification of inserted objects
        # Querying with an aware datetime should work fine.
        track_listen = self.session.query(Listen).filter(Listen.played_at == make_played_at_dt(SAMPLE_TRACK_ITEM_NEW['played_at'])).one()
        self.assertEqual(track_listen.item_type, 'track')
        self.assertEqual(track_listen.track_id, SAMPLE_TRACK_ITEM_NEW['track']['id'])
        self.assertIsNotNone(track_listen.artist_id)
        self.assertIsNotNone(track_listen.album_id)
        self.assertIsNone(track_listen.episode_id)

        artist = self.session.query(Artist).filter_by(artist_id=SAMPLE_TRACK_ITEM_NEW['track']['artists'][0]['id']).one_or_none()
        self.assertIsNotNone(artist)
        self.assertEqual(artist.name, SAMPLE_TRACK_ITEM_NEW['track']['artists'][0]['name'])
        # For SQLite with JSON type override, genres will be stored as JSON string or Python list/dict
        self.assertTrue(isinstance(artist.genres, (list, str)))


        album = self.session.query(Album).filter_by(album_id=SAMPLE_TRACK_ITEM_NEW['track']['album']['id']).one_or_none()
        self.assertIsNotNone(album)
        self.assertEqual(album.name, SAMPLE_TRACK_ITEM_NEW['track']['album']['name'])
        self.assertEqual(album.primary_artist_id, artist.artist_id)

        track = self.session.query(Track).filter_by(track_id=SAMPLE_TRACK_ITEM_NEW['track']['id']).one_or_none()
        self.assertIsNotNone(track)
        self.assertEqual(track.name, SAMPLE_TRACK_ITEM_NEW['track']['name'])
        self.assertEqual(track.album_id, album.album_id)
        self.assertTrue(isinstance(track.available_markets, (list, str)))

        # Querying with an aware datetime for episode listen
        episode_listen = self.session.query(Listen).filter(Listen.played_at == make_played_at_dt(SAMPLE_EPISODE_ITEM_NEW['played_at'])).one()
        self.assertEqual(episode_listen.item_type, 'episode')
        self.assertEqual(episode_listen.episode_id, SAMPLE_EPISODE_ITEM_NEW['track']['id'])
        self.assertIsNone(episode_listen.track_id)
        self.assertIsNone(episode_listen.artist_id)
        self.assertIsNone(episode_listen.album_id)

        series = self.session.query(PodcastSeries).filter_by(series_id=SAMPLE_EPISODE_ITEM_NEW['track']['show']['id']).one_or_none()
        self.assertIsNotNone(series)
        self.assertEqual(series.name, SAMPLE_EPISODE_ITEM_NEW['track']['show']['name'])

        episode = self.session.query(PodcastEpisode).filter_by(episode_id=SAMPLE_EPISODE_ITEM_NEW['track']['id']).one_or_none()
        self.assertIsNotNone(episode)
        self.assertEqual(episode.name, SAMPLE_EPISODE_ITEM_NEW['track']['name'])
        self.assertEqual(episode.series_id, series.series_id)

        self.assertEqual(self.session.query(Artist).count(), 2)
        self.assertEqual(self.session.query(Album).count(), 2)
        self.assertEqual(self.session.query(Track).count(), 2)
        self.assertEqual(self.session.query(PodcastSeries).count(), 2)
        self.assertEqual(self.session.query(PodcastEpisode).count(), 2)


    @patch('backend.main.get_spotify_credentials')
    @patch('backend.main.SpotifyOAuthClient')
    @patch('backend.main.get_recently_played_tracks')
    @patch('backend.main.get_db_engine')
    def test_ingestion_only_existing_items_returned(
        self, mock_get_main_db_engine, mock_get_recently_played,
        mock_spotify_oauth_client, mock_get_creds
    ):
        mock_get_main_db_engine.return_value = self.engine

        mock_get_creds.return_value = ("id", "secret", "refresh")
        mock_spotify_oauth_client.return_value.get_access_token_from_refresh.return_value = "test_access_token"

        mock_get_recently_played.return_value = {
            "items": [ # These items are older than or same as initial_max_played_at
                SAMPLE_EPISODE_ITEM_EXISTING_LISTEN,
                SAMPLE_TRACK_ITEM_EXISTING_LISTEN
            ],
            "next": None
        }

        initial_listen_count = self.session.query(Listen).count()
        self.assertEqual(initial_listen_count, 2)

        process_spotify_data()

        final_listen_count = self.session.query(Listen).count()
        self.assertEqual(final_listen_count, initial_listen_count) # No new listens should be added

        final_max_played_at = get_max_played_at(self.session)
        self.assertEqual(final_max_played_at, self.initial_max_played_at)

        # Counts of entities should remain 1 each, as set up in setUp()
        self.assertEqual(self.session.query(Artist).count(), 1)
        self.assertEqual(self.session.query(Album).count(), 1)
        self.assertEqual(self.session.query(Track).count(), 1)
        self.assertEqual(self.session.query(PodcastSeries).count(), 1)
        self.assertEqual(self.session.query(PodcastEpisode).count(), 1)

if __name__ == '__main__':
    unittest.main()
