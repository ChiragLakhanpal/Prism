"""The deck's data (ticket 47; the 47 brief, sections 6 and 9.1): the values the slides at /present show, read from
the same dated measures snapshot as the proposal (ticket 46), by the same register keys, with the registries that
set the deck's design counts, the rubric's points, the panel's addresses and the demo package's recorded answers.

The deck never queries the warehouse. web/public/deck/data.json is built from docs/proposal/snapshot.json, which only
the workspace pull writes, and the screen tests read tests/fixtures/api/deck-data.json, built from the fixture
database and the made-up month in tests/proposal_seed.py. Expected values come from tests/ground_truth/values.toml,
docs/assessment.md and the seeds, never from the code under test.
"""

import json
import tomllib
from pathlib import Path

import pytest

from proposal_seed import merged
from strata import config
from strata.proposal import deck, register, snapshot

ROOT = Path(__file__).resolve().parents[1]
RECORDED = ROOT / "tests" / "fixtures" / "api"


def recorded_demo() -> dict:
    return {"comparables": json.loads((RECORDED / "comparables-ke-nwwda-541055.json").read_text()),
            "estimate": json.loads((RECORDED / "estimate-ke-nwwda-541055.json").read_text())}


def values() -> dict:
    with open(ROOT / "tests" / "ground_truth" / "values.toml", "rb") as handle:
        return tomllib.load(handle)


@pytest.fixture(scope="module")
def fixture_deck(fixture_db):
    return deck.build(merged(fixture_db), recorded_demo())


def test_with_no_snapshot_every_result_is_not_measured_and_the_registries_still_fill_the_deck():
    data = deck.build(None, None)
    assert data["pulled_on"] is None
    assert [key for key, found in data["results"].items() if found["measured"]] == []
    # The verifier runs six checks on every sentence (GLOSSARY.md, "Six checks").
    assert data["settings"]["check-count"]["value"] == 6
    assert data["checks"] == [1, 2, 3, 4, 5, 6]
    # config/slice.toml [demo_plan] and [showcase]: the demo package in NWWDA's plan of October 9, 2026, and P130164.
    demo = {key: value for key, value in data["demo"].items() if key not in ("links", "sentence", "question")}
    assert demo == {"step_reference": "KE-NWWDA-541055-CW-RFB", "project_id": "P156634",
                    "agency": "Northern Water Works Development Agency", "plan_date": "2026-10-09",
                    "plan_href": "/projects/P156634/procurement/northern-water-works-development-agency",
                    "comparables": None, "estimate": None}
    assert data["showcase"] == {"project_id": "P130164"}


def test_the_demo_slides_open_the_start_here_links_and_type_the_registrys_own_words():
    demo = deck.build(None, None)["demo"]
    # config/examples.toml [[start_here]], filled as Home fills them: the demo plan's check on its date, the package
    # planned from a sentence, and the showcase project's timeline.
    assert demo["links"] == {"checkPlan": "/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09",
                             "planPackage": "/packages?box=plan&example=rural_roads_kenya",
                             "wholeStory": "/projects/P130164/timeline"}
    # config/examples.toml [packages.rural_roads_kenya], the sentence that link fills into the box.
    assert demo["sentence"] == "rural roads, Kenya, about US$15 million"
    # config/slice.toml's smoke question, search-passages-icr-rebidding in evals/benchmark.yaml, on one line.
    assert demo["question"] == ("In P130164, why did so many works contracts have to go through rebidding, and what does "
                                "the completion report say about the estimates?")


@pytest.mark.parametrize("href", ["/packages?box=plan", "/packages?box=plan&example=no_such_example"])
def test_a_package_link_that_names_no_registered_example_stops_the_build(tmp_path, href):
    # Without this, the package demo's box would go blank with nothing to say why (the 106 review, round 2).
    registry = (ROOT / "config" / "examples.toml").read_text()
    edited = tmp_path / "examples.toml"
    edited.write_text(registry.replace('href = "/packages?box=plan&example=rural_roads_kenya"', f'href = "{href}"'))
    examples = config.load_examples(edited)
    with pytest.raises(deck.DeckError, match="planPackage"):
        deck._demo_links("northern-water-works-development-agency", examples)


def test_a_result_carries_its_measured_values_and_what_the_register_says_it_counts(fixture_deck):
    passed = fixture_deck["results"]["benchmark-passed"]
    # tests/dashboard_seed.py: the October 20 gate passed 45 of 52 benchmark questions.
    assert (passed["n"], passed["d"], passed["measured_on"], passed["run_id"]) == (45, 52, "2026-10-20", "gate-2")
    assert (passed["kind"], passed["noun"], passed["table"]) == ("Benchmark run", "benchmark questions",
                                                                  "strata.ops.evaluation_result")
    assert passed["name"].startswith("Benchmark questions that met their expected answer")


