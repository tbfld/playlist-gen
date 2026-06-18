"""Thin wrapper around the real Spotify Web API (via spotipy).

Requires a Spotify Developer app (https://developer.spotify.com/dashboard)
with SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET / SPOTIFY_REDIRECT_URI set in
a .env file at the repo root (copy .env.example). See pipeline/README.md.

Two auth modes, used for different steps:

- get_search_client(): app-only "Client Credentials" auth. No user login.
  Used for read-only calls (search, album tracks) -- i.e. building a manifest.
- get_user_client(): user-authorized "Authorization Code" auth. Required only
  for writes (creating/editing a playlist). The first call opens your browser
  for a one-time Spotify login + consent; spotipy runs a temporary local
  server on the redirect URI's port to catch the response automatically, so
  there's no manual copy-pasting. The resulting refresh token is cached in
  .cache-playlist-gen (gitignored) so this only happens once per machine.
"""
from __future__ import annotations

import os
import re
import time
import unicodedata
from dataclasses import dataclass

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

# Spotify tightened Developer Mode rate limits in their Feb 2026 API changes
# (partly aimed at automated/scripted usage). A short pause between calls
# keeps us well under the rolling 30s window instead of bursting requests.
REQUEST_DELAY_SECONDS = 0.3

USER_SCOPE = "playlist-modify-public playlist-modify-private"


