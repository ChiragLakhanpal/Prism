"""Contract awards since FY2020 (Finances One DS00005) into strata.silver.awards.

Each row of the dataset is one supplier of one contract. The transform types each field, works out
the fiscal year from the signing date, parses the STEP reference, maps an old method name to the
current one, and keeps the dataset's INDIVIDUAL CONSULTANT label out of the supplier's name: the
label stands for many people, each with their own supplier ID, and no person is named (spec,
user story 115).
"""

from __future__ import annotations

import datetime as dt
import decimal

from strata.lakehouse import clean

TABLES = {
    "strata.silver.awards": (
        "wb_contract_number", "supplier_id", "project_id", "project_name", "borrower_country_code",
        "borrower_country", "region", "global_practice", "borrower_contract_reference_number", "step_reference",
        "reference_method_code", "contract_description", "procurement_category", "procurement_method",
        "procurement_method_as_written", "review_type", "supplier", "individual_consultant", "supplier_country",
        "supplier_country_code", "supplier_contract_amount_usd", "contract_signing_date", "fiscal_year",
        "page_hash", "fetched_at", "public_from"),
}

PENDING = """
SELECT p.page_hash, p.body, p.fetched_at
FROM strata.bronze.api_pages AS p
WHERE p.source = :source
  AND NOT EXISTS (SELECT 1 FROM strata.silver.awards AS s WHERE s.page_hash = p.page_hash)
ORDER BY p.fetched_at, p.page_hash
"""

INDIVIDUAL_CONSULTANT = "INDIVIDUAL CONSULTANT"


def _text(value) -> str | None:
    text = " ".join(str(value).split()) if value is not None else ""
    return text or None


def _amount(value) -> decimal.Decimal | None:
    if value is None or str(value).strip() == "":
        return None
    return decimal.Decimal(str(value)).quantize(decimal.Decimal("0.01"))


def parse(body: dict, page_hash: str, fetched_at: dt.datetime) -> dict[str, list[tuple]]:
    fetched = fetched_at.astimezone(dt.UTC).date()
    rows = []
    for record in body.get("data") or []:
        if not _text(record.get("wb_contract_number")):
            continue  # a row without its contract number cannot be keyed
        reference = clean.step_reference(record.get("borrower_contract_reference_number"))
        method = clean.method(name=record.get("procurement_method"))
        signed = clean.parse_date(record.get("contract_signing_date"))
        individual = _text(record.get("supplier")) == INDIVIDUAL_CONSULTANT
        rows.append((
            _text(record.get("wb_contract_number")),
            _text(record.get("supplier_id")),
            _text(record.get("project_id")),
            _text(record.get("project_name")),
            _text(record.get("borrower_country_code")),
            _text(record.get("borrower_country")),
            _text(record.get("region")),
            _text(record.get("project_global_practice")),
            _text(record.get("borrower_contract_reference_number")),
            reference.reference if reference else None,
            reference.method_code if reference else None,
            _text(record.get("contract_description")),
            _text(record.get("procurement_category")),
            method.name if method else None,
            _text(record.get("procurement_method")),
            _text(record.get("review_type")),
            None if individual else _text(record.get("supplier")),
            individual,
            _text(record.get("supplier_country")),
            _text(record.get("supplier_country_code")),
            _amount(record.get("supplier_contract_amount_usd")),
            signed,
            clean.fiscal_year(signed),
            page_hash,
            fetched_at,
            clean.public_from(signed, fetched),
        ))
    return {"strata.silver.awards": rows}
