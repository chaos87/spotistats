import unittest
import datetime
from backend.src.normalizer import SpotifyItemNormalizer, parse_release_date
from backend.src.models import Artist, Album, Track, Listen, PodcastSeries, PodcastEpisode

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


class TestSpotifyItemNormalizer(unittest.TestCase):
    def setUp(self):
        self.normalizer = SpotifyItemNormalizer()
        # self.played_at_dt = make_played_at_dt(2023, 1, 15, 10, 30, 0) # played_at is now in the item
        self.sample_spotify_track_item_full = {
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
            "played_at": "2023-01-15T10:30:00.000Z", # Corresponds to self.played_at_dt
        }
        self.played_at_dt = make_played_at_dt(2023, 1, 15, 10, 30, 0) # For direct comparison

        self.sample_spotify_episode_item_full = {
            "track": {
                "show": {
                    "name": "Tech Talks Daily",
                    "publisher": "Neil Hughes",
                    "id": "show123",
                    "description": "Podcast about technology.",
                    "images": [{"url": "http://example.com/show_image.png"}],
                    "external_urls": {"spotify": "http://spotify.com/show/show123"}
                },
                "id": "ep456",
                "name": "The Future of AI",
                "description": "A discussion about AI.",
                "duration_ms": 1800000, # 30 minutes
                "explicit": False,
                "release_date": "2023-05-10",
                "release_date_precision": "day",
                "external_urls": {"spotify": "http://spotify.com/episode/ep456"},
                "type": "episode"
            },
            "played_at": "2023-05-15T14:00:00.000Z"
        }
        self.episode_played_at_dt = make_played_at_dt(2023, 5, 15, 14, 0, 0)


    def test_normalize_item_for_track(self):
        result_dict = self.normalizer.normalize_item(self.sample_spotify_track_item_full)
        self.assertIsNotNone(result_dict)
        self.assertEqual(result_dict['type'], 'track')

        artist = result_dict['artist']
        album = result_dict['album']
        track = result_dict['track']
        listen = result_dict['listen']

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
        self.assertEqual(track.last_played_at, self.played_at_dt) # from played_at in item

        # Listen assertions
        self.assertIsInstance(listen, Listen)
        self.assertEqual(listen.played_at, self.played_at_dt) # from played_at in item
        self.assertEqual(listen.item_type, "track")
        self.assertEqual(listen.track_id, "07MDkzUKhLmc7i53vj83fF")
        self.assertEqual(listen.artist_id, "0TnOYISbd1XYRBk9myaseg")
        self.assertEqual(listen.album_id, "5B4PYA7wNN4WdF25VGSo6Q")
        self.assertIsNone(listen.episode_id)

    def test_normalize_item_for_track_missing_optional_fields(self):
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
            },
            "played_at": "2023-01-15T10:30:00.000Z" # Corresponds to self.played_at_dt
        }
        result_dict = self.normalizer.normalize_item(minimal_item)
        self.assertIsNotNone(result_dict)
        self.assertEqual(result_dict['type'], 'track')
        artist = result_dict['artist']
        album = result_dict['album']
        track = result_dict['track']
        listen = result_dict['listen']

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

    def test_normalize_item_for_track_release_date_month_precision(self):
        item_month_release = self.sample_spotify_track_item_full.copy() # shallow copy
        item_month_release["track"]["album"]["release_date"] = "2011-04"
        item_month_release["track"]["album"]["release_date_precision"] = "month"

        result_dict = self.normalizer.normalize_item(item_month_release)
        self.assertIsNotNone(result_dict)
        album = result_dict['album']
        self.assertEqual(album.release_date, datetime.date(2011, 4, 1))

    def test_normalize_item_for_track_release_date_year_precision(self):
        item_year_release = self.sample_spotify_track_item_full.copy()
        item_year_release["track"]["album"]["release_date"] = "2011"
        item_year_release["track"]["album"]["release_date_precision"] = "year"

        result_dict = self.normalizer.normalize_item(item_year_release)
        self.assertIsNotNone(result_dict)
        album = result_dict['album']
        self.assertEqual(album.release_date, datetime.date(2011, 1, 1))

    def test_normalize_item_unknown_type(self):
        unknown_type_item = {"track": {"type": "unknown", "name": "Unknown thing"}, "played_at": "2023-01-15T10:30:00.000Z"}
        result = self.normalizer.normalize_item(unknown_type_item)
        self.assertIsNone(result)

    def test_normalize_item_no_track_data_in_item(self):
        no_track_item = {"played_at": "2023-01-15T10:30:00.000Z"} # Missing 'track' key
        result = self.normalizer.normalize_item(no_track_item)
        self.assertIsNone(result)

    def test_normalize_item_no_played_at_in_item(self):
        item_no_played_at = self.sample_spotify_track_item_full.copy()
        del item_no_played_at["played_at"]
        result = self.normalizer.normalize_item(item_no_played_at)
        self.assertIsNone(result)


    def test_normalize_item_for_track_missing_artist_album_data_gracefully(self):
        item_missing_sub_data = {
            "track": {
                # "album": {}, # Missing album entirely - handled by .get('album', {})
                "artists": [], # Empty artists list
                "artists": [], # Empty artists list
                "id": "track_only_id",
                "name": "Track Only",
                "duration_ms": 1000,
                "explicit": False,
                "external_urls": {"spotify": "track_url_only"},
                "type": "track"
            },
            "played_at": "2023-01-15T10:30:00.000Z"
        }
        result_dict = self.normalizer.normalize_item(item_missing_sub_data)
        self.assertIsNotNone(result_dict)
        artist = result_dict['artist']
        album = result_dict['album']
        track = result_dict['track']
        listen = result_dict['listen']


        self.assertIsNone(artist.artist_id)
        self.assertIsNone(artist.name)
        self.assertIsNone(artist.image_url) # No album, so no image from there
        self.assertEqual(artist.genres, [])

        self.assertIsNone(album.album_id) # because track.album is {}
        self.assertIsNone(album.name)
        self.assertIsNone(album.primary_artist_id)


        self.assertEqual(track.track_id, "track_only_id")
        self.assertIsNone(track.album_id)
        self.assertEqual(track.last_played_at, self.played_at_dt)

        self.assertEqual(listen.track_id, "track_only_id")
        self.assertIsNone(listen.artist_id)
        self.assertIsNone(listen.album_id)

    def test_normalize_item_for_track_no_album_images(self):
        item_no_album_images = self.sample_spotify_track_item_full.copy()
        item_no_album_images["track"]["album"]["images"] = [] # Empty images list

        result_dict = self.normalizer.normalize_item(item_no_album_images)
        self.assertIsNotNone(result_dict)
        artist = result_dict['artist']
        album = result_dict['album']


        self.assertIsNone(artist.image_url) # Should be None if album images are empty
        self.assertIsNone(album.image_url)  # Should be None if album images are empty

    def test_normalize_item_for_track_no_artists_in_track(self):
        item_no_artists = self.sample_spotify_track_item_full.copy()
        item_no_artists["track"]["artists"] = [] # No artists for the track

        result_dict = self.normalizer.normalize_item(item_no_artists)
        self.assertIsNotNone(result_dict)
        artist = result_dict['artist']
        album = result_dict['album']
        listen = result_dict['listen']

        self.assertIsNone(artist.artist_id)
        self.assertIsNone(artist.name)
        self.assertEqual(artist.genres, [])
        # artist.image_url might still exist if album and album.images exist, as per current logic

        self.assertIsNone(album.primary_artist_id) # artist_id is None

        self.assertIsNone(listen.artist_id) # artist_id is None

    def test_normalize_item_for_episode(self):
        result_dict = self.normalizer.normalize_item(self.sample_spotify_episode_item_full)
        self.assertIsNotNone(result_dict)
        self.assertEqual(result_dict['type'], 'episode')

        series = result_dict['series']
        episode = result_dict['episode']
        listen = result_dict['listen']

        # PodcastSeries assertions
        self.assertIsInstance(series, PodcastSeries)
        self.assertEqual(series.series_id, "show123")
        self.assertEqual(series.name, "Tech Talks Daily")
        self.assertEqual(series.publisher, "Neil Hughes")
        self.assertEqual(series.description, "Podcast about technology.")
        self.assertEqual(series.image_url, "http://example.com/show_image.png")
        self.assertEqual(series.spotify_url, "http://spotify.com/show/show123")

        # PodcastEpisode assertions
        self.assertIsInstance(episode, PodcastEpisode)
        self.assertEqual(episode.episode_id, "ep456")
        self.assertEqual(episode.name, "The Future of AI")
        self.assertEqual(episode.description, "A discussion about AI.")
        self.assertEqual(episode.duration_ms, 1800000)
        self.assertFalse(episode.explicit)
        self.assertEqual(episode.release_date, datetime.date(2023, 5, 10))
        self.assertEqual(episode.spotify_url, "http://spotify.com/episode/ep456")
        self.assertEqual(episode.series_id, "show123")

        # Listen assertions
        self.assertIsInstance(listen, Listen)
        self.assertEqual(listen.played_at, self.episode_played_at_dt)
        self.assertEqual(listen.item_type, "episode")
        self.assertEqual(listen.episode_id, "ep456")
        self.assertIsNone(listen.track_id)
        self.assertIsNone(listen.artist_id)
        self.assertIsNone(listen.album_id)

    def test_normalize_episode_item_direct_call(self):
        # This tests the normalize_episode_item method more directly
        # It's useful if normalize_item has complex routing you want to bypass for this specific test
        series, episode, listen = self.normalizer.normalize_episode_item(self.sample_spotify_episode_item_full)

        self.assertEqual(series.series_id, "show123")
        self.assertEqual(episode.episode_id, "ep456")
        self.assertEqual(listen.played_at, self.episode_played_at_dt)
        self.assertEqual(listen.item_type, "episode")


if __name__ == "__main__": # pragma: no cover
    unittest.main()
