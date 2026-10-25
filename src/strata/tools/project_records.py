"""project_records: the records a mission brief is written from, for one project (ticket 37).

The registry (config/tools.toml) defines the tool's parameters and result shape; this module is its adapter. It
reads, as of the as-of date (ADR 0002), the records behind the mission brief's five parts, each a row cited by its
own evidence id, in the shape the evidence drawer shows a record (its fields by key, with the kind each is written
as), with the part it belongs to:

- plans: each implementing agency's latest Procurement Plan, with how many activities it lists and how many of
  them check_plan marks as needing a look or worth watching (strata.silver.plan_versions:<document>);
- awards: each contract signed after the latest ISR's date, oldest first, with the supplier as the award record
  names it (never an individual consultant's name) and the Estimated Amount of the latest plan that lists its STEP
  reference (strata.gold.contract:<contract>);
- ratings: each rating each ISR read printed for progress towards the development objective and for overall
  implementation progress, oldest ISR first (strata.silver.isr_ratings:<project>/<document>/<rating>);
- disbursement: each loan or credit in its newest snapshot (strata.gold.loan:<project>/<loan>), with its amounts
  in US$ millions to one decimal as well;
- closing: each month the loan history first showed a new closing date (strata.gold.project_closing_date), and
  each activity in an agency's latest plan with no signed contract whose planned completion falls after the
  closing date, with how many days after (strata.silver.plan_rows:<document>/<reference>).

Every figure a sentence may state that no single record holds (how many contracts were signed and their total,
the commitment, disbursed and undisbursed totals and the share disbursed, the days and whole months left before
closing, how many times the closing date moved, how many activities finish after it) is a column of the result's
summary record (CLAUDE.md rule 1), and parts says which parts have no records and why.
"""

from __future__ import annotations

import datetime as dt
from decimal import ROUND_HALF_UP, Decimal
from importlib import resources

from strata.config import load_project_page, load_sources
from strata.tools import check_plan as plan_check
from strata.tools import project_signals as signals
from strata.tools.registry import Call

PARTS = ("plans", "awards", "ratings", "disbursement", "closing")
CENT, WHOLE = Decimal("0.01"), Decimal(1)
INDIVIDUAL = "individual consultant"


def _sql(folder: str, name: str) -> str:
    return (resources.files("strata.tools") / "sql" / folder / name).read_text()


def _rows(call: Call, folder: str, name: str, **params) -> list[dict]:
    result = call.engine.run(_sql(folder, name), {**params, "as_of": call.as_of})
    return [dict(zip(result.columns, row)) for row in result.rows]


def _iso(value) -> str | None:
    return signals._iso(value)


def _date(value) -> dt.date | None:
    return signals._date(value)


def _cents(value) -> str | None:
    return None if value is None or value == "" else str(Decimal(str(value)).quantize(CENT))


def _record(evidence_id: str, public_from, part: str, source_key: str, project_id: str, date, reference: str,
            fields: list[tuple[str, object, str]]) -> dict:
    """One record as the evidence drawer shows it, with the part of the mission brief it belongs to."""
    return {"evidence_id": evidence_id, "public_from": _iso(public_from), "part": part, "reference": reference,
            "source": {"source_key": source_key, "document_type": _dataset(source_key), "project_id": project_id,
                       "document_date": _iso(date)},
            "fields": [{"key": key, "value": value, "kind": kind} for key, value, kind in fields
                       if value is not None and value != ""]}


# The source registry's key for the dataset each kind of record comes from (config/sources.toml).
DATASETS = {"plans": "documents", "awards": "awards", "isr_ratings": "documents", "loans": "ida_credits",
            "loan_history": "ida_credit_history"}


def _dataset(source_key: str) -> str:
    """The dataset or collection a record comes from, as the source registry names it."""
    source = load_sources().get(DATASETS.get(source_key, source_key))
    return source.dataset_name if source else source_key


