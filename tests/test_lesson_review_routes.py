"""The lesson review queue at seam 3, through the HTTP routes (ticket 29; docs/PLAN.md section 11, "Lesson
governance").

Strata proposes; an accredited procurement specialist recommends; a different lead procurement specialist
decides, each with a reason; nobody recommends or decides on a lesson from their own project. The roles
come from tests/fixtures/roles.toml, the viewer from the headers the Databricks App forwards, and the
reviewers' acts go to a copy of the fixture database, as the viewer.

Expected values come from tests/ground_truth/values.toml and the 29 design brief's section 13.
"""

import asyncio
import datetime as dt
import shutil
import tomllib
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

from strata.config import load_roles
from strata.knowledge.lessons.review import LessonReview
from strata.lakehouse.engine import DuckDBEngine
from strata.server.app import create_app

ROOT = Path(__file__).resolve().parents[1]
ROLES = load_roles(ROOT / "tests" / "fixtures" / "roles.toml")
VALUES = {value["id"]: value for value in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
TODAY = dt.date(2026, 10, 27)


def viewer(email: str) -> dict:
    return {"X-Forwarded-Email": email, "X-Forwarded-User": f"id-{email}", "X-Forwarded-Access-Token": "not-a-real-token"}


ANA = viewer("ana.example@worldbank.org")  # in no group
ASHA = viewer("asha.raman@worldbank.example")  # accredited, South Asia
LEELA = viewer("leela.iyer@worldbank.example")  # lead, South Asia, works on P130164
OMAR = viewer("omar.haddad@worldbank.example")  # lead, South Asia
WANJIRU = viewer("wanjiru.kamau@worldbank.example")  # lead, Eastern and Southern Africa


@pytest.fixture
def database(fixture_db, tmp_path):
    target = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, target)
    return target


@pytest.fixture
def app(database):
    @contextmanager
    def engine_for(_viewer):
        with DuckDBEngine.open(database) as engine:
            yield engine

    review = LessonReview(ROLES, today=lambda: TODAY,
                          now=lambda: dt.datetime.combine(TODAY, dt.time(14, 0), tzinfo=dt.UTC))
    return create_app(engine_for=engine_for, lessons=review)


def call(app, method, path, headers=None, **options):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.request(method, path, headers=headers or {}, **options)
    return asyncio.run(go())


def query(path, sql, **params):
    with DuckDBEngine.open(path, read_only=True) as engine:
        result = engine.run(sql, params)
        return [dict(zip(result.columns, row, strict=True)) for row in result.rows]


def item_for(app, headers, paragraph_passage: str) -> dict:
    """The queue row of the proposal from a passage, as the viewer sees it."""
    queue = call(app, "GET", "/api/lessons/review", headers).json()
    rows = queue["groups"]["you"] + queue["groups"]["others"]
    [row] = [row for row in rows if row["source"]["passage_id"] == paragraph_passage]
    return row


def act(app, headers, item_id, verb, **body):
    return call(app, "POST", f"/api/lessons/review/{item_id}/{verb}", headers, json=body)


REBIDDING = "31525018/v1/54"


# ── Who sees the queue ───────────────────────────────────────────────────

def test_someone_who_is_not_a_lesson_reviewer_gets_a_permission_error_and_no_queue_tab(app):
    item = item_for(app, ASHA, REBIDDING)

    assert call(app, "GET", "/api/lessons/me", ANA).json()["tabs"] == ["library"]
    for method, path in (("GET", "/api/lessons/review"), ("GET", f"/api/lessons/review/{item['item_id']}")):
        refused = call(app, method, path, ANA)
        assert (refused.status_code, refused.json()["code"]) == (403, "not_a_reviewer")
    refused = act(app, ANA, item["item_id"], "recommend", expected_stage="recommendation", outcome="add", reason="Yes.")
    assert (refused.status_code, refused.json()["code"]) == (403, "not_a_reviewer")


