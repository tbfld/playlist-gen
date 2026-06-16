# Project: Chronological Discography → Playlist Pipeline
## Seed case: Abdullah Ibrahim

This document captures the research process and output from an exploratory session, intended as a seed/spec for building a generalized "chronological discography to playlist" tool (e.g., in Cowork or as a standalone script).

---

## Goal

Given a musician/band, produce:
1. A reliable, complete, chronologically ordered list of their recorded output (as leader/primary artist).
2. A streaming-service playlist (Spotify) built from that list, in order.

## Why this is harder than it sounds

- Discographies for long-career artists are scattered across many small/defunct labels, reissues, and compilations.
- Recording date vs. release date frequently diverge (sometimes by years or decades) — need to pick one consistently as the sort key and note when sources disagree.
- Name changes mid-career (e.g., "Dollar Brand" → "Abdullah Ibrahim") fragment search results and streaming catalogs.
- Compilations, live albums, and alternate-title reissues create ambiguity for automated title-matching against a streaming API.
- No single source is complete or fully reliable; cross-referencing multiple sources is necessary.

## Sources used (in order of usefulness for this case)

1. **Discogs** (discogs.com/artist/248560-Abdullah-Ibrahim) — most complete release-level data (70 releases: 55 albums, 13 compilations), but page required filtering/sorting that wasn't fully scraped this session.
2. **AllMusic** (allmusic.com/artist/abdullah-ibrahim-mn0000923935) — good narrative discography with years, useful for cross-checking.
3. **Wikipedia** — individual album pages (e.g., *Ancient Africa*, *Sangoma*, *Good News from Africa*, *Autobiography*) have the most precise recording dates/locations/labels; the Category:Abdullah Ibrahim albums page lists 24 pages but wasn't fully enumerated.
4. **jazzmusicarchives.com** — useful condensed year-by-year list, especially for filling in 1980s–2000s.
5. **Encyclopedia.com** — useful condensed early-career list with labels.
6. **flatint.blogspot.com** ("flatint: Abdullah Ibrahim (Dollar Brand) — Discography") — a fan-compiled visual discography, useful for the obscure early period, explicitly notes it's non-exhaustive and was a work in progress (covered up to ~1980 as of last update).
7. **Rate Your Music, Album of the Year** — useful for cross-checking years/alternate titles, lower priority.

**Not yet done:** a full Discogs scrape sorted strictly by year; a targeted search for 2010s–2020s releases (his output in the last 15 years of his life is underrepresented in what surfaced this session).

## Compiled chronological list (as of this session — INCOMPLETE, see gaps below)

1. Duke Ellington Presents the Dollar Brand Trio (1963)
2. Anatomy of a South African Village (1965)
3. The Dream (recorded 1965, released later)
4. African Piano (1969)
5. African Sketchbook (1969)
6. This Is Dollar Brand (recorded 1965, released 1973)
7. Ancient Africa (recorded 1972, released 1974)
8. Sangoma (recorded/released 1973)
9. African Portraits (1973)
10. Good News from Africa (1974)
11. African Space Program (1974)
12. Underground in Africa (1974)
13. Mannenberg (1974)
14. Banyana (1976)
15. Cape Town Fringe (1977)
16. The Journey (1977)
17. Autobiography (recorded 1978)
18. Echoes from Africa (1979)
19. Africa: Tears and Laughter (1979)
20. African Marketplace (1980)
21. Live at Montreux (1980)
22. African Dawn (1982)
23. Desert Flowers (1982)
24. Ekaya (1983)
25. Zimbabwe (1983)
26. Water from an Ancient Well (1985)
27. South Africa (1986)
28. Mindif (1988)
29. Blues for a Hip King (1989)
30. African River (1989)
31. The Mountain (1989)
32. No Fear, No Die (1990)
33. Mantra Mode (1991)
34. Knysna Blue (1993)
35. African Sun (1994)
36. Yarona (1995)
37. Cape Town Flowers (1997)
38. African Suite (1999)
39. Cape Town Revisited (2000)
40. Ekapa Lodumo (2001)
41. African Magic (2002)
42. Senzo (2008)
43. Bombella (2009)
44. Sotho Blue (2010)
45. Mukashi / Once Upon a Time (recorded 2013, released 2014/2015)
46. The Song Is My Story (2014, solo piano/sax)
47. Dream Time (2019)
48. The Balance (2019, Gearbox, with nonet version of Ekaya)
49. Universal Silence (recorded 1972 with Don Cherry & Carlos Ward, released 2019, Lepo Glasbo)
50. Solotude (recorded live, solo, 86th birthday concert, no audience, 2020; released 2021/2022, Gearbox)
51. 3 (recorded Barbican Hall, London, July 15 2023; released January 26, 2024, Gearbox — two volumes, trio w/ Cleave Guyton Jr. & Noah Jackson)

