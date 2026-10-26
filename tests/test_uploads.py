"""An implementing agency's private upload of its Procurement Plan at seams 2 and 3 (ticket 38).

An officer on team A, the Northern Water Works Development Agency's, uploads the fixture plan through POST
/api/uploads; the server reads it with the STEP column registry, checks it with check_plan, and only then keeps its
activities in strata.ops with the team. A viewer on team B, another agency's, and World Bank staff, get nothing of
it from any route or tool, and a question about it is turned down.

The upload is tests/fixtures/uploads/nwwda-plan-2026-10-09.csv, the plan of October 9, 2026 as STEP prints it
(tests/record_upload_fixture.py). Expected marks come from the benchmark question check_plan answers for the same
plan, whose source is the blueprint's wireframe (tests/ground_truth/values.toml, plan_row wireframe_mark, and
plan.also_lists). App state is a DuckDB file written as the app's own service principal; the fixture database is
opened read-only.
"""

import asyncio
import dataclasses
import datetime as dt
import json
import tomllib
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote

import httpx
import pytest
import yaml

from strata.config import load_roles
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine
from strata.server.access import Access, StaticGroups
from strata.server.app import create_app
from strata.uploads.store import UploadStore

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "uploads" / "nwwda-plan-2026-10-09.csv"
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
BENCHMARK = next(question for question in yaml.safe_load((ROOT / "evals" / "benchmark.yaml").read_text())["questions"]
                 if question["id"] == "check-plan-nwwda-2026-10-09")
TODAY = dt.date(2026, 10, 22)  # the benchmark question's date, so its marks hold
NWWDA = "Northern Water Works Development Agency"


def viewer(number: int, name: str) -> dict:
    return {"X-Forwarded-Email": f"{name.lower()}.example@worldbank.org", "X-Forwarded-Preferred-Username": f"{name} Example",
            "X-Forwarded-User": f"50{number}@1984", "X-Forwarded-Access-Token": f"token-for-{name.lower()}-only"}


# Amina and Baraka are officers on team A; Chege is an officer on team B; Dana is World Bank staff on no team.
AMINA, BARAKA, CHEGE, DANA = viewer(31, "Amina"), viewer(32, "Baraka"), viewer(33, "Chege"), viewer(34, "Dana")
GROUPS = {"5031@1984": ["users", "strata-agency-nwwda"], "5032@1984": ["users", "strata-agency-nwwda"],
          "5033@1984": ["users", "strata-agency-cwwda"], "5034@1984": ["users"]}


def roles():
    """config/roles.toml, with the test roles file's two implementing agency teams."""
    real = load_roles()
    return dataclasses.replace(real, teams=real.teams + load_roles(ROOT / "tests" / "fixtures" / "roles.toml").teams)


def call(app, method, path, headers=None, **options):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.request(method, path, headers=headers or {}, **options)
    return asyncio.run(go())


@pytest.fixture
def state_db(tmp_path):
    path = tmp_path / "state.duckdb"
    with DuckDBEngine.open(path) as engine:
        catalog.build(engine)
    return path


