"""Contract awards from FY2001 to FY2016 (Finances One DS01004) into strata.silver.awards_fy2001_2016.

The dataset holds prior-review contracts only and has not changed since March 2022. Each row is
one contract, in US dollars, with no STEP supplier ID: a joint venture is one row whose supplier
names its members. Its references are free text, which a STEP reference rarely matches, and it
writes methods by their names before the 2016 Procurement Regulations, such as International
Competitive Bidding. The transform stores the current name with the market approach the old name
implies, and keeps the dataset's own words in their own column (strata.lakehouse.clean). It also
writes Civil Works as STEP's Works.

The dataset names people, where the later dataset writes INDIVIDUAL CONSULTANT: as the supplier of
an Individual Consultant Selection, as the supplier of a Consultant Qualification Selection that
hired one person, and in contract descriptions such as "the Consultancy Services of Dr. ...". A row
is a contract with a person when its method is Individual Consultant Selection, when its supplier
is INDIVIDUAL CONSULTANT, or when it is for Consultant Services and its description gives a
personal title followed by a name. Such a row keeps no supplier and no description, and is marked
individual_consultant, so no person is named (spec, user stories 59 and 115).
"""

from __future__ import annotations

import datetime as dt

from strata.lakehouse import clean

TABLES = {
    "strata.silver.awards_fy2001_2016": (
        "contract_number", "project_id", "project_name", "borrower_country", "region", "global_practice",
        "borrower_contract_reference_number", "step_reference", "reference_method_code", "contract_description",
        "procurement_category", "procurement_method", "procurement_method_as_written", "market_approach",
        "supplier", "individual_consultant", "supplier_country", "supplier_contract_amount_usd",
        "contract_signing_date", "fiscal_year", "page_hash", "fetched_at", "public_from"),
}

# The columns that tell one of the source's records from another (strata.lakehouse.readiness).
RECORD_KEY = ("contract_number", "supplier", "supplier_contract_amount_usd")


INDIVIDUAL = ("INDIVIDUAL CONSULTANT", "INDIVIDUAL CONSULTANT SELECTION")


def _with_a_person(record: dict) -> bool:
    """Whether the row is a contract with a person, whom the dataset may name."""
    if any((clean.text(record.get(field)) or "").upper() in INDIVIDUAL for field in ("supplier", "procurement_method")):
        return True
    return (clean.names_a_person(record.get("procurement_category"), record.get("contract_description"))
            or clean.titled(record.get("supplier")))


def parse(body: dict, page_hash: str, fetched_at: dt.datetime) -> dict[str, list[tuple]]:
    fetched = fetched_at.astimezone(dt.UTC).date()
    rows = []
    for record in body.get("data") or []:
        number = clean.text(record.get("contract_number"))
        if not number:
            continue  # a row without its contract number cannot be keyed
        reference = clean.step_reference(record.get("borrower_contract_reference_number"))
        method = clean.method(name=record.get("procurement_method"))
        signed = clean.parse_date(record.get("contract_signing_date"))
        individual = _with_a_person(record)
        rows.append((
            number,
            clean.text(record.get("project_id")),
            clean.text(record.get("project_name")),
            clean.text(record.get("borrower_country")),
            clean.text(record.get("region")),
            clean.text(record.get("project_global_practice")),
            clean.text(record.get("borrower_contract_reference_number")),
            reference.reference if reference else None,
            reference.method_code if reference else None,
            None if individual else clean.text(record.get("contract_description")),
            clean.category(record.get("procurement_category")),
            method.name if method else None,
            clean.text(record.get("procurement_method")),
            method.market_approach if method else None,
            None if individual else clean.text(record.get("supplier")),
            individual,
            clean.text(record.get("supplier_country")),
            clean.amount(record.get("supplier_contract_amount")),
            signed,
            clean.fiscal_year(signed),
            page_hash,
            fetched_at,
            clean.public_from(signed, fetched),
        ))
    return {"strata.silver.awards_fy2001_2016": rows}
