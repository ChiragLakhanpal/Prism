"""Ingestion takes out every contact detail the nightly check looks for (ticket 76; CLAUDE.md rules 4 and 8).

On October 26, 2026 the nightly job's contacts_left check found a labelled phone number in the text of 1,256 of the
workspace's 158,587 notices, because ingestion's removal used stricter patterns than the check. Now the two share one
definition: the removal's last pass is the check's own patterns (contacts.LEFT_EMAIL and LEFT_PHONE), with the label
and the words around it kept. These tests run the check as the nightly job runs it (quality.check_table, on DuckDB,
with the patterns as bound parameters) over what the removal leaves. Silver runs the removal again on each notices
page it reads, and the notices transform's VERSION is 2, so the pages bronze kept before the fix are read again.

SHAPES are the twenty the second session recorded (docs/workspace-catchup.md, "Ticket 76, before step 1"), with every
digit written as 9 and thirty characters kept on each side of the label. Where those thirty characters cut through a
[contact removed] or a number, the shape here is completed in the same way, and its one email address is replaced by
a made-up one of the same shape, with a space after the "@". No value here is a real number or address.
"""

import datetime as dt
import importlib.util
import json
import random
import shutil
from pathlib import Path

import pytest
from nightly_helpers import clock

from strata.config import load_quality_checks, load_sources
from strata.lakehouse import bronze, contacts, nightly, quality, silver
from strata.lakehouse.catalog import table_definitions
from strata.lakehouse.engine import DuckDBEngine
from strata.lakehouse.silver import notices as notices_module

ROOT = Path(__file__).resolve().parents[1]
R = contacts.REMOVED

# Each shape as the workspace's silver.notices holds it, and what ingestion must leave of it.
SHAPES = [
    (f"etnam. Tel: {R} Fax: 99-9-9999999 Email: {R} ; {R}",
     f"etnam. Tel: {R} Fax: {R} Email: {R} ; {R}"),
    (f"eral Phone: {R} Fax: 99-9-99999999 E-mail: {R}",
     f"eral Phone: {R} Fax: {R} E-mail: {R}"),
    (f"oad. Phone: {R} Fax #: 9999 99-999 9999 E-mail Address: {R}",
     f"oad. Phone: {R} Fax #: {R} E-mail Address: {R}"),
    (f"akistan Ph: {R} Fax:: 99-99-9999999 Email: {R} Web:",
     f"akistan Ph: {R} Fax:: {R} Email: {R} Web:"),
    (f"Telephone: {R} Fax: 99-99-9999999",
     f"Telephone: {R} Fax: {R}"),
    (f"Telephone: {R} Fax: 99-9-9999999 Email: {R}",
     f"Telephone: {R} Fax: {R} Email: {R}"),
    ("o 999, Building C, 9th Floor. Telephone: 999 999 9 999 999. Facsimile number: 999 999 9 999 999",
     f"o 999, Building C, 9th Floor. Telephone: {R}. Facsimile number: {R}"),
    (f"ietnam Tel: {R} Fax: 99-9-99999999 E-mail: jdoe@ example.vn",
     f"ietnam Tel: {R} Fax: {R} E-mail: {R}"),
    (f"{R}, 99-99-99999999 Fax: 99-99-99999999 Email: {R}",
     f"{R}, {R} Fax: {R} Email: {R}"),
    (f"kistan Tel: {R} Fax: 99-99-99999999 Email: {R}",
     f"kistan Tel: {R} Fax: {R} Email: {R}"),
    (f"{R} or {R} Tel. (99) 9 -9 9 . 999 . 999 ; Fax. ( 99) 9 -9 9 . 999 . 999",
     f"{R} or {R} Tel. {R} ; Fax. {R}"),
    (f"et Nam Tel: {R} Fax: 99-9-99999999 E-mail: {R}",
     f"et Nam Tel: {R} Fax: {R} E-mail: {R}"),
    (f"999 Giang Vo, Hanoi , Vietnam Tel: (-99-9)9999999 Fax: (-99-9)9999999 Email: {R}",
     f"999 Giang Vo, Hanoi , Vietnam Tel: {R} Fax: {R} Email: {R}"),
    (f"{R} Ph: {R} Fax: 99-99-9999999",
     f"{R} Ph: {R} Fax: {R}"),
    (f"Phone99 99 9999999l, 99999999 Fax 99 99 99999999, 99999999 E-mail: {R}",
     f"Phone{R}l, {R} Fax {R} E-mail: {R}"),
    (f"ietnam Tel: {R} Fax: 99-9-99999999 E-mail: {R}",
     f"ietnam Tel: {R} Fax: {R} E-mail: {R}"),
    (f"stafabad, Dharampura, Lahore. Phone No. 99 99 9999999l - 99999999 Fax No. {R}",
     f"stafabad, Dharampura, Lahore. Phone No. {R}l - {R} Fax No. {R}"),
    (f"{R}, {R} Fax: 99 99 9999999",
     f"{R}, {R} Fax: {R}"),
    (f"{R}l, 99999999 Fax: 99-99-99999999, 99999999 E-mail: {R}",
     f"{R}l, {R} Fax: {R} E-mail: {R}"),
    (f"etnam Tel.: {R} Fax: + 99 9 99999999 9. Qualifications requirement",
     f"etnam Tel.: {R} Fax: {R}. Qualifications requirement"),
]
NOTICES = next(entry for entry in load_quality_checks() if entry.contacts)


