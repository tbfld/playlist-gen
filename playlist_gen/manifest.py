"""Build and render the human-review manifest required before any playlist write.

See README.md's "Suggested pipeline shape", step 5: a reviewable manifest
(title, year, match confidence, streaming URI) must be produced and approved
by a human before a live playlist is created or written to.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .cache import DEFAULT_CACHE_PATH, load_cache, save_cache
from .spotify_client import REQUEST_DELAY_SECONDS, AlbumMatch, album_track_uris, album_tracks, match_album


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


def fetch_track_listings(sp, rows: list[ManifestRow], delay: float = REQUEST_DELAY_SECONDS) -> dict[int, list[dict]]:
    """Fetch the full track listing (disc/track number, title, duration) for
    every row that has a Spotify match, keyed by manifest `order`. Read-only,
    app-only auth (get_search_client()) -- no user login needed, same as
    `manifest`. Rows with no match are simply absent from the result.
    """
    listings: dict[int, list[dict]] = {}
    for r in rows:
        if not r.spotify_id:
            continue
        time.sleep(delay)
        listings[r.order] = album_tracks(sp, r.spotify_id)
    return listings


def render_track_listings(data: dict, rows: list[ManifestRow], listings: dict[int, list[dict]]) -> str:
    """Render the second section of the combined discography document: an
    album-by-album track listing, in the same chronological order as
    `discography.render_outline`'s first section (including reissues/
    compilations, which point back to their canonical entry instead of
    repeating a listing).
    """
    by_order = {r.order: r for r in rows}
    albums = sorted(data["albums"], key=lambda a: a["order"])

    lines = ["TRACK LISTINGS", "(album-by-album, same order as the outline above)", ""]
    for a in albums:
        order = a["order"]
        lines.append(f"{order}. {a['title']} ({a['year']})")

        relation = a.get("relation")
        if relation:
            of = ", ".join(f"#{n}" for n in relation["of"])
            lines.append(f"    [{relation['type']} of {of} -- see that entry for the track listing]")
            lines.append("")
            continue

        row = by_order.get(order)
        tracks = listings.get(order) if row else None
        if not tracks:
            reason = "no Spotify match" if not row or not row.spotify_id else "not fetched"
            lines.append(f"    ({reason} -- track listing not available; see research.md)")
            lines.append("")
            continue

        multi_disc = len({t["disc_number"] for t in tracks}) > 1
        for t in tracks:
            num = f"{t['disc_number']}.{t['track_number']:02d}" if multi_disc else f"{t['track_number']:>2}"
            mins, secs = divmod(round(t["duration_ms"] / 1000), 60)
            lines.append(f"   {num}. {t['name']}  ({mins}:{secs:02d})")
        lines.append("")

    return "\n".join(lines)
