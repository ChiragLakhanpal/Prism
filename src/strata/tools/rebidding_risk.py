"""rebidding_risk: how many comparable packages were advertised again, and why (ticket 28).

The registry (config/tools.toml) defines the tool's parameters and result shape; this module is its adapter. It
takes find_comparables' own criteria and counts over the same comparable packages, so the reference class is
defined once (CLAUDE.md rule 4):

- m is the comparables find_comparables returned, with the canceled packages it leaves out put back
  (past_range.canceled_as_still_open = false), since a canceled package is the plainest case of one advertised
  again. When m differs from the past range's total for that reason, past_range_total and denominator_reason
  say so. n is those advertised again, by the labels of strata.estimates.rebidding, as of the call's date.
- Each row is one package advertised again, a case: the reason it is grouped under, what line 2 of the screen's
  row shows (row_kind: quote, again, canceled_row or no_award), the reason word for word when one of its notices
  gives one (config/rebidding_reasons.toml), and the records that say so, each cited (evidence). A package goes
  under one group: a reason in words first, then a second notice under its STEP reference, then a canceled plan
  row, then no award.
- groups count the packages under each reason code, most packages first, then the order of
  config/rebidding_reasons.toml and of LABEL_GROUPS. Rows come in the groups' order, and within a group newest
  first by the date of the record that gave the label, then by STEP reference.
- model is the champion's natural frequency, "about k in 10 packages like this one", and the track record behind
  it. It is shown only when m is at least past_range.min_comparables and the champion beat its baseline in its
  latest test year (strata.estimates.rebidding_backtest); otherwise not_shown_reason says why. The screen trusts
  model.shown and checks neither condition itself.

A package that is still inside the no-award wait, or open in any other way, counts among the packages with no
sign of being advertised again, which is what the screen's words say.
"""

from __future__ import annotations

import datetime as dt

from strata.config import load_rebidding_reasons
from strata.estimates import rebidding
from strata.estimates.rebidding import CANCELED_ROW, NO_AWARD, SAME_REFERENCE, Label, Reason
from strata.reader.repair import LOOK_ALIKE
from strata.tools import common, find_comparables, rejected_bids
from strata.lakehouse.clean import agency_id
from strata.tools.registry import Call
from strata.tools.search_passages import notice_page

TOOL = "rebidding_risk"
# The groups a label gives when no notice gives a reason in words, in their order after the reasons in words.
AGAIN_NO_REASON = "again_no_reason"
LABEL_GROUPS = ((SAME_REFERENCE, AGAIN_NO_REASON, "again"), (CANCELED_ROW, CANCELED_ROW, "canceled_row"),
                (NO_AWARD, NO_AWARD, "no_award"))
CANCELED_INCLUDED = "canceled_included"
# The tool's sources that hold notices, for the Data readiness link of "I found no sign" (the 28 brief, 7.4).
NOTICE_SOURCES = ("notices",)
PACKAGE_TABLE = "strata.gold.package"


# ── The records a row cites, as the evidence drawer opens them ───────────

def read_notice(engine, key: str, as_of: dt.date) -> dict | None:
    """One notice as the drawer shows it from a row (strata.silver.notices:{notice_id}): its type, date, STEP
    reference and project, and, when its text gives a reason for advertising again, that sentence word for word,
    highlighted. It never lists a bidder. None when no notice has the id by the as-of date."""
    found = rebidding.engine_rows(engine, as_of)(common.sql(TOOL, "notice"), notice_id=key)
    if not found:
        return None
    notice = found[0]
    award = notice["notice_type"] == "Contract Award"
    fields = [{"key": "notice_type", "value": notice["notice_type"], "kind": "text"},
              {"key": "published", "value": common.iso(notice["notice_date"]), "kind": "date"},
              {"key": "bid_reference", "value": notice["step_reference"], "kind": "text"},
              {"key": "project_id", "value": notice["project_id"], "kind": "text"}]
    given = rebidding.reason_in(notice["notice_text"] or "")
    if given:
        fields.append({"key": "notice_says", "value": given[1], "kind": "text", "highlight": True})
    return {"kind": "record", "row": {
        "reference": key, "notice_id": key, "fields": fields, "public_from": common.iso(notice["public_from"]),
        # Its page on the World Bank's site, the drawer's way out to the source (ticket 28's design review, F1).
        "url": notice_page(key),
        "source": {"source_key": "award_notices" if award else "notices", "document_type": notice["notice_type"],
                   "project_id": notice["project_id"], "document_date": common.iso(notice["notice_date"])}}}


