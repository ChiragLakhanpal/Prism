"""Ticket 147: the deep research item store (strata.ops.research_runs and research_items) and the demo seed
(ops/research/seed.py), which loads the items the sample brief cites for P156634 as one run dated November 5, 2026.

The store writes a run's items first and its row last through the engine it is given, as the uploads store does: the
app's own on the workspace (a fake warehouse here would add nothing a DuckDB file does not show), the local DuckDB
file the drafts use on this computer."""

import datetime as dt
import sys

import pytest
from research_world import NOV_5, ROOT, research_tables

from strata.lakehouse.engine import DuckDBEngine, EngineError
from strata.research.items import ITEM_KEYS
from strata.research.store import ResearchStore, Run

sys.path.insert(0, str(ROOT / "ops" / "research"))

import seed as research_seed  # noqa: E402


def item(key: str, read_on: str = "2026-11-05") -> dict:
    return {"evidence_id": f"strata.research.item:P156634/mastodon/{key}", "public_from": "2026-10-01",
            "source": {"key": "mastodon", "label": "Mastodon", "kind": "social", "license": "Each post belongs to its "
                       "author.", "url_of_source": "https://mastodon.social"}, "kind": "social",
            "title": "A post", "text": "Wajir's water", "url": f"https://mastodon.social/@a/{key}",
            "published": "2026-10-01", "date_known": True, "observed": None,
            "location": {"geo_loc_id": "178440", "name": "Wajir District", "latitude": 1.75, "longitude": 40.01667},
            "image_urls": [], "author": "A person", "read_on": read_on}


def run(run_id: str, day: dt.date = dt.date(2026, 11, 5)) -> Run:
    started = dt.datetime.combine(day, dt.time(9), tzinfo=dt.UTC)
    return Run(run_id=run_id, project_id="P156634", started=started, as_of=day, sources_asked=("mastodon",),
               reached=("mastodon",), finished=started, viewer="viewer-1", note="A test run.",
               source_notes={"mastodon": {"status": "200", "note": "Read.", "items": 1}})


@pytest.fixture
def store():
    engine = research_tables()
    yield ResearchStore(lambda: engine.cursor())
    engine.close()


def test_a_run_and_its_items_are_kept_and_read_back_in_the_one_shape(store):
    assert store.save(run("run-1"), [item("1")])

    kept = store.run("run-1")
    assert (kept.project_id, kept.as_of, kept.reached, kept.viewer) == ("P156634", dt.date(2026, 11, 5),
                                                                        ("mastodon",), "viewer-1")
    assert kept.source_notes["mastodon"]["items"] == 1
    assert store.items("run-1") == [item("1")]
    assert list(store.items("run-1")[0]) == list(ITEM_KEYS)
    assert store.items("no-such-run") == []


def test_an_item_read_again_in_a_later_run_keeps_its_first_read_on(store):
    store.save(run("run-1"), [item("1", read_on="2026-11-05")])
    store.save(run("run-2", dt.date(2026, 11, 9)), [item("1", read_on="2026-11-09"), item("2", read_on="2026-11-09")])

    assert {entry["evidence_id"][-1]: entry["read_on"] for entry in store.items("run-2")} == {
        "1": "2026-11-05", "2": "2026-11-09"}
    assert [entry.run_id for entry in store.runs("P156634")] == ["run-2", "run-1"]


def test_a_run_kept_already_is_not_written_again(store):
    assert store.save(run("run-1"), [item("1")])
    assert not store.save(run("run-1"), [item("1"), item("2")])

    assert len(store.items("run-1")) == 1


def test_a_save_that_fails_part_way_leaves_no_item_a_reader_could_find():
    engine = research_tables()
    engine.run("DROP TABLE strata.ops.research_runs")  # the run's row cannot be written
    store = ResearchStore(lambda: engine.cursor())

    with pytest.raises(EngineError):
        store.save(run("run-1"), [item("1")])

    assert engine.run("SELECT count(*) FROM strata.ops.research_items").rows == ((0,),)


def test_the_seed_loads_the_sample_s_items_as_one_run_of_november_5_2026_and_a_second_seed_changes_nothing(
        fixture_db, tmp_path):
    from strata.lakehouse import catalog

    path = tmp_path / "state.duckdb"
    with DuckDBEngine.open(path) as engine:
        catalog.build(engine)
    store = ResearchStore(lambda: DuckDBEngine.open(path))
    said = []

    assert research_seed.seed(store, "P156634", fixture_db=fixture_db, say=said.append)
    assert not research_seed.seed(store, "P156634", fixture_db=fixture_db, say=said.append)

    kept = store.run("seed:P156634:2026-11-05")
    assert kept.as_of == dt.date(2026, 11, 5) and kept.viewer == "prism"
    assert "read on November 5, 2026" in kept.note
    assert "gdelt_news" in kept.sources_asked and "gdelt_news" not in kept.reached
    assert kept.source_notes["gdelt_news"]["note"] == "GDELT limited calls from this network."
    assert kept.source_notes["inspection_panel"]["note"] == ("The Inspection Panel's register lists 197 cases, 0 of "
                                                             "them naming P156634.")
    assert "Eastleigh Voice's page answered a bot check page" in kept.source_notes["outlet_feeds"]["note"]
    items = store.items(kept.run_id)
    counts = {key: sum(entry["source"]["key"] == key for entry in items) for key in kept.sources_asked}
    assert counts == {"isr_narrative": 7, "procurement_notices": 7, "gdelt_news": 0, "outlet_feeds": 14,
                      "inspection_panel": 0, "sentinel2_mosaic": 1, "mastodon": 0}
    assert all(entry["read_on"] == "2026-11-05" for entry in items)
    by_title = {entry["title"]: entry for entry in items}
    assert "Baricho" in by_title["Solar water project set to cut power costs, improve supply in Kilifi"]["text"]
    eastleigh = by_title["Mombasa water project sparks outrage in Mwembe Tayari over job promises, disruptions"]
    assert eastleigh["text"] == eastleigh["title"] and eastleigh["date_known"] is False
    record = by_title["World Bank project record: Coastal Region Water Security and Climate Resilience Project (P513697)"]
    assert record["published"] == "2026-03-20"
    assert "Kept the run seed:P156634:2026-11-05 with 29 items" in said[0] and "kept already" in said[1]
    assert NOV_5.date() == kept.as_of
