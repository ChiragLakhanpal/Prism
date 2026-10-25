"""The hand-made set for the planned date of each STEP step (ticket 27), which tests/test_step_dates.py and
tests/test_step_backtest.py build in a DuckDB file of their own. tests/ground_truth/values.toml's [step_dates]
says how it is made and how each expected value was worked out by hand.

One Kenya project, P900002, and one implementing agency's plan versions:

- 910000001, dated and public August 1, 2019: the first listing of 25 comparable works packages under Request for
  Bids, C01 to C25, each with planned dates for five steps: the bid invitation on B (September 2, 2019 plus 7
  days for each package after the first), the bidding document 7 days later, the bid opening 37 days after B, the
  bid evaluation report 60 days after B and the signed contract 101 days after B. No completion date is planned.
- 910000002, dated and public December 15, 2020: the same 25, now with actual dates, and the first listing of the
  target package, KE-HAND-900000-CW-RFB, planned but not yet advertised.
- 910000003, dated and public December 1, 2021: the target's actual dates, which only the backtest's outcomes see.
"""

import datetime as dt

from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine

DAY = dt.timedelta(days=1)
PROJECT = "P900002"
AGENCY = "Hand-made Roads Agency"
FIRST, SECOND, THIRD = "910000001", "910000002", "910000003"
FIRST_ON, SECOND_ON, THIRD_ON = dt.date(2019, 8, 1), dt.date(2020, 12, 15), dt.date(2021, 12, 1)
TARGET = "KE-HAND-900000-CW-RFB"
STEPS = ("Specific Procurement Notice / Invitation", "Bidding Documents as Issued",
         "Proposal Submission / Opening / Minutes", "Bid Evaluation Report and Recommendation for Award",
         "Signed Contract", "Contract Completion")
# Each step's planned days after the bid invitation, in the first listing; Contract Completion is not planned.
PLANNED_AFTER = (0, 7, 37, 60, 101, None)
# The target's first planned dates, in version 910000002, and its actual dates, in version 910000003.
TARGET_PLANNED = (dt.date(2021, 3, 1), dt.date(2021, 3, 8), dt.date(2021, 4, 7), dt.date(2021, 4, 30),
                  dt.date(2021, 6, 10), dt.date(2022, 6, 10))
TARGET_ACTUAL = (dt.date(2021, 3, 10), dt.date(2021, 3, 30), dt.date(2021, 4, 20), dt.date(2021, 5, 20),
                 dt.date(2021, 7, 20), None)


def comparable(i: int) -> str:
    return f"KE-HAND-{900000 + i}-CW-RFB"


def comparable_dates(i: int) -> tuple[list[dt.date | None], list[dt.date | None]]:
    """Comparable i's planned dates in its first listing and its actual dates: the bid invitation i - 5 days
    after its plan, the bidding document 7 days after the invitation, the opening 30 days after that, the bid
    evaluation report 20 + 2i days after the opening, and the signed contract 41 days after the report."""
    base = dt.date(2019, 9, 2) + 7 * (i - 1) * DAY
    planned = [None if after is None else base + after * DAY for after in PLANNED_AFTER]
    invitation = base + (i - 5) * DAY
    document = invitation + 7 * DAY
    opening = document + 30 * DAY
    report = opening + (20 + 2 * i) * DAY
    signed = report + 41 * DAY
    return planned, [invitation, document, opening, report, signed, None]


def insert(engine, table: str, rows: list[dict]) -> None:
    columns = tuple(rows[0])
    engine.insert_rows(table, columns, [tuple(row[column] for column in columns) for row in rows])


def version(document_id: str, plan_date: dt.date, order: int, latest: bool) -> dict:
    return {"document_id": document_id, "project_id": PROJECT, "implementing_agency": AGENCY, "plan_date": plan_date,
            "disclosed_on": plan_date, "series_order": order, "previous_document_id": None, "is_latest": latest,
            "pdf_pages": 1, "route_b_pages": 1, "text_url": f"https://example.org/{document_id}.txt",
            "pdf_url": f"https://example.org/{document_id}.pdf", "public_from": plan_date}


def plan_row(document_id: str, public_from: dt.date, reference: str, status: str) -> dict:
    return {"document_id": document_id, "project_id": PROJECT, "section": "WORKS", "activity_reference_no": reference,
            "description": "Hand-made works", "review_type": "Post", "method": "Request for Bids",
            "market_approach": "Open - National", "prequalification": "N", "estimated_amount_usd": "1000000.00",
            "process_status": status, "pdf_page": 1, "parser": "hand-made", "public_from": public_from}


def listing(document_id: str, public_from: dt.date, reference: str, first: bool) -> dict:
    return {"document_id": document_id, "project_id": PROJECT, "activity_reference_no": reference,
            "is_first_listing": first, "first_listing_confirmed": True, "public_from": public_from}


