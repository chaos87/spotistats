import unittest
import sqlalchemy
import datetime
from sqlalchemy import create_engine, JSON, TEXT # Ensure JSON, TEXT are imported
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError # For testing constraint violations
from sqlalchemy.dialects.postgresql import ARRAY, JSONB # Import ARRAY and JSONB

# Adjust the import path if your project structure for src is different
from backend.src.models import Base, Artist, Album, Track, Listen, RecentlyPlayedTracksRaw, PodcastSeries, PodcastEpisode

class TestModels(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')

        # Store original types
        self.original_artist_genres_type = Artist.genres.property.columns[0].type
        self.original_track_markets_type = Track.available_markets.property.columns[0].type
        self.original_raw_data_type = RecentlyPlayedTracksRaw.data.property.columns[0].type

        # Temporarily change types for SQLite compatibility
        # ARRAY(TEXT) and JSONB are not natively supported by SQLite's SQLAlchemy dialect
        Artist.genres.property.columns[0].type = JSON()
        Track.available_markets.property.columns[0].type = JSON()
        RecentlyPlayedTracksRaw.data.property.columns[0].type = JSON() # JSONB to JSON

        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine) # Clean up tables

        # Restore original types
        Artist.genres.property.columns[0].type = self.original_artist_genres_type
        Track.available_markets.property.columns[0].type = self.original_track_markets_type
        RecentlyPlayedTracksRaw.data.property.columns[0].type = self.original_raw_data_type

    def test_create_all_tables_exist(self):
        insp = sqlalchemy.inspect(self.engine)
        table_names = insp.get_table_names()
        self.assertIn('artists', table_names)
        self.assertIn('albums', table_names)
        self.assertIn('tracks', table_names)
        self.assertIn('listens', table_names)
        self.assertIn('recently_played_tracks_raw', table_names)
        self.assertIn('podcast_series', table_names)
        self.assertIn('podcast_episodes', table_names)

    def test_create_podcast_series_and_episode(self):
        new_series = PodcastSeries(
            series_id="series1",
            name="Test Podcast Series",
            publisher="Test Publisher",
            description="A test podcast series.",
            image_url="http://example.com/image.png",
            spotify_url="http://example.com/series"
        )
        self.session.add(new_series)
        self.session.commit()

        new_episode = PodcastEpisode(
            episode_id="episode1",
            name="Test Podcast Episode",
            description="A test podcast episode.",
            duration_ms=3600000,
            explicit=False,
            release_date=datetime.date(2024, 1, 1),
            spotify_url="http://example.com/episode",
            series_id=new_series.series_id
        )
        self.session.add(new_episode)
        self.session.commit()

        retrieved_series = self.session.query(PodcastSeries).filter_by(series_id="series1").one()
        self.assertEqual(retrieved_series.name, "Test Podcast Series")
        retrieved_episode = self.session.query(PodcastEpisode).filter_by(episode_id="episode1").one()
        self.assertEqual(retrieved_episode.name, "Test Podcast Episode")
        self.assertEqual(retrieved_episode.series_id, retrieved_series.series_id)

    def test_insert_valid_listen_track(self):
        # When inserting data for testing, ensure it's compatible with JSON for array fields
        valid_artist = Artist(artist_id="artist1", name="Test Artist", genres=["rock", "pop"]) # Example with genres
        valid_album = Album(album_id="album1", name="Test Album", primary_artist_id=valid_artist.artist_id)
        # Example with available_markets
        valid_track = Track(track_id="track1", name="Test Track", album_id=valid_album.album_id, available_markets=["US", "CA"])

        self.session.add_all([valid_artist, valid_album, valid_track])
        self.session.commit()

        # Verify data was stored (optional, but good for sanity check of JSON conversion)
        retrieved_artist = self.session.query(Artist).filter_by(artist_id="artist1").one()
        self.assertEqual(retrieved_artist.genres, ["rock", "pop"])

        retrieved_track = self.session.query(Track).filter_by(track_id="track1").one()
        self.assertEqual(retrieved_track.available_markets, ["US", "CA"])


        valid_listen_track = Listen(
            played_at=datetime.datetime.now(datetime.timezone.utc),
            item_type='track',
            track_id=valid_track.track_id,
            artist_id=valid_artist.artist_id,
            album_id=valid_album.album_id
        )
        self.session.add(valid_listen_track)
        try:
            self.session.commit()
        except Exception as e:
            self.fail(f"Committing a valid track listen should not fail: {e}")

    def test_insert_invalid_listen_violates_check_constraint(self):
        invalid_listen = Listen(
            played_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=1),
            item_type='track',
            track_id=None,
            episode_id=None
        )
        self.session.add(invalid_listen)
        try:
            self.session.commit()
            if self.engine.name == 'postgresql': # pragma: no cover
                 self.fail("IntegrityError not raised for CHECK constraint violation on PostgreSQL")
        except IntegrityError:
            self.session.rollback()
            pass
        except Exception as e: # pragma: no cover
            self.session.rollback()
            self.fail(f"An unexpected error occurred: {e}")

    def test_insert_valid_listen_episode(self):
        valid_series = PodcastSeries(series_id="series2", name="Another Test Series")
        valid_episode = PodcastEpisode(episode_id="episode2", name="Another Test Episode", series_id=valid_series.series_id)
        self.session.add_all([valid_series, valid_episode])
        self.session.commit()

        valid_listen_episode = Listen(
            played_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=2),
            item_type='episode',
            episode_id=valid_episode.episode_id
        )
        self.session.add(valid_listen_episode)
        try:
            self.session.commit()
        except Exception as e:
            self.fail(f"Committing a valid episode listen should not fail: {e}")

    def test_insert_invalid_listen_episode_with_artist_id(self):
        # Setup for episode listen
        valid_series = PodcastSeries(series_id="series3", name="Series For Invalid Listen")
        valid_episode = PodcastEpisode(episode_id="episode3", name="Episode For Invalid Listen", series_id=valid_series.series_id)
        # Also need an artist to attempt to link, even though it's invalid for an episode
        valid_artist = Artist(artist_id="artist_for_invalid_listen", name="Artist For Invalid Listen")
        self.session.add_all([valid_series, valid_episode, valid_artist])
        self.session.commit()

        invalid_listen = Listen(
            played_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=3),
            item_type='episode',
            episode_id=valid_episode.episode_id,
            artist_id=valid_artist.artist_id  # This should make it invalid
        )
        self.session.add(invalid_listen)
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()

    def test_insert_invalid_listen_track_without_album_id(self):
        # Setup for track listen
        valid_artist = Artist(artist_id="artist_for_invalid_track", name="Artist For Invalid Track")
        # No album created or linked to the track here to make it invalid
        valid_track = Track(track_id="track_for_invalid_listen", name="Track For Invalid Listen") # album_id is missing
        self.session.add_all([valid_artist, valid_track])
        self.session.commit()

        invalid_listen = Listen(
            played_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=4),
            item_type='track',
            track_id=valid_track.track_id,
            artist_id=valid_artist.artist_id,
            album_id=None # This makes it invalid
        )
        self.session.add(invalid_listen)
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()


if __name__ == '__main__': # pragma: no cover
    unittest.main()
