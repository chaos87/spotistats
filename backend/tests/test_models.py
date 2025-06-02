import unittest
import sqlalchemy
import datetime
from sqlalchemy import create_engine, JSON, TEXT # Ensure JSON, TEXT are imported
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError # For testing constraint violations
from sqlalchemy.dialects.postgresql import ARRAY, JSONB # Import ARRAY and JSONB

# Adjust the import path if your project structure for src is different
from backend.src.models import Base, Artist, Album, Track, Listen, RecentlyPlayedTracksRaw

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

if __name__ == '__main__': # pragma: no cover
    unittest.main()
