import unittest
import datetime
from backend.src.normalizer import SpotifyMusicNormalizer, parse_release_date
from backend.src.models import Artist, Album, Track, Listen

# Helper to create a timezone-aware datetime object
def make_played_at_dt(year, month, day, hour, minute, second):
    return datetime.datetime(year, month, day, hour, minute, second, tzinfo=datetime.timezone.utc)

class TestParseReleaseDate(unittest.TestCase):
    def test_parse_day_precision(self):
        self.assertEqual(parse_release_date("2023-03-15", "day"), datetime.date(2023, 3, 15))

    def test_parse_month_precision(self):
        self.assertEqual(parse_release_date("2023-03", "month"), datetime.date(2023, 3, 1))

    def test_parse_year_precision(self):
        self.assertEqual(parse_release_date("2023", "year"), datetime.date(2023, 1, 1))

    def test_parse_invalid_date_format_for_day(self):
        self.assertIsNone(parse_release_date("2023/03/15", "day"))

    def test_parse_invalid_date_format_for_month(self):
        self.assertIsNone(parse_release_date("2023/03", "month"))

    def test_parse_invalid_date_format_for_year(self):
        self.assertIsNone(parse_release_date("23", "year"))

    def test_parse_invalid_date_value(self):
        self.assertIsNone(parse_release_date("2023-13-01", "day")) # Invalid month

    def test_parse_invalid_precision(self):
        self.assertIsNone(parse_release_date("2023-03-15", "invalid_precision"))

    def test_parse_empty_date(self):
        self.assertIsNone(parse_release_date("", "day"))

    def test_parse_none_date(self):
        self.assertIsNone(parse_release_date(None, "day"))