@pytest.fixture
def notices():
    """An empty strata.silver.notices, from its catalog definition, in memory."""
    with DuckDBEngine.open() as engine:
        engine.run("CREATE SCHEMA IF NOT EXISTS strata.silver")
        engine.run(next(d for d in table_definitions() if d.full_name == NOTICES.table).sql)
        yield engine


def contacts_left(engine, texts: list[str]) -> int:
    """How many notices holding these texts the nightly check flags, as the job runs it."""
    engine.run(f"DELETE FROM {NOTICES.table} WHERE page_hash = :page",  # sql-lint: names only, the registry's table
               {"page": "made-up"})
    when = dt.datetime(2026, 10, 26, tzinfo=dt.UTC)
    engine.insert_rows(NOTICES.table, ("notice_id", "notice_text", "contact_details_removed", "page_hash",
                                       "fetched_at", "public_from"),
                       [(f"OP-made-up-{number}", text, False, "made-up", when, when.date())
                        for number, text in enumerate(texts)])
    [found] = [r.found for r in quality.check_table(engine, NOTICES) if r.check_kind == "contacts_left"]
    return found


def strip_notices(texts: list[str]) -> list[str]:
    """What ingestion keeps of each text, as a notice's free text on a fetched page."""
    page = {"procnotices": [{"id": f"OP-made-up-{n}", "notice_text": text} for n, text in enumerate(texts)]}
    stripped, _ = contacts.strip(page)
    return [notice["notice_text"] for notice in stripped["procnotices"]]


def silver_texts(texts: list[str]) -> list[str]:
    """What silver keeps of each text, read from a page bronze kept as it is."""
    page = {"procnotices": [{"id": f"OP-made-up-{n}", "notice_text": text} for n, text in enumerate(texts)]}
    column = notices_module.TABLES[NOTICES.table].index("notice_text")
    rows = notices_module.parse(page, "page-1", dt.datetime(2026, 10, 26, tzinfo=dt.UTC))[NOTICES.table]
    return [row[column] or "" for row in rows]


def test_the_check_flags_every_recorded_shape_and_ingestion_leaves_none_of_them_keeping_each_label(notices):
    recorded = [shape for shape, _ in SHAPES]

    kept = strip_notices(recorded)

    assert contacts_left(notices, recorded) == len(SHAPES)
    assert kept == [expected for _, expected in SHAPES]
    assert contacts_left(notices, kept) == 0


