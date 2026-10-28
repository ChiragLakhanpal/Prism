"""The evidence routes the answer panel and the evidence drawer call (ticket 14).

- GET /api/evidence?id= gives one source by its evidence id, read as the viewer and as of the page's date,
  in the shape the answer stream's evidence event carries, so a drawer opened from a link shows the same
  paragraph as one opened from an answer. Its answers for ICR P130164 paragraph 54 and for a section of
  P130164's first ISR are recorded once in tests/fixtures/api, and the screen tests serve the same files.
- POST /api/evidence/opened records that a viewer opened a source in the drawer: one row per viewer and
  evidence id in strata.ops.evidence_opened, written by the app's own service principal (a DuckDB file
  here). A preview records nothing; the server decides that, not the browser.
- GET /api/evidence/opened?id= says which of an answer's sources this viewer has opened.

Expected values come from the ICR of October 10, 2019 (tests/ground_truth/values.toml, icr-para-54).
"""

import asyncio
import datetime as dt
import json
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine
from strata.server.app import create_app
from strata.server.evidence import OpenedLog

RECORDED = Path(__file__).parent / "fixtures" / "api"
ICR_54 = "strata.gold.passage:31525018/v1/54"
ICR_55 = "strata.gold.passage:31525018/v1/55"
# ISR 1 of P130164, February 22, 2014: its section on the PDO indicators (values.toml, isr-1-pdo-indicators).
ISR_1_S4 = "strata.gold.passage:19095337/v1/s4"
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-User": "4021@1984",
       "X-Forwarded-Access-Token": "token-for-ana-only"}
BEN = {"X-Forwarded-Email": "ben.example@worldbank.org", "X-Forwarded-User": "4022@1984",
       "X-Forwarded-Access-Token": "token-for-ben-only"}


def call(app, method, path, headers=None, **options):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.request(method, path, headers=headers or {}, **options)
    return asyncio.run(go())


