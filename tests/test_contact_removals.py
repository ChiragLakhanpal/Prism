"""Contact details removed at ingestion, counted by kind (ticket 45; the 45 brief, section 6.2, tile 18).

contacts.strip() takes contact details out of each notice page before bronze keeps it (CLAUDE.md rule 8). It now
counts what it removed by kind: names, emails and phones, which the Governance page shows, and addresses and web
addresses, which come out of the contact fields only. bronze.store() writes those counts to
strata.ops.contact_removals beside each page, so the dashboard counts what ingestion removed without reading a
notice. The values in the page below are made up.
"""

import json

from strata.lakehouse import contacts
from strata.lakehouse.engine import DuckDBEngine

PAGE = {"procnotices": [
    {"id": "OP-made-up-1", "contact_name": "Jane Wanjiru", "contact_email": "jane@example.org",
     "contact_phone_no": "0722 123456", "contact_address": "P.O. Box 1, Nairobi", "contact_web_url": "www.example.org",
     "notice_text": "Contact Jane Wanjiru at jane@example.org or Tel 0722 123456. Bids to bids@example.com."},
    {"id": "OP-made-up-2", "notice_text": "Email sales@example.co for the documents."},
    {"id": "OP-made-up-3", "notice_text": "The works are in Kisumu."},
]}


def test_stripping_counts_each_kind_of_contact_detail_and_the_notices_it_came_from():
    stripped, removals = contacts.strip_counted(PAGE)

    assert {kind: (found.removed, found.records) for kind, found in removals.items()} == {
        "names": (2, 1), "emails": (4, 2), "phones": (2, 1), "addresses": (1, 1), "web_addresses": (1, 1),
        "any": (10, 2)}  # every kind together: two notices lost something, and the third kept all its words
    assert stripped["procnotices"][0]["notice_text"] == (
        "Contact [contact removed] at [contact removed] or Tel [contact removed]. Bids to [contact removed].")


def test_the_counts_by_kind_add_up_to_the_total_strip_has_always_returned():
    _, total = contacts.strip(PAGE)
    _, removals = contacts.strip_counted(PAGE)

    assert total == sum(found.removed for kind, found in removals.items() if kind in contacts.KINDS) == 10


def test_bronze_keeps_each_page_s_removals_by_kind_and_they_add_up_to_its_count(fixture_db):
    """The fixture's notice pages went through bronze.store, so every contact detail bronze counted for a page is in
    strata.ops.contact_removals, by kind."""
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        pages = dict(engine.run("SELECT page_hash, contact_details_removed FROM strata.bronze.api_pages "
                                "WHERE contact_details_removed > 0").rows)
        kinds = engine.run("SELECT page_hash, kind, removed FROM strata.ops.contact_removals").rows

    by_page: dict[str, int] = {}
    for page_hash, kind, removed in kinds:
        if kind in contacts.KINDS:
            by_page[page_hash] = by_page.get(page_hash, 0) + removed
    assert by_page == pages
    assert {page_hash: removed for page_hash, kind, removed in kinds if kind == contacts.ANY} == pages
    assert {kind for _, kind, _ in kinds} <= {*contacts.KINDS, contacts.ANY}
    assert {"names", "emails", "phones"} <= {kind for _, kind, _ in kinds}
    json.dumps(kinds, default=str)  # counts only: no value of a contact detail is kept
