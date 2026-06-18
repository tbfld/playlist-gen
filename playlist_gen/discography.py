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


def render_outline(data: dict[str, Any]) -> str:
    """Render a plain-text, minimally annotated chronological outline of every
    entry in the discography -- including reissues/compilations, which are
    flagged inline rather than omitted (unlike `primary_albums`, this is meant
    as a quick human-readable index of everything in the dataset, not an input
    to playlist-building).
    """
    albums = sorted(data["albums"], key=lambda a: a["order"])
    artist = data["artist"]
    variants = [v for v in data.get("name_variants", []) if v != artist]

    lines = [artist.upper() + " — CHRONOLOGICAL DISCOGRAPHY"]
    if variants:
        lines.append("(also recorded as " + ", ".join(variants) + ")")
    lines.append("")
    lines.append(f"{len(albums)} entries, in chronological order (recording year where known, else release year).")
    lines.append("Reissues/compilations are flagged inline, not counted as separate originals.")
    lines.append("'?' marks a tentative entry (single source, or conflicting year/title info).")
    lines.append("Generated from discography.json -- see that file and research.md for sources and notes.")
    lines.append("")

    title_width = max(len(a["title"]) for a in albums)
    for a in albums:
        rec, rel = a.get("recording_year"), a.get("release_year")
        if rec and rel and rec != rel:
            year_str = f"{rec}/{rel}"
        else:
            year_str = str(a["year"])
        flag = "?" if a.get("status") == "tentative" else " "

        bits = []
        if a.get("label"):
            bits.append(a["label"])
        relation = a.get("relation")
        if relation:
            of = ",".join(f"#{n}" for n in relation["of"])
            bits.append(f"{relation['type']} of {of}")
        if a.get("status") == "gap":
            bits.append("gap")
        suffix = "  — " + "; ".join(bits) if bits else ""

        line = f"{a['order']:>3}. {year_str:<9}{flag} {a['title']:<{title_width}}{suffix}"
        lines.append(line.rstrip())

    lines.append("")
    return "\n".join(lines)
