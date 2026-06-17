"""Command-line entry point.

Usage:
    python -m playlist_gen.cli manifest <discography.json> [--out manifest.md] [--json manifest.json]
    python -m playlist_gen.cli create <manifest.json> --name "..." [--exclude 10,19]

The two subcommands are deliberately separate. `manifest` only reads from
Spotify (search, app-only auth) and writes local files -- no browser login,
no account changes. `create` is the only subcommand that writes to your
Spotify account (requires the one-time user login), and it only runs against
a manifest you've already reviewed -- per the project's human-in-the-loop
requirement (README.md, "Suggested pipeline shape", step 5).
"""
from __future__ import annotations

import argparse
import sys

from .discography import load_discography
from .manifest import build_manifest, collect_track_uris, load_manifest_json, render_markdown, save_manifest_json
from .spotify_client import get_search_client, get_user_client


def cmd_manifest(args: argparse.Namespace) -> None:
    data = load_discography(args.discography)
    sp = get_search_client()
    rows = build_manifest(sp, data)

    md = render_markdown(rows)
    print(md)

    if args.json:
        save_manifest_json(rows, args.json)
        print(f"\nSaved machine-readable manifest to {args.json}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Saved manifest to {args.out}")


def cmd_create(args: argparse.Namespace) -> None:
    rows = load_manifest_json(args.manifest)

    exclude = {int(x) for x in args.exclude.split(",")} if args.exclude else set()
    rows = [r for r in rows if r.order not in exclude]

    matched_rows = [r for r in rows if r.spotify_id]

    sp = get_user_client()
    me = sp.current_user()
    print(f"Authenticated as Spotify user: {me['id']}")
    track_uris = collect_track_uris(sp, rows)

    if not track_uris:
        print("No track URIs to add -- nothing created.", file=sys.stderr)
        sys.exit(1)

    # NOTE: spotipy's `user_playlist_create(user, ...)` posts to the now-removed
    # `POST /users/{user_id}/playlists` endpoint (Spotify retired it for
    # Development Mode apps in the Feb/Mar 2026 API changes -- it 403s even
    # when `user` is your own ID). `current_user_playlist_create(...)` posts to
    # the replacement, `POST /me/playlists`, instead. See:
    # https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide
    playlist = sp.current_user_playlist_create(args.name, public=False, description=args.description or "")
    for i in range(0, len(track_uris), 100):
        sp.playlist_add_items(playlist["id"], track_uris[i : i + 100])

    print(f"Created playlist '{args.name}': {playlist['external_urls']['spotify']}")
    print(f"{len(track_uris)} tracks added across {len(matched_rows)} albums "
          f"({len(rows) - len(matched_rows)} approved rows had no Spotify match and contributed nothing).")


def main() -> None:
    parser = argparse.ArgumentParser(prog="playlist_gen")
    sub = parser.add_subparsers(dest="command", required=True)

    p_manifest = sub.add_parser("manifest", help="Search Spotify and build a reviewable manifest (no writes).")
    p_manifest.add_argument("discography", help="Path to a discography.json file")
    p_manifest.add_argument("--out", help="Write the manifest as Markdown to this path")
    p_manifest.add_argument("--json", help="Write the manifest as JSON to this path (required input for `create`)")
    p_manifest.set_defaults(func=cmd_manifest)

    p_create = sub.add_parser("create", help="Create the real Spotify playlist from an approved manifest JSON.")
    p_create.add_argument("manifest", help="Path to a manifest JSON file produced by `manifest --json`")
    p_create.add_argument("--name", required=True)
    p_create.add_argument("--description", default="")
    p_create.add_argument("--exclude", help="Comma-separated list of manifest order numbers to skip")
    p_create.set_defaults(func=cmd_create)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
