"""Tiny on-disk cache for Spotify search responses.

Spotify tightened Developer Mode rate limits substantially as of their
February 2026 API changes (aimed partly at curbing automated/scripted usage
-- exactly what this pipeline is). A single `manifest` run for a ~60-album
discography, multiplied across several name variants and (previously) an
unconditional fallback search, can add up to several hundred calls. This
cache makes repeated runs during development -- and resumed runs after a
rate-limit error -- nearly free: it's keyed by the literal query string, so
changing scoring/filtering logic downstream doesn't invalidate it; only
changing the query text itself does.
"""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_CACHE_PATH = Path(".spotify_search_cache.json")


def load_cache(path: str | Path = DEFAULT_CACHE_PATH) -> dict:
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_cache(cache: dict, path: str | Path = DEFAULT_CACHE_PATH) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f)
