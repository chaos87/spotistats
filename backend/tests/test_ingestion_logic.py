import unittest
import datetime
import logging
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, text, JSON, TEXT # Ensure JSON, TEXT are imported
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import ARRAY, JSONB # Import ARRAY and JSONB

from backend.src.models import Base, Artist, Album, Track, Listen, RecentlyPlayedTracksRaw # Import RecentlyPlayedTracksRaw
from backend.src.database import (
    get_max_played_at, upsert_artist, upsert_album, upsert_track, insert_listen,
    get_session as get_real_session,
    init_db
)
from backend.main import process_spotify_data

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

def make_dt(dt_str):
    return datetime.datetime.fromisoformat(dt_str.replace('Z', '+00:00'))

class TestIngestionLogic(unittest.TestCase):
    engine = None
    SessionLocal = None # This will be the sessionmaker class

    # Class-level storage for original types
    original_artist_genres_type = None
    original_track_markets_type = None
    original_raw_data_type = None

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(TEST_SQLALCHEMY_DATABASE_URL)

        # Store original types before any modification
        cls.original_artist_genres_type = Artist.genres.property.columns[0].type
        cls.original_track_markets_type = Track.available_markets.property.columns[0].type
        cls.original_raw_data_type = RecentlyPlayedTracksRaw.data.property.columns[0].type

        # Temporarily change types for SQLite compatibility
        Artist.genres.property.columns[0].type = JSON()
        Track.available_markets.property.columns[0].type = JSON()
        RecentlyPlayedTracksRaw.data.property.columns[0].type = JSON()

        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        logger.info(f"Test database tables created using engine: {cls.engine.url}")

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine)
        logger.info("Test database tables dropped.")

        # Restore original types
        if cls.original_artist_genres_type is not None:
            Artist.genres.property.columns[0].type = cls.original_artist_genres_type
        if cls.original_track_markets_type is not None:
            Track.available_markets.property.columns[0].type = cls.original_track_markets_type
        if cls.original_raw_data_type is not None:
            RecentlyPlayedTracksRaw.data.property.columns[0].type = cls.original_raw_data_type
        logger.info("Original model types restored.")


    def setUp(self):
        # self.session is created per test method
        self.session = self.SessionLocal()
        # Clean out tables before each test to ensure isolation
        for table in reversed(Base.metadata.sorted_tables):
            self.session.execute(table.delete())
        self.session.commit()
        logger.debug("Database tables cleaned for new test.")


    def tearDown(self):
        self.session.rollback()
        self.session.close()
        logger.debug("Test session closed and rolled back.")

    # 1. Test get_max_played_at
    def test_get_max_played_at_empty(self):
        max_played = get_max_played_at(self.session)
        self.assertIsNone(max_played)

    def test_get_max_played_at_populated(self):
        dt1 = make_dt("2023-01-01T10:00:00Z")
        dt2 = make_dt("2023-01-01T12:00:00Z")
        artist = Artist(artist_id="art1", name="Test Artist", genres=["test"]) # genres as list for JSON
        album = Album(album_id="alb1", name="Test Album", primary_artist_id="art1")
        track = Track(track_id="trk1", name="Test Track", album_id="alb1", available_markets=["US"]) # markets as list
        self.session.add_all([artist, album, track])
        # Must commit artist, album, track before Listen due to FKs
        self.session.commit()

        self.session.add(Listen(played_at=dt1, item_type="track", track_id="trk1", artist_id="art1", album_id="alb1"))
        self.session.add(Listen(played_at=dt2, item_type="track", track_id="trk1", artist_id="art1", album_id="alb1"))
        self.session.commit()

        max_played = get_max_played_at(self.session)
        self.assertEqual(max_played, dt2)

    # 2. Test UPSERT functions
    def test_upsert_artist(self):
        artist_obj = Artist(artist_id="artist1", name="Original Name", genres=["rock"])
        result_dict = upsert_artist(self.session, artist_obj)
        self.session.commit()
        self.assertIsNotNone(result_dict)
        self.assertEqual(result_dict['name'], "Original Name")
        # For JSON type in SQLite, list is stored and retrieved as list
        self.assertEqual(result_dict['genres'], ["rock"])

        artist_obj_updated = Artist(artist_id="artist1", name="Updated Name", genres=["pop", "rock"])
        result_dict_updated = upsert_artist(self.session, artist_obj_updated)
        self.session.commit()
        self.assertIsNotNone(result_dict_updated)

        if self.engine.name == 'sqlite':
            logger.warning("SQLite ON CONFLICT DO UPDATE test: Name update might not reflect if insert was ignored.")
            # With PK conflict, SQLite usually ignores. Let's check what's there.
            # The pg_insert().on_conflict_do_update() is PG specific.
            # If the second insert is ignored due to PK, the name would be "Original Name".
            # If we were doing a manual SELECT then UPDATE/INSERT, behavior would be different.
            # Current test checks the returned dict from upsert_artist which is based on RETURNING clause.
            # On SQLite, the RETURNING clause of pg_insert might not behave as on PG after a conflict.
            # It's possible result_dict_updated is None or reflects the original insert on SQLite.
            # For this test, we rely on the fact that a row with "artist1" exists.
            # A more robust SQLite check would be to query after commit.
            db_artist = self.session.query(Artist).filter_by(artist_id="artist1").one_or_none()
            self.assertIsNotNone(db_artist)
            # Depending on SQLite's handling of pg_insert's ON CONFLICT, name could be original or updated.
            # The RETURNING clause might give what *would* be inserted/updated.
            # Let's assume for this test, if it returns, the values are what pg_insert intended.
            self.assertEqual(result_dict_updated['name'], "Updated Name")
            self.assertCountEqual(result_dict_updated['genres'], ["pop", "rock"])
        else: # Assuming PostgreSQL
             self.assertEqual(result_dict_updated['name'], "Updated Name")
             self.assertCountEqual(result_dict_updated['genres'], ["pop", "rock"])


    def test_upsert_album_and_track(self):
        # Artist needed for FK if primary_artist_id is enforced early (not an issue for SQLite with JSON types)
        artist_for_album = Artist(artist_id="artist_for_album", name="Art for Alb", genres=["test"])
        self.session.add(artist_for_album)
        self.session.commit()

        album_obj = Album(album_id="album1", name="Original Album", primary_artist_id=artist_for_album.artist_id)
        res_album = upsert_album(self.session, album_obj)
        self.session.commit()
        self.assertIsNotNone(res_album)
        self.assertEqual(res_album['name'], "Original Album")

        track_obj = Track(track_id="track1", name="Original Track", album_id="album1", available_markets=["US", "DE"], last_played_at=make_dt("2023-01-01T00:00:00Z"))
        res_track = upsert_track(self.session, track_obj)
        self.session.commit()
        self.assertIsNotNone(res_track)
        self.assertEqual(res_track['name'], "Original Track")
        self.assertEqual(res_track['available_markets'], ["US", "DE"])

        if self.engine.name == 'sqlite':
            logger.warning("SQLite ON CONFLICT DO UPDATE for album/track: update behavior might differ.")


    # 3. Test insert_listen
    def test_insert_listen_successful(self):
        artist = Artist(artist_id="art_listen", name="Listen Artist", genres=[])
        album = Album(album_id="alb_listen", name="Listen Album", primary_artist_id="art_listen")
        track = Track(track_id="trk_listen", name="Listen Track", album_id="alb_listen", available_markets=[])
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
        self.session.commit()
        self.assertIsNotNone(result)
        self.assertEqual(result.played_at, make_dt("2023-02-01T10:00:00Z"))

    def test_insert_listen_duplicate_played_at(self):
        artist = Artist(artist_id="art_dup", name="Dup Artist", genres=[])
        album = Album(album_id="alb_dup", name="Dup Album", primary_artist_id="art_dup")
        track = Track(track_id="trk_dup", name="Dup Track", album_id="alb_dup", available_markets=[])
        self.session.add_all([artist, album, track])
        self.session.commit()

        dt_played = make_dt("2023-02-02T10:00:00Z")
        listen1 = Listen(played_at=dt_played, item_type="track", track_id="trk_dup", artist_id="art_dup", album_id="alb_dup")
        insert_listen(self.session, listen1)
        self.session.commit()

        listen2 = Listen(played_at=dt_played, item_type="track", track_id="trk_dup", artist_id="art_dup", album_id="alb_dup")
        result = insert_listen(self.session, listen2) # This should return None due to duplicate played_at
        self.assertIsNone(result)
        self.session.rollback()


    # 4. Test main ingestion loop (process_spotify_data)
    @patch('backend.main.get_spotify_credentials')
    @patch('backend.main.SpotifyOAuthClient')
    @patch('backend.main.get_recently_played_tracks')
    @patch('backend.main.get_session')
    def test_process_spotify_data_flow(self, mock_get_session, mock_get_played, mock_spotify_client, mock_creds):
        mock_get_session.return_value = self.session
        mock_creds.return_value = ("test_id", "test_secret", "test_refresh")
        mock_client_instance = MagicMock()
        mock_client_instance.get_access_token_from_refresh.return_value = "mock_access_token"
        mock_spotify_client.return_value = mock_client_instance

        played_at_future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
        played_at_past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)

        mock_spotify_items = {
            "items": [
                {
                    "track": {
                        "id": "new_track_1", "name": "New Track", "type": "track", "popularity": 70,
                        "artists": [{"id": "new_artist_1", "name": "New Artist", "external_urls": {"spotify":"new_artist_url"}, "genres": ["new wave", "synthpop"]}],
                        "album": {"id": "new_album_1", "name": "New Album", "images": [{"url": "new_img_url"}], "external_urls": {"spotify":"new_album_url"}, "release_date":"2024-01-01", "release_date_precision":"day"},
                        "duration_ms": 180000, "explicit": False, "external_urls": {"spotify":"new_track_url"}, "available_markets": ["US", "GB"]
                    },
                    "played_at": played_at_future.isoformat().replace('+00:00', 'Z')
                },
                {
                    "track": {
                        "id": "old_track_1", "name": "Old Track", "type": "track",
                        "artists": [{"id": "old_artist_1", "name": "Old Artist", "external_urls": {"spotify":"old_artist_url"}}], # No genres
                        "album": {"id": "old_album_1", "name": "Old Album", "images": [{"url": "old_img_url"}], "external_urls": {"spotify":"old_album_url"}, "release_date":"2022-01-01", "release_date_precision":"day"},
                         "duration_ms": 180000, "explicit": False, "external_urls": {"spotify":"old_track_url"} # No markets
                    },
                    "played_at": played_at_past.isoformat().replace('+00:00', 'Z')
                }
            ]
        }
        mock_get_played.return_value = mock_spotify_items

        initial_played_at = datetime.datetime.now(datetime.timezone.utc)
        # Ensure initial data uses list for genres/markets for JSON compatibility
        artist_initial = Artist(artist_id="initial_artist", name="Initial Artist", genres=[])
        album_initial = Album(album_id="initial_album", name="Initial Album", primary_artist_id="initial_artist")
        track_initial = Track(track_id="initial_track", name="Initial Track", album_id="initial_album", available_markets=[])
        listen_initial = Listen(played_at=initial_played_at, item_type="track", track_id="initial_track", artist_id="initial_artist", album_id="initial_album")
        self.session.add_all([artist_initial, album_initial, track_initial, listen_initial])
        self.session.commit()
        logger.info(f"Initial max_played_at set to: {initial_played_at}")

        process_spotify_data()

        listens_in_db = self.session.query(Listen).all()
        self.assertEqual(len(listens_in_db), 2)

        new_listen_entry = self.session.query(Listen).filter(Listen.track_id == "new_track_1").one_or_none()
        self.assertIsNotNone(new_listen_entry)
        self.assertAlmostEqual(new_listen_entry.played_at, played_at_future, delta=datetime.timedelta(seconds=1))

        db_artist = self.session.query(Artist).filter(Artist.artist_id == "new_artist_1").one_or_none()
        self.assertIsNotNone(db_artist)
        self.assertEqual(db_artist.genres, ["new wave", "synthpop"]) # Check JSON stored list

        db_track = self.session.query(Track).filter(Track.track_id == "new_track_1").one_or_none()
        self.assertIsNotNone(db_track)
        self.assertEqual(db_track.available_markets, ["US", "GB"]) # Check JSON stored list

        old_listen_entry = self.session.query(Listen).filter(Listen.track_id == "old_track_1").one_or_none()
        self.assertIsNone(old_listen_entry)


if __name__ == '__main__': # pragma: no cover
    unittest.main()