def _plans(call: Call, project: dict, record_agencies: list[str]) -> tuple[list[dict], list[dict], list[str]]:
    """The latest plan of each agency, the activities in those plans planned to finish after closing, and the
    agencies the project record names that published no plan."""
    rows, after, series = [], [], []
    closing = _date(project["closing_date"])
    for latest in signals._rows(call, "latest_plans.sql", project_id=project["project_id"]):
        result = plan_check.check_plan(call, project["project_id"], latest["implementing_agency"])
        if result["plan"] is None:
            continue
        plan, counts = result["plan"], result["counts"]
        series.append(plan["implementing_agency"].lower())
        rows.append(_record(plan["evidence_id"], plan["public_from"], "plans", "plans", project["project_id"],
                            plan["plan_date"], plan["implementing_agency"],
                            [("implementing_agency", plan["implementing_agency"], "text"),
                             ("plan_date", plan["plan_date"], "date"), ("activities", counts["activities"], "count"),
                             ("needs_a_look", counts["needs_a_look"], "count"), ("watch", counts["watch"], "count")]))
        for row in result["rows"]:
            finish = _date(row["planned_completion_on"])
            signed = row["signed_on"] is not None or row["process_status"] in plan_check.CONTRACT_STATUSES
            if closing and finish and finish > closing and not signed and row["process_status"] != "Canceled":
                after.append(_record(row["evidence_id"], row["public_from"], "closing", "plans", project["project_id"],
                                     plan["plan_date"], row["activity_reference_no"],
                                     [("activity_reference_no", row["activity_reference_no"], "text"),
                                      ("implementing_agency", plan["implementing_agency"], "text"),
                                      ("planned_completion_on", row["planned_completion_on"], "date"),
                                      ("days_after_closing", (finish - closing).days, "count")]))
    unmatched = [name for name in record_agencies if name.lower() not in series]
    return rows, after, unmatched


def _estimates(call: Call, project_id: str) -> dict[str, dict]:
    """Each STEP reference's Estimated Amount in the latest plan version that lists it."""
    latest: dict[str, dict] = {}
    for row in _rows(call, "project_records", "estimates.sql", project_id=project_id):
        latest[row["activity_reference_no"]] = row  # ordered by plan date, so the last one wins
    return latest


def _awards(call: Call, project_id: str, since: dt.date) -> list[dict]:
    estimates = _estimates(call, project_id)
    rows = []
    for row in _rows(call, "project_records", "awards.sql", project_id=project_id, since=since):
        reference = row["step_reference"]
        estimate = estimates.get(reference) if reference else None
        individual = row["supplier_kind"] == INDIVIDUAL
        usd = row["contract_amount_usd"]
        rows.append(_record(f"strata.gold.contract:{row['contract_id']}", row["public_from"], "awards", "awards",
                            project_id, row["contract_signing_date"], reference or row["contract_id"],
                            [("step_reference", reference, "text"),
                             ("contract_description", row["contract_description"], "text"),
                             ("signed_on", _iso(row["contract_signing_date"]), "date"),
                             ("supplier", None if individual else row["supplier_name"], "text"),
                             ("individual_consultant", True if individual else None, "flag"),
                             ("signed_amount_usd", _cents(usd), "usd"),
                             ("signed_amount", None if usd is not None else _cents(row["contract_amount"]), "amount"),
                             ("currency", None if usd is not None else row["contract_currency"], "text"),
                             ("estimated_amount_usd", _cents(estimate["estimated_amount_usd"]) if estimate else None, "usd")]))
    return rows


def _ratings(call: Call, project_id: str) -> list[dict]:
    rated = load_project_page().isr_ratings
    rows = []
    for row in reversed(signals._rows(call, "isr_ratings.sql", project_id=project_id)):
        key = rated.get(row["rating_name"])
        if not key:
            continue
        item = signals._rating_item(project_id, row, key)
        rows.append(_record(item["evidence_id"], row["public_from"], "ratings", "isr_ratings", project_id,
                            row["isr_date"], project_id,
                            [("sequence", item["sequence"], "count"), ("isr_date", item["isr_date"], "date"),
                             ("rating_key", key, "key"), ("rating_name", row["rating_name"], "text"),
                             ("current_rating", row["current_rating"], "text"),
                             ("previous_rating", row["previous_rating"], "text")]))
    return rows


def _loans(call: Call, project_id: str) -> list[dict]:
    rows = []
    for row in signals._rows(call, "loans.sql", project_id=project_id):
        amounts = {key: Decimal(str(row[key])) if row[key] is not None else Decimal(0)
                   for key in ("original_principal_usd", "disbursed_usd", "undisbursed_usd", "cancelled_usd")}
        rows.append(_record(f"strata.gold.loan:{project_id}/{row['loan_number']}", row["public_from"], "disbursement",
                            "loans", project_id, row["as_of"], row["loan_number"],
                            [("loan_number", row["loan_number"], "text"),
                             *((key, _cents(row[key]), "usd") for key in amounts),
                             *((f"{key.removesuffix('_usd')}_millions", signals.millions(value), "millions")
                               for key, value in amounts.items()),
                             ("snapshot", _iso(row["as_of"]), "date")]))
    return rows