def steps(document_id: str, public_from: dt.date, reference: str, planned, actual) -> list[dict]:
    return [{"document_id": document_id, "project_id": PROJECT, "activity_reference_no": reference, "step": name,
             "step_order": order, "planned_on": planned[order - 1], "actual_on": actual[order - 1],
             "public_from": public_from} for order, name in enumerate(STEPS, 1)]


def package(reference: str, notice_on: dt.date, signed_on: dt.date) -> tuple[dict, dict, dict]:
    """A comparable's gold rows: its notice, its contract and its package row."""
    notice = {"notice_id": f"N-{reference}", "notice_type": "Invitation for Bids", "notice_date": notice_on,
              "project_id": PROJECT, "country_code": "KE", "step_reference": reference,
              "procurement_category": "Works", "procurement_method": "Request for Bids", "public_from": notice_on}
    contract = {"contract_id": f"C-{reference}", "source": "awards", "project_id": PROJECT, "country_code": "KE",
                "step_reference": reference, "procurement_category": "Works", "procurement_method": "Request for Bids",
                "review_type": "Post", "contract_signing_date": signed_on, "contract_amount_usd": "900000.00",
                "amount_basis": "US dollars", "supplier_count": 1, "joint_venture": False, "public_from": signed_on}
    row = {"step_reference": reference, "project_id": PROJECT, "country_code": "KE", "procurement_category": "Works",
           "procurement_method": "Request for Bids", "first_notice_id": notice["notice_id"],
           "first_notice_type": "Invitation for Bids", "first_notice_date": notice_on, "contract_signed_on": signed_on,
           "signed_in": "contract awards", "contract_count": 1, "review_type": "Post", "process_status": "Signed",
           "public_from": notice_on}
    return notice, contract, row


UNRECORDED, UNRECORDED_ON = "910000004", dt.date(2020, 12, 20)


def build(path, bidding_document_unrecorded: bool = False) -> DuckDBEngine:
    """The hand-made set in a DuckDB file at path, with every table the catalog defines. Delay comes from the one
    definition of it (src/strata/lakehouse/sql/plans/plan_step_delays.sql), run over the plan steps above.

    bidding_document_unrecorded adds a plan of December 20, 2020 that lists the 25 comparables again with every
    actual date but the bidding document's, as the fixture's plans never record that step."""
    from strata.lakehouse import plans

    engine = DuckDBEngine.open(path)
    catalog.build(engine)
    insert(engine, "strata.gold.country", [{"country_code": "KE", "country_name": "Kenya",
                                             "region": "Eastern and Southern Africa", "public_from": dt.date(2008, 12, 10)}])
    insert(engine, "strata.gold.project", [{"project_id": PROJECT, "project_name": "Hand-made roads project",
                                             "country_code": "KE", "region": "Eastern and Southern Africa",
                                             "public_from": dt.date(2018, 1, 1)}])
    insert(engine, "strata.silver.plan_versions", [version(FIRST, FIRST_ON, 1, False), version(SECOND, SECOND_ON, 2, False),
                                                    version(THIRD, THIRD_ON, 3, True)]
           + ([version(UNRECORDED, UNRECORDED_ON, 4, False)] if bidding_document_unrecorded else []))
    rows, listings, dated, notices, contracts, packages = [], [], [], [], [], []
    for i in range(1, 26):
        reference = comparable(i)
        planned, actual = comparable_dates(i)
        rows += [plan_row(FIRST, FIRST_ON, reference, "Pending Implementation"), plan_row(SECOND, SECOND_ON, reference, "Signed")]
        listings += [listing(FIRST, FIRST_ON, reference, True), listing(SECOND, SECOND_ON, reference, False)]
        dated += steps(FIRST, FIRST_ON, reference, planned, [None] * 6) + steps(SECOND, SECOND_ON, reference, planned, actual)
        if bidding_document_unrecorded:
            rows.append(plan_row(UNRECORDED, UNRECORDED_ON, reference, "Signed"))
            dated += steps(UNRECORDED, UNRECORDED_ON, reference, planned, [actual[0], None, *actual[2:]])
        notice, contract, row = package(reference, actual[0], actual[4])
        notices.append(notice)
        contracts.append(contract)
        packages.append(row)
    rows += [plan_row(SECOND, SECOND_ON, TARGET, "Pending Implementation"), plan_row(THIRD, THIRD_ON, TARGET, "Signed")]
    listings += [listing(SECOND, SECOND_ON, TARGET, True), listing(THIRD, THIRD_ON, TARGET, False)]
    dated += (steps(SECOND, SECOND_ON, TARGET, TARGET_PLANNED, [None] * 6)
              + steps(THIRD, THIRD_ON, TARGET, TARGET_PLANNED, TARGET_ACTUAL))
    insert(engine, "strata.silver.plan_rows", rows)
    insert(engine, "strata.silver.plan_listings", listings)
    insert(engine, "strata.silver.plan_steps", dated)
    insert(engine, "strata.gold.notice", notices)
    insert(engine, "strata.gold.contract", contracts)
    insert(engine, "strata.gold.package", packages)
    engine.run(plans._sql("plan_step_delays.sql"), {"project_id": PROJECT})
    return engine