@pytest.fixture
def reading(fixture_db):
    @contextmanager
    def engine_for(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine
    return engine_for


@pytest.fixture
def ops_db(tmp_path):
    path = tmp_path / "ops.duckdb"
    with DuckDBEngine.open(path) as engine:
        catalog.build(engine)
    return path


def opened_rows(path):
    with DuckDBEngine.open(path, read_only=True) as engine:
        result = engine.run("SELECT viewer_id, evidence_id, times_opened, last_run_id, last_route "
                            "FROM strata.ops.evidence_opened ORDER BY viewer_id, evidence_id")
        return [dict(zip(result.columns, row)) for row in result.rows]


def test_a_passage_opens_by_its_evidence_id_as_the_answer_stream_sent_it(reading):
    response = call(create_app(engine_for=reading), "GET", "/api/evidence", ANA, params={"id": ICR_54})

    assert response.status_code == 200
    evidence = response.json()
    row = evidence["row"]
    assert (evidence["id"], evidence["kind"]) == (ICR_54, "passage")
    assert (row["paragraph"], row["section_path"], row["pdf_page"], row["source"]["pdf_pages"]) == ("54", "III.B", 23, 66)
    assert row["source"]["document_date"] == "2019-10-10"
    assert row["source"]["document_type"] == "Implementation Completion and Results Report"
    assert "108 of 328 cases had to go through rebidding" in row["text"]
    assert evidence == json.loads((RECORDED / "evidence-icr-p130164-54.json").read_text())


def test_an_isr_section_has_no_paragraph_number_and_is_named_by_its_section(reading):
    # An ISR numbers no paragraphs, so its passage carries a key for the section ("s4") and says the
    # paragraph is not numbered; the drawer and the card name the section instead.
    response = call(create_app(engine_for=reading), "GET", "/api/evidence", ANA, params={"id": ISR_1_S4})

    assert response.status_code == 200
    evidence = response.json()
    row = evidence["row"]
    assert (evidence["id"], evidence["short_name"]) == (ISR_1_S4, "ISR")
    assert (row["section_path"], row["paragraph_numbered"], row["pdf_page"], row["source"]["pdf_pages"]) == (
        "Project Development Objective Indicators", False, 2, 4)
    assert row["source"]["document_date"] == "2014-02-22"
    assert evidence == json.loads((RECORDED / "evidence-isr-p130164-s4.json").read_text())


def test_a_passage_not_yet_public_on_the_page_s_date_is_not_there(reading):
    # The ICR of October 10, 2019 was public from November 2, 2019.
    response = call(create_app(engine_for=reading), "GET", "/api/evidence", ANA,
                    params={"id": ICR_54, "asof": "2019-10-15"})

    assert (response.status_code, response.json()) == (404, {"code": "unknown_evidence"})


@pytest.mark.parametrize("evidence_id", ["strata.gold.passage:31525018/v1/9999", "not-an-evidence-id",
                                         "strata.gold.nothing:1"])
def test_an_evidence_id_no_source_has_answers_404(reading, evidence_id):
    response = call(create_app(engine_for=reading), "GET", "/api/evidence", ANA, params={"id": evidence_id})

    assert (response.status_code, response.json()) == (404, {"code": "unknown_evidence"})


def test_each_viewer_s_opened_sources_are_one_row_per_evidence_id(ops_db):
    app = create_app(opened=OpenedLog(lambda: DuckDBEngine.open(ops_db), now=lambda: dt.datetime(2026, 10, 23, 12, tzinfo=dt.UTC)))
    for headers, evidence_id in ((ANA, ICR_54), (ANA, ICR_54), (BEN, ICR_54), (ANA, ICR_55)):
        response = call(app, "POST", "/api/evidence/opened", headers,
                        json={"evidence_id": evidence_id, "run_id": "run-0001", "route": "/projects/P130164"})
        assert response.json() == {"recorded": True}

    assert opened_rows(ops_db) == [
        {"viewer_id": "4021@1984", "evidence_id": ICR_54, "times_opened": 2, "last_run_id": "run-0001",
         "last_route": "/projects/P130164"},
        {"viewer_id": "4021@1984", "evidence_id": ICR_55, "times_opened": 1, "last_run_id": "run-0001",
         "last_route": "/projects/P130164"},
        {"viewer_id": "4022@1984", "evidence_id": ICR_54, "times_opened": 1, "last_run_id": "run-0001",
         "last_route": "/projects/P130164"},
    ]
    seen = call(app, "GET", "/api/evidence/opened", BEN, params={"id": [ICR_54, ICR_55]})
    assert seen.json() == {"opened": [ICR_54]}


@pytest.mark.parametrize("evidence_id", ["not-an-evidence-id", "strata.gold.nothing:1", "strata.gold.passage:",
                                         "strata.tools.no_such_tool:P130164@2026-10-23"])
def test_an_evidence_id_no_source_has_is_not_recorded_as_opened(ops_db, evidence_id):
    """Ticket 14's verification round 5, observation 4: only an id the drawer can open is written."""
    app = create_app(opened=OpenedLog(lambda: DuckDBEngine.open(ops_db)))

    response = call(app, "POST", "/api/evidence/opened", ANA, json={"evidence_id": evidence_id})

    assert (response.status_code, response.json()) == (404, {"code": "unknown_evidence"})
    assert opened_rows(ops_db) == []


@pytest.mark.parametrize("evidence_id", [
    "strata.tools.find_comparables:KE-NWWDA-541055-CW-RFB@2026-10-22",  # a tool's summary, opened from its answer
    "steps:KE-NWWDA-541055-CW-RFB:bid_evaluation",  # section 2's list of a step, which a draft's page records
    "steps-longest:KE-NWWDA-541055-CW-RFB",
    "upload-row:upload-0001:3",  # an upload's row, read through the one access rule
])
def test_a_source_the_drawer_opens_without_a_reader_by_id_is_recorded(ops_db, evidence_id):
    app = create_app(opened=OpenedLog(lambda: DuckDBEngine.open(ops_db)))

    assert call(app, "POST", "/api/evidence/opened", ANA, json={"evidence_id": evidence_id}).json() == {
        "recorded": True}


@pytest.mark.parametrize("view", ["piu", "public"])
def test_a_preview_records_no_opened_source(ops_db, view):
    app = create_app(opened=OpenedLog(lambda: DuckDBEngine.open(ops_db)))

    response = call(app, "POST", "/api/evidence/opened", ANA, json={"evidence_id": ICR_54, "view": view})

    assert response.json() == {"recorded": False}
    assert opened_rows(ops_db) == []


def test_a_viewer_no_one_signed_in_as_records_nothing(ops_db):
    app = create_app(opened=OpenedLog(lambda: DuckDBEngine.open(ops_db)))

    response = call(app, "POST", "/api/evidence/opened", {}, json={"evidence_id": ICR_54})

    assert response.json() == {"recorded": False}
    assert opened_rows(ops_db) == []


def test_without_the_app_s_own_engine_nothing_is_recorded_and_nothing_reads_as_opened():
    app = create_app()

    assert call(app, "POST", "/api/evidence/opened", ANA, json={"evidence_id": ICR_54}).json() == {"recorded": False}
    assert call(app, "GET", "/api/evidence/opened", ANA, params={"id": ICR_54}).json() == {"opened": []}


def test_a_write_that_fails_says_so_and_leaves_the_viewer_s_page_alone(tmp_path):
    app = create_app(opened=OpenedLog(lambda: DuckDBEngine.open(tmp_path / "no-tables.duckdb")))

    response = call(app, "POST", "/api/evidence/opened", ANA, json={"evidence_id": ICR_54})

    assert (response.status_code, response.json()) == (200, {"recorded": False})


# Ticket 18's kinds of passage, which the drawer opens from a link: a paragraph the layout parser read from
# a scanned page, a row of a table and its summary, a section of a notice's text, and a paragraph in
# French. tests/record_api.py writes each answer, and the screen tests serve the same files.
NEW_KINDS = [
    ("evidence-pad-p130164-scanned.json", "strata.gold.passage:18381488/v1/23", "paragraph", "layout_parser", True),
    ("evidence-pad-p130164-risk-row.json", "strata.gold.passage:18381488/v1/table65.2", "table_row", "layout_parser", True),
    ("evidence-pad-p130164-risk-summary.json", "strata.gold.passage:18381488/v1/table65", "table_summary",
     "layout_parser", True),
    ("evidence-notice-op00118817.json", "strata.gold.passage:OP00118817/v1/s8", "notice_text", "published_text", False),
    ("evidence-notice-op00118817-qualifications.json", "strata.gold.passage:OP00118817/v1/s5", "notice_text",
     "published_text", False),
    ("evidence-icr-p127203-fr.json", "strata.gold.passage:33407968/v1/1", "paragraph", "published_text", False),
]


@pytest.mark.parametrize("recorded, evidence_id, kind, route, scanned", NEW_KINDS, ids=[case[0] for case in NEW_KINDS])
def test_each_kind_of_passage_opens_by_its_evidence_id_with_its_kind_route_and_scan(reading, recorded, evidence_id,
                                                                                    kind, route, scanned):
    response = call(create_app(engine_for=reading), "GET", "/api/evidence", ANA, params={"id": evidence_id})

    assert response.status_code == 200
    row = response.json()["row"]
    assert (row["kind"], row["route"], row["scanned"]) == (kind, route, scanned)
    assert response.json() == json.loads((RECORDED / recorded).read_text())


def test_a_table_row_carries_its_table_its_row_and_its_cells_and_a_notice_its_id_and_page(reading):
    app = create_app(engine_for=reading)

    row = call(app, "GET", "/api/evidence", ANA, params={"id": "strata.gold.passage:18381488/v1/table65.2"}).json()["row"]
    notice = call(app, "GET", "/api/evidence", ANA, params={"id": "strata.gold.passage:OP00118817/v1/s8"}).json()

    assert (row["table_title"], row["table_row"], row["pdf_page"]) == (
        "Annex 4 - Operational Risk Assessment Framework (ORAF)", 2, 65)
    assert row["cells"][:2] == [["Risk", "Capacity"], ["Rating", "Low"]]
    assert (notice["stratum"], notice["short_name"], notice["row"]["notice_id"]) == ("What", "Notice", "OP00118817")
    assert "[contact removed]" in notice["row"]["text"]
