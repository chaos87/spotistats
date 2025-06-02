import unittest
from unittest.mock import patch, MagicMock
import datetime
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Models and db functions
from backend.src.models import Base, Artist, Album, Track, Listen, PodcastSeries, PodcastEpisode
from backend.src.database import (
    get_max_played_at, upsert_artist, upsert_album, upsert_track,
    upsert_podcast_series, upsert_podcast_episode, insert_listen, init_db
)
# Main processing function
from backend.main import process_spotify_data, get_spotify_credentials, SpotifyOAuthClient # Import process_spotify_data

# Normalizer
from backend.src.normalizer import SpotifyItemNormalizer


# Helper to create a timezone-aware datetime object
def make_played_at_dt(iso_string):
    return datetime.datetime.fromisoformat(iso_string.replace('Z', '+00:00'))

# Sample data for mocking Spotify API responses
SAMPLE_TRACK_ITEM_NEW = {
    "track": {
        "id": "track_id_new", "name": "New Test Track", "type": "track", "duration_ms": 180000, "explicit": False,
        "artists": [{"id": "artist_id_new", "name": "New Test Artist", "external_urls": {"spotify":"new_artist_url"}, "genres": ["new genre"]}],
        "album": {"id": "album_id_new", "name": "New Test Album", "images": [{"url": "new_img_url"}], "external_urls": {"spotify":"new_album_url"}, "release_date":"2024-01-01", "release_date_precision":"day", "album_type": "album"},
        "external_urls": {"spotify":"new_track_url"}, "available_markets": ["US"]
    }, "played_at": "2024-03-01T10:00:00Z" # Newer than any existing
}
SAMPLE_EPISODE_ITEM_NEW = {
    "track": {
        "id": "ep_id_new", "name": "New Test Episode", "type": "episode", "duration_ms": 1800000, "explicit": False,
        "show": {"id": "show_id_new", "name": "New Test Show", "publisher": "New Publisher", "description": "A new show.", "images":[{"url":"new_show_img"}], "external_urls":{"spotify":"new_show_url"}},
        "external_urls": {"spotify":"new_ep_url"}, "release_date": "2024-02-01", "release_date_precision": "day"
    }, "played_at": "2024-03-01T11:00:00Z" # Newer than any existing
}
SAMPLE_TRACK_ITEM_EXISTING_LISTEN = { # Same as new, but older played_at
    "track": {
        "id": "track_id_existing_listen", "name": "Existing Listen Track", "type": "track", "duration_ms": 190000, "explicit": True,
        "artists": [{"id": "artist_id_existing_listen", "name": "Existing Listen Artist", "external_urls": {"spotify":"existing_listen_artist_url"}}],
        "album": {"id": "album_id_existing_listen", "name": "Existing Listen Album", "images": [{"url": "existing_listen_img"}], "external_urls": {"spotify":"existing_listen_album_url"}, "release_date":"2023-01-01", "release_date_precision":"day"},
        "external_urls": {"spotify":"existing_listen_track_url"}
    }, "played_at": "2023-02-01T10:00:00Z" # Older, should be in DB already
}
SAMPLE_EPISODE_ITEM_EXISTING_LISTEN = {
     "track": {
        "id": "ep_id_existing_listen", "name": "Existing Listen Episode", "type": "episode", "duration_ms": 1900000, "explicit": False,
        "show": {"id": "show_id_existing_listen", "name": "Existing Listen Show", "publisher": "Existing Publisher", "description": "An old show.", "images":[{"url":"old_show_img"}], "external_urls":{"spotify":"old_show_url"}},
        "external_urls": {"spotify":"old_ep_url"}, "release_date": "2023-01-15", "release_date_precision": "day"
    }, "played_at": "2023-02-01T11:00:00Z" # Older, should be in DB already
}