def test_a_lesson_reviewer_sees_the_queue_tab_with_the_items_waiting_in_their_region(app):
    me = call(app, "GET", "/api/lessons/me", ASHA).json()
    queue = call(app, "GET", "/api/lessons/review", ASHA).json()

    assert me["tabs"] == ["library", "review"]
    assert (me["regions"], me["waiting"]) == (["South Asia"], 3)
    assert [row["stage"] for row in queue["groups"]["you"]] == ["recommendation"] * 3
    assert queue["groups"]["others"] == []
    assert call(app, "GET", "/api/lessons/me", WANJIRU).json()["waiting"] == 0


# ── Two people, and recusal ──────────────────────────────────────────────

def test_the_same_person_cannot_both_recommend_and_decide(app):
    item = item_for(app, OMAR, REBIDDING)
    recommended = act(app, OMAR, item["item_id"], "recommend", expected_stage="recommendation", outcome="add",
                      reason="The quote shows the cost of low estimates.")

    refused = act(app, OMAR, item["item_id"], "decide", expected_stage="decision", outcome="add",
                  reason="I recommended it, and I agree.")

    assert recommended.status_code == 200
    assert (refused.status_code, refused.json()["code"]) == (403, "same_person")
    assert item_for(app, OMAR, REBIDDING)["can"] == {"act": None, "reason_code": "same_person", "values": {}}


def test_nobody_can_recommend_or_decide_on_a_lesson_from_their_own_project(app):
    item = item_for(app, ASHA, REBIDDING)
    own = act(app, LEELA, item["item_id"], "recommend", expected_stage="recommendation", outcome="add", reason="Yes.")
    act(app, ASHA, item["item_id"], "recommend", expected_stage="recommendation", outcome="add", reason="Yes.")

    refused = act(app, LEELA, item["item_id"], "decide", expected_stage="decision", outcome="add", reason="Yes.")

    assert (own.status_code, own.json()["code"]) == (403, "own_project")
    assert (refused.status_code, refused.json()["code"]) == (403, "own_project")
    assert refused.json()["values"]["pid"] == "P130164"


def test_an_act_on_a_stage_the_item_has_left_is_refused_as_stale_with_the_new_state(app):
    item = item_for(app, ASHA, REBIDDING)
    act(app, ASHA, item["item_id"], "recommend", expected_stage="recommendation", outcome="add", reason="Yes.")

    stale = act(app, OMAR, item["item_id"], "recommend", expected_stage="recommendation", outcome="reject",
                reason="It repeats what everyone knows.")

    assert (stale.status_code, stale.json()["code"]) == (409, "stale")
    assert stale.json()["item"]["stage"] == "decision"


# ── Decisions ────────────────────────────────────────────────────────────

def test_a_decision_makes_the_lesson_current_at_version_1_with_both_names_reasons_and_dates(app, database):
    item = item_for(app, ASHA, REBIDDING)
    act(app, ASHA, item["item_id"], "recommend", expected_stage="recommendation", outcome="add",
        reason="The ICR and IEG both say it.")

    decided = act(app, OMAR, item["item_id"], "decide", expected_stage="decision", outcome="add",
                  reason="Clear evidence from two reports.")

    assert decided.status_code == 200
    [version] = query(database, "SELECT * FROM strata.ops.lesson_versions")
    assert (version["version"], version["state"], version["statement"]) == (
        1, "current", "Base works estimates on market rates to avoid rebidding")
    assert (version["recommended_by_name"], version["decided_by_name"]) == ("Asha Raman", "Omar Haddad")
    assert (version["recommended_reason"], version["reason"]) == ("The ICR and IEG both say it.",
                                                                    "Clear evidence from two reports.")
    assert version["decided_on"] == TODAY
    # The ICR became public on November 2, 2019 (values.toml, icr-disclosed): 2,551 days before October 27, 2026.
    assert VALUES["icr-disclosed"]["value"] == dt.date(2019, 11, 2)
    assert version["days_from_publication"] == 2551

    history = call(app, "GET", f"/api/lessons/review/{item['item_id']}", ASHA).json()["history"]
    acts = [(event["event"], event.get("name"), event.get("reason"), event["on"]) for event in history
            if event["event"] in ("recommended", "decided")]
    assert acts == [("recommended", "Asha Raman", "The ICR and IEG both say it.", TODAY.isoformat()),
                    ("decided", "Omar Haddad", "Clear evidence from two reports.", TODAY.isoformat())]

    library = call(app, "GET", "/api/lessons", ANA).json()
    [lesson] = library["lessons"]
    assert (lesson["statement"], lesson["version"], lesson["ieg_status"]) == (
        "Base works estimates on market rates to avoid rebidding", 1, "restated")
    assert [(source["doc_short"], source["page"]) for source in lesson["evidence"]] == [("ICR", 23), ("ICR Review", 13)]


