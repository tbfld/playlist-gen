from playlist_gen.manifest import ManifestRow, fetch_track_listings, render_track_listings


class FakeSpotify:
    """Stand-in app-only client: returns one fixed track per album_id, and
    records which IDs were actually queried (to verify unmatched rows are
    skipped without hitting the network)."""

    def __init__(self):
        self.calls: list[str] = []

    def album_tracks(self, album_id, limit=50):
        self.calls.append(album_id)
        return {
            "items": [
                {
                    "disc_number": 1,
                    "track_number": 1,
                    "name": f"{album_id} Opener",
                    "duration_ms": 200000,
                    "uri": f"spotify:track:{album_id}",
                }
            ],
            "next": None,
        }

    def next(self, results):
        return None


def test_fetch_track_listings_skips_rows_with_no_spotify_id():
    rows = [
        ManifestRow(order=1, title="A", year=2000, status="confirmed", match="exact", spotify_id="id1"),
        ManifestRow(order=2, title="B", year=2001, status="confirmed", match="none", spotify_id=None),
    ]
    sp = FakeSpotify()
    listings = fetch_track_listings(sp, rows, delay=0)

    assert set(listings) == {1}
    assert sp.calls == ["id1"]


def test_render_track_listings_covers_match_unmatched_and_relation():
    data = {
        "albums": [
            {"order": 1, "title": "A", "year": 2000},
            {"order": 2, "title": "B", "year": 2001},
            {"order": 3, "title": "B (reissue)", "year": 2002, "relation": {"type": "reissue", "of": [2]}},
        ]
    }
    rows = [
        ManifestRow(order=1, title="A", year=2000, status="confirmed", match="exact", spotify_id="id1"),
        ManifestRow(order=2, title="B", year=2001, status="confirmed", match="none", spotify_id=None),
    ]
    listings = {
        1: [{"disc_number": 1, "track_number": 1, "name": "Opener", "duration_ms": 200000, "uri": "u"}],
    }

    out = render_track_listings(data, rows, listings)

    assert "1. A (2000)" in out
    assert "Opener" in out
    assert "(3:20)" in out  # 200000ms
    assert "no Spotify match" in out
    assert "reissue of #2" in out


def test_render_track_listings_flags_multi_disc_numbering():
    data = {"albums": [{"order": 1, "title": "A", "year": 2000}]}
    rows = [ManifestRow(order=1, title="A", year=2000, status="confirmed", match="exact", spotify_id="id1")]
    listings = {
        1: [
            {"disc_number": 1, "track_number": 1, "name": "First", "duration_ms": 60000, "uri": "u1"},
            {"disc_number": 2, "track_number": 1, "name": "Second", "duration_ms": 60000, "uri": "u2"},
        ]
    }

    out = render_track_listings(data, rows, listings)

    assert "1.01. First" in out
    assert "2.01. Second" in out