def test_every_result_the_deck_reads_is_defined_once_in_the_proposals_register(fixture_deck):
    defined = register.load_results()
    assert set(fixture_deck["results"]) <= set(defined)
    with pytest.raises(deck.DeckError, match="not-a-result"):
        deck.build(None, None, results=("passages", "not-a-result"))


def test_a_design_count_names_the_registry_it_counts_and_a_planning_choice_names_its_document():
    settings = deck.build(None, None)["settings"]
    # config/kpis.toml names three loops: knowledge, retrieval and estimates (docs/PLAN.md section 11).
    assert settings["loop-count"] == {"value": 3, "name": "Learning loops, each with its leading and lagging indicator",
                                      "where": "config/kpis.toml, the loops its indicators name", "kind": "Count"}
    # docs/PLAN.md section 11, Rollout: World Bank staff in two countries, then agencies, then the public.
    assert (settings["pilot-countries"]["value"], settings["pilot-countries"]["kind"]) == (2, "Setting")
    assert settings["rollout-phases"]["value"] == 3
    # docs/PLAN.md section 10: blamed risks are coded by two people, at five risks per package.
    assert (settings["hindsight-coders"]["value"], settings["risks-per-package"]["value"]) == (2, 5)
    # The spec's hindsight test: the baseline is "a checklist of the sector's five commonest risks", a setting of its
    # own (hindsight.checklist_size), not the risk table's length.
    assert settings["checklist-size"] == {"value": 5, "name": "Risks on the hindsight test's checklist, the sector's "
                                          "commonest", "where": "config/thresholds.toml, hindsight.checklist_size",
                                          "kind": "Setting"}


def test_the_rubric_points_are_the_assessments():
    rubric = deck.build(None, None)["rubric"]
    # docs/assessment.md, section 5: 30, 30, 25 and 15 points.
    assert [(row["name"], row["points"]) for row in rubric["dimensions"]] == [
        ("System and knowledge architecture", 30), ("Analytical and AI methodology", 30),
        ("Domain alignment and data use", 25), ("Operationalization and scalability", 15)]
    assert rubric["source"] == "docs/assessment.md"


def test_the_award_gap_is_the_known_gap_and_the_rows_by_year_must_agree(fixture_deck):
    # docs/proposal/results.toml, gap-contracts: neither awards dataset covers fiscal 2017 to 2019. The deck states the
    # known gap from config/sources.toml before the rows are measured too, as the Data readiness page's Gap row does.
    assert fixture_deck["award_gap"] == {"start": 2017, "end": 2019}
    assert deck.build(None, None)["award_gap"] == {"start": 2017, "end": 2019}
    rows = fixture_deck["results"]["award-rows-by-year"]
    stray = {**rows, "series": [*rows["series"], {**rows["series"][-1], "fiscal_year": 2018}]}
    with pytest.raises(deck.DeckError, match="fy2017_2019"):
        deck._award_gap(stray)


def test_the_demo_package_is_the_one_the_slice_names_with_its_recorded_answers(fixture_deck):
    demo = fixture_deck["demo"]
    assert demo["step_reference"] == "KE-NWWDA-541055-CW-RFB"
    counted = values()["comparables"]
    # values.toml [comparables]: 45 signed and four still open are the comparable packages; the three canceled are not.
    assert demo["comparables"]["counts"]["comparables"] == counted["signed"] + counted["still_open"]
    assert demo["estimate"]["abstention"]["reason"] == "outside_training"


def test_an_answer_recorded_for_another_package_is_refused():
    answers = recorded_demo()
    answers["estimate"]["package"]["step_reference"] = "KE-NWWDA-229129-CW-RFB"
    with pytest.raises(deck.DeckError, match="KE-NWWDA-541055-CW-RFB"):
        deck.build(None, answers)


def test_the_addresses_and_the_presenter_come_from_their_config_files():
    data = deck.build(None, None)
    assert data["urls"]["deck"] == data["urls"]["app"] + "/present"
    assert set(data["presenter"]) == {"name", "date"}