def _history(call: Call, project_id: str) -> list[dict]:
    history = signals._rows(call, "history.sql", project_id=project_id)
    return [_record(item["evidence_id"], item["public_from"], "closing", "loan_history", project_id, item["reported_on"],
                    project_id, [("closing_date", item["closing_date"], "date"),
                                 ("previous_closing_date", item["previous_closing_date"], "date"),
                                 ("reported_on", item["reported_on"], "date")])
            for item in (signals._history_item(project_id, row) for row in history[1:])]


def _value(row: dict, key: str):
    return next((field["value"] for field in row["fields"] if field["key"] == key), None)


def project_records(call: Call, project_id: str) -> dict:
    """The mission brief's records for one project, as of call.as_of."""
    history = signals._rows(call, "history.sql", project_id=project_id)
    project = signals._project(call, project_id, history)
    empty = {"rows": [], "coverage": {"matched": 0, "used": 0, "not_used": []}, "project": project, "isr": None,
             "parts": {}, "unmatched_agencies": [], "totals": {}}
    if project is None:
        return {**empty, "abstention": {"reason": "unknown_project", "project_id": project_id}}
    found = signals._rows(call, "project.sql", project_id=project_id)
    record_agencies = (plan_check.implementing_agencies(found[0]["implementing_agency"])
                       if found and plan_check.record_is_current(found[0], call.as_of) else [])

    plans, after, unmatched = _plans(call, project, record_agencies)
    ratings = _ratings(call, project_id)
    latest = ratings[-1] if ratings else None
    isr = None if latest is None else {"evidence_id": latest["evidence_id"], "document_id": latest["evidence_id"].split("/")[1],
                                        "isr_date": _value(latest, "isr_date"), "sequence": _value(latest, "sequence")}
    awards = _awards(call, project_id, dt.date.fromisoformat(isr["isr_date"])) if isr else []
    loans = _loans(call, project_id)
    moves = _history(call, project_id)
    parts = {
        "plans": None if plans else "no_plans",
        "awards": "no_isr" if isr is None else (None if awards else "no_awards"),
        "ratings": None if ratings else "no_isr",
        "disbursement": None if loans else "no_loans",
        "closing": "closed" if project["status"] != signals.ACTIVE else (None if project["closing_date"] else "no_closing_date"),
    }

    total_signed = sum((Decimal(_value(row, "signed_amount_usd")) for row in awards if _value(row, "signed_amount_usd")), Decimal(0))
    raw = signals._rows(call, "loans.sql", project_id=project_id)
    disbursed, available, share = signals.disbursed_share(raw) if raw else (Decimal(0), Decimal(0), Decimal(0))

    def summed(key: str) -> Decimal:
        return sum((Decimal(str(row[key])) for row in raw if row[key] is not None), Decimal(0))

    closing = _date(project["closing_date"])
    totals = {
        "awards": {"count": len(awards), "signed_usd": str(total_signed.quantize(CENT)),
                   "signed_millions": signals.millions(total_signed), "isr_date": isr["isr_date"] if isr else None,
                   "isr_sequence": isr["sequence"] if isr else None},
        "plans": {"agencies": len(plans), "without_plan": len(unmatched)},
        "ratings": {"isrs": len({row["evidence_id"].split("/")[1] for row in ratings})},
        "disbursement": {"loans": len(raw), "commitment_millions": signals.millions(summed("original_principal_usd")),
                         "disbursed_millions": signals.millions(disbursed),
                         "undisbursed_millions": signals.millions(summed("undisbursed_usd")),
                         "canceled_millions": signals.millions(summed("cancelled_usd")),
                         "available_millions": signals.millions(available),
                         "disbursed_percent": int((share * 100).quantize(WHOLE, ROUND_HALF_UP)) if raw else None,
                         "as_of_date": _iso(max((row["as_of"] for row in raw), default=None))},
        "closing": {"closing_date": project["closing_date"], "days_to_close": project["days_to_close"],
                    "months_to_close": signals.whole_months(call.as_of, closing) if closing and closing >= call.as_of else None,
                    "moves": len(moves), "after_closing": len(after)},
    }
    rows = plans + awards + ratings + loans + moves + after
    left_out = [{"reason": reason, "count": 1, "parts": [part]} for part, reason in parts.items() if reason]
    return {
        "rows": rows,
        "coverage": {"matched": len(PARTS), "used": sum(1 for reason in parts.values() if reason is None),
                     "not_used": left_out},
        "abstention": None,
        "project": project,
        "isr": isr,
        "parts": {part: {"state": "none" if reason else "ok", "reason": reason} for part, reason in parts.items()},
        "unmatched_agencies": unmatched,
        "totals": totals,
    }