class TestSpotifyMusicNormalizer(unittest.TestCase):
    def setUp(self):
        self.normalizer = SpotifyMusicNormalizer()
        self.played_at_dt = make_played_at_dt(2023, 1, 15, 10, 30, 0)
        self.sample_spotify_item_full = {
            "track": {
                "album": {
                    "album_type": "album",
                    "artists": [
                        {
                            "external_urls": {"spotify": "https://open.spotify.com/artist/0TnOYISbd1XYRBk9myaseg"},
                            "id": "0TnOYISbd1XYRBk9myaseg",
                            "name": "Foo Fighters",
                        }
                    ],
                    "available_markets": ["US", "GB"], # Typically on track, but can be on album for simplicity in test
                    "external_urls": {"spotify": "https://open.spotify.com/album/5B4PYA7wNN4WdF25VGSo6Q"},
                    "id": "5B4PYA7wNN4WdF25VGSo6Q",
                    "images": [
                        {"height": 640, "url": "https://i.scdn.co/image/ab67616d0000b27370293c1c7d7506f96995c500", "width": 640},
                        {"height": 300, "url": "https://i.scdn.co/image/ab67616d00001e0270293c1c7d7506f96995c500", "width": 300}
                    ],
                    "name": "Wasting Light",
                    "release_date": "2011-04-12",
                    "release_date_precision": "day",
                    "total_tracks": 11,
                    "type": "album",
                },
                "artists": [
                    {
                        "external_urls": {"spotify": "https://open.spotify.com/artist/0TnOYISbd1XYRBk9myaseg"},
                        "id": "0TnOYISbd1XYRBk9myaseg",
                        "name": "Foo Fighters",
                        "genres": ["alternative rock", "post-grunge", "rock"]
                    }
                ],
                "available_markets": ["US", "GB"],
                "duration_ms": 268000,
                "explicit": False,
                "external_urls": {"spotify": "https://open.spotify.com/track/07MDkzUKhLmc7i53vj83fF"},
                "id": "07MDkzUKhLmc7i53vj83fF",
                "name": "Rope",
                "popularity": 60,
                "preview_url": "https://p.scdn.co/mp3-preview/SAMPLE",
                "type": "track",
            },
            "played_at": "2023-01-15T10:30:00.000Z",
        }

    def test_normalize_full_item(self):
        result = self.normalizer.normalize_track_item(self.sample_spotify_item_full, self.played_at_dt)
        self.assertIsNotNone(result)
        artist, album, track, listen = result

        # Artist assertions
        self.assertIsInstance(artist, Artist)
        self.assertEqual(artist.artist_id, "0TnOYISbd1XYRBk9myaseg")
        self.assertEqual(artist.name, "Foo Fighters")
        self.assertEqual(artist.spotify_url, "https://open.spotify.com/artist/0TnOYISbd1XYRBk9myaseg")
        self.assertEqual(artist.image_url, "https://i.scdn.co/image/ab67616d0000b27370293c1c7d7506f96995c500") # From album
        self.assertEqual(artist.genres, ["alternative rock", "post-grunge", "rock"])

        # Album assertions
        self.assertIsInstance(album, Album)
        self.assertEqual(album.album_id, "5B4PYA7wNN4WdF25VGSo6Q")
        self.assertEqual(album.name, "Wasting Light")
        self.assertEqual(album.release_date, datetime.date(2011, 4, 12))
        self.assertEqual(album.album_type, "album")
        self.assertEqual(album.spotify_url, "https://open.spotify.com/album/5B4PYA7wNN4WdF25VGSo6Q")
        self.assertEqual(album.image_url, "https://i.scdn.co/image/ab67616d0000b27370293c1c7d7506f96995c500")
        self.assertEqual(album.primary_artist_id, "0TnOYISbd1XYRBk9myaseg")

        # Track assertions
        self.assertIsInstance(track, Track)
        self.assertEqual(track.track_id, "07MDkzUKhLmc7i53vj83fF")
        self.assertEqual(track.name, "Rope")
        self.assertEqual(track.duration_ms, 268000)
        self.assertFalse(track.explicit)
        self.assertEqual(track.popularity, 60)
        self.assertEqual(track.preview_url, "https://p.scdn.co/mp3-preview/SAMPLE")
        self.assertEqual(track.spotify_url, "https://open.spotify.com/track/07MDkzUKhLmc7i53vj83fF")
        self.assertEqual(track.album_id, "5B4PYA7wNN4WdF25VGSo6Q")
        self.assertEqual(track.available_markets, ["US", "GB"])
        self.assertEqual(track.last_played_at, self.played_at_dt)

        # Listen assertions
        self.assertIsInstance(listen, Listen)
        self.assertEqual(listen.played_at, self.played_at_dt)
        self.assertEqual(listen.item_type, "track")
        self.assertEqual(listen.track_id, "07MDkzUKhLmc7i53vj83fF")
        self.assertEqual(listen.artist_id, "0TnOYISbd1XYRBk9myaseg")
        self.assertEqual(listen.album_id, "5B4PYA7wNN4WdF25VGSo6Q")
        self.assertIsNone(listen.episode_id)

    def test_normalize_item_missing_optional_fields(self):
        minimal_item = {
            "track": {
                "album": {
                    "id": "album1",
                    "name": "Minimal Album",
                    "artists": [{"id": "artist1", "name": "Minimal Artist"}],
                    "external_urls": {"spotify": "album_url"},
                    "release_date": "2020",
                    "release_date_precision": "year"
                    # No images, no album_type
                },
                "artists": [
                    {
                        "id": "artist1",
                        "name": "Minimal Artist",
                        "external_urls": {"spotify": "artist_url"}
                        # No genres
                    }
                ],
                "id": "track1",
                "name": "Minimal Track",
                "duration_ms": 180000,
                "explicit": True,
                "external_urls": {"spotify": "track_url"},
                "type": "track"
                # No popularity, preview_url, available_markets
            }
        }
        result = self.normalizer.normalize_track_item(minimal_item, self.played_at_dt)
        self.assertIsNotNone(result)
        artist, album, track, listen = result

        self.assertEqual(artist.artist_id, "artist1")
        self.assertIsNone(artist.image_url)
        self.assertEqual(artist.genres, [])

        self.assertEqual(album.album_id, "album1")
        self.assertIsNone(album.image_url)
        self.assertEqual(album.release_date, datetime.date(2020, 1, 1))
        self.assertIsNone(album.album_type) # Check missing optional field

        self.assertEqual(track.track_id, "track1")
        self.assertIsNone(track.popularity)
        self.assertIsNone(track.preview_url)
        self.assertEqual(track.available_markets, [])
        self.assertEqual(track.last_played_at, self.played_at_dt)

        self.assertEqual(listen.track_id, "track1")

    def test_normalize_item_release_date_month_precision(self):
        item_month_release = self.sample_spotify_item_full.copy() # shallow copy
        item_month_release["track"]["album"]["release_date"] = "2011-04"
        item_month_release["track"]["album"]["release_date_precision"] = "month"

        result = self.normalizer.normalize_track_item(item_month_release, self.played_at_dt)
        self.assertIsNotNone(result)
        _, album, _, _ = result
        self.assertEqual(album.release_date, datetime.date(2011, 4, 1))

    def test_normalize_item_release_date_year_precision(self):
        item_year_release = self.sample_spotify_item_full.copy()
        item_year_release["track"]["album"]["release_date"] = "2011"
        item_year_release["track"]["album"]["release_date_precision"] = "year"

        result = self.normalizer.normalize_track_item(item_year_release, self.played_at_dt)
        self.assertIsNotNone(result)
        _, album, _, _ = result
        self.assertEqual(album.release_date, datetime.date(2011, 1, 1))

    def test_normalize_non_track_item(self):
        episode_item = {"track": {"type": "episode", "name": "Podcast Episode"}}
        result = self.normalizer.normalize_track_item(episode_item, self.played_at_dt)
        self.assertIsNone(result)

    def test_normalize_item_no_track_data(self):
        no_track_item = {}
        result = self.normalizer.normalize_track_item(no_track_item, self.played_at_dt)
        self.assertIsNone(result)

    def test_normalize_item_missing_artist_album_data_gracefully(self):
        item_missing_sub_data = {
            "track": {
                # "album": {}, # Missing album entirely
                "artists": [], # Empty artists list
                "id": "track_only_id",
                "name": "Track Only",
                "duration_ms": 1000,
                "explicit": False,
                "external_urls": {"spotify": "track_url_only"},
                "type": "track"
            }
        }
        result = self.normalizer.normalize_track_item(item_missing_sub_data, self.played_at_dt)
        self.assertIsNotNone(result)
        artist, album, track, listen = result

        self.assertIsNone(artist.artist_id)
        self.assertIsNone(artist.name)
        self.assertIsNone(artist.image_url) # No album, so no image from there
        self.assertEqual(artist.genres, [])

        self.assertIsNone(album.album_id)
        self.assertIsNone(album.name)
        self.assertIsNone(album.primary_artist_id)

        self.assertEqual(track.track_id, "track_only_id")
        self.assertIsNone(track.album_id)
        self.assertEqual(track.last_played_at, self.played_at_dt)

        self.assertEqual(listen.track_id, "track_only_id")
        self.assertIsNone(listen.artist_id)
        self.assertIsNone(listen.album_id)

    def test_normalize_item_no_album_images(self):
        item_no_album_images = self.sample_spotify_item_full.copy()
        item_no_album_images["track"]["album"]["images"] = [] # Empty images list

        result = self.normalizer.normalize_track_item(item_no_album_images, self.played_at_dt)
        self.assertIsNotNone(result)
        artist, album, _, _ = result

        self.assertIsNone(artist.image_url) # Should be None if album images are empty
        self.assertIsNone(album.image_url)  # Should be None if album images are empty

    def test_normalize_item_no_artists_in_track(self):
        item_no_artists = self.sample_spotify_item_full.copy()
        item_no_artists["track"]["artists"] = [] # No artists for the track

        result = self.normalizer.normalize_track_item(item_no_artists, self.played_at_dt)
        self.assertIsNotNone(result)
        artist, album, track, listen = result

        self.assertIsNone(artist.artist_id)
        self.assertIsNone(artist.name)
        self.assertEqual(artist.genres, [])
        # artist.image_url might still exist if album and album.images exist, as per current logic

        self.assertIsNone(album.primary_artist_id) # artist_id is None

        self.assertIsNone(listen.artist_id) # artist_id is None


if __name__ == "__main__": # pragma: no cover
    unittest.main()
