"""Contract awards since FY2020 (Finances One DS00005) into strata.silver.awards.

Each row of the dataset is one supplier of one contract. The transform types each field, works out
the fiscal year from the signing date, parses the STEP reference, maps an old method name to the
current one, and keeps the dataset's INDIVIDUAL CONSULTANT label out of the supplier's name: the
label stands for many people, each with their own supplier ID, and no person is named (spec,
user stories 59 and 115). For the same reason, a Consultant Services contract whose description
gives a personal title and a name keeps no description. When its supplier names no firm, or the
supplier is written with a personal title and no word that names a firm, the row is a person's
contract: it keeps no supplier name and no description, and counts as an individual consultant
(strata.lakehouse.clean.hires_a_named_person).
"""

from __future__ import annotations

import datetime as dt

from strata.lakehouse import clean

TABLES = {
    "strata.silver.awards": (
        "wb_contract_number", "supplier_id", "project_id", "project_name", "borrower_country_code",
        "borrower_country", "region", "global_practice", "borrower_contract_reference_number", "step_reference",
        "reference_method_code", "contract_description", "procurement_category", "procurement_method",
        "procurement_method_as_written", "market_approach", "review_type", "supplier", "individual_consultant", "supplier_country",
        "supplier_country_code", "supplier_contract_amount_usd", "contract_signing_date", "fiscal_year",
        "page_hash", "fetched_at", "public_from"),
}

# The columns that tell one of the source's records from another (strata.lakehouse.readiness).
RECORD_KEY = ("wb_contract_number", "supplier_id")


INDIVIDUAL_CONSULTANT = "INDIVIDUAL CONSULTANT"


def parse(body: dict, page_hash: str, fetched_at: dt.datetime) -> dict[str, list[tuple]]:
    fetched = fetched_at.astimezone(dt.UTC).date()
    rows = []
    for record in body.get("data") or []:
        if not clean.text(record.get("wb_contract_number")):
            continue  # a row without its contract number cannot be keyed
        reference = clean.step_reference(record.get("borrower_contract_reference_number"))
        method = clean.method(name=record.get("procurement_method"))
        signed = clean.parse_date(record.get("contract_signing_date"))
        # A person is written INDIVIDUAL CONSULTANT, in any capitals, but a description or the
        # supplier field could still name one. A firm hired for a person's services keeps its name.
        category, supplier = record.get("procurement_category"), clean.text(record.get("supplier"))
        person = clean.hires_a_named_person(category, record.get("contract_description"), supplier)
        named = person or clean.names_a_person(category, record.get("contract_description"))
        individual = person or (supplier or "").upper() == INDIVIDUAL_CONSULTANT
        rows.append((
            clean.text(record.get("wb_contract_number")),
            clean.text(record.get("supplier_id")),
            clean.text(record.get("project_id")),
            clean.text(record.get("project_name")),
            clean.text(record.get("borrower_country_code")),
            clean.text(record.get("borrower_country")),
            clean.text(record.get("region")),
            clean.text(record.get("project_global_practice")),
            clean.text(record.get("borrower_contract_reference_number")),
            reference.reference if reference else None,
            reference.method_code if reference else None,
            None if named else clean.text(record.get("contract_description")),
            clean.text(record.get("procurement_category")),
            method.name if method else None,
            clean.text(record.get("procurement_method")),
            method.market_approach if method else None,
            clean.text(record.get("review_type")),
            None if individual else supplier,
            individual,
            clean.text(record.get("supplier_country")),
            clean.text(record.get("supplier_country_code")),
            clean.amount(record.get("supplier_contract_amount_usd")),
            signed,
            clean.fiscal_year(signed),
            page_hash,
            fetched_at,
            clean.public_from(signed, fetched),
        ))
    return {"strata.silver.awards": rows}
