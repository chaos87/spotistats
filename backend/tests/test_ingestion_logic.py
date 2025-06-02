import unittest
import datetime
import logging
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.src.models import Base, Artist, Album, Track, Listen
from backend.src.database import (
    get_max_played_at, upsert_artist, upsert_album, upsert_track, insert_listen,
    get_session as get_real_session, # Keep real one for direct tests
    init_db
)
# Functions/classes to be mocked from main
# Assuming main.py is structured to allow these imports for mocking:
from backend.main import process_spotify_data
# If main.py imports get_recently_played_tracks from spotify_data, that's what we patch.
# For this example, let's assume it's backend.main.get_recently_played_tracks for simplicity of the mock target.

# Configure logging for tests to see output if needed
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Use an in-memory SQLite database for most tests, acknowledge limitations for ON CONFLICT
# For true PostgreSQL specific testing, a live test PG database would be needed.
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
# TEST_SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost:5432/test_db" # Example for PG

def make_dt(dt_str):
    return datetime.datetime.fromisoformat(dt_str.replace('Z', '+00:00'))

class TestIngestionLogic(unittest.TestCase):
    engine = None
    SessionLocal = None

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(TEST_SQLALCHEMY_DATABASE_URL)
        Base.metadata.create_all(cls.engine) # Create tables
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        logger.info(f"Test database tables created using engine: {cls.engine.url}")

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine) # Drop tables
        logger.info("Test database tables dropped.")

    def setUp(self):
        self.session = self.SessionLocal() # New session for each test
        # Clean out tables before each test to ensure isolation
        for table in reversed(Base.metadata.sorted_tables):
            self.session.execute(table.delete())
        self.session.commit()
        logger.debug("Database tables cleaned for new test.")


    def tearDown(self):
        self.session.rollback() # Rollback any uncommitted changes
        self.session.close()
        logger.debug("Test session closed and rolled back.")

    # 1. Test get_max_played_at
    def test_get_max_played_at_empty(self):
        max_played = get_max_played_at(self.session)
        self.assertIsNone(max_played)

    def test_get_max_played_at_populated(self):
        dt1 = make_dt("2023-01-01T10:00:00Z")
        dt2 = make_dt("2023-01-01T12:00:00Z")
        # Need dummy artist, album, track for Listen FKs
        artist = Artist(artist_id="art1", name="Test Artist")
        album = Album(album_id="alb1", name="Test Album", primary_artist_id="art1")
        track = Track(track_id="trk1", name="Test Track", album_id="alb1")
        self.session.add_all([artist, album, track])
        self.session.add(Listen(played_at=dt1, item_type="track", track_id="trk1", artist_id="art1", album_id="alb1"))
        self.session.add(Listen(played_at=dt2, item_type="track", track_id="trk1", artist_id="art1", album_id="alb1"))
        self.session.commit()

        max_played = get_max_played_at(self.session)
        self.assertEqual(max_played, dt2)

    # 2. Test UPSERT functions (basic check, full ON CONFLICT needs PG)
    def test_upsert_artist(self):
        artist_obj = Artist(artist_id="artist1", name="Original Name", genres=["rock"])
        # Insert
        result_dict = upsert_artist(self.session, artist_obj)
        self.session.commit() # Commit to make it queryable by next operations
        self.assertIsNotNone(result_dict)
        self.assertEqual(result_dict['name'], "Original Name")

        # Update
        artist_obj_updated = Artist(artist_id="artist1", name="Updated Name", genres=["pop", "rock"])
        result_dict_updated = upsert_artist(self.session, artist_obj_updated)
        self.session.commit()
        self.assertIsNotNone(result_dict_updated)
        self.assertEqual(result_dict_updated['name'], "Updated Name")
        # Note: SQLite won't do the update part of ON CONFLICT DO UPDATE. It will likely insert or ignore.
        # This test will behave differently on SQLite vs PostgreSQL.
        # On SQLite, this might result in two rows or an error depending on unique constraints if any.
        # The pg_insert().on_conflict_do_update() is PostgreSQL specific.
        # For SQLite, a true upsert needs a different approach (e.g. session.merge or query then update/insert)
        # Here, we are testing the function as written for PG.
        if self.engine.name == 'sqlite':
            logger.warning("SQLite does not fully support ON CONFLICT DO UPDATE. Test for upsert_artist may not be accurate for update behavior.")
            # Query to see what happened
            res = self.session.execute(text("SELECT * FROM artists WHERE artist_id='artist1'")).fetchall()
            self.assertEqual(len(res), 1) # Should still be one due to PK, but update might not happen via pg_insert
            # The actual name might be 'Original Name' on SQLite if the second insert was ignored.
        else: # Assuming PostgreSQL
             self.assertEqual(result_dict_updated['name'], "Updated Name")
             self.assertCountEqual(result_dict_updated['genres'], ["pop", "rock"])


    def test_upsert_album_and_track(self): # Simplified combined test for brevity
        # Album
        album_obj = Album(album_id="album1", name="Original Album", primary_artist_id="artist1") # Assume artist1 exists or FK is deferred
        res_album = upsert_album(self.session, album_obj)
        self.session.commit()
        self.assertEqual(res_album['name'], "Original Album")
        # Track
        track_obj = Track(track_id="track1", name="Original Track", album_id="album1", last_played_at=make_dt("2023-01-01T00:00:00Z"))
        res_track = upsert_track(self.session, track_obj)
        self.session.commit()
        self.assertEqual(res_track['name'], "Original Track")

        if self.engine.name == 'sqlite':
            logger.warning("SQLite does not fully support ON CONFLICT DO UPDATE for album/track tests.")


    # 3. Test insert_listen
    def test_insert_listen_successful(self):
        artist = Artist(artist_id="art_listen", name="Listen Artist")
        album = Album(album_id="alb_listen", name="Listen Album", primary_artist_id="art_listen")
        track = Track(track_id="trk_listen", name="Listen Track", album_id="alb_listen")
        self.session.add_all([artist, album, track])
        self.session.commit()

        listen_obj = Listen(
            played_at=make_dt("2023-02-01T10:00:00Z"),
            item_type="track",
            track_id="trk_listen",
            artist_id="art_listen",
            album_id="alb_listen"
        )
        result = insert_listen(self.session, listen_obj)
        self.session.commit() # Commit to save the listen
        self.assertIsNotNone(result)
        self.assertEqual(result.played_at, make_dt("2023-02-01T10:00:00Z"))

    def test_insert_listen_duplicate_played_at(self):
        # Pre-populate necessary entities
        artist = Artist(artist_id="art_dup", name="Dup Artist")
        album = Album(album_id="alb_dup", name="Dup Album", primary_artist_id="art_dup")
        track = Track(track_id="trk_dup", name="Dup Track", album_id="alb_dup")
        self.session.add_all([artist, album, track])

        # First listen
        dt_played = make_dt("2023-02-02T10:00:00Z")
        listen1 = Listen(played_at=dt_played, item_type="track", track_id="trk_dup", artist_id="art_dup", album_id="alb_dup")
        insert_listen(self.session, listen1)
        self.session.commit()

        # Attempt to insert duplicate
        listen2 = Listen(played_at=dt_played, item_type="track", track_id="trk_dup", artist_id="art_dup", album_id="alb_dup")
        result = insert_listen(self.session, listen2)
        # self.session.commit() # No commit needed as insert_listen should fail and return None
        self.assertIsNone(result)
        # Ensure session is still usable (no unhandled exception, rollback was handled by insert_listen or will be by main loop)
        self.session.rollback() # Important: insert_listen does not rollback, the caller (this test or main) should.


    # 4. Test main ingestion loop (process_spotify_data)
    @patch('backend.main.get_spotify_credentials') # Mock config dependency
    @patch('backend.main.SpotifyOAuthClient') # Mock client
    @patch('backend.main.get_recently_played_tracks') # Mock actual Spotify call
    @patch('backend.main.get_session') # Mock get_session to use our test session
    def test_process_spotify_data_flow(self, mock_get_session, mock_get_played, mock_spotify_client, mock_creds):
        # --- Setup Mocks ---
        mock_get_session.return_value = self.session # Critical: use the test session

        # Mock get_spotify_credentials
        mock_creds.return_value = ("test_id", "test_secret", "test_refresh")

        # Mock SpotifyOAuthClient instance and its method
        mock_client_instance = MagicMock()
        mock_client_instance.get_access_token_from_refresh.return_value = "mock_access_token"
        mock_spotify_client.return_value = mock_client_instance

        # Mock Spotify API response
        played_at_future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
        played_at_past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)

        mock_spotify_items = {
            "items": [
                { # New item
                    "track": {
                        "id": "new_track_1", "name": "New Track", "type": "track", "popularity": 70,
                        "artists": [{"id": "new_artist_1", "name": "New Artist", "external_urls": {"spotify":"new_artist_url"}}],
                        "album": {"id": "new_album_1", "name": "New Album", "images": [{"url": "new_img_url"}], "external_urls": {"spotify":"new_album_url"}, "release_date":"2024-01-01", "release_date_precision":"day"},
                        "duration_ms": 180000, "explicit": False, "external_urls": {"spotify":"new_track_url"}
                    },
                    "played_at": played_at_future.isoformat().replace('+00:00', 'Z')
                },
                { # Item that should be filtered by max_played_at
                    "track": {
                        "id": "old_track_1", "name": "Old Track", "type": "track",
                        "artists": [{"id": "old_artist_1", "name": "Old Artist", "external_urls": {"spotify":"old_artist_url"}}],
                        "album": {"id": "old_album_1", "name": "Old Album", "images": [{"url": "old_img_url"}], "external_urls": {"spotify":"old_album_url"}, "release_date":"2022-01-01", "release_date_precision":"day"},
                         "duration_ms": 180000, "explicit": False, "external_urls": {"spotify":"old_track_url"}
                    },
                    "played_at": played_at_past.isoformat().replace('+00:00', 'Z')
                }
            ]
        }
        mock_get_played.return_value = mock_spotify_items

        # --- Pre-populate DB with a listen to set max_played_at ---
        # This listen's played_at should be now, so played_at_past is filtered, played_at_future is processed.
        initial_played_at = datetime.datetime.now(datetime.timezone.utc)
        artist_initial = Artist(artist_id="initial_artist", name="Initial Artist")
        album_initial = Album(album_id="initial_album", name="Initial Album", primary_artist_id="initial_artist")
        track_initial = Track(track_id="initial_track", name="Initial Track", album_id="initial_album")
        listen_initial = Listen(played_at=initial_played_at, item_type="track", track_id="initial_track", artist_id="initial_artist", album_id="initial_album")
        self.session.add_all([artist_initial, album_initial, track_initial, listen_initial])
        self.session.commit()
        logger.info(f"Initial max_played_at set to: {initial_played_at}")

        # --- Execute ---
        process_spotify_data() # This will use the mocked session and Spotify calls

        # --- Assertions ---
        # Check that only the new listen was added
        listens_in_db = self.session.query(Listen).all()
        self.assertEqual(len(listens_in_db), 2) # Initial + 1 new track

        new_listen_entry = self.session.query(Listen).filter(Listen.track_id == "new_track_1").one_or_none()
        self.assertIsNotNone(new_listen_entry)
        # Python datetime comparison can be tricky with microseconds, ensure they match closely
        self.assertAlmostEqual(new_listen_entry.played_at, played_at_future, delta=datetime.timedelta(seconds=1))

        # Check that artist, album, track for the new item were created
        self.assertIsNotNone(self.session.query(Artist).filter(Artist.artist_id == "new_artist_1").one_or_none())
        self.assertIsNotNone(self.session.query(Album).filter(Album.album_id == "new_album_1").one_or_none())
        self.assertIsNotNone(self.session.query(Track).filter(Track.track_id == "new_track_1").one_or_none())

        # Verify old track was not processed
        old_listen_entry = self.session.query(Listen).filter(Listen.track_id == "old_track_1").one_or_none()
        self.assertIsNone(old_listen_entry)

        # Ensure commit was called on the session by process_spotify_data (indirectly via checking data)
        # And rollback wasn't called unless an error (which we don't expect here)
        # Hard to directly check commit call without more complex session mocking. Data presence is good proxy.


if __name__ == '__main__': # pragma: no cover
    unittest.main()
