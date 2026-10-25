"""Planned dates for an implementing agency's upload, and the STEP rows CSV, at seams 2 and 3 (ticket 38).

An officer drafts planned dates from their team's upload through POST /api/drafts (kind step_rows). No model writes
them: estimate_time dates every step of every activity from the delay model, the verifier checks every date and count
against what it returned, and only then is the draft saved with the team. The officer checks it and exports STEP rows.

Two databases make the stories:

- On the fixture, every activity of the October 9, 2026 plan gets each STEP step's count of comparable packages, and
  every step abstains, because none has min_comparables of them (config/thresholds.toml), so nothing is saved.
- On ticket 27's hand-made set (tests/step_set.py), where the target package's five steps can be dated, an upload of
  the target with its own planned dates gets tests/ground_truth/values.toml's [step_dates] dates, worked out by hand.
"""

import csv
import datetime as dt
import io
import json
import tomllib
from contextlib import contextmanager
from pathlib import Path

import pytest
import step_set
from test_uploads import AMINA, BARAKA, CHEGE, DANA, FIXTURE, GROUPS, call, roles, upload

from strata.config import load_draft_kinds, load_thresholds
from strata.drafts.store import DraftStore
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine
from strata.reader.step_columns import registry as step_columns
from strata.server.access import Access, StaticGroups
from strata.server.app import create_app
from strata.uploads.store import UploadStore

ROOT = Path(__file__).resolve().parents[1]
DATES = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["step_dates"]
MIN = int(load_thresholds().value("time_estimate.min_comparables"))
HAND_PROJECT = "P900003"  # a project whose record names team A's agency, beside the hand-made set's packages
NWWDA = "Northern Water Works Development Agency"


def events(text: str) -> list[tuple[str, dict]]:
    found = []
    for block in text.split("\n\n"):
        lines = [line for line in block.splitlines() if line and not line.startswith(":")]
        if lines:
            found.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return found


@pytest.fixture
def state(tmp_path):
    path = tmp_path / "state.duckdb"
    with DuckDBEngine.open(path) as engine:
        catalog.build(engine)
    return path


def app_on(database, state, today, at):
    @contextmanager
    def reading(viewer):
        with DuckDBEngine.open(database, read_only=True) as engine:
            yield engine

    numbers = iter(range(1, 100))
    return create_app(engine_for=reading, uploads=UploadStore(lambda: DuckDBEngine.open(state)),
                      drafts=DraftStore(lambda: DuckDBEngine.open(state)), access=Access(roles(), StaticGroups(GROUPS)),
                      today=lambda: today, now=lambda: at, new_upload_id=lambda: f"upl-{next(numbers):012d}",
                      new_draft_id=lambda: f"draft-{next(numbers):04d}", new_run_id=lambda: "run-0001")


def draft(app, headers, source, key="key-1"):
    sent = events(call(app, "POST", "/api/drafts", headers, json={"kind": "step_rows", "source": source,
                                                                   "idempotency_key": key}).text)
    made = [data["draft_id"] for kind, data in sent if kind == "draft"]
    return sent, made[0] if made else None


# ── On the fixture: every step names its count, and none has enough ──────

def test_on_the_fixture_every_step_of_every_activity_names_its_comparables_and_abstains_so_nothing_is_saved(
        fixture_db, state):
    from strata.dbx import viewer_from_headers
    from strata.server.uploads import reader
    from strata.tools import registry

    app = app_on(fixture_db, state, dt.date(2026, 10, 22), dt.datetime(2026, 10, 22, 9, 30, tzinfo=dt.UTC))
    upload_id = upload(app).json()["upload_id"]
    officer = viewer_from_headers(AMINA)
    read = reader(UploadStore(lambda: DuckDBEngine.open(state)), Access(roles(), StaticGroups(GROUPS)), officer)
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        for position in range(1, 10):
            answer = registry.call("estimate_time", {"upload_row": f"{upload_id}:{position}"},
                                   registry.Context(engine, officer, as_of=dt.date(2026, 10, 22), uploads=read))
            steps = answer["step_dates"]
            assert steps["family"] and steps["steps"], position
            for step in steps["steps"]:
                # Every step names how many comparable packages recorded it, and none reaches the threshold.
                assert isinstance(step["comparables_n"], int) and step["comparables_n"] < MIN
                assert step["cautious"] is None or step["cautious"]["planned_date"] is None
                assert step["abstain_reason"] == "few_comparables" or steps["abstain_all"]["n"] < MIN

    sent, made = draft(app, AMINA, f"upload:{upload_id}")

    assert made is None
    [nothing] = [data for kind, data in sent if kind == "nothing_dated"]
    assert nothing["counts"]["activities"] == 9 and nothing["counts"]["dated"] == {"middle": 0, "cautious": 0}
    assert nothing["min_comparables"] == MIN
    with DuckDBEngine.open(state, read_only=True) as engine:
        assert engine.run("SELECT count(*) FROM strata.ops.drafts").rows[0][0] == 0


