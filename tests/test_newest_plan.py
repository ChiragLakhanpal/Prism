"""The plan reader reads only each project's newest Procurement Plan, and parses the newest plan's pages first
(seam 1; ticket 108).

On the paid workspace on October 27, 2026, the plan reader's 30 minutes went to the pages of P156634's plan of May
2023 (document 34106903), and the October 9, 2026 demo plan, document 40132287, still had no plan rows after three
passes. The reader now reads a project's newest plan, the one by_plan_date ranks first, and lists each older plan
once as superseded in strata.ops.skipped_documents, unless config/thresholds.toml's ingestion.plan_versions says
"all". Here P156634's document list names three of its recorded plans, so the project has three plan versions.
"""

import datetime as dt
import tomllib
from pathlib import Path

import pytest

from strata import config
from strata.fixture import recorded as fmt
from strata.lakehouse import catalog, plans
from strata.lakehouse.engine import DuckDBEngine
from strata.reader.documents import Fetched, RecordedDocuments
from strata.reader.layout import RecordedLayout, https

ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
DEMO_PLAN = "40132287"  # P156634's October 9, 2026 plan (config/slice.toml's demo plan), its newest
# The three plan versions: the demo plan with one table page, and two older plans with two table pages each.
PLAN_DATES = ("2026-10-09", "2025-03-19", "2019-08-26")


class ThreePlans:
    """The recorded documents, with P156634's document list naming only three of its Procurement Plans. It notes the
    address of each text and PDF the reader asks for."""

    def __init__(self, manifest):
        self.recorded = RecordedDocuments(manifest)
        self.asked: list[str] = []

    def listing(self, url):
        fetched = self.recorded.listing(url)
        kept = {key: document for key, document in fetched.body["documents"].items()
                if not isinstance(document, dict) or document.get("docty") != plans.PLAN
                or str(document.get("docdt", ""))[:10] in PLAN_DATES}
        return Fetched(url, {**fetched.body, "documents": kept}, fetched.fetched_at)

    def text(self, url):
        self.asked.append(https(url))
        return self.recorded.text(url)

    def pages(self, url):
        self.asked.append(https(url))
        return self.recorded.pages(url)


class Noting:
    """The recorded layout parser, noting each page it reads in the order it reads them."""

    def __init__(self, manifest):
        self.recorded = RecordedLayout(manifest)
        self.name = self.recorded.name
        self.read: list[tuple[str, int]] = []

    def parse(self, page):
        self.read.append((page.document_id, page.pdf_page))
        return self.recorded.parse(page)


def clock(day: dt.date):
    """A clock that starts at noon UTC on the day and moves a second each time it is read."""
    ticks = iter(range(1, 1_000_000))
    return lambda: dt.datetime.combine(day, dt.time(12), dt.UTC) + dt.timedelta(seconds=next(ticks))


def column(engine, sql: str, **params) -> list:
    return [row[0] for row in engine.run(sql, params).rows]


def plan_versions(chosen: str) -> config.Thresholds:
    """config/thresholds.toml with ingestion.plan_versions set to chosen; "all" is the reader's behavior before
    ticket 108."""
    found = config.load_thresholds()
    return config.Thresholds(found.path, {**found.values, "ingestion": {**found.values["ingestion"],
                                                                        "plan_versions": chosen}})


def every_version() -> config.Thresholds:
    return plan_versions("all")


@pytest.fixture
def fresh():
    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        yield engine


@pytest.fixture
def manifest():
    return fmt.load_manifest()


def read_twice(engine, manifest, thresholds=None):
    """Two nights of the plan reader over P156634's three plan versions."""
    documents, layout = ThreePlans(manifest), Noting(manifest)
    options = {"thresholds": thresholds} if thresholds else {}
    for day in (dt.date(2026, 10, 27), dt.date(2026, 10, 28)):
        plans.run(engine, documents, layout, "P156634", clock=clock(day), run_id=f"night-{day.day}", **options)
    listed = {entry.document_id: entry for entry in plans.listed_plans(engine, "P156634").entries}
    return documents, layout, listed