def test_a_rejection_keeps_its_reason_and_adds_nothing_to_the_library(app, database):
    item = item_for(app, ASHA, REBIDDING)
    act(app, ASHA, item["item_id"], "recommend", expected_stage="recommendation", outcome="reject",
        reason="It names no step to take.")

    rejected = act(app, OMAR, item["item_id"], "decide", expected_stage="decision", outcome="reject",
                   reason="Too general to act on.")

    assert rejected.status_code == 200
    assert query(database, "SELECT * FROM strata.ops.lesson_versions") == []
    reasons = [row["reason"] for row in query(database, "SELECT reason FROM strata.ops.lesson_review_acts "
                                                        "WHERE item_id = :item_id ORDER BY acted_at",
                                              item_id=item["item_id"])]
    assert reasons == ["It names no step to take.", "Too general to act on."]
    decided = call(app, "GET", "/api/lessons/review", ASHA).json()["decided"]["rows"]
    assert [(row["item_id"], row["outcome"]) for row in decided] == [(item["item_id"], "rejected")]


def test_any_lesson_reviewer_can_ask_for_a_re_check_once_while_one_is_open(app):
    item = item_for(app, ASHA, REBIDDING)
    act(app, ASHA, item["item_id"], "recommend", expected_stage="recommendation", outcome="add", reason="Yes.")
    act(app, OMAR, item["item_id"], "decide", expected_stage="decision", outcome="add", reason="Yes.")
    [lesson] = call(app, "GET", "/api/lessons", ASHA).json()["lessons"]

    asked = call(app, "POST", f"/api/lessons/{lesson['lesson_id']}/recheck", WANJIRU,
                 json={"reason": "The 2025 Regulations changed how estimates are made."})
    again = call(app, "POST", f"/api/lessons/{lesson['lesson_id']}/recheck", ASHA, json={"reason": "Again."})
    refused = call(app, "POST", f"/api/lessons/{lesson['lesson_id']}/recheck", ANA, json={"reason": "Me too."})

    assert asked.status_code == 200
    assert (again.status_code, again.json()["code"]) == (409, "recheck_open")
    assert (refused.status_code, refused.json()["code"]) == (403, "not_a_reviewer")
    [card] = call(app, "GET", "/api/lessons", ANA).json()["lessons"]
    assert card["rechecking_since"] == TODAY.isoformat()


# ── The screens' recorded answers ────────────────────────────────────────

def test_the_screens_recorded_lesson_answers_are_what_the_routes_answer(fixture_db, tmp_path):
    """tests/record_lessons_api.py writes the answers the Lessons screens' tests and the gallery serve, from one
    story on the fixture; the routes must still answer with them word for word."""
    from record_lessons_api import answers

    for name, text in answers(tmp_path).items():
        assert text == (ROOT / "tests" / "fixtures" / "api" / name).read_text(), f"{name} is out of date"
