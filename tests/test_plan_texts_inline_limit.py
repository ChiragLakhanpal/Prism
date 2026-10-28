"""The plan reader reads a project's plan versions in statements that fit the warehouse's inline limit: seam 1, the
lakehouse run, over a fake bronze (ticket 123).

On October 28, 2026, ops/plans/run_live.py --rewrite stopped at P156634 with "Inline byte limit exceeded. Statements
executed with disposition=INLINE can have a result size of at most 26214400 bytes": the plan reader read the texts of
all 236 plan versions bronze held for the project in one statement. Here a project has 300 plan versions in bronze,
and an engine that notes every statement it runs counts the reads and the bytes of each result, written as the
warehouse's JSON_ARRAY result writes them. Each test builds only the tables the plan reader touches, from the
catalog's own definitions, so the 300 versions take well under a second.
"""

import datetime as dt
import json

import pytest

from strata import config
from strata.lakehouse import catalog, plans
from strata.lakehouse.engine import DuckDBEngine
from strata.reader import step
from strata.reader.documents import Fetched
from strata.reader.layout import Table, tables_to_json

PROJECT = "P900300"
VERSIONS = 300
ACTIVITIES = 4  # in each plan version
AGENCY = "Northern Water Works Development Agency"
WAREHOUSE_LIMIT = 26_214_400  # the warehouse's inline limit, as its error of October 28, 2026 gave it
SMALL_LIMIT = 50_000  # below what the versions' texts hold together, above what any one version's hold
FETCHED = dt.datetime(2026, 10, 28, 8, 0, tzinfo=dt.UTC)
PLAN_TEXT_TABLES = ("document_texts", "document_pages", "layout_pages")  # in bronze
TABLES = ("bronze.document_lists", "bronze.document_texts", "bronze.document_pages", "bronze.layout_pages",
          "silver.plan_versions", "silver.plan_listings", "silver.plan_rows", "silver.plan_steps",
          "silver.plan_step_delays", "silver.plan_data_notes", "ops.skipped_documents", "ops.parse_runs",
          "ops.parse_failures", "ops.data_readiness")


def document_id(number: int) -> str:
    return f"{90_000_000 + number}"


def plan_date(number: int) -> dt.date:
    return dt.date(2017, 1, 1) + dt.timedelta(days=10 * number)


def plan_text(number: int) -> str:
    """A plan's published text as the documents API gives it: its Executing Agency(ies) line, then its activities,
    the first new in this version, so each version is some activity's first listing."""
    return "\n".join([f"Procurement Plan of {PROJECT}, version {number}", f"Executing Agency(ies): {AGENCY}",
                      *(f"KE-NWWDA-{number + row:06d}-CW-RFB / Supply, installation and commissioning of water "
                        f"transmission pipes, valves and meters for the northern towns, lot {row}"
                        for row in range(ACTIVITIES))])


def page_texts(number: int) -> list[str]:
    """Two PDF pages: the cover, then the table page."""
    return [f"Executing Agency(ies): {AGENCY}\nProcurement Plan, version {number}",
            "Activity Reference No. / Description\n" + plan_text(number)]


def parsed_tables(number: int) -> str:
    """The table page as the layout parser read it: the WORKS table with the plan's activities."""
    return tables_to_json([Table("WORKS", 1, (("Activity Reference No. / Description", "Procurement Method"),
                                              *((line, "Request for Bids") for line in plan_text(number).split("\n")[2:])))])


def listing_response() -> str:
    documents = {f"D{number}": {"id": document_id(number), "docty": plans.PLAN, "docdt": f"{plan_date(number)}T00:00:00Z",
                                "disclosure_date": f"{plan_date(number)}T00:00:00Z",
                                "txturl": f"http://documents.example/{document_id(number)}.txt",
                                "pdfurl": f"http://documents.example/{document_id(number)}.pdf"}
                 for number in range(1, VERSIONS + 1)}
    return json.dumps({"documents": documents, "rows": VERSIONS, "total": VERSIONS})


