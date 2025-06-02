import unittest
import datetime
import logging
from unittest.mock import patch, MagicMock, call # Ensure 'call' is imported
import pytest # For pytest.fail if needed in side_effect

from sqlalchemy import create_engine, text, JSON, TEXT
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from backend.src.models import Base, Artist, Album, Track, Listen, RecentlyPlayedTracksRaw
# Import for mocking normalizer
from backend.src.normalizer import SpotifyMusicNormalizer as RealNormalizer

from backend.src.database import (
    get_max_played_at as real_get_max_played_at,
    upsert_artist, upsert_album, upsert_track,
    insert_listen as real_insert_listen,
    init_db
)
from backend.main import process_spotify_data

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

def make_dt(dt_str: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(dt_str.replace('Z', '+00:00'))

class TestIngestionLogic(unittest.TestCase):
    engine = None
    SessionLocal = None

    original_artist_genres_type = None
    original_track_markets_type = None
    original_raw_data_type = None

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(TEST_SQLALCHEMY_DATABASE_URL)

        cls.original_artist_genres_type = Artist.genres.property.columns[0].type
        cls.original_track_markets_type = Track.available_markets.property.columns[0].type
        cls.original_raw_data_type = RecentlyPlayedTracksRaw.data.property.columns[0].type

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

        if cls.original_artist_genres_type is not None:
            Artist.genres.property.columns[0].type = cls.original_artist_genres_type
        if cls.original_track_markets_type is not None:
            Track.available_markets.property.columns[0].type = cls.original_track_markets_type
        if cls.original_raw_data_type is not None:
            RecentlyPlayedTracksRaw.data.property.columns[0].type = cls.original_raw_data_type
        logger.info("Original model types restored.")

    def setUp(self):
        self.session = self.SessionLocal()
        for table in reversed(Base.metadata.sorted_tables):
            self.session.execute(table.delete())
        self.session.commit()
        logger.debug("Database tables cleaned for new test.")

    def tearDown(self):
        self.session.rollback()
        self.session.close()
        logger.debug("Test session closed and rolled back.")

    def test_get_max_played_at_empty(self):
        max_played = real_get_max_played_at(self.session)
        self.assertIsNone(max_played)

    def test_get_max_played_at_populated(self):
        dt1_str = "2023-01-01T10:00:00Z"
        dt2_str = "2023-01-01T12:00:00Z"

        dt1 = make_dt(dt1_str)
        dt2_expected = make_dt(dt2_str)

        artist = Artist(artist_id="art1", name="Test Artist", genres=["test"])
        album = Album(album_id="alb1", name="Test Album", primary_artist_id="art1")
        track = Track(track_id="trk1", name="Test Track", album_id="alb1", available_markets=["US"])
        self.session.add_all([artist, album, track])
        self.session.commit()

        self.session.add(Listen(played_at=dt1, item_type="track", track_id="trk1", artist_id="art1", album_id="alb1"))
        self.session.add(Listen(played_at=dt2_expected, item_type="track", track_id="trk1", artist_id="art1", album_id="alb1"))
        self.session.commit()

        max_played_from_db = real_get_max_played_at(self.session)

        if max_played_from_db and max_played_from_db.tzinfo is None:
            logger.debug(f"Max played_at from DB was naive: {max_played_from_db}, making it UTC aware.")
            max_played_from_db = max_played_from_db.replace(tzinfo=datetime.timezone.utc)

        self.assertEqual(max_played_from_db, dt2_expected)


    def test_insert_listen_successful(self):
        artist = Artist(artist_id="art_listen", name="Listen Artist", genres=[])
        album = Album(album_id="alb_listen", name="Listen Album", primary_artist_id="art_listen")
        track = Track(track_id="trk_listen", name="Listen Track", album_id="alb_listen", available_markets=[])
        self.session.add_all([artist, album, track])
        self.session.commit()

        expected_played_at_dt = datetime.datetime(2023, 2, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)
        listen_obj = Listen(
            played_at=expected_played_at_dt,
            item_type="track",
            track_id="trk_listen",
            artist_id="art_listen",
            album_id="alb_listen"
        )
        inserted_listen_result = real_insert_listen(self.session, listen_obj)
        self.session.commit()

        self.assertIsNotNone(inserted_listen_result)

        actual_played_at_from_db = inserted_listen_result.played_at
        if actual_played_at_from_db and actual_played_at_from_db.tzinfo is None:
            logger.debug(f"Inserted listen played_at from DB was naive: {actual_played_at_from_db}, making it UTC aware.")
            actual_played_at_from_db = actual_played_at_from_db.replace(tzinfo=datetime.timezone.utc)

        self.assertEqual(actual_played_at_from_db, expected_played_at_dt)

    @patch('backend.main.get_spotify_credentials')
    @patch('backend.main.SpotifyOAuthClient')
    @patch('backend.main.get_recently_played_tracks')
    @patch('backend.main.get_session')
    @patch('backend.main.get_max_played_at')
    @patch('backend.main.SpotifyMusicNormalizer')
    @patch('backend.main.insert_listen')
    @patch('backend.main.upsert_artist')
    @patch('backend.main.upsert_album')
    @patch('backend.main.upsert_track')
    def test_process_spotify_data_flow_logic(
        self, mock_upsert_track, mock_upsert_album, mock_upsert_artist,
        mock_insert_listen, mock_normalizer_class, mock_get_max_played_at,
        mock_get_session, mock_get_played_tracks, mock_spotify_client, mock_creds):

        mock_get_session.return_value = self.session
        mock_creds.return_value = ("test_id", "test_secret", "test_refresh")
        mock_client_instance = MagicMock()
        mock_client_instance.get_access_token_from_refresh.return_value = "mock_access_token"
        mock_spotify_client.return_value = mock_client_instance

        max_played_at_val = datetime.datetime(2023, 1, 10, 0, 0, 0, tzinfo=datetime.timezone.utc)
        mock_get_max_played_at.return_value = max_played_at_val

        # Define unique track IDs
        item_good_1_track_id = "test_track_good_1_flow_logic"
        item_good_2_track_id = "test_track_good_2_flow_logic"
        item_normalize_fail_track_id = "test_track_norm_fail_flow_logic"

        # Pre-define mock ORM objects that normalizer will return
        artist_mock_1 = MagicMock(spec=Artist, name="Artist1_FlowLogic")
        album_mock_1 = MagicMock(spec=Album, name="Album1_FlowLogic")
        track_mock_1 = MagicMock(spec=Track, name="Track1_FlowLogic", id=item_good_1_track_id) # Ensure ID matches
        listen_obj_for_good_item_1 = MagicMock(spec=Listen, name="ListenForGoodItem1_FlowLogic")

        artist_mock_2 = MagicMock(spec=Artist, name="Artist2_FlowLogic")
        album_mock_2 = MagicMock(spec=Album, name="Album2_FlowLogic")
        track_mock_2 = MagicMock(spec=Track, name="Track2_FlowLogic", id=item_good_2_track_id) # Ensure ID matches
        listen_obj_for_good_item_2 = MagicMock(spec=Listen, name="ListenForGoodItem2_FlowLogic")

        # Mock Spotify items using these unique track IDs
        item_normalize_fail = {"track": {"id": item_normalize_fail_track_id, "type": "track", "name":"NormFail"}, "played_at": (max_played_at_val + datetime.timedelta(hours=4)).isoformat().replace('+00:00', 'Z')}
        item_episode = {"track": {"id": "ep1", "type": "episode", "name":"Podcast"}, "played_at": (max_played_at_val + datetime.timedelta(hours=3)).isoformat().replace('+00:00', 'Z')}
        item_good_2 = {"track": {"id": item_good_2_track_id, "type": "track", "name":"Good2"}, "played_at": (max_played_at_val + datetime.timedelta(hours=2)).isoformat().replace('+00:00', 'Z')}
        item_good_1 = {"track": {"id": item_good_1_track_id, "type": "track", "name":"Good1"}, "played_at": (max_played_at_val + datetime.timedelta(hours=1)).isoformat().replace('+00:00', 'Z')}
        item_old = {"track": {"id": "old_track", "type": "track", "name":"Oldie"}, "played_at": (max_played_at_val - datetime.timedelta(days=1)).isoformat().replace('+00:00', 'Z')}

        spotify_api_items_list = [item_normalize_fail, item_episode, item_good_2, item_good_1, item_old]
        mock_get_played_tracks.return_value = {"items": spotify_api_items_list}

        mock_normalizer_instance = MagicMock(spec=RealNormalizer)
        def custom_normalize_side_effect(spotify_item, played_at_dt):
            track_id = spotify_item.get('track', {}).get('id')
            if not played_at_dt.tzinfo:
                logger.error("Normalizer mock received naive datetime!")
                played_at_dt = played_at_dt.replace(tzinfo=datetime.timezone.utc)

            if track_id == item_good_1_track_id:
                return (artist_mock_1, album_mock_1, track_mock_1, listen_obj_for_good_item_1)
            elif track_id == item_good_2_track_id:
                return (artist_mock_2, album_mock_2, track_mock_2, listen_obj_for_good_item_2)
            elif track_id == item_normalize_fail_track_id:
                return None
            # Fallback for other items like 'old_track' or 'ep1' if they somehow reach normalizer
            # and were not filtered out by earlier checks in process_spotify_data
            logger.warning(f"custom_normalize_side_effect called with unexpected track_id: {track_id}")
            return (MagicMock(spec=Artist), MagicMock(spec=Album), MagicMock(spec=Track), MagicMock(spec=Listen))

        mock_normalizer_instance.normalize_track_item.side_effect = custom_normalize_side_effect
        mock_normalizer_class.return_value = mock_normalizer_instance

        mock_upsert_artist.return_value = {"artist_id": "mock_artist_id"}
        mock_upsert_album.return_value = {"album_id": "mock_album_id"}
        mock_upsert_track.return_value = {"track_id": "mock_track_id"}

        mock_insert_listen.return_value = MagicMock(spec=Listen)

        process_spotify_data()

        expected_after_param = int(max_played_at_val.timestamp() * 1000)
        mock_get_played_tracks.assert_called_once_with("mock_access_token", limit=50, after=expected_after_param)

        self.assertEqual(mock_insert_listen.call_count, 2)

        calls_to_normalizer = [
            call(item_good_1, make_dt(item_good_1['played_at'])),
            call(item_good_2, make_dt(item_good_2['played_at'])),
            call(item_normalize_fail, make_dt(item_normalize_fail['played_at']))
        ]
        mock_normalizer_instance.normalize_track_item.assert_has_calls(calls_to_normalizer, any_order=False)
        self.assertEqual(mock_normalizer_instance.normalize_track_item.call_count, 3)

        expected_insert_listen_calls = [
            call(self.session, listen_obj_for_good_item_1),
            call(self.session, listen_obj_for_good_item_2)
        ]
        mock_insert_listen.assert_has_calls(expected_insert_listen_calls, any_order=False)

        self.assertEqual(mock_upsert_artist.call_count, 2)
        self.assertEqual(mock_upsert_album.call_count, 2)
        self.assertEqual(mock_upsert_track.call_count, 2)

    def test_upsert_artist(self):
        artist_obj = Artist(artist_id="artist1", name="Original Name", genres=["rock"])
        result_dict = upsert_artist(self.session, artist_obj)
        self.session.commit()
        self.assertIsNotNone(result_dict)
        self.assertEqual(result_dict['name'], "Original Name")
        self.assertEqual(result_dict['genres'], ["rock"])

        artist_obj_updated = Artist(artist_id="artist1", name="Updated Name", genres=["pop", "rock"])
        result_dict_updated = upsert_artist(self.session, artist_obj_updated)
        self.session.commit()
        self.assertIsNotNone(result_dict_updated)

        if self.engine.name == 'sqlite':
            logger.warning("SQLite ON CONFLICT DO UPDATE test: Name update might not reflect if insert was ignored.")
            db_artist = self.session.query(Artist).filter_by(artist_id="artist1").one_or_none()
            self.assertIsNotNone(db_artist)
            self.assertEqual(result_dict_updated['name'], "Updated Name")
            self.assertCountEqual(result_dict_updated['genres'], ["pop", "rock"])
        else:
             self.assertEqual(result_dict_updated['name'], "Updated Name")
             self.assertCountEqual(result_dict_updated['genres'], ["pop", "rock"])

    def test_insert_listen_duplicate_played_at(self):
        artist = Artist(artist_id="art_dup", name="Dup Artist", genres=[])
        album = Album(album_id="alb_dup", name="Dup Album", primary_artist_id="art_dup")
        track = Track(track_id="trk_dup", name="Dup Track", album_id="alb_dup", available_markets=[])
        self.session.add_all([artist, album, track])
        self.session.commit()

        dt_played = make_dt("2023-02-02T10:00:00Z")
        listen1 = Listen(played_at=dt_played, item_type="track", track_id="trk_dup", artist_id="art_dup", album_id="alb_dup")
        real_insert_listen(self.session, listen1)
        self.session.commit()

        listen2 = Listen(played_at=dt_played, item_type="track", track_id="trk_dup", artist_id="art_dup", album_id="alb_dup")
        result = real_insert_listen(self.session, listen2)
        self.assertIsNone(result)
        self.session.rollback()

if __name__ == '__main__': # pragma: no cover
    unittest.main()