def test_only_an_officer_drafts_planned_dates_and_only_from_their_own_teams_upload_or_agencys_plan(fixture_db, state):
    app = app_on(fixture_db, state, dt.date(2026, 10, 22), dt.datetime(2026, 10, 22, 9, 30, tzinfo=dt.UTC))
    upload_id = upload(app).json()["upload_id"]
    plan = "plan:P156634:northern-water-works-development-agency:2026-10-09"

    for headers, source, status, code in ((CHEGE, f"upload:{upload_id}", 404, "unknown_upload"),
                                          (DANA, f"upload:{upload_id}", 403, "not_agency_team"),
                                          (CHEGE, plan, 403, "not_own_agency")):
        answer = call(app, "POST", "/api/drafts", headers, json={"kind": "step_rows", "source": source})
        assert (answer.status_code, answer.json()["code"]) == (status, code)


# ── On the hand-made set: the dates worked out by hand, checked and exported ──

@pytest.fixture
def hand(tmp_path):
    """Ticket 27's hand-made set, with a project whose record names team A's agency in the same country."""
    path = tmp_path / "hand.duckdb"
    engine = step_set.build(path)
    step_set.insert(engine, "strata.gold.project", [{"project_id": HAND_PROJECT, "project_name": "Hand-made water project",
                                                     "country_code": "KE", "region": "Eastern and Southern Africa",
                                                     "implementing_agency": NWWDA, "public_from": dt.date(2018, 1, 1)}])
    engine.close()
    return path


STEPS = step_set.STEPS


def hand_file() -> bytes:
    """Team A's draft plan on the hand-made set: the target package with its own planned dates and one actual date,
    and a new activity with no reference and no dates yet, laid out as STEP prints a table."""
    head = ["Activity Reference No. / Description", "Loan / Credit No.", "Review Type", "Method", "Market Approach",
            "High SEA/SH Risk", "Estimated Amount (US$)", "Actual Amount (US$)", "Process Status"]
    out = io.StringIO()
    sheet = csv.writer(out, lineterminator="\r\n")
    sheet.writerow(["WORKS"])
    sheet.writerow(head + [cell for step in STEPS for cell in (step, "")])
    sheet.writerow([""] * len(head) + ["Planned", "Actual"] * len(STEPS))
    planned = [day.isoformat() for day in step_set.TARGET_PLANNED]
    sheet.writerow([f"{step_set.TARGET} / Hand-made works", "IDA / 99999", "Post", "Request for Bids", "Open - National",
                    "Y", "1,000,000.00", "0.00", "Pending Implementation",
                    planned[0], "2021-03-10", *[cell for day in planned[1:] for cell in (day, "")]])
    sheet.writerow([" / New boreholes in the north", "IDA / 99999", "Post", "Request for Bids", "Open - National", "",
                    "400,000.00", "", ""] + [""] * (2 * len(STEPS)))
    return out.getvalue().encode()