### Known gaps / next steps
- **2024–2026 releases still unconfirmed.** Given he performed live as recently as March 27, 2026, check for any posthumous or late archival releases not yet indexed.
- 1974 alone reportedly included ~9 releases per AllMusic — list above may be missing some (e.g., "Memories" mentioned by AllMusic, not yet placed). Also "Voice of Africa" (1988, per jazzmusicarchives) not yet placed relative to Mindif/Blues for a Hip King.
- Need to verify recording-vs-release year convention before finalizing sort order (this list mixes both inconsistently — flagged per-entry where known).
- Discogs full release list (70 entries: 55 albums + 13 compilations) not yet fully cross-checked against this list — likely several omissions, especially obscure 1970s small-label releases.
- Name variants to search under: "Dollar Brand", "Abdullah Ibrahim", "Adolph(us) Johannes Brand".
- All About Jazz's discography page (sorted by label/year, e.g. "Gearbox Records, 2024", "Sunnyside Records, 2010/2011/2014/2015") suggests additional Sunnyside-era releases circa 2009-2015 not yet individually titled/confirmed in this list.

## Process notes for generalizing this into a tool

1. **Discography assembly step**: query Discogs (has an API), Wikipedia (artist discography category + individual album infoboxes), and AllMusic for a given artist; merge by normalized title; flag conflicts (different years/labels for similarly-named releases).
2. **Disambiguation step**: surface compilations/reissues/live-duplicate-of-studio-album cases for human review rather than auto-resolving — this is where automation alone produced an incomplete/ambiguous list even with good sources.
3. **Ordering step**: choose recording date when known and available across sources; fall back to release date; flag which was used per entry.
4. **Playlist-building step**: for each resolved title, query Spotify (or target service) search API, prefer original-label/era pressing where multiple versions exist, queue in order, log any title that fails to match cleanly for manual review.
5. **Output**: a reviewable manifest (title, year, source-of-truth, match confidence, streaming URI) before committing to a live playlist — i.e., human-in-the-loop checkpoint before the irreversible step.

## Context for this seed case

Abdullah Ibrahim (b. 1934, Cape Town, South Africa), South African jazz pianist/composer, died June 15, 2026, age 91, in Germany. Recorded under "Dollar Brand" early in career, adopted name Abdullah Ibrahim after converting to Islam in 1968. One of the most important figures in South African and global jazz; performed at Nelson Mandela's 1994 inauguration.

## Verification pass — 2026-06-16

Following import into Cowork, the flagged conflicts/gaps from the section above were checked via web search and a Discogs fetch. Findings (full detail and sources are in `discography.json`, which is now the up-to-date version — this section is a changelog, not a re-statement):

- **"Memories" and "African Breeze" (1974 cluster)**: both confirmed as real, distinct albums (not duplicates of anything else). Moved from `tentative` to `confirmed`. Recording/release details added.
- **"Blues for a Hip King" (1976 vs. 1989)**: not a conflict — the 1976 release is the original album; the 1989 release is the 4th volume of a compilation series ("The African Recordings") that reuses the title and also draws from *Underground in Africa* (1974), *Black Lightning* (1976), and *Dollar Brand Plays Sphere Jazz* (1962). Both entries kept, with the 1989 one now tagged as a compilation via a `relation` field rather than treated as a duplicate original.
- **"Desert Flowers" (1982 vs. 1992)**: the 1982 year was wrong. Confirmed release is July 1992 on Enja (ENJ 70112). Corrected and re-sorted into chronological position (was order 33, now order 44).
- **"The Dream" (1965 vs. 1979)**: confirmed as one recording (30 Jan 1965, Jazzhus Montmartre) with a 1979 vinyl reissue (also reissued 1980 and as a 1991 CD under "Dollar Brand Trio"). The 1979 entry is now tagged as a reissue via `relation` rather than a separate work.
- **Mukashi (Once Upon a Time)**: confirmed as a single album (Sunnyside, 2014; recorded 2012–13 in Bonn). The earlier "JAPO" label note was an error — JAPO is an unrelated ECM-affiliated label used on 1969's *African Piano* — and Discogs' 2013/2014 listings reflect promo vs. general release, not two regional editions.
- **2024–2026 / posthumous releases**: searched specifically; nothing found after *3* (2024). Reasonable given his death (15 June 2026, Prien am Chiemsee, Germany) was only confirmed the day before this check — worth rechecking in a few months.
- **Discogs full cross-check**: fetched the Discogs artist page (id 248560) directly. It confirms the same totals already cited here — 70 releases (55 albums + 13 compilations) — so the dataset's premise checks out, but a title-by-title diff against all 70 still hasn't been done (Discogs' release list is JS-paginated and wasn't fully enumerable by a plain fetch). This remains the top open item, flagged in `discography.json`'s `open_questions`, and is well-suited to the pipeline's planned Discogs API step rather than more manual searching.
- **Not re-investigated**: the "Voice of Africa" placement and the "Sunnyside-era 2009–2015" cluster mentioned above — these weren't part of `discography.json`'s explicit `open_questions` array and were left alone this pass.

Net effect: discography.json's `albums` array is unchanged in length (62 entries) but corrected, re-sorted, and annotated; its `open_questions` array now reflects only what's genuinely still unresolved.
