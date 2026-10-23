"""Contract awards since FY2020 (Finances One DS00005) into strata.silver.awards.

Each row of the dataset is one supplier of one contract. The transform types each field, works out
the fiscal year from the signing date, parses the STEP reference, maps an old method name to the
current one, and keeps the dataset's INDIVIDUAL CONSULTANT label out of the supplier's name: the
label stands for many people, each with their own supplier ID, and no person is named (spec,
user story 115).
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

PENDING = """
SELECT p.page_hash, p.body, p.fetched_at
FROM strata.bronze.api_pages AS p
WHERE p.source = :source
  AND NOT EXISTS (SELECT 1 FROM strata.silver.awards AS s WHERE s.page_hash = p.page_hash)
ORDER BY p.fetched_at, p.page_hash
"""

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
        individual = (clean.text(record.get("supplier")) or "").upper() == INDIVIDUAL_CONSULTANT  # in any capitals
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
            clean.text(record.get("contract_description")),
            clean.text(record.get("procurement_category")),
            method.name if method else None,
            clean.text(record.get("procurement_method")),
            method.market_approach if method else None,
            clean.text(record.get("review_type")),
            None if individual else clean.text(record.get("supplier")),
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
