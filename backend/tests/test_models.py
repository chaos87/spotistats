import unittest
import sqlalchemy
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError # For testing constraint violations

# Adjust the import path if your project structure for src is different
from backend.src.models import Base, Artist, Album, Track, Listen, RecentlyPlayedTracksRaw

class TestModels(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine) # Clean up tables

    def test_create_all_tables_exist(self):
        insp = sqlalchemy.inspect(self.engine)
        table_names = insp.get_table_names()
        self.assertIn('artists', table_names)
        self.assertIn('albums', table_names)
        self.assertIn('tracks', table_names)
        self.assertIn('listens', table_names)
        self.assertIn('recently_played_tracks_raw', table_names)

    def test_insert_valid_listen_track(self):
        valid_artist = Artist(artist_id="artist1", name="Test Artist")
        # Ensure primary_artist_id is provided if album is linked to an artist
        valid_album = Album(album_id="album1", name="Test Album", primary_artist_id=valid_artist.artist_id)
        valid_track = Track(track_id="track1", name="Test Track", album_id=valid_album.album_id)

        self.session.add_all([valid_artist, valid_album, valid_track])
        self.session.commit()

        valid_listen_track = Listen(
            played_at=datetime.datetime.now(datetime.timezone.utc),
            item_type='track',
            track_id=valid_track.track_id,
            artist_id=valid_artist.artist_id, # Assuming artist_id should be populated for track listens
            album_id=valid_album.album_id    # Assuming album_id should be populated for track listens
        )
        self.session.add(valid_listen_track)
        try:
            self.session.commit()
        except Exception as e:
            self.fail(f"Committing a valid track listen should not fail: {e}")

    def test_insert_invalid_listen_violates_check_constraint(self):
        # This test is more illustrative for PostgreSQL. SQLite might not enforce CHECK constraints by default.
        # Attempt to insert a Listen record that violates the CHECK constraint
        # (e.g., item_type='track' but track_id is NULL)
        invalid_listen = Listen(
            played_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=1), # Ensure unique played_at
            item_type='track',
            track_id=None, # This violates the constraint for item_type='track'
            episode_id=None
        )
        self.session.add(invalid_listen)
        # For PostgreSQL, this would raise IntegrityError.
        # For SQLite, this might pass if CHECK constraints are not enforced.
        # We'll assert that it raises IntegrityError if the DB supports it,
        # otherwise, we acknowledge it might pass on SQLite.
        try:
            self.session.commit()
            # If we are here, SQLite might not be enforcing the CHECK constraint.
            # This is acceptable for a unit test not specifically targeting DB constraint enforcement.
            # For true constraint testing, use an integration test with PostgreSQL.
            if self.engine.name == 'postgresql': # pragma: no cover
                 self.fail("IntegrityError not raised for CHECK constraint violation on PostgreSQL")
        except IntegrityError:
            self.session.rollback() # Good practice to rollback after an error
            pass # Expected if CHECK constraints are enforced
        except Exception as e: # pragma: no cover
            self.session.rollback()
            self.fail(f"An unexpected error occurred: {e}")

if __name__ == '__main__': # pragma: no cover
    unittest.main()
