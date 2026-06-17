"""Load and query the structured discography JSON for an artist.

This module reads the format documented in the root README.md ("Files" /
discography.json description) and seeded by seed-cases/abdullah-ibrahim/.
It does NOT yet implement the "Discography assembly" step from the README's
suggested pipeline shape (querying Discogs/Wikipedia/AllMusic to build this
file from scratch) -- that file is currently hand-compiled. This module is
the read side: given a discography.json, answer the questions the rest of
the pipeline needs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_discography(path: str | Path) -> dict[str, Any]:
    """Load a discography.json file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def primary_albums(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return albums in chronological order, excluding entries tagged via the
    `relation` field as a reissue/compilation of another entry.

    Those entries are kept in the dataset for completeness (e.g. cross-
    referencing against Discogs' full release list) but should not appear
    a second time in a playlist built from the primary chronological list.
    """
    albums = [a for a in data["albums"] if "relation" not in a]
    return sorted(albums, key=lambda a: a["order"])


def relation_entries(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the entries that ARE reissues/compilations, for reference/logging."""
    return [a for a in data["albums"] if "relation" in a]
