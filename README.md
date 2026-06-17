# playlist-gen

A small toolkit that takes a structured discography for a musician/band and
turns it into a reviewable Spotify-matching manifest, then — after a human
approves it — creates a real, chronologically ordered Spotify playlist from
it.

It does **not** (yet) assemble the discography itself. You provide that as a
JSON file (format below); this tool handles the Spotify-matching and
playlist-creation half of the pipeline.

## Status

Working v0 CLI: `manifest` (search Spotify, score matches, write a
reviewable report) and `create` (build the actual playlist from an approved
manifest) subcommands. Built and exercised against one real discography —
Abdullah Ibrahim's — which lives in a sibling repo,
`abdullah-ibrahim-chronological-discography`, as a worked example and test
fixture.

## Why two steps (manifest, then create)

Automated title-matching against a streaming catalog is unreliable on its
own: compilations, live-album duplicates of studio albums, reissue
retitling, and generic titles that collide with unrelated artists all
produce confident-looking wrong matches. Concrete examples hit while
building this tool, where the most literal "exact title" match was wrong:

- *The Dream* (Abdullah Ibrahim, 1965) matched to an unrelated **alt-J**
  album of the same name.
- *The Mountain* matched to an unrelated **Steve Earle & The Del McCoury
  Band** album.
- *Desert Flowers* matched to an unrelated **Massimo Lisi / Garden Glass**
  release.
- *Blues for a Hip King* fuzzy-matched to the Grateful Dead's "Blues for
  Allah."
- *Mantra Mode* fuzzy-matched to Frost Children's "Freak Mode."
- *The Children of Africa* fuzzy-matched to the *Out of Africa* movie
  soundtrack.

Because of this, `manifest` never writes to Spotify. It only searches,
scores, and reports — including an artist-credit check that rejects a
title match if the returned album's artist credit doesn't actually include
the artist you're matching against (this is what caught the three "exact
match" false positives above). A human reviews the manifest, and only then
does `create` get run, which is the one command that writes to a real
Spotify playlist.

## Setup

```
pip install -r requirements.txt
cp .env.example .env   # fill in your Spotify app credentials
```

You'll need a Spotify Developer app (client ID/secret) with a redirect URI
matching `.env.example`. First run will prompt an OAuth browser flow; the
refresh token gets cached locally (gitignored) so you don't repeat it.

As of Spotify's Feb/Mar 2026 API changes, Development Mode apps require the
app owner to have an active Spotify Premium subscription, and are capped at
5 users. `create` already targets the post-migration endpoints
(`POST /me/playlists`, not the retired `POST /users/{id}/playlists`); if you
hit a 403 on playlist creation, it's most likely this account/quota
requirement rather than a code bug.

**Run this locally, not in a sandboxed environment** — it needs to reach
Spotify's API and open a browser for OAuth.

## Usage

```
python -m playlist_gen.cli manifest path/to/discography.json --json manifest.json --out manifest.md
# review manifest.md by hand
python -m playlist_gen.cli create manifest.json --name "Artist Name, chronological"
```

`create` only acts on entries the manifest marked as matched — review and
edit `manifest.json`/`manifest.md` first if you want to exclude or
hand-correct anything.

## discography.json format

```json
{
  "artist": "Artist Name",
  "albums": [
    {
      "order": 1,
      "title": "Album Title",
      "year": 1970,
      "recording_year": 1969,
      "release_year": 1970,
      "label": "Label Name",
      "status": "confirmed",
      "sources": ["discogs", "wikipedia"],
      "note": "free text for conflicts/ambiguity"
    }
  ],
  "open_questions": ["anything still genuinely unresolved"]
}
```

Entries that are a reissue or compilation of another entry carry a
`relation` field instead of being a separate duplicate:

```json
"relation": { "type": "reissue", "of": [1] }
```

`order` is the field used for chronological sort, separately from `year`,
since recording date and release date frequently disagree (common in jazz
and other genres with a large gap between session and release) — pick one
as canonical per entry but keep both, and use `note`/`open_questions` to
flag disagreements rather than silently resolving them.

This tool doesn't build this file for you yet. Compiling one by hand (or
with an LLM doing the cross-referencing across Discogs/Wikipedia/AllMusic,
as was done for the Abdullah Ibrahim example) is the current workflow; see
the sibling discography repo for a real worked example, including process
notes on the pitfalls of doing that compilation.

## Tests

```
pip install pytest
pytest
```

`tests/fixtures/abdullah-ibrahim-discography.json` is a self-contained copy
of the Abdullah Ibrahim discography, used as a regression fixture so this
repo's tests don't depend on the separate data repo. The canonical, evolving
version of that file lives in the sibling repo linked above.

## Known limitations

- No discography-assembly step — see above.
- Matching is title/artist-based against Spotify search; it doesn't yet
  prefer a specific pressing/label/era when multiple versions of the same
  album exist on Spotify under the same artist.
- Only tested end-to-end against one discography. Other artists' catalogs
  (different naming conventions, more or fewer reissues, different Spotify
  catalog completeness) will likely surface new edge cases — issues and
  PRs welcome.

## License

MIT — see `LICENSE`.
