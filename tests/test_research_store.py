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
            "image_urls": [], "author": "A person", "read_on": read_on, "team": None}


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

    fixture = lambda: DuckDBEngine.open(fixture_db, read_only=True)  # noqa: E731
    assert research_seed.seed(store, "P156634", bank=fixture, say=said.append)
    assert not research_seed.seed(store, "P156634", bank=fixture, say=said.append)

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
                      "inspection_panel": 0, "sentinel2_mosaic": 1, "mastodon": 0, "site_conditions": 3,
                      "agency_statements": 28, "sanctions": 0}
    # Ticket 154's sources are asked, and the run keeps every item their readers give, though the sample lists none:
    # GDACS's 3 events for Kenya and the agencies' 28 entries, each source's note counting its items. With no copy
    # of the sanctions list under data/research/sanctions/, the check did not run, and the run's note says so.
    assert kept.source_notes["site_conditions"]["note"] == ("GDACS lists 3 events for Kenya in the window, 3 of them "
                                                            "naming it.")
    assert (kept.source_notes["site_conditions"]["items"], kept.source_notes["agency_statements"]["items"]) == (3, 28)
    assert "sanctions" not in kept.reached
    assert kept.source_notes["sanctions"]["note"] == ("The sanctions check did not run: the list needs a download "
                                                      "from the page.")
    assert all(entry["read_on"] == "2026-11-05" for entry in items)
    by_title = {entry["title"]: entry for entry in items}
    assert "Baricho" in by_title["Solar water project set to cut power costs, improve supply in Kilifi"]["text"]
    eastleigh = by_title["Mombasa water project sparks outrage in Mwembe Tayari over job promises, disruptions"]
    assert eastleigh["text"] == eastleigh["title"] and eastleigh["date_known"] is False
    record = by_title["World Bank project record: Coastal Region Water Security and Climate Resilience Project (P513697)"]
    assert record["published"] == "2026-03-20"
    assert "Kept the run seed:P156634:2026-11-05 with 60 items" in said[0] and "kept already" in said[1]
    assert NOV_5.date() == kept.as_of


# Ticket 152: the seed reads the World Bank's own items through the engine the store writes to (on the workspace,
# strata.gold on the warehouse), takes --project more than once or --all, and uses a sample's own sites for the
# Sentinel-2 grids when the project's record has no locations.

PASSAGE = "40114539-p2-s4"  # the ISR passage the sample cites first


def test_the_seed_reads_the_isr_passages_and_notices_through_the_store_s_engine(fixture_db, tmp_path):
    import shutil

    warehouse = tmp_path / "warehouse.duckdb"  # stands for the workspace: the Bank's records and the research tables
    shutil.copy(fixture_db, warehouse)
    with DuckDBEngine.open(warehouse) as engine:
        engine.run("UPDATE strata.gold.passage SET text = text || ' As the warehouse holds it.' "
                   "WHERE document_id = '40114539' AND pdf_page = 2 AND paragraph = 's4'")
    store = ResearchStore(lambda: DuckDBEngine.open(warehouse))

    assert research_seed.seed(store, "P156634", say=lambda _: None)

    items = store.items("seed:P156634:2026-11-05")
    counts = {key: sum(entry["source"]["key"] == key for entry in items)
              for key in ("isr_narrative", "procurement_notices")}
    assert counts == {"isr_narrative": 7, "procurement_notices": 7}
    [passage] = [entry for entry in items if entry["evidence_id"].endswith(PASSAGE)]
    assert passage["text"].endswith("As the warehouse holds it.")


def test_all_seeds_every_sample_file_into_the_state_file(fixture_db, tmp_path, monkeypatch):
    import shutil

    samples = tmp_path / "samples"
    samples.mkdir()
    shutil.copy(ROOT / "ops" / "research" / "sample_P156634.toml", samples)
    (samples / "sample_P127203.toml").write_text('project = "P127203"\nas_of = 2026-11-05\ncited = []\n')
    monkeypatch.setattr(research_seed, "SAMPLES", samples)
    monkeypatch.setattr(research_seed, "FIXTURE_DB", fixture_db)
    state = tmp_path / "state.duckdb"

    assert research_seed.main(["--all", "--state-file", str(state)], environ={}) == 0

    with DuckDBEngine.open(state) as engine:
        kept = engine.run("SELECT run_id FROM strata.ops.research_runs ORDER BY run_id").rows
    assert kept == (("seed:P127203:2026-11-05",), ("seed:P156634:2026-11-05",))


def test_project_may_be_named_more_than_once(tmp_path):
    assert research_seed.projects_named(["--project", "P156634", "--project", "P127203"]) == ["P156634", "P127203"]
    assert research_seed.projects_named(["--all"], samples=ROOT / "ops" / "research") == research_seed.sample_projects()
    assert "P156634" in research_seed.sample_projects()


def test_a_sample_s_sites_get_grids_beside_the_record_s_locations():
    from dataclasses import replace

    from strata.research.project import project_facts

    facts = project_facts("P156634")
    sample = {"sites": [{"name": "Baricho well field", "latitude": -3.1, "longitude": 39.8}]}

    assert research_seed.with_sites(facts, {}) == facts
    sited = research_seed.with_sites(facts, sample)
    assert sited.locations[:-1] == facts.locations
    bare = research_seed.with_sites(replace(facts, locations=()), sample)
    assert [(site.geo_loc_id, site.name, site.latitude, site.longitude) for site in bare.locations] == [
        ("site-1", "Baricho well field", -3.1, 39.8)]


def test_a_closed_project_s_sample_seeds_its_sites_grids_a_notice_by_key_and_notes_what_it_could_not_find(
        fixture_db, tmp_path, monkeypatch):
    """P130164 closed on December 31, 2018: its notices are years older than the reader's window, its record names
    one location, and its sample adds three sites."""
    samples = tmp_path / "samples"
    samples.mkdir()
    with DuckDBEngine.open(fixture_db, read_only=True) as fixture:
        [(notice,)] = fixture.run("SELECT max(notice_id) FROM strata.gold.notice "
                                  "WHERE project_id = 'P130164' AND notice_type = 'Contract Award'").rows
    (samples / "sample_P130164.toml").write_text(f"""project = "P130164"
as_of = 2026-11-05
sites = [{{ name = "Deeg", latitude = 27.4773321, longitude = 77.3257027 }}]
[[cited]]
number = 1
items = [
  {{ source = "procurement_notices", key = "{notice}" }},
  {{ source = "procurement_notices", key = "OP00999999" }},
  {{ source = "sentinel2_mosaic", key = "1258899-2018-2025" }},
  {{ source = "sentinel2_mosaic", key = "site-1-2018-2025" }},
]
""")
    said = []

    run, items = research_seed.sample_run("P130164", DuckDBEngine.open(fixture_db, read_only=True), samples=samples,
                                          say=said.append)

    # Beside the sample's items, the run keeps GDACS's 11 events for India, which the sample does not list.
    keys = sorted(item["evidence_id"].rsplit("/", 1)[-1] for item in items
                  if item["source"]["key"] != "site_conditions")
    assert keys == sorted([notice, "1258899-2018-2025", "site-1-2018-2025"])
    assert sum(item["source"]["key"] == "site_conditions" for item in items) == 11
    deeg = next(item for item in items if item["evidence_id"].endswith("site-1-2018-2025"))
    assert deeg["location"]["name"] == "Deeg" and len(deeg["image_urls"]) == 2
    assert "OP00999999" in run.source_notes["procurement_notices"]["note"] and "OP00999999" in said[0]
