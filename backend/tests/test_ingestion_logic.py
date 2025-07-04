import os # Added import os
import unittest
import json # Added for conditional parsing in tests
import datetime
import logging
from unittest.mock import patch, MagicMock, call # Ensure 'call' is imported
import pytest # For pytest.fail if needed in side_effect

from sqlalchemy import create_engine, text, JSON, TEXT
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from backend.src.models import Base, Artist, Album, Track, Listen, RecentlyPlayedTracksRaw, PodcastSeries, PodcastEpisode
# Import for mocking normalizer
from backend.src.normalizer import SpotifyItemNormalizer as RealNormalizer

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
    @patch('backend.main.SpotifyItemNormalizer')
    @patch('backend.main.insert_listen')
    @patch('backend.main.upsert_artist')
    @patch('backend.main.upsert_album')
    @patch('backend.main.upsert_track')
    @patch.dict(os.environ, {"DATABASE_URL": TEST_SQLALCHEMY_DATABASE_URL, "LOG_LEVEL": "DEBUG"}) # Added to provide DATABASE_URL
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
        # The normalize_item method now returns a dictionary.
        # The side_effect needs to be updated to reflect this.
        # It also now handles item_type internally.
        def custom_normalize_side_effect(spotify_item):
            track_id = spotify_item.get('track', {}).get('id')
            item_type = spotify_item.get('track', {}).get('type', 'unknown') # Get type from item

            if item_type == 'episode': # Handle episode type
                 # For episodes, the normalizer returns a dict with 'type', 'series', 'episode', 'listen'
                mock_series = MagicMock(spec=PodcastSeries)
                mock_series.series_id = "mock_series_id_ep1"
                mock_series.name = "Mock Series For Episode"
                mock_series.publisher = "Mock Publisher"
                mock_series.description = "Mock Series Description"
                mock_series.image_url = "http://example.com/mock_series.png"
                mock_series.spotify_url = "http://spotify.com/series/mock_series_id_ep1"

                mock_episode = MagicMock(spec=PodcastEpisode)
                mock_episode.episode_id = "mock_episode_id_ep1"
                mock_episode.name = "Mock Episode ep1"
                mock_episode.description = "Mock Episode Description"
                mock_episode.duration_ms = 1800000
                mock_episode.explicit = False
                mock_episode.release_date = datetime.date(2023, 1, 10)
                mock_episode.spotify_url = "http://spotify.com/episode/mock_episode_id_ep1"
                mock_episode.series_id = "mock_series_id_ep1"

                mock_listen_episode = MagicMock(spec=Listen)
                mock_listen_episode.episode_id = "mock_episode_id_ep1"
                # Ensure other FKs are None for episode listen
                mock_listen_episode.track_id = None
                mock_listen_episode.artist_id = None
                mock_listen_episode.album_id = None
                return {
                    'type': 'episode',
                    'series': mock_series,
                    'episode': mock_episode,
                    'listen': mock_listen_episode
                }

            # Existing track logic
            if track_id == item_good_1_track_id:
                return {
                    'type': 'track', 'artist': artist_mock_1, 'album': album_mock_1,
                    'track': track_mock_1, 'listen': listen_obj_for_good_item_1
                }
            elif track_id == item_good_2_track_id:
                return {
                    'type': 'track', 'artist': artist_mock_2, 'album': album_mock_2,
                    'track': track_mock_2, 'listen': listen_obj_for_good_item_2
                }
            elif track_id == item_normalize_fail_track_id:
                return None # Normalization failure

            logger.warning(f"custom_normalize_side_effect called with unhandled track_id or type: {track_id}, type: {item_type}")
            return None # Default to None for unhandled cases to avoid downstream errors

        mock_normalizer_instance.normalize_item.side_effect = custom_normalize_side_effect
        mock_normalizer_class.return_value = mock_normalizer_instance

        mock_upsert_artist.return_value = {"artist_id": "mock_artist_id"}
        mock_upsert_album.return_value = {"album_id": "mock_album_id"}
        mock_upsert_track.return_value = {"track_id": "mock_track_id"}

        mock_insert_listen.return_value = MagicMock(spec=Listen)

        process_spotify_data()

        expected_after_param = int(max_played_at_val.timestamp() * 1000)
        mock_get_played_tracks.assert_called_once_with("mock_access_token", limit=50, after=expected_after_param)

        # mock_insert_listen should still be called twice (for item_good_1 and item_good_2)
        # item_episode will also result in a listen if handled correctly by new logic
        # The custom_normalize_side_effect for episodes returns a mock listen object.
        # So, 2 tracks + 1 episode = 3 listens
        self.assertEqual(mock_insert_listen.call_count, 3)


        # The items passed to normalizer are now just the spotify_item
        calls_to_normalizer = [
            call(item_good_1), # Oldest among the new ones after reverse
            call(item_good_2),
            call(item_episode),
            call(item_normalize_fail) # Newest, processed first in original loop, last after reverse
        ]
        # The loop in process_spotify_data is reversed.
        # Spotify returns newest first: [item_normalize_fail, item_episode, item_good_2, item_good_1, item_old]
        # Reversed loop processes: [item_old, item_good_1, item_good_2, item_episode, item_normalize_fail]
        # Filtered by played_at: [item_good_1, item_good_2, item_episode, item_normalize_fail]

        # Expected calls to normalize_item based on processing order (oldest of the new items first)
        expected_normalize_calls_in_order = [
            call(item_good_1),
            call(item_good_2),
            call(item_episode), # This is now processed as it's newer than max_played_at_val
            call(item_normalize_fail)
        ]
        mock_normalizer_instance.normalize_item.assert_has_calls(expected_normalize_calls_in_order, any_order=False)
        # Total calls: item_good_1, item_good_2, item_episode, item_normalize_fail = 4
        self.assertEqual(mock_normalizer_instance.normalize_item.call_count, 4)


        # Check calls to insert_listen
        # Listen object for item_episode is a generic MagicMock from the side_effect
        # We need to find it in the calls to mock_insert_listen
        actual_listen_calls = mock_insert_listen.call_args_list
        self.assertIn(call(self.session, listen_obj_for_good_item_1), actual_listen_calls)
        self.assertIn(call(self.session, listen_obj_for_good_item_2), actual_listen_calls)
        # For the episode, the listen object is a generic MagicMock.
        # We can check if a third listen call was made with a MagicMock.
        # This is a bit less precise but reflects the current mock setup.
        found_episode_listen_call = False
        for actual_call in actual_listen_calls:
            args, _ = actual_call
            if args[1] not in [listen_obj_for_good_item_1, listen_obj_for_good_item_2]:
                found_episode_listen_call = True
                break
        self.assertTrue(found_episode_listen_call, "insert_listen was not called for the episode item")


        self.assertEqual(mock_upsert_artist.call_count, 2) # Only for the two good track items
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

    def test_upsert_track_last_played_at_logic(self):
        # Setup: Insert an initial Artist and Album
        initial_artist = Artist(artist_id="test_artist_lpa", name="Test Artist LPA", genres=["test"])
        self.session.add(initial_artist)
        initial_album = Album(album_id="test_album_lpa", name="Test Album LPA", primary_artist_id="test_artist_lpa")
        self.session.add(initial_album)
        self.session.commit()

        track_id = "test_track_lpa_1"
        initial_played_at_str = "2023-01-01T10:00:00Z"
        initial_played_at_dt = make_dt(initial_played_at_str)

        # Initial Track object
        initial_track_obj = Track(
            track_id=track_id,
            name="Test Track Initial LPA",
            album_id="test_album_lpa",
            last_played_at=initial_played_at_dt,
            available_markets=["US"],
            duration_ms=180000,
            explicit=False,
            popularity=50,
            preview_url="http://example.com/preview_initial.mp3",
            spotify_url="http://example.com/track_initial"
        )
        # Call upsert_track to insert this initial track
        returned_track_dict = upsert_track(self.session, initial_track_obj)
        self.session.commit()

        # Verify initial insertion
        self.assertIsNotNone(returned_track_dict)
        self.assertEqual(returned_track_dict["track_id"], track_id)
        # For SQLite, datetime might come back as string if not handled by type decorator,
        # or naive if handled by SQLAlchemy's default. make_dt ensures timezone awareness.
        returned_lpa = make_dt(str(returned_track_dict["last_played_at"])) if isinstance(returned_track_dict["last_played_at"], str) else returned_track_dict["last_played_at"]
        if returned_lpa.tzinfo is None: # Ensure timezone for comparison
            returned_lpa = returned_lpa.replace(tzinfo=datetime.timezone.utc)
        self.assertEqual(returned_lpa, initial_played_at_dt)

        db_track = self.session.query(Track).filter_by(track_id=track_id).one()
        db_lpa = db_track.last_played_at
        if db_lpa.tzinfo is None: db_lpa = db_lpa.replace(tzinfo=datetime.timezone.utc) # Ensure timezone
        self.assertEqual(db_lpa, initial_played_at_dt)

        # Scenario 1: Update with more recent last_played_at
        more_recent_played_at_str = "2023-01-01T12:00:00Z"
        more_recent_played_at_dt = make_dt(more_recent_played_at_str)
        updated_track_obj_recent = Track(
            track_id=track_id, name="Test Track Updated Recent LPA", album_id="test_album_lpa",
            last_played_at=more_recent_played_at_dt, available_markets=["US", "CA"] # also update markets to see if other fields update
        )
        returned_track_dict_recent = upsert_track(self.session, updated_track_obj_recent)
        self.session.commit()

        self.assertIsNotNone(returned_track_dict_recent)
        returned_lpa_recent = make_dt(str(returned_track_dict_recent["last_played_at"])) if isinstance(returned_track_dict_recent["last_played_at"], str) else returned_track_dict_recent["last_played_at"]
        if returned_lpa_recent.tzinfo is None: returned_lpa_recent = returned_lpa_recent.replace(tzinfo=datetime.timezone.utc)
        self.assertEqual(returned_lpa_recent, more_recent_played_at_dt)
        self.assertEqual(returned_track_dict_recent["available_markets"], ["US", "CA"])


        db_track_recent = self.session.query(Track).filter_by(track_id=track_id).one()
        db_lpa_recent = db_track_recent.last_played_at
        if db_lpa_recent.tzinfo is None: db_lpa_recent = db_lpa_recent.replace(tzinfo=datetime.timezone.utc)
        self.assertEqual(db_lpa_recent, more_recent_played_at_dt)
        # Ensure other fields like name are also updated as per normal upsert logic
        self.assertEqual(db_track_recent.name, "Test Track Updated Recent LPA")
        db_markets = db_track_recent.available_markets
        if self.engine.name == 'sqlite' and isinstance(db_markets, str):
            db_markets = json.loads(db_markets)
        self.assertEqual(db_markets, ["US", "CA"])


        # Scenario 2: Attempt update with older last_played_at
        older_played_at_str = "2023-01-01T08:00:00Z"
        older_played_at_dt = make_dt(older_played_at_str)
        updated_track_obj_older = Track(
            track_id=track_id, name="Test Track Attempt Older LPA", album_id="test_album_lpa",
            last_played_at=older_played_at_dt
        )
        returned_track_dict_older = upsert_track(self.session, updated_track_obj_older)
        self.session.commit()

        self.assertIsNotNone(returned_track_dict_older)
        returned_lpa_older = make_dt(str(returned_track_dict_older["last_played_at"])) if isinstance(returned_track_dict_older["last_played_at"], str) else returned_track_dict_older["last_played_at"]
        if returned_lpa_older.tzinfo is None: returned_lpa_older = returned_lpa_older.replace(tzinfo=datetime.timezone.utc)
        # last_played_at should NOT have changed, should still be more_recent_played_at_dt
        self.assertEqual(returned_lpa_older, more_recent_played_at_dt)
        # However, other fields like 'name' should be updated by the upsert
        self.assertEqual(returned_track_dict_older["name"], "Test Track Attempt Older LPA")


        db_track_older = self.session.query(Track).filter_by(track_id=track_id).one()
        db_lpa_older = db_track_older.last_played_at
        if db_lpa_older.tzinfo is None: db_lpa_older = db_lpa_older.replace(tzinfo=datetime.timezone.utc)
        self.assertEqual(db_lpa_older, more_recent_played_at_dt) # Still the more recent one
        self.assertEqual(db_track_older.name, "Test Track Attempt Older LPA") # Name should update

        # Scenario 3: Attempt update with same last_played_at
        # Current DB state for last_played_at is more_recent_played_at_dt
        updated_track_obj_same = Track(
            track_id=track_id, name="Test Track Attempt Same LPA", album_id="test_album_lpa",
            last_played_at=more_recent_played_at_dt # Using the same timestamp
        )
        returned_track_dict_same = upsert_track(self.session, updated_track_obj_same)
        self.session.commit()

        self.assertIsNotNone(returned_track_dict_same)
        returned_lpa_same = make_dt(str(returned_track_dict_same["last_played_at"])) if isinstance(returned_track_dict_same["last_played_at"], str) else returned_track_dict_same["last_played_at"]
        if returned_lpa_same.tzinfo is None: returned_lpa_same = returned_lpa_same.replace(tzinfo=datetime.timezone.utc)
        self.assertEqual(returned_lpa_same, more_recent_played_at_dt) # Should remain unchanged
        self.assertEqual(returned_track_dict_same["name"], "Test Track Attempt Same LPA")

        db_track_same = self.session.query(Track).filter_by(track_id=track_id).one()
        db_lpa_same = db_track_same.last_played_at
        if db_lpa_same.tzinfo is None: db_lpa_same = db_lpa_same.replace(tzinfo=datetime.timezone.utc)
        self.assertEqual(db_lpa_same, more_recent_played_at_dt)
        self.assertEqual(db_track_same.name, "Test Track Attempt Same LPA")

        # Scenario 4: Insert a completely new track
        new_track_id = "test_track_lpa_2_new"
        new_track_played_at_str = "2023-02-01T10:00:00Z"
        new_track_played_at_dt = make_dt(new_track_played_at_str)
        new_track_obj = Track(
            track_id=new_track_id,
            name="Completely New Track LPA",
            album_id="test_album_lpa", # Can use same album
            last_played_at=new_track_played_at_dt,
            available_markets=["DE"]
        )
        returned_new_track_dict = upsert_track(self.session, new_track_obj)
        self.session.commit()

        self.assertIsNotNone(returned_new_track_dict)
        self.assertEqual(returned_new_track_dict["track_id"], new_track_id)
        returned_lpa_new = make_dt(str(returned_new_track_dict["last_played_at"])) if isinstance(returned_new_track_dict["last_played_at"], str) else returned_new_track_dict["last_played_at"]
        if returned_lpa_new.tzinfo is None: returned_lpa_new = returned_lpa_new.replace(tzinfo=datetime.timezone.utc)
        self.assertEqual(returned_lpa_new, new_track_played_at_dt)
        self.assertEqual(returned_new_track_dict["name"], "Completely New Track LPA")

        db_new_track = self.session.query(Track).filter_by(track_id=new_track_id).one()
        db_lpa_new = db_new_track.last_played_at
        if db_lpa_new.tzinfo is None: db_lpa_new = db_lpa_new.replace(tzinfo=datetime.timezone.utc)
        self.assertEqual(db_lpa_new, new_track_played_at_dt)
        self.assertEqual(db_new_track.name, "Completely New Track LPA")


if __name__ == '__main__': # pragma: no cover
    unittest.main()