def test_the_research_talks_recorded_numbers_carry_their_day_how_and_kind():
    # Ticket 162 (.notes/deck3/brief.md, section 8): the ten numbers the research talk states that no query measures.
    recorded = deck.build(None, None)["recorded"]
    assert list(recorded) == ["lines-prism", "tests-prism", "lines-procintel", "tests-procintel", "isr-progress",
                              "wajir-progress", "late-awards", "kept-low", "kept-high", "tile-metres"]
    assert {found["kind"] for found in recorded.values()} == {"Recorded"}
    assert all(found["how"] and found["measured_on"] for found in recorded.values())
    # Both repositories counted the same way on November 5, 2026; P156634's ISR 19 gives only its month.
    assert (recorded["lines-prism"]["value"], recorded["tests-procintel"]["value"]) == (61653, 351)
    assert (recorded["isr-progress"]["form"], recorded["isr-progress"]["value"],
            recorded["isr-progress"]["measured_on"]) == ("percent", 85, "2026-03")
    # A ratio carries its parts and no value.
    assert {key: recorded["kept-high"].get(key) for key in ("n", "d", "value")} == {"n": 83, "d": 88, "value": None}


@pytest.mark.parametrize("old, new, says", [
    ('form = "ratio"\nn = 65', 'form = "share"\nn = 65', "form must be one of"),
    ("n = 65\nd = 71", "value = 65", "needs n and d"),
    ('measured_on = "2026-03"', 'measured_on = "March 2026"', "measured_on must be a day"),
    ('how = "P156634', 'note = "P156634', "keys I do not know"),
])
def test_a_recorded_entry_out_of_shape_stops_with_a_sentence(tmp_path, old, new, says):
    text = register.RECORDED_FILE.read_text()
    assert old in text
    edited = tmp_path / "recorded.toml"
    edited.write_text(text.replace(old, new, 1))
    with pytest.raises(register.RegisterError, match=says):
        register.load_recorded(edited)


def test_the_research_talks_settings_are_read_from_the_files_that_set_them():
    settings = deck.build(None, None)["settings"]
    with open(ROOT / "config" / "thresholds.toml", "rb") as handle:
        late = tomllib.load(handle)["research"]["late_award_days"]
    with open(ROOT / "config" / "research.toml", "rb") as handle:
        sources = tomllib.load(handle)["sources"]
    assert settings["late-award-days"]["value"] == late
    assert (settings["research-source-count"]["value"], settings["research-source-count"]["kind"]) == (
        sum(1 for source in sources.values() if source["enabled"]), "Count")
    assert settings["isr-reports"]["value"] == sources["isr_narrative"]["settings"]["reports"]


def test_the_research_talk_names_its_presenters_and_opens_the_demo_projects_research_tab():
    research = deck.build(None, None)["research"]
    # config/deck.toml [research]: both presenters, the day not set yet; config/slice.toml [demo_plan]: P156634.
    assert research == {"presenters": ["Chirag Lakhanpal", "Surya Yadav"], "date": None,
                        "demo": {"project_id": "P156634", "project_name": "Kenya Water and Sanitation Development Project",
                                 "href": "/projects/P156634/research"}}


def test_the_live_recording_asks_the_apps_own_routes_for_the_demo_package(fixture_db):
    import importlib.util
    from contextlib import contextmanager

    from strata.lakehouse.engine import DuckDBEngine

    spec = importlib.util.spec_from_file_location("record_demo_live", ROOT / "ops" / "proposal" / "record_demo_live.py")
    recorder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recorder)

    @contextmanager
    def reading(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    answers = recorder.record(reading, "not-a-real-key")
    demo = deck.build(None, answers)["demo"]
    assert demo["comparables"]["package"]["step_reference"] == "KE-NWWDA-541055-CW-RFB"
    counted = values()["comparables"]
    # values.toml [comparables]: 45 signed and four still open.
    assert demo["comparables"]["counts"]["comparables"] == counted["signed"] + counted["still_open"]
    assert demo["estimate"]["tool"] == "estimate_time"


def test_the_committed_deck_data_is_built_from_the_committed_snapshot():
    snap = snapshot.read() if snapshot.SNAPSHOT_FILE.exists() else None
    demo = json.loads(deck.DEMO_FILE.read_text()) if deck.DEMO_FILE.exists() else None
    assert json.loads(deck.DECK_FILE.read_text()) == deck.build(snap, demo), (
        "web/public/deck/data.json is out of date. Run uv run python -m strata.proposal deck.")


def test_the_screen_tests_deck_data_is_built_from_the_fixture(fixture_deck):
    assert json.loads((RECORDED / "deck-data.json").read_text()) == fixture_deck, (
        "tests/fixtures/api/deck-data.json is out of date. Run uv run --frozen python tests/record_deck_api.py.")


def test_a_count_carries_the_column_the_register_counts(fixture_deck):
    # The data slide said Prism built 2,466 contracts from award notices, then 1,722: those were the ones in local
    # currency (n). The register counts every contract built from the notices (count_of = "d"), as the proposal does.
    assert fixture_deck["results"]["gap-contracts"]["count_of"] == "d"
    assert fixture_deck["results"]["passages"]["count_of"] == "n"