class TestPodcastIngestion(unittest.TestCase):
    engine = None
    Session = None

    @classmethod
    def setUpClass(cls):
        # Use a test-specific database URL, e.g., from environment variable or default
        db_url = os.getenv("TEST_DATABASE_URL", "postgresql://user:password@localhost:5432/test_spotify_dashboard")
        cls.engine = create_engine(db_url)
        Base.metadata.drop_all(cls.engine) # Ensure clean database for each test run
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine)
        if cls.engine:
            cls.engine.dispose()

    def setUp(self):
        self.session = self.Session()
        # Clean tables before each test method
        for table in reversed(Base.metadata.sorted_tables):
            self.session.execute(table.delete())
        self.session.commit()

        # Pre-populate with one existing listen for track and one for episode
        self.normalizer = SpotifyItemNormalizer()

        # Pre-populate existing track listen
        track_data_existing = self.normalizer.normalize_item(SAMPLE_TRACK_ITEM_EXISTING_LISTEN)
        if track_data_existing:
            upsert_artist(self.session, track_data_existing['artist'])
            upsert_album(self.session, track_data_existing['album'])
            upsert_track(self.session, track_data_existing['track'])
            insert_listen(self.session, track_data_existing['listen'])

        # Pre-populate existing episode listen
        episode_data_existing = self.normalizer.normalize_item(SAMPLE_EPISODE_ITEM_EXISTING_LISTEN)
        if episode_data_existing:
            upsert_podcast_series(self.session, episode_data_existing['series'])
            upsert_podcast_episode(self.session, episode_data_existing['episode'])
            insert_listen(self.session, episode_data_existing['listen'])
        self.session.commit()

        self.initial_max_played_at = get_max_played_at(self.session)
        self.assertEqual(self.initial_max_played_at, make_played_at_dt(SAMPLE_EPISODE_ITEM_EXISTING_LISTEN['played_at']))


    def tearDown(self):
        self.session.rollback() # Rollback any uncommitted changes from a failed test
        self.session.close()

    @patch('backend.main.get_spotify_credentials')
    @patch('backend.main.SpotifyOAuthClient')
    @patch('backend.main.get_recently_played_tracks')
    def test_ingestion_mixed_new_and_existing_items(
        self, mock_get_recently_played, mock_spotify_oauth_client, mock_get_creds
    ):
        # Mock credentials and client
        mock_get_creds.return_value = ("id", "secret", "refresh")
        mock_spotify_oauth_client.return_value.get_access_token_from_refresh.return_value = "test_access_token"

        # Mock Spotify API to return a mix of items
        # The order in 'items' from Spotify is newest first. `process_spotify_data` reverses this.
        # So, to test `after` correctly, ensure `played_at` are distinct and in order.
        mock_response_items = [
            SAMPLE_TRACK_ITEM_NEW, # played_at: 2024-03-01T10:00:00Z (newest)
            SAMPLE_EPISODE_ITEM_NEW, # played_at: 2024-03-01T11:00:00Z (also new, but normalizer sorts internally by played_at if needed, main loop reverses) -> actually main loop reverses, so this will be processed after track_item_new
                                      # Let's adjust played_at to be distinct and test ordering
                                      # Corrected: Spotify returns newest first. Loop reverses to process oldest first.
                                      # So, if SAMPLE_EPISODE_ITEM_NEW is "newer" than SAMPLE_TRACK_ITEM_NEW from Spotify perspective,
                                      # it should be listed first in mock_response_items.
        ]
        # Let's ensure played_at are distinct for clarity in testing `after`
        # SAMPLE_EPISODE_ITEM_NEW['played_at'] = "2024-03-01T11:00:00Z" (newer)
        # SAMPLE_TRACK_ITEM_NEW['played_at'] = "2024-03-01T10:00:00Z" (older than episode, but still new)
        # Existing items are older than self.initial_max_played_at (2023-02-01T11:00:00Z)
        # So, they should not be fetched if `after` is working.
        # The test for `after` is implicit: only new items should result in new listens.

        mock_get_recently_played.return_value = {
            "items": [
                SAMPLE_EPISODE_ITEM_NEW, # newest by played_at
                SAMPLE_TRACK_ITEM_NEW,   # second newest
                # Not including existing items here, as Spotify API `after` should filter them.
                # If we wanted to test the internal duplicate check for items Spotify *still sends*,
                # we'd include them and ensure no new Listen rows are created.
                # For now, assume `after` works and Spotify only sends newer items.
            ],
            "next": None
        }

        # Call the main processing function
        with patch('backend.main.get_db_engine', return_value=self.engine): # Ensure main uses the test engine
             process_spotify_data()


        # --- Verification ---
        # 1. Verify get_max_played_at was called and returned the initial max
        #    (This is implicitly tested by only new items being processed)

        # 2. Verify only new listens are inserted
        listens = self.session.query(Listen).order_by(Listen.played_at).all()
        # Initial 2 + 2 new ones = 4
        self.assertEqual(len(listens), 4)
        self.assertEqual(listens[0].played_at, make_played_at_dt(SAMPLE_TRACK_ITEM_EXISTING_LISTEN['played_at']))
        self.assertEqual(listens[1].played_at, make_played_at_dt(SAMPLE_EPISODE_ITEM_EXISTING_LISTEN['played_at']))
        self.assertEqual(listens[2].played_at, make_played_at_dt(SAMPLE_TRACK_ITEM_NEW['played_at']))
        self.assertEqual(listens[3].played_at, make_played_at_dt(SAMPLE_EPISODE_ITEM_NEW['played_at']))

        # Verify new max_played_at in DB
        new_max_played_at = get_max_played_at(self.session)
        self.assertEqual(new_max_played_at, make_played_at_dt(SAMPLE_EPISODE_ITEM_NEW['played_at']))


        # 3. Verify entities for NEW track item
        track_listen = self.session.query(Listen).filter_by(played_at=make_played_at_dt(SAMPLE_TRACK_ITEM_NEW['played_at'])).one()
        self.assertEqual(track_listen.item_type, 'track')
        self.assertEqual(track_listen.track_id, SAMPLE_TRACK_ITEM_NEW['track']['id'])
        self.assertIsNotNone(track_listen.artist_id)
        self.assertIsNotNone(track_listen.album_id)
        self.assertIsNone(track_listen.episode_id)

        artist = self.session.query(Artist).filter_by(artist_id=SAMPLE_TRACK_ITEM_NEW['track']['artists'][0]['id']).one_or_none()
        self.assertIsNotNone(artist)
        self.assertEqual(artist.name, SAMPLE_TRACK_ITEM_NEW['track']['artists'][0]['name'])

        album = self.session.query(Album).filter_by(album_id=SAMPLE_TRACK_ITEM_NEW['track']['album']['id']).one_or_none()
        self.assertIsNotNone(album)
        self.assertEqual(album.name, SAMPLE_TRACK_ITEM_NEW['track']['album']['name'])
        self.assertEqual(album.primary_artist_id, artist.artist_id)

        track = self.session.query(Track).filter_by(track_id=SAMPLE_TRACK_ITEM_NEW['track']['id']).one_or_none()
        self.assertIsNotNone(track)
        self.assertEqual(track.name, SAMPLE_TRACK_ITEM_NEW['track']['name'])
        self.assertEqual(track.album_id, album.album_id)


        # 4. Verify entities for NEW episode item
        episode_listen = self.session.query(Listen).filter_by(played_at=make_played_at_dt(SAMPLE_EPISODE_ITEM_NEW['played_at'])).one()
        self.assertEqual(episode_listen.item_type, 'episode')
        self.assertEqual(episode_listen.episode_id, SAMPLE_EPISODE_ITEM_NEW['track']['id'])
        self.assertIsNone(episode_listen.track_id)
        self.assertIsNone(episode_listen.artist_id)
        self.assertIsNone(episode_listen.album_id)

        series = self.session.query(PodcastSeries).filter_by(series_id=SAMPLE_EPISODE_ITEM_NEW['track']['show']['id']).one_or_none()
        self.assertIsNotNone(series)
        self.assertEqual(series.name, SAMPLE_EPISODE_ITEM_NEW['track']['show']['name'])
        self.assertEqual(series.publisher, SAMPLE_EPISODE_ITEM_NEW['track']['show']['publisher'])

        episode = self.session.query(PodcastEpisode).filter_by(episode_id=SAMPLE_EPISODE_ITEM_NEW['track']['id']).one_or_none()
        self.assertIsNotNone(episode)
        self.assertEqual(episode.name, SAMPLE_EPISODE_ITEM_NEW['track']['name'])
        self.assertEqual(episode.series_id, series.series_id)

        # 5. De-duplication test (implicit via count of listens and checking played_at times)
        # If we included existing items in mock_get_recently_played, we'd check that no *new* Listen rows were added for them.
        # Since we assume `after` works, this part is mostly covered by initial setup + new item checks.

        # Verify total counts of entities if desired (e.g. 2 artists, 2 albums, etc.)
        self.assertEqual(self.session.query(Artist).count(), 2) # existing_listen_artist + new_artist
        self.assertEqual(self.session.query(Album).count(), 2)
        self.assertEqual(self.session.query(Track).count(), 2)
        self.assertEqual(self.session.query(PodcastSeries).count(), 2)
        self.assertEqual(self.session.query(PodcastEpisode).count(), 2)


    @patch('backend.main.get_spotify_credentials')
    @patch('backend.main.SpotifyOAuthClient')
    @patch('backend.main.get_recently_played_tracks')
    def test_ingestion_only_existing_items_returned(
        self, mock_get_recently_played, mock_spotify_oauth_client, mock_get_creds
    ):
        # Scenario: Spotify API's `after` parameter didn't work as expected,
        # or we want to test the app's internal de-duplication of listens.
        mock_get_creds.return_value = ("id", "secret", "refresh")
        mock_spotify_oauth_client.return_value.get_access_token_from_refresh.return_value = "test_access_token"

        # Spotify returns items that are ALREADY in the database and match max_played_at or are older
        # These should be skipped by the `played_at_dt <= max_played_at_db` check or by `insert_listen` failing due to unique constraint
        mock_get_recently_played.return_value = {
            "items": [
                SAMPLE_EPISODE_ITEM_EXISTING_LISTEN, # played_at: 2023-02-01T11:00:00Z
                SAMPLE_TRACK_ITEM_EXISTING_LISTEN    # played_at: 2023-02-01T10:00:00Z
            ],
            "next": None
        }

        initial_listen_count = self.session.query(Listen).count()
        self.assertEqual(initial_listen_count, 2)

        with patch('backend.main.get_db_engine', return_value=self.engine):
             process_spotify_data()

        # Verify no new listens were added
        final_listen_count = self.session.query(Listen).count()
        self.assertEqual(final_listen_count, initial_listen_count)

        # Verify max_played_at hasn't changed
        final_max_played_at = get_max_played_at(self.session)
        self.assertEqual(final_max_played_at, self.initial_max_played_at)

        # Verify entities were not re-upserted in a way that changes them if DO NOTHING was effective
        # (counts should remain the same)
        self.assertEqual(self.session.query(Artist).count(), 1)
        self.assertEqual(self.session.query(Album).count(), 1)
        self.assertEqual(self.session.query(Track).count(), 1)
        self.assertEqual(self.session.query(PodcastSeries).count(), 1)
        self.assertEqual(self.session.query(PodcastEpisode).count(), 1)


if __name__ == '__main__':
    unittest.main()