def test_silver_reads_a_page_bronze_kept_before_the_fix_without_the_numbers_the_check_finds(notices):
    """The workspace's bronze pages were stripped by the removal as it was, so silver runs the removal again when it
    reads one. A notice is HTML, and an entity between a label and its number (Fax:&#160;99...) hid the number from
    a removal that reads the HTML, so the last pass runs again on the plain text silver keeps, the text the check
    reads."""
    shapes = [shape for shape, _ in SHAPES] + ["Fax:&#160;99-9-9999999 Tel:<b> </b>99 99 9999999"]
    body = {"procnotices": [{"id": "OP-made-up-1", "notice_type": "Invitation for Bids", "noticedate": "2009-06-01",
                             "notice_text": "".join(f"<p>{shape}</p>" for shape in shapes),
                             "bid_description": "Works. Mobile: 99999 99999. Fax 99-99-9999999"}]}
    columns = notices_module.TABLES[NOTICES.table]

    [row] = notices_module.parse(body, "page-1", dt.datetime(2026, 10, 26, tzinfo=dt.UTC))[NOTICES.table]
    notice = dict(zip(columns, row, strict=True))

    assert notice["notice_text"].split("\n") == [expected for _, expected in SHAPES] + [f"Fax: {R} Tel: {R}"]
    assert notice["bid_description"] == f"Works. Mobile: {R}. Fax {R}"
    assert notice["contact_details_removed"] is True
    assert contacts_left(notices, [notice["notice_text"], notice["bid_description"]]) == 0


def made_up_texts(count: int, seed: int = 76) -> list[str]:
    """Notice text put together at random from labels, the characters between a label and its number, numbers in
    many shapes, removed details and the words around them. Every digit and address is made up."""
    pick = random.Random(seed)
    labels = ["Tel", "TEL", "Telephone", "Telefax", "Phone", "Cellphone", "Mobile", "Mob", "Cell", "Fax", "Facsimile",
              "Ph", "Contact", "E-mail", "Ref"]
    between = ["", " ", ": ", ":: ", " No. ", " #: ", ". (", ": (-", ": + ", " number: ", "/Fax: ", " (office): ",
               "</b>&nbsp;", "&#160;", "<br/>", " Nr ", "\n", " and "]
    around = [R, "Nairobi", "2019-2020", "P.O. Box 05586-00100", "USD 1,234,567.00", "jdoe@ example.org",
              "JDOE @ EXAMPLE.COM", "l, ", ", ", " / ", " - ", "; ", "l - ", " or ", "Dated 12/03/2019", "Ext. 42301",
              "Société", "Tél"]

    def number() -> str:
        groups = ["".join(pick.choice("0123456789") for _ in range(pick.randint(1, 8)))
                  for _ in range(pick.randint(1, 5))]
        return "".join(group + pick.choice(["", " ", "-", ".", " . ", ")", "(", " -"]) for group in groups).strip()

    def part() -> str:
        kind = pick.random()
        if kind < 0.45:
            return pick.choice(labels) + pick.choice(between) + number()
        return pick.choice(around) if kind < 0.8 else number()

    return [pick.choice(["", " "]).join(part() for _ in range(pick.randint(2, 8))) for _ in range(count)]


def test_the_check_finds_nothing_in_what_either_removal_leaves_of_a_thousand_made_up_texts(notices):
    """The removal and the check share one definition, so the check never finds what the removal leaves: not
    in a page bronze keeps, and not in the plain text silver keeps. The check reads the patterns with RE2, as on
    DuckDB, and the removal with Python, so this also shows that the two read them the same way."""
    texts = made_up_texts(1000)
    from_bronze = strip_notices(texts)
    from_silver = silver_texts(texts)

    assert contacts_left(notices, texts) > 300  # the texts carry what the check looks for
    assert contacts_left(notices, from_bronze) == 0
    assert contacts_left(notices, from_silver) == 0


