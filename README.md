# playlist-gen

A tool that takes a musician/band name and produces (1) a reliable, chronologically
ordered discography and (2) a streaming-service playlist built from it, in order.

## Status: pre-build. This repo currently contains research + a spec, not code.

## Files

- `seed-cases/abdullah-ibrahim/research.md` — narrative process notes: sources
  used, methodology, lessons learned. Read this first for context.
- `seed-cases/abdullah-ibrahim/discography.json` — the same discography as
  structured data: 62 entries, each with `title`, `year`, `recording_year`,
  `release_year`, `label`, `status` ('confirmed' / 'tentative'), `sources`,
  and a free-text `note` flagging conflicts or ambiguity. Entries that are a
  reissue or compilation of another entry carry a `relation` field
  (`{"type": "reissue"|"compilation", "of": [<order>]}`) instead of being
  treated as duplicates. Also includes a top-level `open_questions` array.
  Use this to diff a future pipeline's output against the manual baseline,
  and to drive the test cases below.

## How this started

A manual, conversational pass at building a complete chronological discography
and Spotify playlist for **Abdullah Ibrahim** (South African jazz pianist,
1934–2026), done by hand in a Claude.ai chat by cross-referencing Discogs,
Wikipedia, AllMusic, and a few genre-specific archive sites. See
`seed-cases/abdullah-ibrahim/research.md` for the full process notes, source
list, compiled (but still incomplete) discography, and — most importantly —
the lessons learned about *why* this is harder than "call an API."

## What's reusable vs. what's specific to the seed case

**Reusable (build these into the pipeline):**
- Source-priority ordering: Discogs > Wikipedia artist/album pages > AllMusic
  narrative bio > genre-archive sites (e.g. jazzmusicarchives, AllAboutJazz) >
  fan-compiled blogs. Likely needs adjustting per-genre/era; this ranking
  came from a deeply-documented 60-year jazz career and may not hold for,
  e.g., a contemporary pop artist with a cleaner Spotify/Wikipedia presence.
- **Recording-date vs. release-date conflict.** Many releases (esp. live
  albums, jazz/improvised music generally) were recorded years or decades
  before release. Pick one as the canonical sort key, but log both, and flag
  disagreements between sources rather than silently picking one.
- **The "late-period gap" failure mode.** In the manual pass, initial search
  queries surfaced the canonical/famous-era catalog well but significantly
  undershot the most recent ~15 years of output, even though sources for that
  period existed in the same search results. A pipeline should explicitly
  search for "[artist] discography [recent year range]" as a separate step,
  not rely on a single broad query.
- **Human-in-the-loop checkpoint before committing to a streaming match.**
  Compilations, live-album duplicates of studio albums, and reissue retitling
  make automated title-matching against a streaming API unreliable on its
  own. The pipeline should produce a reviewable manifest (title, year,
  source, match confidence, streaming URI) and let a human approve before
  any playlist is actually created/written to.
- **Name-variant handling.** Artists who changed names mid-career (stage
  names, religious conversions, band-name vs. solo-name) fragment search
  results. Need to search under all known variants and merge.

**Specific to the seed case (kept as a worked example / test fixture, not
meant to generalize):**
- The actual ~51 Abdullah Ibrahim album titles compiled so far.
- The "Dollar Brand" / "Abdullah Ibrahim" name-variant specifics.
- The specific remaining gaps. **Update 2026-06-16:** most of the conflicts
  below were checked and resolved during import into Cowork — see
  "Verification pass — 2026-06-16" at the end of
  `seed-cases/abdullah-ibrahim/research.md` and the `open_questions` array in
  `discography.json` for what's still genuinely open (mainly: a full
  title-by-title Discogs cross-check, and a periodic recheck for posthumous
  releases).

## Suggested pipeline shape

1. **Discography assembly** — query Discogs API, Wikipedia (artist discography
   category + album infoboxes), AllMusic for a given artist name (+ known
   variants); merge by normalized title; flag conflicts.
2. **Disambiguation** — surface compilations / reissues / live-duplicate-of-
   studio cases for human review rather than auto-resolving.
3. **Ordering** — recording date where known & cross-source-agreed, else
   release date; flag which was used per entry.
4. **Playlist building** — for each resolved title, query the target
   streaming API (Spotify, etc.), prefer original-label/era pressing where
   multiple versions exist, queue in order, log unmatched titles for manual
   review.
5. **Output** — reviewable manifest before the irreversible step (creating/
   writing to a live playlist).

## Suggested test cases for validating a built pipeline

Use the Abdullah Ibrahim seed case as a fixture. A correct pipeline should,
at minimum:
- Find *Solotude* (2021/2022) and *Universal Silence* (2019, but recorded
  1972) — both were nearly missed in the manual pass and are good tests of
  the "late-period gap" and "recording vs. release date" failure modes.
- Correctly handle the "Dollar Brand" → "Abdullah Ibrahim" name change
  without producing two disconnected partial discographies.
- Correctly distinguish reissues/compilations from original releases — e.g.
  the two "Blues for a Hip King" entries (1976 original vs. 1989 compilation)
  and the two "The Dream" entries (1965 original vs. 1979 reissue), both
  resolved via the `relation` field in `discography.json` rather than
  treated as duplicates or silently merged.

## Next steps

- Use this README + `seed-cases/abdullah-ibrahim/research.md` as the spec
  when starting the build (e.g. "generalize this into a reusable pipeline").
- Decide on language/runtime and where the human-review checkpoint lives
  (CLI prompt? generated HTML manifest? etc.) before writing code.
  **Note:** the target streaming service question is already answered for
  this Cowork session — a Spotify connector (search / create playlist /
  currently playing) is connected.
