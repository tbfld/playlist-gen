"""Build and render the human-review manifest required before any playlist write.

See README.md's "Suggested pipeline shape", step 5: a reviewable manifest
(title, year, match confidence, streaming URI) must be produced and approved
by a human before a live playlist is created or written to.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .cache import DEFAULT_CACHE_PATH, load_cache, save_cache
from .spotify_client import AlbumMatch, album_track_uris, match_album


@dataclass
class ManifestRow:
    order: int
    title: str
    year: int
    status: str  # the dataset's own confidence: confirmed / tentative / gap
    match: str  # spotify match confidence: exact / fuzzy / none
    spotify_id: str | None = None
    spotify_album: str | None = None
    spotify_url: str | None = None
    track_count: int | None = None
    score: float = 0.0


def build_manifest(sp, data: dict, cache_path: str | Path = DEFAULT_CACHE_PATH) -> list[ManifestRow]:
    """Build a manifest from a loaded discography.json dict (not just its
    album list) so matching can use the artist's full `name_variants`.

    Search results are cached to `cache_path` (see cache.py) and saved even
    if this is interrupted partway (e.g. by hitting Spotify's rate limit) --
    a retry will resume instantly for already-resolved albums.
    """
    from .discography import primary_albums

    albums = primary_albums(data)
    artists = data.get("name_variants") or [data["artist"]]
    cache = load_cache(cache_path)

    rows: list[ManifestRow] = []
    try:
        for album in albums:
            m: AlbumMatch = match_album(
                sp, album["title"], year=album.get("year"), artists=artists, cache=cache
            )
            rows.append(
                ManifestRow(
                    order=album["order"],
                    title=album["title"],
                    year=album["year"],
                    status=album["status"],
                    match=m.confidence,
                    spotify_id=m.spotify_id,
                    spotify_album=m.spotify_name,
                    spotify_url=m.spotify_url,
                    track_count=m.track_count,
                    score=m.score,
                )
            )
    finally:
        save_cache(cache, cache_path)

    _demote_collisions(rows)
    return rows


def _demote_collisions(rows: list[ManifestRow]) -> None:
    """A single Spotify album can't legitimately be the correct match for two
    different (non-reissue/compilation) entries in the same discography. When
    that happens, keep whichever row has the strongest match score and demote
    the rest to "none" -- they were almost always a generic fuzzy fallback
    landing on someone else's correct match (e.g. several different 1970s
    titles all weakly resembling the same "Heritage Collection" reissue).
    """
    groups: dict[str, list[int]] = {}
    for i, r in enumerate(rows):
        if r.spotify_id:
            groups.setdefault(r.spotify_id, []).append(i)

    for spotify_id, idxs in groups.items():
        if len(idxs) <= 1:
            continue
        best = max(idxs, key=lambda i: rows[i].score)
        for i in idxs:
            if i != best:
                rows[i].match = "none"
                rows[i].spotify_id = None
                rows[i].spotify_album = None
                rows[i].spotify_url = None
                rows[i].track_count = None
                rows[i].score = 0.0


def save_manifest_json(rows: list[ManifestRow], path: str | Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in rows], f, indent=2)


def load_manifest_json(path: str | Path) -> list[ManifestRow]:
    with open(path, encoding="utf-8") as f:
        return [ManifestRow(**r) for r in json.load(f)]


def render_markdown(rows: list[ManifestRow]) -> str:
    unmatched = [r for r in rows if r.match == "none"]
    fuzzy = [r for r in rows if r.match == "fuzzy"]
    exact = len(rows) - len(unmatched) - len(fuzzy)
    summary = (
        f"{len(rows)} albums -- {exact} exact match, {len(fuzzy)} fuzzy "
        f"(please check these), {len(unmatched)} unmatched.\n"
    )

    lines = ["| # | Title | Year | Match | Score | Spotify album | Link |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        link = f"[open]({r.spotify_url})" if r.spotify_url else "—"
        score = f"{r.score:.2f}" if r.match != "none" else "—"
        lines.append(
            f"| {r.order} | {r.title} | {r.year} | {r.match} | {score} | {r.spotify_album or '—'} | {link} |"
        )
    return summary + "\n" + "\n".join(lines)


def collect_track_uris(sp, rows: list[ManifestRow]) -> list[str]:
    """Pull ordered track URIs for every row that has a matched album, in
    manifest (chronological) order. Callers should already have filtered
    `rows` down to what the human approved (e.g. via the CLI's --exclude).
    """
    uris: list[str] = []
    for r in rows:
        if not r.spotify_id:
            continue
        uris.extend(album_track_uris(sp, r.spotify_id))
    return uris
