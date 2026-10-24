"""get_lessons at seam 2, the tool contract (ticket 29): current lessons at their versions, with their evidence
ids, ranked by fit and evidence and never by use, each tagged with the edition of the procurement rules its
project followed.

The fixture's queue has no decided lesson, so each test first has two people decide lessons on a copy of the
fixture database (tests/lesson_scenario.py), as the review routes would. Expected values come from
tests/ground_truth/values.toml.
"""

import datetime as dt
import tomllib
from pathlib import Path

import pytest

import lesson_scenario as scenario
from strata.lakehouse.engine import DuckDBEngine
from strata.tools import registry

ROOT = Path(__file__).resolve().parents[1]
VALUES = {value["id"]: value for value in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
DECIDED = dt.date(2026, 10, 27)


@pytest.fixture(scope="module")
def library(fixture_db, tmp_path_factory):
    """The rebidding lesson, the permits lesson and IEG's lesson, each added to the library by two people."""
    database = scenario.copy_of(fixture_db, tmp_path_factory.mktemp("library"))
    for passage in (scenario.REBIDDING, scenario.PERMITS, scenario.IEG_LESSON):
        scenario.decide(database, passage, DECIDED)
    return database


def get_lessons(database, **arguments):
    with DuckDBEngine.open(database) as engine:
        return registry.call("get_lessons", {"as_of": "2026-10-28", **arguments},
                             registry.Context(engine=engine, viewer=scenario.ASHA))


def statements(result) -> list[str]:
    return [row["statement"] for row in result["rows"]]


def test_the_lesson_that_fits_the_query_comes_first_with_its_evidence_ids(library):
    result = get_lessons(library, query="works contract estimates market rates rebidding")

    first = result["rows"][0]
    assert first["statement"] == "Base works estimates on market rates to avoid rebidding"
    assert first["version"] == 1
    assert first["evidence_id"].startswith("strata.ops.lesson_versions:")
    assert [(source["evidence_id"], source["page"]) for source in first["evidence"]] == [
        ("strata.gold.passage:31525018/v1/54", VALUES["icr-para-54"]["pdf_page"]),
        ("strata.gold.passage:34056616/v2/10.b", VALUES["icr-review-2023-restates-para-54"]["pdf_page"])]
    assert first["ieg_status"] == "restated"


def test_with_no_query_the_stronger_evidence_ranks_first(library):
    result = get_lessons(library)

    # IEG's own lesson and the lesson IEG restated come before the one that rests on the ICR alone.
    assert [row["ieg_status"] for row in result["rows"]] == ["ieg_lesson", "restated", "not_restated"]


def test_the_order_is_the_same_however_often_each_lesson_was_used(library):
    before = statements(get_lessons(library))
    last = get_lessons(library)["rows"][-1]
    with DuckDBEngine.open(library) as engine:
        engine.insert_rows("strata.ops.lesson_uses", ("lesson_id", "version", "used_in", "used_by", "used_at",
                                                      "public_from"),
                           [(last["lesson_id"], 1, f"run-{n}", "ana.example@worldbank.org",
                             dt.datetime(2026, 10, 27, 16, tzinfo=dt.UTC), DECIDED) for n in range(50)])

    assert statements(get_lessons(library)) == before


def test_each_lesson_carries_the_edition_of_the_rules_its_project_followed(library):
    """P130164's PAD names the January 2011 Guidelines (values.toml, pad-procurement-guidelines)."""
    result = get_lessons(library)

    assert {row["edition"]["key"] for row in result["rows"]} == {"guidelines_2011"}
    assert all("January 2011" in row["edition"]["name"] for row in result["rows"])


def test_as_of_a_date_before_any_decision_there_are_no_lessons(library):
    result = get_lessons(library, as_of=(DECIDED - dt.timedelta(days=1)).isoformat())

    assert result["rows"] == []
    assert result["abstention"]["reason"] == "no_lessons"


def test_a_filter_by_risk_factor_keeps_only_the_lessons_tagged_with_it(library):
    result = get_lessons(library, risk_factor="permits_before_award")

    assert sorted(statements(result)) == ["Get land and forest permits before awarding works contracts",
                                          "Put forest and other permits in place before awarding contracts"]
    assert get_lessons(library, risk_factor="not_a_factor")["abstention"]["reason"] == "unknown_risk_factor"