@pytest.fixture
def make(fixture_db, state_db):
    """The app on the fixture database, with uploads kept in a DuckDB file as the app's own account."""
    @contextmanager
    def reading(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    def build(today=TODAY, store=None):
        numbers = iter(range(1, 100))
        return create_app(engine_for=reading, uploads=store or UploadStore(lambda: DuckDBEngine.open(state_db)),
                          access=Access(roles(), StaticGroups(GROUPS)), today=lambda: today,
                          now=lambda: dt.datetime(2026, 10, 22, 9, 30, tzinfo=dt.UTC),
                          new_upload_id=lambda: f"upl-{next(numbers):012d}")
    return build


def upload(app, headers=AMINA, data=None, name="nwwda-plan-2026-10-09.csv", project="P156634", **query):
    return call(app, "POST", "/api/uploads", {**headers, "X-Strata-File-Name": quote(name)},
                params={"project_id": project, **query},
                content=FIXTURE.read_bytes() if data is None else data)


def marks(result) -> dict[str, list[str]]:
    """The references under each mark, in the benchmark question's shape."""
    found = {"unmarked": sorted(row["activity_reference_no"] for row in result["rows"] if not row["marks"])}
    for mark in ("needs_a_look", "watch", "data_note"):
        found[mark] = sorted(row["activity_reference_no"] for row in result["rows"]
                             if any(given["mark"] == mark for given in row["marks"]))
    return found


# ── Team A uploads its plan and gets its check ───────────────────────────

def test_an_officer_uploads_the_fixture_plan_and_gets_its_check_with_the_published_plans_marks(make):
    app = make()

    answer = upload(app)

    assert answer.status_code == 200, answer.text
    result = answer.json()
    assert result["kept"] is True and result["upload_id"] == "upl-000000000001"
    assert marks(result) == {mark: BENCHMARK["expected"][mark]
                             for mark in ("needs_a_look", "watch", "data_note", "unmarked")}
    # Nine activities: the wireframe's eight and the one it leaves out, in the order of the officer's file.
    references = [row["reference"] for row in TRUTH["plan_row"]] + TRUTH["plan"]["also_lists"]
    assert sorted(row["activity_reference_no"] for row in result["rows"]) == sorted(references)
    assert [row["position"] for row in result["rows"]] == list(range(1, 10))
    assert result["counts"]["activities"] == 9
    # Every row is cited as a row of this upload, public on the day it was kept.
    assert {row["evidence_id"] for row in result["rows"]} == {f"upload-row:upl-000000000001:{n}" for n in range(1, 10)}
    assert {row["public_from"] for row in result["rows"]} == {"2026-10-22"}
    assert result["upload"]["reading"]["activities"] == 9


def marker_file(description: str, method: str = "Request for Bids", *, header: str | None = None) -> bytes:
    """A one-row-header upload of one new activity, with no reference yet, as the STEP rows CSV lays it out."""
    head = header or ("Activity Reference No.,Description,Review Type,Method,Market Approach,Estimated Amount (US$),"
                      "Specific Procurement Notice / Invitation (Planned),Signed Contract (Planned),"
                      "Contract Completion (Planned)")
    return (f"{head}\r\n,{description},Post,{method},Open - National,\"450,000.00\",2026-11-02,2027-02-01,"
            "2027-08-01\r\n").encode()


# ── Nothing of it reaches anyone else ────────────────────────────────────

def test_a_teammate_opens_the_upload_and_another_team_or_staff_get_the_answer_for_one_that_does_not_exist(make):
    app = make()
    upload_id = upload(app).json()["upload_id"]

    mine = call(app, "GET", f"/api/uploads/{upload_id}", BARAKA)
    assert mine.status_code == 200 and mine.json()["counts"]["activities"] == 9
    assert mine.json()["upload"]["uploader"] == {"name": "Amina Example", "you": False}
    missing = call(app, "GET", "/api/uploads/upl-999999999999", CHEGE)
    for outsider in (CHEGE, DANA):
        found = call(app, "GET", f"/api/uploads/{upload_id}", outsider)
        assert (found.status_code, found.json()) == (404, missing.json()) == (404, {"code": "unknown_upload",
                                                                                  "error": "unknown_upload"})
        assert call(app, "GET", "/api/uploads", outsider).json()["uploads"] == []
        assert call(app, "GET", f"/api/uploads/{upload_id}/rows/1", outsider).status_code == 404
        evidence = call(app, "GET", "/api/evidence", outsider, params={"id": f"upload-row:{upload_id}:1"})
        assert (evidence.status_code, evidence.json()) == (404, {"code": "unknown_evidence"})
    assert [row["upload_id"] for row in call(app, "GET", "/api/uploads", BARAKA).json()["uploads"]] == [upload_id]
    assert call(app, "GET", "/api/evidence", BARAKA, params={"id": f"upload-row:{upload_id}:1"}).status_code == 200
    # A preview never shows any team's upload, the previewing person's own team's included. An officer's ?view=piu is
    # their own view (ticket 40), so their preview is the public one.
    assert call(app, "GET", f"/api/uploads/{upload_id}", AMINA, params={"view": "public"}).status_code == 404
    assert call(app, "GET", "/api/uploads", AMINA, params={"view": "public"}).json()["uploads"] == []
    assert call(app, "GET", f"/api/uploads/{upload_id}", AMINA, params={"view": "piu"}).status_code == 200


def test_the_tools_read_an_upload_only_through_the_team_rule(make, fixture_db, state_db):
    """check_plan called by name through the registry: with the server's reader for team B, or with none, as the
    agent calls it, the upload is an unknown upload with no rows."""
    from strata.dbx import Viewer, viewer_from_headers
    from strata.server.uploads import reader
    from strata.tools import registry

    app = make()
    upload_id = upload(app).json()["upload_id"]
    store, access = UploadStore(lambda: DuckDBEngine.open(state_db)), Access(roles(), StaticGroups(GROUPS))
    arguments = {"project_id": "P156634", "implementing_agency": NWWDA, "upload_id": upload_id}
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        for given in (reader(store, access, viewer_from_headers(CHEGE)), reader(store, access, viewer_from_headers(DANA)),
                      None):
            result = registry.call("check_plan", arguments,
                                   registry.Context(engine, Viewer(user_id="5033@1984"), as_of=TODAY, uploads=given))
            assert result["abstention"] == {"reason": "unknown_upload"} and result["rows"] == []
            assert result["project"] is None
        mine = registry.call("check_plan", arguments, registry.Context(
            engine, viewer_from_headers(BARAKA), as_of=TODAY, uploads=reader(store, access, viewer_from_headers(BARAKA))))
    assert len(mine["rows"]) == 9


def test_a_question_about_the_upload_from_another_team_is_refused_and_returns_nothing_of_it(make, fixture_db, state_db):
    """The must-refuse case at seam 3, asked by an officer on team B after team A kept its upload: the scripted agent
    answers with the private_uploads refusal, and neither the stream nor anything a tool gave the agent holds the
    upload's id, its file or any of its Descriptions."""
    from strata.agent.loop import answer_runner
    from strata.agent.scripted import ScriptedAgent, ScriptedJudge, app_engine_for, load_cases
    from strata.harness.sse import events

    kept = upload(make(), name="nwwda-draft-plan.csv").json()
    case = load_cases()["refuses-private-uploads"]
    agents = []

    @contextmanager
    def engine_for(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    def agent_for(turn):
        agents.append(ScriptedAgent(case))
        return agents[-1]

    app = create_app(runner=answer_runner(agent_for, engine_for, today=lambda: TODAY),
                     engine_for=app_engine_for(case, engine_for), judge=ScriptedJudge(case), new_run_id=lambda: "run-1",
                     uploads=UploadStore(lambda: DuckDBEngine.open(state_db)), access=Access(roles(), StaticGroups(GROUPS)))
    answer = call(app, "POST", "/api/ask", CHEGE, json={"question": case.question, "scope": case.scope,
                                                        "asof": case.as_of.isoformat()})
    parsed = events(answer.text)

    assert [data for kind, data in parsed if kind == "refusal"] == [{"key": "private_uploads", "partial": False}]
    assert [data for kind, data in parsed if kind == "sentence"] == []
    seen = answer.text + json.dumps(agents[0].received, ensure_ascii=False)
    private = [kept["upload_id"], "nwwda-draft-plan.csv"] + [row["description"] for row in kept["rows"]]
    assert [value for value in private if value in seen] == []
    # Had the agent asked for the upload by its id, the tool would have found nothing, for the uploading team too:
    # /api/ask's tools get the Context answer_runner builds with tool_context (src/strata/agent/loop.py), which
    # carries no reader of uploads.
    from strata.agent.loop import tool_context
    from strata.config import load_thresholds
    from strata.dbx import viewer_from_headers
    from strata.tools import registry

    for headers in (CHEGE, AMINA):
        viewer = viewer_from_headers(headers)
        with engine_for(viewer) as engine:
            asked = registry.call("check_plan", {"project_id": "P156634", "implementing_agency": NWWDA,
                                                 "upload_id": kept["upload_id"]},
                                  tool_context(engine, viewer, "staff", case.as_of, load_thresholds()))
        assert (asked["abstention"], asked["rows"]) == ({"reason": "unknown_upload"}, [])


def test_no_upload_text_ever_reaches_the_shared_search_index(fixture_db, tmp_path):
    """The upload is kept in the same catalog as the search index's source table, strata.gold.passage. The search
    over that catalog finds none of it, the only table that holds its words is strata.ops.upload_rows, and no code
    that builds the passages or the index reads an upload's activities."""
    import shutil

    from strata.dbx import Viewer
    from strata.knowledge.search import SOURCE_TABLE
    from strata.tools import registry

    shared = tmp_path / "catalog.duckdb"
    shutil.copy(fixture_db, shared)
    marker = "Rehabilitation of the Zebrafinch Hill pumping station"

    @contextmanager
    def reading(viewer):
        with DuckDBEngine.open(shared, read_only=True) as engine:
            yield engine

    app = create_app(engine_for=reading, uploads=UploadStore(lambda: DuckDBEngine.open(shared)),
                     access=Access(roles(), StaticGroups(GROUPS)), today=lambda: TODAY,
                     now=lambda: dt.datetime(2026, 10, 22, 9, 30, tzinfo=dt.UTC))
    assert upload(app, data=marker_file(marker), name="zebrafinch.csv").status_code == 200

    with DuckDBEngine.open(shared, read_only=True) as engine:
        holding = []
        columns = engine.run("SELECT c.table_schema, c.table_name, c.column_name FROM system.information_schema.columns AS c "
                             "JOIN system.information_schema.tables AS t ON t.table_catalog = c.table_catalog "
                             "AND t.table_schema = c.table_schema AND t.table_name = c.table_name "
                             "WHERE c.table_catalog = 'strata' AND t.table_type = 'BASE TABLE' AND c.data_type = 'VARCHAR'")
        texts: dict[tuple[str, str], list[str]] = {}
        for schema, table, column in columns.rows:
            texts.setdefault((schema, table), []).append(column)
        for (schema, table), names in texts.items():
            joined = ", ".join(f"coalesce(`{name}`, '')" for name in names)
            hits = engine.run(f"SELECT count(*) FROM strata.`{schema}`.`{table}` "  # sql-lint: names only
                              f"WHERE concat_ws('|', {joined}) LIKE :marker", {"marker": "%Zebrafinch%"})
            if hits.rows[0][0]:
                holding.append(f"strata.{schema}.{table}")
        found = registry.call("search_passages", {"query": marker},
                              registry.Context(engine, Viewer(user_id="5033@1984"), as_of=TODAY))
        assert [row for row in found["rows"] if "Zebrafinch" in json.dumps(row)] == []
    assert sorted(set(holding)) == ["strata.ops.upload_rows"] and SOURCE_TABLE not in holding
    readers = [path.relative_to(ROOT).as_posix() for path in (ROOT / "src" / "strata").rglob("*")
               if path.suffix in (".py", ".sql") and "upload_rows" in path.read_text()]
    # The table's definition, its mask and the store; the app's settings name it only to say where uploads are kept.
    assert sorted(readers) == ["src/strata/lakehouse/masks.py", "src/strata/lakehouse/tables/ops/upload_rows.sql",
                               "src/strata/lakehouse/tables/ops/uploads.sql", "src/strata/server/settings.py",
                               "src/strata/uploads/sql/remove_rows.sql", "src/strata/uploads/sql/rows.sql",
                               "src/strata/uploads/store.py"]


# ── Only an officer uploads, and a reading that fails keeps nothing ──────

def kept_rows(state_db) -> tuple[int, int]:
    with DuckDBEngine.open(state_db, read_only=True) as engine:
        return (engine.run("SELECT count(*) FROM strata.ops.uploads").rows[0][0],
                engine.run("SELECT count(*) FROM strata.ops.upload_rows").rows[0][0])


def test_only_an_officer_of_the_projects_agency_uploads_and_a_preview_uploads_nothing(make, state_db):
    app = make()

    assert upload(app, DANA).json()["code"] == "not_agency_team"
    assert upload(app, CHEGE, project="P130164").json()["code"] == "unknown_project"
    # The officer's preview of the public view (ticket 40: their ?view=piu is their own view) refuses the upload with the
    # reason the roles file names, which the held button shows.
    held = upload(app, AMINA, view="public")
    assert (held.status_code, held.json()["code"], held.json()["copy_key"]) == (403, "preview", "upload.holdPreview")
    assert kept_rows(state_db) == (0, 0)
    form = call(app, "GET", "/api/uploads/form", DANA).json()
    assert (form["officer"], form["agency"]) == (False, None)
    form = call(app, "GET", "/api/uploads/form", AMINA).json()
    assert form["agency"] == {"name": NWWDA, "agency_id": "northern-water-works-development-agency"}
    assert [project["project_id"] for project in form["projects"]] == ["P156634"]
    assert form["projects"][0]["latest_plan"]["plan_date"] == "2026-10-09"
    assert form["columns"]["needed"] == ["Activity Reference No. / Description", "Method"]


@pytest.mark.parametrize("name, data, code, details", [
    ("plan.pdf", b"%PDF-1.7", "type", {"extension": ".pdf"}),
    ("plan.csv", b"", "empty", {}),
    ("plan.xlsx", b"not a zip at all", "unreadable", {}),
    ("plan.csv", b"Title,Notes\r\nSomething,else\r\n", "no_table", {}),
    ("plan.csv", b"Activity Reference No. / Description,Review Type\r\n / New works,Post\r\n", "missing_columns",
     {"missing": ["Method"]}),
    ("plan.csv", b"Activity Reference No. / Description,Method\r\n", "no_rows", {}),
])
def test_a_file_that_cannot_be_read_says_why_and_keeps_nothing(make, state_db, name, data, code, details):
    answer = upload(make(), data=data, name=name)

    assert answer.status_code == 422
    assert {key: answer.json()[key] for key in ("code", "kept", *details)} == {"code": code, "kept": False, **details}
    assert kept_rows(state_db) == (0, 0)


def test_a_file_over_the_size_limit_is_refused_before_the_server_reads_it_all(make, state_db):
    """The server stops reading a body as soon as it passes uploads.max_size_bytes (config/uploads.toml), whether
    the request says its length or not, and keeps nothing."""
    limit = tomllib.loads((ROOT / "config" / "uploads.toml").read_text())["uploads"]["max_size_bytes"]
    sent = []

    async def chunks():
        for _ in range(4 * limit // 1_000_000 + 4):
            sent.append(1_000_000)
            yield b"x" * 1_000_000

    told = upload(make(), data=b"x" * (limit + 1))
    streamed = call(make(), "POST", "/api/uploads", {**AMINA, "X-Strata-File-Name": "big.csv"},
                    params={"project_id": "P156634"},
                    content=chunks())

    for answer in (told, streamed):
        assert (answer.status_code, answer.json()["code"], answer.json()["kept"]) == (422, "size", False)
    assert sum(sent) <= limit + 2_000_000
    assert kept_rows(state_db) == (0, 0)


def test_two_requests_with_one_key_keep_one_upload(make, state_db):
    """A second request with the same idempotency key that kept its upload while this one was read and checked:
    this one keeps nothing and answers with that upload."""
    class Racing(UploadStore):
        asked = 0

        def by_key(self, uploader_id, idempotency_key):
            self.asked += 1  # nothing kept yet when the request arrives; the other request's upload by the save
            return None if self.asked == 1 else "upl-000000000099"

    answer = upload(make(store=Racing(lambda: DuckDBEngine.open(state_db))), idempotency_key="key-1")

    assert answer.json() == {"upload_id": "upl-000000000099", "kept": True}
    assert kept_rows(state_db) == (0, 0)


def test_a_fault_while_reading_back_a_kept_upload_answers_with_the_kept_upload_not_an_error(make, state_db):
    """The upload was kept; a warehouse fault on the read back must not answer HTTP 500 or say nothing was kept. The
    answer names the kept upload, as a repeated request with the same key does, and its page reads it."""
    from strata.lakehouse.engine import EngineError

    class Flaky(UploadStore):
        failed = False

        def get(self, upload_id):
            if not self.failed:
                self.failed = True
                raise EngineError("the warehouse dropped the connection")
            return super().get(upload_id)

    app = make(store=Flaky(lambda: DuckDBEngine.open(state_db)))
    answer = upload(app)

    assert (answer.status_code, answer.json()) == (200, {"upload_id": "upl-000000000001", "kept": True})
    assert call(app, "GET", "/api/uploads/upl-000000000001", AMINA).status_code == 200


def test_a_save_that_fails_part_way_leaves_nothing_a_reader_can_find(make, state_db):
    from strata.lakehouse.engine import EngineError

    class Failing:
        """The app's engine, refusing the upload's own row after its activities were written."""

        def __init__(self):
            self.engine = DuckDBEngine.open(state_db)

        def insert_rows(self, table, columns, rows):
            if table == "strata.ops.uploads":
                raise EngineError("the warehouse dropped the connection")
            return self.engine.insert_rows(table, columns, rows)

        def run(self, sql, params=None):
            return self.engine.run(sql, params)

        def close(self):
            self.engine.close()

    answer = upload(make(store=UploadStore(Failing)))

    assert (answer.status_code, answer.json()["code"], answer.json()["kept"]) == (503, "service", False)
    assert kept_rows(state_db) == (0, 0)


def test_an_excel_file_with_one_header_row_is_read_like_the_csv(make):
    """An .xlsx upload with each step column as "{step} (Planned)", read by the same registry, with an unreadable date
    noted on its row and a column Strata does not use listed."""
    header = ["Activity Reference No.", "Description", "Method", "Market Approach", "Estimated Amount (US$)",
              "Signed Contract (Planned)", "Contract Completion (Planned)", "Remarks"]
    rows = [header, ["KE-NWWDA-541055-CW-RFB", "Equipping of boreholes, lot 1", "Request for Bids", "Open - National",
                     1230000, 46136, "soon"]]
    answer = upload(make(), data=xlsx(rows), name="plan.xlsx")

    assert answer.status_code == 200, answer.text
    [row] = answer.json()["rows"]
    assert (row["activity_reference_no"], row["estimated_amount_usd"], row["listed"]) == (
        "KE-NWWDA-541055-CW-RFB", "1230000.00", True)
    notes = [reason for mark in row["marks"] for reason in mark["reasons"] if reason["code"] == "unread_date"]
    assert notes == [{"code": "unread_date", "mark": "data_note", "column": "Contract Completion (Planned)",
                      "value": "soon", "evidence_ids": [row["evidence_id"]]}]
    assert answer.json()["upload"]["reading"]["unused"] == ["Remarks"]


def test_an_excel_cell_past_the_last_column_strata_reads_is_left_unread(make):
    """An Excel file may name a cell as far right as column XFD, the 16,384th. The reader skips any cell past
    uploads.max_columns (config/uploads.toml), so one far cell cannot make every row that wide."""
    limit = tomllib.loads((ROOT / "config" / "uploads.toml").read_text())["uploads"]["max_columns"]
    header = {0: "Activity Reference No.", 1: "Description", 2: "Method", limit - 1: "Remarks", 16_383: "Far away"}
    rows = [header, {0: "KE-NWWDA-541055-CW-RFB", 1: "Equipping of boreholes, lot 1", 2: "Request for Bids"}]

    answer = upload(make(), data=xlsx(rows), name="plan.xlsx")

    assert answer.status_code == 200, answer.text
    assert answer.json()["upload"]["reading"]["unused"] == ["Remarks"]


TOO_LONG = "1" + "0" * 27  # 28 digits, as a pasted ID number would be: more than an amount's 28 places can hold
EXCEL_HEADER = ["Activity Reference No.", "Description", "Method", "Estimated Amount (US$)", "Signed Contract (Planned)"]
EXCEL_ROW = ["KE-NWWDA-541055-CW-RFB", "Equipping of boreholes, lot 1", "Request for Bids"]


@pytest.mark.parametrize("name, data, code, column, value", [
    ("plan.csv", marker_file("New works").replace(b'"450,000.00"', TOO_LONG.encode()), "unread_amount",
     "Estimated Amount (US$)", TOO_LONG),
    ("plan.xlsx", [EXCEL_HEADER, [*EXCEL_ROW, 1e30, 46136]], "unread_amount", "Estimated Amount (US$)",
     "1000000000000000000000000000000"),
    ("plan.xlsx", [EXCEL_HEADER, [*EXCEL_ROW, 450000, float("inf")]], "unread_date", "Signed Contract (Planned)",
     "inf"),
], ids=["csv amount of 28 digits", "excel amount of 1E+30", "excel date of infinity"])
def test_a_value_too_large_to_read_becomes_a_data_note_on_its_row(make, state_db, name, data, code, column, value):
    """A value that will not read is noted on its row and the upload is kept, never an error."""
    answer = upload(make(), data=xlsx(data) if isinstance(data, list) else data, name=name)

    assert answer.status_code == 200, answer.text
    [row] = answer.json()["rows"]
    notes = [reason for mark in row["marks"] for reason in mark["reasons"] if reason["code"] == code]
    assert notes == [{"code": code, "mark": "data_note", "column": column, "value": value,
                      "evidence_ids": [row["evidence_id"]]}]
    assert kept_rows(state_db) == (1, 1)


def xlsx(rows: list[list | dict]) -> bytes:
    """A one-sheet Excel file, as the standard library can write one: strings inline, numbers as numbers. A row is
    its cells in order, or a dict of cells by column index from 0."""
    import io
    import zipfile
    from xml.sax.saxutils import escape

    def letters(column: int) -> str:
        name = ""
        column += 1
        while column:
            column, left = divmod(column - 1, 26)
            name = chr(65 + left) + name
        return name

    def cell(column: int, value) -> str:
        if isinstance(value, int | float):
            return f'<c r="{letters(column)}1" t="n"><v>{value}</v></c>'
        return f'<c r="{letters(column)}1" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'

    def cells(row: list | dict) -> str:
        return "".join(cell(i, value) for i, value in (row.items() if isinstance(row, dict) else enumerate(row)))

    sheet = "".join(f'<row r="{n}">{cells(row)}</row>' for n, row in enumerate(rows, 1))
    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rels = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as book:
        book.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/'
                      'package/2006/content-types"/>')
        book.writestr("xl/workbook.xml", f'<workbook xmlns="{main}" xmlns:r="{rels}"><sheets>'
                      '<sheet name="WORKS" sheetId="1" r:id="rId1"/></sheets></workbook>')
        book.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
                      '2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        book.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="{main}"><sheetData>{sheet}</sheetData></worksheet>')
    return out.getvalue()
