"""Ingestion takes out every contact detail the nightly check looks for (ticket 76; CLAUDE.md rules 4 and 8).

On October 26, 2026 the nightly job's contacts_left check found a labelled phone number in the text of 1,256 of the
workspace's 158,587 notices, because ingestion's removal used stricter patterns than the check. Now the two share one
definition: the removal's last pass is the check's own patterns (contacts.LEFT_EMAIL and LEFT_PHONE), with the label
and the words around it kept. These tests run the check as the nightly job runs it (quality.check_table, on DuckDB,
with the patterns as bound parameters) over what the removal leaves.

SHAPES are the twenty the second session recorded (docs/workspace-catchup.md, "Ticket 76, before step 1"), with every
digit written as 9 and thirty characters kept on each side of the label. Where those thirty characters cut through a
[contact removed] or a number, the shape here is completed in the same way, and its one email address is replaced by
a made-up one of the same shape, with a space after the "@". No value here is a real number or address.
"""

import datetime as dt

import pytest

from strata.config import load_quality_checks
from strata.lakehouse import contacts, quality
from strata.lakehouse.catalog import table_definitions
from strata.lakehouse.engine import DuckDBEngine

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


def test_the_check_flags_every_recorded_shape_and_ingestion_leaves_none_of_them_keeping_each_label(notices):
    recorded = [shape for shape, _ in SHAPES]

    kept = strip_notices(recorded)

    assert contacts_left(notices, recorded) == len(SHAPES)
    assert kept == [expected for _, expected in SHAPES]
    assert contacts_left(notices, kept) == 0