@pytest.fixture
def bronze():
    """A fresh database whose bronze holds the project's document list and 300 plan versions, each with its text
    and two PDF pages."""
    with DuckDBEngine.open() as engine:
        definitions = {definition.full_name: definition.sql for definition in catalog.table_definitions()}
        for schema in ("bronze", "silver", "ops"):
            engine.run(f"CREATE SCHEMA IF NOT EXISTS strata.{schema}")  # sql-lint: names only
        for table in TABLES:
            engine.run(definitions[f"strata.{table}"])
        engine.insert_rows("strata.bronze.document_lists",
                           ("source", "project_id", "url", "content_hash", "response", "fetched_at", "public_from"),
                           [(plans.SOURCE, PROJECT, "https://search.example/list", "hash", listing_response(), FETCHED,
                             FETCHED.date())])
        engine.insert_rows("strata.bronze.document_texts",
                           ("document_id", "project_id", "url", "content_hash", "text", "fetched_at", "public_from"),
                           [(document_id(number), PROJECT, "url", "hash", plan_text(number), FETCHED, plan_date(number))
                            for number in range(1, VERSIONS + 1)])
        engine.insert_rows("strata.bronze.document_pages",
                           ("document_id", "project_id", "pdf_page", "url", "page_hash", "text", "fetched_at",
                            "public_from"),
                           [(document_id(number), PROJECT, page, "url", f"hash-{number}-{page}", text, FETCHED,
                             plan_date(number))
                            for number in range(1, VERSIONS + 1) for page, text in enumerate(page_texts(number), 1)])
        engine.insert_rows("strata.bronze.layout_pages",
                           ("document_id", "project_id", "pdf_page", "page_hash", "parser", "tables", "text",
                            "figures", "parsed_at", "run_id", "public_from"),
                           [(document_id(number), PROJECT, 2, f"hash-{number}-2", "recorded", parsed_tables(number), "",
                             0, FETCHED, "night", plan_date(number)) for number in range(1, VERSIONS + 1)])
        yield engine


class Noting:
    """The engine, noting each statement it runs with its parameters, the columns it returned and the bytes of its
    rows as the warehouse's JSON_ARRAY result writes them, and the plans whose texts it returned."""

    name = "duckdb"

    def __init__(self, engine):
        self.engine = engine
        self.asked: list[tuple[str, dict, tuple[str, ...], int]] = []
        self.returned: set[str] = set()

    def run(self, sql, params=None):
        result = self.engine.run(sql, params)
        written = len(json.dumps(result.as_text(), ensure_ascii=False).encode("utf-8"))
        self.asked.append((sql, dict(params or {}), result.columns, written))
        if "document_id" in result.columns and {"text", "tables"} & set(result.columns):
            self.returned |= {str(row[result.columns.index("document_id")]) for row in result.rows}
        return result

    def insert_rows(self, table, columns, rows):
        return self.engine.insert_rows(table, columns, rows)

    def largest_on_plan_texts(self) -> int:
        """The most bytes any statement on the plans' texts, pages or parsed tables returned, measures and reads."""
        return max(written for sql, _, _, written in self.asked
                   if any(f"strata.bronze.{table}" in sql for table in PLAN_TEXT_TABLES))

    def reads(self, table: str, column: str) -> list[tuple[str, dict, tuple[str, ...], int]]:
        """The statements that returned the long text column of a bronze table: the reads, not the measures."""
        return [asked for asked in self.asked if f"strata.bronze.{table}" in asked[0] and column in asked[2]]


def listed(engine) -> plans.Listing:
    return plans.listed_plans(engine, PROJECT)


def as_read(versions: list[plans.Version]) -> list[tuple]:
    return [(v.document_id, v.agency, v.listings, v.pages, v.series_order, v.is_latest, v.first_listings, v.reasons)
            for v in versions]


def test_versions_that_fit_the_warehouse_limit_are_read_in_one_statement(bronze):
    """config/thresholds.toml holds the warehouse's own limit, and the 300 versions' texts fit it, so the reader asks
    for every version's text in one statement, by document id, and for every version's pages in one more."""
    limit = plans.inline_result_bytes(config.load_thresholds())
    noting = Noting(bronze)

    versions = plans.read_versions(noting, PROJECT, listed(bronze), limit)

    texts, pages = noting.reads("document_texts", "text"), noting.reads("document_pages", "text")
    assert limit == WAREHOUSE_LIMIT
    assert len(texts) == len(pages) == 1 and len(versions) == VERSIONS
    assert {value for _, params, _, _ in texts for value in params.values() if value != PROJECT} == {
        document_id(number) for number in range(1, VERSIONS + 1)}