def test_a_project_with_three_plan_versions_has_only_its_newest_fetched_parsed_and_read_into_plan_rows(
        fresh, manifest):
    documents, layout, listed = read_twice(fresh, manifest)

    assert sorted(str(entry.plan_date) for entry in listed.values()) == sorted(PLAN_DATES)
    newest = listed[DEMO_PLAN]
    assert documents.asked == [https(newest.text_url), https(newest.pdf_url)]  # once, on the first night
    assert {document_id for document_id, _ in layout.read} == {DEMO_PLAN}
    assert column(fresh, "SELECT DISTINCT document_id FROM strata.bronze.document_texts") == [DEMO_PLAN]
    assert column(fresh, "SELECT DISTINCT document_id FROM strata.silver.plan_versions") == [DEMO_PLAN]
    # The plan rows are the demo plan's eight activities and the ones it also lists (tests/ground_truth/values.toml).
    references = column(fresh, "SELECT activity_reference_no FROM strata.silver.plan_rows WHERE document_id = :id",
                        id=DEMO_PLAN)
    assert set(references) == ({row["reference"] for row in GROUND_TRUTH["plan_row"]}
                               | set(GROUND_TRUTH["plan"]["also_lists"]))
    assert column(fresh, "SELECT DISTINCT document_id FROM strata.silver.plan_rows") == [DEMO_PLAN]

    # Each older plan has one superseded row, written by the first night and not again by the second.
    superseded = fresh.run("SELECT run_id, reader, document_id, url, reason FROM strata.ops.skipped_documents "
                           "WHERE outcome = 'superseded' ORDER BY document_id").rows
    older = sorted(document_id for document_id in listed if document_id != DEMO_PLAN)
    assert [document_id for _, _, document_id, _, _ in superseded] == older
    assert {(run_id, reader) for run_id, reader, *_ in superseded} == {("night-27", "plans")}
    assert [url for *_, url, _ in superseded] == [listed[document_id].text_url for document_id in older]
    assert all(f"document {DEMO_PLAN} of October 9, 2026" in reason for *_, reason in superseded)
    assert column(fresh, "SELECT count(*) FROM strata.ops.skipped_documents WHERE outcome <> 'superseded'") == [0]


def test_with_plan_versions_all_every_plan_is_read_and_the_newest_plan_s_pages_are_parsed_before_any_older_one(
        fresh, manifest):
    documents, layout, listed = read_twice(fresh, manifest, every_version())

    newest_first = sorted(listed.values(), key=lambda entry: entry.plan_date, reverse=True)
    assert newest_first[0].document_id == DEMO_PLAN
    # Each plan's text and PDF, newest plan first, on the first night only.
    assert documents.asked == [https(url) for entry in newest_first for url in (entry.text_url, entry.pdf_url)]
    # The waiting pages, by the plan's date, newest first, then by page: the demo plan's table page 3, then pages 3
    # and 4 of the March 19, 2025 plan, then pages 3 and 4 of the August 26, 2019 plan.
    march_2025, august_2019 = (entry.document_id for entry in newest_first[1:])
    assert layout.read == [(DEMO_PLAN, 3), (march_2025, 3), (march_2025, 4), (august_2019, 3), (august_2019, 4)]
    assert sorted(column(fresh, "SELECT DISTINCT document_id FROM strata.silver.plan_rows")) == sorted(listed)
    assert column(fresh, "SELECT count(*) FROM strata.ops.skipped_documents") == [0]


def test_the_thresholds_file_holds_the_newest_plan_rule_and_any_other_value_stops_the_run_and_says_what_to_write(
        fresh, manifest):
    assert config.load_thresholds().value("ingestion.plan_versions") == "newest"

    with pytest.raises(config.ConfigError, match="""is 'every'. Write 'newest' .* or 'all'"""):
        plans.run(fresh, ThreePlans(manifest), Noting(manifest), "P156634", thresholds=plan_versions("every"))
    assert column(fresh, "SELECT count(*) FROM strata.bronze.document_lists") == [0]
