from playlist_gen.spotify_client import album_track_uris, album_tracks


class FakeSpotify:
    """Minimal stand-in for spotipy.Spotify covering just the two calls
    album_tracks() makes, so pagination/disc-number handling can be tested
    without real network access."""

    def __init__(self):
        self.page1 = {
            "items": [
                {"disc_number": 1, "track_number": 1, "name": "A", "duration_ms": 60000, "uri": "spotify:track:1"},
                {"disc_number": 1, "track_number": 2, "name": "B", "duration_ms": 65000, "uri": "spotify:track:2"},
            ],
            "next": "page2",
        }
        self.page2 = {
            "items": [
                {"disc_number": 2, "track_number": 1, "name": "C", "duration_ms": 70000, "uri": "spotify:track:3"},
            ],
            "next": None,
        }

    def album_tracks(self, album_id, limit=50):
        return self.page1

    def next(self, results):
        return self.page2 if results is self.page1 else None


def test_album_tracks_handles_pagination_and_disc_number():
    tracks = album_tracks(FakeSpotify(), "abc")
    assert [t["name"] for t in tracks] == ["A", "B", "C"]
    assert [t["disc_number"] for t in tracks] == [1, 1, 2]
    assert tracks[0]["duration_ms"] == 60000


def test_album_track_uris_flattens_pages():
    uris = album_track_uris(FakeSpotify(), "abc")
    assert uris == ["spotify:track:1", "spotify:track:2", "spotify:track:3"]