def test_a_read_past_the_limit_asks_for_one_plan_version_at_a_time_and_no_statement_returns_more(bronze):
    """The 300 versions' texts together hold more than the limit, so the reader asks for one version a statement, and
    reads the same versions as one statement would."""
    noting = Noting(bronze)

    versions = plans.read_versions(noting, PROJECT, listed(bronze), SMALL_LIMIT)

    texts, pages = noting.reads("document_texts", "text"), noting.reads("document_pages", "text")
    assert len(versions) == VERSIONS
    assert len(texts) == VERSIONS and len(pages) == VERSIONS
    assert all(len([value for value in params.values() if value != PROJECT]) == 1 for _, params, _, _ in texts + pages)
    assert noting.largest_on_plan_texts() <= SMALL_LIMIT
    assert sum(written for *_, written in texts) > SMALL_LIMIT  # the versions' texts together do not fit one statement
    assert as_read(versions) == as_read(plans.read_versions(bronze, PROJECT, listed(bronze), WAREHOUSE_LIMIT))


def with_limit(limit: int) -> config.Thresholds:
    """config/thresholds.toml with ingestion.inline_result_bytes set to limit."""
    thresholds = config.load_thresholds()
    return config.Thresholds(thresholds.path, {**thresholds.values, "ingestion": {
        **thresholds.values["ingestion"], "inline_result_bytes": limit}})


def test_the_rewrite_reads_only_the_versions_silver_holds_through_the_same_read(bronze):
    """ops/plans/run_live.py --rewrite writes each project's rows again from the plan versions its last run read,
    which silver.plan_versions holds: here every other one of the 300, 150 versions."""
    listing = listed(bronze)
    held = plans.read_versions(bronze, PROJECT, plans.Listing(
        [entry for entry in listing.entries if int(entry.document_id) % 2 == 0], listing.dates), WAREHOUSE_LIMIT)
    plans.write_versions(bronze, PROJECT, held)
    noting = Noting(bronze)

    read = plans.rewrite(noting, PROJECT, thresholds=with_limit(SMALL_LIMIT))

    texts, pages = noting.reads("document_texts", "text"), noting.reads("document_pages", "text")
    parsed = noting.reads("layout_pages", "tables")
    asked_for = {value for _, params, _, _ in texts + pages + parsed for value in params.values() if value != PROJECT}
    assert len(texts) == len(pages) == len(parsed) == len(held) == VERSIONS // 2
    assert asked_for == {version.document_id for version in held}
    assert noting.largest_on_plan_texts() <= SMALL_LIMIT
    assert sum(written for *_, written in parsed) > SMALL_LIMIT
    assert read.versions == {version.document_id for version in held} and read.with_reference == ACTIVITIES * len(held)


class TheListOnly:
    """The documents API with the project's document list. Bronze holds every plan's text and pages already, so the
    run asks for none."""

    def listing(self, url):
        return Fetched(url, json.loads(listing_response()), FETCHED)

    def text(self, url):
        raise AssertionError(f"The run asked for {url}, which bronze holds.")

    pages = text


class ParsedAlready:
    """A layout parser the run never needs: bronze holds the parsed tables of every plan's table page."""

    name = "recorded"

    def parse(self, page):
        raise AssertionError(f"The run asked to parse page {page.pdf_page} of {page.document_id}, which bronze holds.")


def test_the_nightly_run_reads_the_newest_plan_version_alone_by_its_document_id(bronze):
    """The nightly's plan reader reads each project's newest plan only (ticket 108), so it asks bronze for that plan's
    text, pages and parsed tables, by its document id, and for none of the 299 older plans bronze holds."""
    noting = Noting(bronze)

    report = plans.run(noting, TheListOnly(), ParsedAlready(), PROJECT, endpoint="https://search.example/list",
                       thresholds=plans.with_plan_versions(config.load_thresholds(), plans.NEWEST),
                       clock=lambda: FETCHED)

    reads = (noting.reads("document_texts", "text") + noting.reads("document_pages", "text")
             + noting.reads("layout_pages", "tables"))
    assert len(reads) == 3 and report.versions == report.versions_with_rows == 1
    assert {value for _, params, _, _ in reads for value in params.values() if value != PROJECT} == {
        document_id(VERSIONS)}
    assert noting.returned == {document_id(VERSIONS)}  # no statement returned an older plan's text