def test_an_upload_gets_the_dates_worked_out_by_hand_checked_and_exported_as_step_rows(hand, state):
    today = DATES["as_of"]
    app = app_on(hand, state, today, dt.datetime(2021, 1, 15, 10, 0, tzinfo=dt.UTC))
    kept = upload(app, data=hand_file(), name="team-a-plan.csv", project=HAND_PROJECT)
    assert kept.status_code == 200, kept.text
    upload_id = kept.json()["upload_id"]

    sent, draft_id = draft(app, AMINA, f"upload:{upload_id}")
    assert draft_id, sent
    shown = call(app, "GET", f"/api/drafts/{draft_id}", AMINA).json()
    target, new = shown["dates"]["activities"]
    dated = target["steps"][:5]
    assert [step["cautious"]["planned_date"] for step in dated] == [day.isoformat() for day in DATES["cautious_dates"]]
    assert [step["middle"]["planned_date"] for step in dated] == [day.isoformat() for day in DATES["middle_dates"]]
    assert [step["comparables_n"] for step in dated] == [DATES["comparables"]] * 5
    # The completion step: no comparable package planned it, so it abstains.
    assert target["steps"][5]["cautious"]["planned_date"] is None and target["steps"][5]["abstain_reason"]
    # The new activity gives no dates, so its steps wait for a start date.
    assert (new["reference"], new["needs_start_date"]) == (None, True)
    # Every date and count on the page matched what estimate_time returned for its list.
    checks = shown["checks"]
    assert checks["dates"]["matched"] == checks["dates"]["total"] > 0
    assert checks["numbers"]["matched"] == checks["numbers"]["total"] > 0 and shown["removed"] == []
    assert shown["opened"]["of"] == shown["dates"]["counts"]["lists"] == 5
    # The team reads it; another team and World Bank staff find nothing.
    assert call(app, "GET", f"/api/drafts/{draft_id}", BARAKA).status_code == 200
    for outsider in (CHEGE, DANA):
        assert call(app, "GET", f"/api/drafts/{draft_id}", outsider).status_code == 404

    switched = call(app, "PUT", f"/api/drafts/{draft_id}/fields", AMINA, json={"row_key": "", "field": "choice",
                                                                               "value": "middle"})
    assert switched.json()["dates"]["choice"] == "middle"
    held = call(app, "POST", f"/api/drafts/{draft_id}/export", AMINA, json={"expected_state": "draft"}).json()
    assert (held["code"], held["holds"]) == ("draft_state", ["notChecked"])
    call(app, "POST", f"/api/drafts/{draft_id}/check", AMINA, json={"expected_state": "draft"})
    locked = call(app, "PUT", f"/api/drafts/{draft_id}/fields", AMINA, json={"row_key": "", "field": "choice",
                                                                             "value": "cautious"})
    assert (locked.status_code, locked.json()["code"]) == (409, "draft_state")
    exported = call(app, "POST", f"/api/drafts/{draft_id}/export", AMINA, json={"expected_state": "checked"}).json()
    stem = f"step-rows-{HAND_PROJECT}-northern-water-works-development-agency-2021-01-15"
    assert sorted(file["name"] for file in exported["export"]["files"]) == sorted(
        f"{stem}{ending}" for ending in (".csv", "-evidence-pack.pdf", "-evidence-pack.csv"))

    from pypdf import PdfReader

    pack = call(app, "GET", f"/api/drafts/{draft_id}/files/{stem}-evidence-pack.pdf", AMINA).content
    first = PdfReader(io.BytesIO(pack)).pages[0].extract_text()
    # The evidence pack carries Official Use Only first, and lists each dated step's list of comparable packages.
    assert first.startswith("Official Use Only")
    lists = list(csv.reader(io.StringIO(call(app, "GET", f"/api/drafts/{draft_id}/files/{stem}-evidence-pack.csv",
                                             AMINA).text)))
    assert [row[1] for row in lists[1:]] == [f"steps:upload:{upload_id}:1:{step}" for step in (
        "bid_invitation", "bidding_document_issued", "bid_opening", "bid_evaluation_report", "contract_signed")]

    data = call(app, "GET", f"/api/drafts/{draft_id}/files/{stem}.csv", AMINA).content
    assert data.startswith("﻿".encode())
    text = data.decode("utf-8-sig")
    assert "\r\n" in text and text.count("\r\n") == 3
    header, first, second = list(csv.reader(io.StringIO(text)))
    columns = step_columns().csv_columns()
    # Exactly STEP's columns, in the registry's order, and no other line.
    assert header == [column.name for column in columns]
    by = dict(zip(header, first))
    planned = {column.step: by[column.name] for column in columns if column.head == "Planned"}
    assert [planned[step] for step in STEPS[:5]] == [day.isoformat() for day in DATES["middle_dates"]]
    assert planned["Contract Completion"] == ""
    # References, actual dates and ratings are left to the officer and STEP, though the upload gave them.
    left = [column.name for column in columns if column.fill == "left"]
    assert {name: by[name] for name in left} == dict.fromkeys(left, "")
    assert "Activity Reference No." in left and "High SEA/SH Risk" in left
    assert all(column.name in left for column in columns if column.head == "Actual")
    # The officer's other values are copied unchanged, and the rows keep the file's order and Descriptions.
    assert (by["Description"], by["Loan / Credit No."], by["Estimated Amount (US$)"], by["Method"]) == (
        "Hand-made works", "IDA / 99999", "1,000,000.00", "Request for Bids")
    assert dict(zip(header, second))["Description"] == "New boreholes in the north"
    assert all(dict(zip(header, second))[column.name] == "" for column in columns if column.fill == "planned")


def test_the_upload_screens_recorded_answers_are_what_the_routes_answer(fixture_db, tmp_path):
    """The upload and planned-dates screens' tests serve these files; the routes must still answer with them."""
    from record_uploads_api import answers

    for name, text in answers(tmp_path, fixture_db).items():
        assert text == (ROOT / "tests" / "fixtures" / "api" / name).read_text(), (
            f"{name} is out of date: uv run --frozen python tests/record_uploads_api.py")


def test_the_draft_kind_registry_makes_planned_dates_an_agency_kind_with_no_model_and_step_rows_as_its_file():
    kind = load_draft_kinds().kinds["step_rows"]

    assert (kind.agent, kind.export, kind.agency_only, kind.sources_list, kind.removed_box) == (
        "", "step_rows", True, False, "when_removed")
    assert kind.csv == ("strata.drafts.step_rows:step_rows_csv",)


def test_the_upload_fixture_reads_back_the_published_plans_nine_activities_in_its_order(fixture_db, state):
    """The reader on the published layout (section titles and two header rows) keeps the file's order."""
    app = app_on(fixture_db, state, dt.date(2026, 10, 22), dt.datetime(2026, 10, 22, 9, 30, tzinfo=dt.UTC))
    rows = upload(app).json()["rows"]
    order = [cells[0].split(" / ")[0] for cells in csv.reader(io.StringIO(FIXTURE.read_text()))
             if cells and " / " in cells[0] and not cells[0].startswith("Activity")]
    assert len(order) == 9 and [row["activity_reference_no"] for row in rows] == order