def get_search_client() -> spotipy.Spotify:
    load_dotenv()
    auth_manager = SpotifyClientCredentials(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def get_user_client() -> spotipy.Spotify:
    load_dotenv()
    auth_manager = SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=os.environ.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback"),
        scope=USER_SCOPE,
        cache_path=".cache-playlist-gen",
        open_browser=True,
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def _normalize(title: str) -> str:
    title = unicodedata.normalize("NFKD", title)
    title = re.sub(r"[\(\[].*?[\)\]]", "", title)  # drop parenthetical/bracketed suffixes
    title = re.sub(r"[^a-z0-9 ]", "", title.lower())
    return re.sub(r"\s+", " ", title).strip()


def _stem(word: str) -> str:
    """Naive plural stemmer (flowers -> flower) so e.g. "Desert Flowers" can
    match a reissue titled "Desert Flower" without over-matching short words."""
    return word[:-1] if len(word) > 3 and word.endswith("s") else word


def _words(title: str) -> set[str]:
    return {_stem(w) for w in _normalize(title).split()}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _normalize_artist(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = re.sub(r"[^a-z0-9 ]", "", name.lower())
    return re.sub(r"\s+", " ", name).strip()


def _artist_matches(item: dict, artists: list[str]) -> bool:
    """True if any of `item`'s credited Spotify artists corresponds to one of
    our known name variants. Substring match (not equality) so e.g. "Abdullah
    Ibrahim" still matches a credit of "Abdullah Ibrahim Trio".

    Without this check, the unquoted fallback search below was returning
    albums by completely unrelated artists that merely shared a title word --
    e.g. "Blues for a Hip King" matching the Grateful Dead's "Blues for
    Allah", and "Mantra Mode" matching a Frost Children remix titled "Freak
    Mode". The quoted `artist:"..."` search is only a ranking hint to
    Spotify, not a hard filter, so this check is applied to ALL candidates,
    not just the fallback ones.
    """
    targets = [_normalize_artist(a) for a in artists]
    credited = [_normalize_artist(a["name"]) for a in item.get("artists", [])]
    return any(t in c or c in t for t in targets for c in credited if t and c)


@dataclass
class AlbumMatch:
    confidence: str  # "exact" | "fuzzy" | "none"
    spotify_id: str | None = None
    spotify_name: str | None = None
    spotify_url: str | None = None
    release_date: str | None = None
    track_count: int | None = None
    score: float = 0.0  # jaccard word-overlap score backing a "fuzzy" call; 1.0 for "exact"


def _search(sp: spotipy.Spotify, query: str, cache: dict | None) -> list[dict]:
    """sp.search(type="album") with an optional on-disk cache (see cache.py)
    and a small delay to stay well under Spotify's rate limit window."""
    if cache is not None and query in cache:
        return cache[query]
    time.sleep(REQUEST_DELAY_SECONDS)
    results = sp.search(q=query, type="album", limit=10)
    items = results.get("albums", {}).get("items", [])
    if cache is not None:
        cache[query] = items
    return items


def match_album(
    sp: spotipy.Spotify,
    title: str,
    year: int | None = None,
    artists: list[str] | None = None,
    min_jaccard: float = 0.3,
    cache: dict | None = None,
) -> AlbumMatch:
    """Search Spotify for an album, preferring an exact normalized-title match
    credited to one of `artists` (pass every known name variant -- artists who
    changed names mid-career fragment search results otherwise, see
    README.md's "Name-variant handling" note).

    Falls back to the best word-overlap candidate (Jaccard similarity over
    title words, ties broken by release-year proximity) if nothing matches
    exactly, flagged "fuzzy" for human review. Candidates with no meaningful
    word overlap with the target title are discarded rather than guessed at
    -- title-only fuzzy fallback was previously picking essentially unrelated
    albums (e.g. matching on the artist's catalog being full of the word
    "Africa") and is exactly the failure mode README.md warns needs a human
    checkpoint rather than full automation.

    Stops issuing further search calls as soon as a confirmed exact match is
    found (instead of always querying every name variant) -- Spotify's
    Developer Mode rate limits got considerably stricter in their Feb 2026
    API changes, so unnecessary calls are worth avoiding. Pass `cache` (a
    plain dict, see cache.py) to additionally persist results across runs.
    """
    artists = artists or ["Abdullah Ibrahim"]
    query_title = re.sub(r"\s*[\(\[].*?[\)\]]\s*", " ", title).strip()
    target_norm = _normalize(title)

    candidates: list[dict] = []
    seen_ids: set[str] = set()

    def _add(items: list[dict]) -> dict | None:
        """Add new items to `candidates`; return the first confirmed exact
        title+artist match among them, if any, so the caller can short-circuit."""
        exact = None
        for item in items:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                candidates.append(item)
                if (
                    exact is None
                    and _normalize(item["name"]) == target_norm
                    and _artist_matches(item, artists)
                ):
                    exact = item
        return exact

    def _exact_match(item: dict) -> AlbumMatch:
        return AlbumMatch(
            confidence="exact",
            spotify_id=item["id"],
            spotify_name=item["name"],
            spotify_url=item["external_urls"]["spotify"],
            release_date=item.get("release_date"),
            track_count=item.get("total_tracks"),
            score=1.0,
        )

    for artist in artists:
        items = _search(sp, f'album:"{query_title}" artist:"{artist}"', cache)
        exact = _add(items)
        if exact:
            return _exact_match(exact)

    if not candidates:
        for artist in artists:
            items = _search(sp, f"{query_title} {artist}", cache)
            exact = _add(items)
            if exact:
                return _exact_match(exact)

    candidates = [c for c in candidates if _artist_matches(c, artists)]

    if not candidates:
        return AlbumMatch(confidence="none")

    target_words = _words(title)

    def year_distance(item: dict) -> int:
        rd = item.get("release_date", "")
        try:
            return abs(int(rd[:4]) - year) if year else 50
        except (ValueError, TypeError):
            return 50

    scored = [(item, _jaccard(target_words, _words(item["name"]))) for item in candidates]
    scored = [(item, j) for item, j in scored if j >= min_jaccard]

    if not scored:
        return AlbumMatch(confidence="none")

    scored.sort(key=lambda pair: (-pair[1], year_distance(pair[0])))
    top, score = scored[0]
    return AlbumMatch(
        confidence="fuzzy",
        spotify_id=top["id"],
        spotify_name=top["name"],
        spotify_url=top["external_urls"]["spotify"],
        release_date=top.get("release_date"),
        track_count=top.get("total_tracks"),
        score=score,
    )


def album_tracks(sp: spotipy.Spotify, album_id: str) -> list[dict]:
    """Return this album's tracks in album order (handles pagination), each
    as {"disc_number", "track_number", "name", "duration_ms", "uri"}.

    Service-agnostic metadata (track titles, numbers, durations) -- useful
    on its own (e.g. as the basis for a playlist on a different streaming
    service), not just for building Spotify URIs.
    """
    tracks: list[dict] = []
    results = sp.album_tracks(album_id, limit=50)
    while results:
        for item in results["items"]:
            tracks.append(
                {
                    "disc_number": item["disc_number"],
                    "track_number": item["track_number"],
                    "name": item["name"],
                    "duration_ms": item["duration_ms"],
                    "uri": item["uri"],
                }
            )
        results = sp.next(results) if results.get("next") else None
    return tracks


def album_track_uris(sp: spotipy.Spotify, album_id: str) -> list[str]:
    """Return this album's track URIs in album order (handles pagination)."""
    return [t["uri"] for t in album_tracks(sp, album_id)]