def read_plan_row(engine, key: str, as_of: dt.date) -> dict | None:
    """One activity's row in one plan version as the drawer shows it from a row
    (strata.silver.plan_rows:{document_id}/{STEP reference}): STEP's fields word for word, with its Process Status
    highlighted. None when the version was not public by the as-of date or does not list the activity."""
    document_id, _, reference = key.partition("/")
    found = rebidding.engine_rows(engine, as_of)(common.sql(TOOL, "plan_row"), document_id=document_id,
                                                 step_reference=reference)
    if not document_id or not reference or not found:
        return None
    row = found[0]
    amount = row["estimated_amount_usd"]
    # The page's words (ticket 131): the reference as read when a look-alike swap changed it, and the description as
    # read. A reference the plan's text settled (ticket 78) is the page's own, so the parser's misreading stays out.
    as_read = row["activity_reference_no_as_read"]
    fields = [*([{"key": "activity_reference_no_as_read", "value": as_read, "kind": "text"}]
                if row["reference_repair"] == LOOK_ALIKE and as_read and as_read != reference else []),
              {"key": "description", "value": row["description"], "kind": "text"},
              {"key": "method", "value": row["method"], "kind": "text"},
              {"key": "market_approach", "value": row["market_approach"], "kind": "text"},
              {"key": "review_type", "value": row["review_type"], "kind": "text"},
              {"key": "estimated_amount_usd", "value": None if amount is None else str(amount), "kind": "usd"},
              {"key": "process_status", "value": row["process_status"], "kind": "text", "highlight": True}]
    plan_date = common.iso(row["plan_date"])
    return {"kind": "record", "row": {
        "reference": reference, "activity_reference_no": reference,
        "fields": [field for field in fields if field["value"] not in (None, "")],
        "public_from": common.iso(row["public_from"]),
        # Check a plan on this plan version, at this row: the drawer's way out to the source, as the trail's plan card
        # has (ticket 28's design review, F1).
        "plan_href": (f"/projects/{row['project_id']}/procurement/{agency_id(row['implementing_agency'])}/{plan_date}"
                      f"#{reference}") if row["implementing_agency"] and plan_date else None,
        "source": {"document_type": "Procurement Plan", "implementing_agency": row["implementing_agency"],
                   "project_id": row["project_id"], "document_id": document_id,
                   "document_date": common.iso(row["plan_date"]), "pdf_page": row["pdf_page"]}}}


def _canceled_left_out(found: dict) -> list[str]:
    return [reference for entry in found["coverage"]["not_used"] if entry["reason"] == "canceled"
            for reference in entry["step_references"]]


def _case(label: Label, reason: Reason | None) -> dict:
    """One package advertised again, as a row."""
    if reason is not None:
        code, kind = reason.code, "quote"
        # An award notice is cited by the id section 5's rejected bids cite it by, so one record keeps one marker
        # number and one visited state across the page (ticket 28's review, follow-up 6).
        award = reason.notice_type == "Contract Award"
        cited = rejected_bids.award_notice_evidence_id(reason.notice_id) if award else \
            rebidding.notice_evidence_id(reason.notice_id)
        evidence = [rebidding.Evidence(cited, reason.public_from, "award_notice" if award else "notice",
                                       reason.notice_id, reason.notice_date)]
        quote = {"text": reason.text, "lang": reason.lang, "notice_id": reason.notice_id}
    else:
        source, code, kind = next(group for group in LABEL_GROUPS if group[0] in label.sources)
        given = label.sources[source]
        evidence = [label.notice(), given] if source == SAME_REFERENCE else [given]
        quote = None
    plan = label.sources.get(CANCELED_ROW)
    again = label.sources.get(SAME_REFERENCE)
    return {
        "evidence_id": evidence[0].evidence_id,
        "public_from": max(item.public_from for item in evidence),
        "source": {"project_id": label.project_id, "notice_id": label.notice_id,
                   "plan_document_id": plan.document_id if plan else None},
        "step_reference": label.step_reference,
        "project_id": label.project_id,
        "country_name": label.country_name,
        "reason_code": code,
        "row_kind": kind,
        "quote": quote,
        "dates": {"notice_date": rebidding.iso(label.notice_date), "bids_due": rebidding.iso(label.bids_due),
                  "again_on": again.date if again else None, "plan_date": plan.date if plan else None},
        "process_status": label.process_status if kind == "canceled_row" else None,
        "evidence": [item.as_row() for item in evidence],
        "label_sources": [source for source in rebidding.SOURCES if source in label.sources],
        "rank": None,
    }


