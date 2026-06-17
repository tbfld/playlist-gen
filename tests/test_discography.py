from pathlib import Path

from playlist_gen.discography import load_discography, primary_albums, relation_entries

FIXTURE = Path(__file__).parent / "fixtures" / "abdullah-ibrahim-discography.json"


def test_loads_seed_case():
    data = load_discography(FIXTURE)
    assert data["artist"] == "Abdullah Ibrahim"
    assert len(data["albums"]) == 62


def test_primary_albums_excludes_relations():
    data = load_discography(FIXTURE)
    primary = primary_albums(data)
    titles = {a["title"] for a in primary}
    assert "The Dream (1979 reissue)" not in titles
    assert "Blues for a Hip King (1989 compilation, The African Recordings)" not in titles
    assert len(primary) == 60


def test_chronological_order():
    data = load_discography(FIXTURE)
    primary = primary_albums(data)
    years = [a["year"] for a in primary]
    assert years == sorted(years)
    orders = [a["order"] for a in primary]
    assert orders == sorted(orders)


def test_late_period_gap_titles_present():
    """Regression test for the 'late-period gap' failure mode described in
    README.md: a naive first pass undershot output from the last ~15 years
    of the artist's life even though sources for it existed."""
    data = load_discography(FIXTURE)
    titles = {a["title"] for a in data["albums"]}
    assert "Solotude" in titles
    assert "Universal Silence" in titles


def test_relation_entries_tagged_not_duplicated():
    data = load_discography(FIXTURE)
    relations = relation_entries(data)
    assert len(relations) == 2
    assert all("relation" in a for a in relations)
    assert all(a["relation"]["type"] in ("reissue", "compilation") for a in relations)