@pytest.fixture
def workspace_before_the_fix(fixture_db, tmp_path):
    """A writable copy of the fixture database holding what the workspace held on October 26, 2026: a notices
    page bronze kept after the removal as it was then, the silver row read from it with a fax number left, and
    ticket 75's record that silver read the page under version 1 of the notices transform."""
    target = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, target)
    fetched = dt.datetime(2026, 10, 20, 6, 54, tzinfo=dt.UTC)
    kept = f"Tel: {R} Fax: 99-9-9999999 Email: {R}"
    page = {"procnotices": [{"id": "OP-made-up-76", "notice_type": "Invitation for Bids", "noticedate": "2009-06-01",
                             "project_id": "P156634", "notice_text": f"<p>The works are in Kisumu.</p><p>{kept}</p>"}]}
    with DuckDBEngine.open(target) as engine:
        engine.insert_rows("strata.bronze.api_pages", bronze.COLUMNS, [(
            "notices", "KE", "made-up request", "made-up-page", json.dumps(page), 1, 1, dt.date(2009, 6, 1), 2,
            fetched, fetched.date())])
        engine.insert_rows(NOTICES.table, ("notice_id", "notice_type", "notice_date", "project_id", "notice_text",
                                           "contact_details_removed", "page_hash", "fetched_at", "public_from"),
                           [("OP-made-up-76", "Invitation for Bids", dt.date(2009, 6, 1), "P156634",
                             f"The works are in Kisumu.\n{kept}", True, "made-up-page", fetched, dt.date(2009, 6, 1))])
        engine.insert_rows(silver.SILVER_PAGES, silver.SILVER_PAGES_COLUMNS, [
            ("notices", "made-up-page", silver.tables(notices_module), 1, fetched, fetched.date())])
        yield engine


class Workspace:
    """The live script's workspace, with the copy of the fixture database for its SQL warehouse."""

    def __init__(self, engine):
        self._engine = engine

    def engine(self):
        return self._engine


def live_script():
    spec = importlib.util.spec_from_file_location("strata_ops_notices_contacts_left_live",
                                                  ROOT / "ops" / "notices" / "contacts_left_live.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_next_bronze_to_gold_reads_the_pages_read_under_version_1_again_and_the_check_then_finds_none(
        workspace_before_the_fix, capsys):
    """The live step's route: the notices transform's VERSION is 2, so ticket 75's record sends every notices page
    read under version 1 back to silver, which runs the fixed removal on it. The fixture's own pages were read under
    version 2, so the page left from before the fix is the only one read again. The live script counts what the
    check finds before and after."""
    engine = workspace_before_the_fix
    script = live_script()
    night = dt.datetime(2026, 10, 27, 7, 0, tzinfo=dt.UTC)
    source = load_sources()["notices"]

    assert silver.pending(engine, source) == ["made-up-page"]
    assert script.main(["--check-zero"], Workspace(engine), env={}) == 1
    nightly.main(["--task", "bronze_to_gold", "--run-id", "night-76", "--src", "src"], engine,
                 fetch=lambda source, engine: (), clock=clock(night, step=dt.timedelta(seconds=1)))
    assert script.main(["--check-zero"], Workspace(engine), env={}) == 0

    assert capsys.readouterr().out.splitlines() == [
        "The nightly check's patterns find 1 notice on 1 page of strata.silver.notices.",
        "The nightly check's patterns find 0 notices on 0 pages of strata.silver.notices."]
    assert engine.run("SELECT notice_text, contact_details_removed FROM strata.silver.notices "
                      "WHERE notice_id = :id", {"id": "OP-made-up-76"}).rows == (
        (f"The works are in Kisumu.\nTel: {R} Fax: {R} Email: {R}", True),)
    assert engine.run("SELECT found FROM strata.ops.quality_checks WHERE run_id = :run AND check_kind = :kind",
                      {"run": "night-76", "kind": "contacts_left"}).rows == ((0,),)
    assert engine.run("SELECT notice_type, project_id FROM strata.gold.notice WHERE notice_id = :id",
                      {"id": "OP-made-up-76"}).rows == (("Invitation for Bids", "P156634"),)
    assert silver.pending(engine, source) == []