def _ordered(cases: list[dict]) -> tuple[list[dict], list[dict]]:
    """The groups, most packages first then the registry's order, and the rows in the groups' order, newest first."""
    order = [reason.code for reason in load_rebidding_reasons()] + [group[1] for group in LABEL_GROUPS]
    by_code: dict[str, list[dict]] = {}
    for case in cases:
        by_code.setdefault(case["reason_code"], []).append(case)
    codes = sorted(by_code, key=lambda code: (-len(by_code[code]), order.index(code)))
    rows, groups = [], []
    for code in codes:
        members = sorted(sorted(by_code[code], key=lambda case: case["step_reference"]),
                         key=lambda case: max(item["date"] for item in case["evidence"]), reverse=True)
        rows += members
        groups.append({"reason_code": code, "count": len(members),
                       "step_references": [case["step_reference"] for case in members]})
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    return rows, groups


def rebidding_risk(call: Call, step_reference: str | None = None, method: str | None = None,
                   category: str | None = None, market_approach: str | None = None, review_type: str | None = None,
                   size_from_usd: float | None = None, size_to_usd: float | None = None, country: str | None = None,
                   notice_from: dt.date | None = None, notice_to: dt.date | None = None) -> dict:
    found = find_comparables.find_comparables(
        call, step_reference=step_reference, method=method, category=category, market_approach=market_approach,
        review_type=review_type, size_from_usd=size_from_usd, size_to_usd=size_to_usd, country=country,
        notice_from=notice_from, notice_to=notice_to)
    floor = int(call.thresholds.value("past_range.min_comparables"))
    refs = [row["step_reference"] for row in found["rows"]] + _canceled_left_out(found)
    m, past_total = len(refs), len(found["rows"])
    coverage = {**found["coverage"], "used": m,
                "not_used": [entry for entry in found["coverage"]["not_used"] if entry["reason"] != "canceled"]}
    result = {"rows": [], "coverage": coverage, "package": found["package"], "criteria": found["criteria"],
              "m": m, "n": 0, "past_range_total": past_total,
              "denominator_reason": CANCELED_INCLUDED if m != past_total else None, "groups": [],
              "model": rebidding.natural_frequency(call, 0, floor, None), "sources": common.sources(TOOL),
              "notice_source_keys": list(NOTICE_SOURCES), "records_through": found["records_through"],
              "rows_per_group": int(call.thresholds.value("rebidding.rows_per_group"))}
    abstention = found["abstention"]
    if abstention is not None and abstention["reason"] != "too_few_comparables":
        return {**result, "abstention": abstention, "m": 0, "past_range_total": past_total, "denominator_reason": None}
    rows_of = rebidding.engine_rows(call.engine, call.as_of)
    labeled = rebidding.labels(rows_of, call.as_of, call.thresholds, refs, period_from=rebidding.EARLIEST)
    again = [labeled[ref] for ref in refs if ref in labeled and labeled[ref].advertised_again]
    given = rebidding.reasons(rows_of, [label.step_reference for label in again])
    rows, groups = _ordered([_case(label, given.get(label.step_reference)) for label in again])
    model = rebidding.natural_frequency(call, m, floor, step_reference if found["package"] else None)
    return {**result, "rows": rows, "n": len(rows), "groups": groups, "model": model, "abstention": None}