def test_a_plan_version_whose_own_pages_pass_the_limit_is_left_out_and_named(bronze, caplog):
    """No statement may return more than the limit, so a plan version whose pages alone hold more is not read: it
    counts as listed but not read, as a plan too long to keep does (Fetching.not_kept), and the log names it."""
    long = document_id(150)
    bronze.insert_rows("strata.bronze.document_pages",
                       ("document_id", "project_id", "pdf_page", "url", "page_hash", "text", "fetched_at",
                        "public_from"),
                       [(long, PROJECT, page, "url", f"hash-150-{page}", "Annex, a page of drawings\n" * 100, FETCHED,
                         plan_date(150)) for page in range(3, 33)])
    noting = Noting(bronze)

    versions = plans.read_versions(noting, PROJECT, listed(bronze), SMALL_LIMIT)

    assert len(versions) == VERSIONS - 1 and long not in {version.document_id for version in versions}
    assert noting.largest_on_plan_texts() <= SMALL_LIMIT
    assert long not in {value for _, params, _, _ in noting.reads("document_pages", "text") for value in params.values()}
    assert f"document {long} of {PROJECT}" in caplog.text and "ingestion.inline_result_bytes" in caplog.text


def step_tables(number: int) -> str:
    """The table page as ai_parse_document reads a STEP table: STEP's columns, then a Planned and an Actual column for
    each step, over two header rows, and a short cell in each column for each activity. Stored as JSON, it holds a
    quote mark every few characters."""
    steps = step.STEPS[:7]
    labels = (*step.COLUMNS, *(name for name in steps for _ in ("Planned", "Actual")))
    heads = (*("" for _ in step.COLUMNS), *(head for _ in steps for head in ("Planned", "Actual")))
    cells = ("IDA-61740", "1", "Post", "RFB", "Open - National", "Single Stage - One Envelope", "N", "Low",
             "Request for Bids", "Admeasurement", "1,230,000.00", "", "Pending Implementation",
             *(f"{plan_date(number) + dt.timedelta(days=30 * order + late):%Y-%m-%d}"
               for order in range(len(steps)) for late in (0, 12)))
    return tables_to_json([Table("WORKS", 2, (labels, heads, *(
        (f'KE-NWWDA-{number + row:06d}-CW-RFB / Supply of "Class C" pipes, lot {row}', *cells)
        for row in range(ACTIVITIES))))])


def test_the_reader_counts_each_mark_the_warehouse_s_json_writes_with_a_backslash(bronze):
    """The warehouse writes a result as JSON, in which each quote mark, backslash and line break inside a text takes
    two characters. The tables ai_parse_document read are JSON themselves, so a reader that counted only their bytes
    would ask for them in one statement when, as the warehouse writes them, they pass the limit. On the fixture,
    P156634's parsed tables write 9 percent more than their bytes."""
    bronze.run("DELETE FROM strata.bronze.layout_pages WHERE project_id = :project_id", {"project_id": PROJECT})
    bronze.insert_rows("strata.bronze.layout_pages",
                       ("document_id", "project_id", "pdf_page", "page_hash", "parser", "tables", "text",
                        "figures", "parsed_at", "run_id", "public_from"),
                       [(document_id(number), PROJECT, 2, f"hash-{number}-2", "ai_parse_document",
                         step_tables(number), "", 0, FETCHED, "night", plan_date(number))
                        for number in range(1, VERSIONS + 1)])
    plans.write_versions(bronze, PROJECT, plans.read_versions(bronze, PROJECT, listed(bronze), WAREHOUSE_LIMIT))
    whole = Noting(bronze)
    plans.rewrite(whole, PROJECT)
    [(*_, written)] = whole.reads("layout_pages", "tables")  # every version's parsed tables, in one statement
    noting = Noting(bronze)

    read = plans.rewrite(noting, PROJECT, thresholds=with_limit(written - 1))

    assert noting.largest_on_plan_texts() <= written - 1
    assert len(noting.reads("layout_pages", "tables")) == VERSIONS
    assert read.with_reference == ACTIVITIES * VERSIONS
