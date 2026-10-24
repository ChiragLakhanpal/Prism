"""A project's Summary (ticket 21; the 21 brief, section 3): what the project is and where it stands,
from precomputed records, before any model call. No model writes it.

One read gives every value the Summary shows, each with its source, and the source itself as the
evidence drawer shows it, so a citation marker opens at once:

- dates: the approval date and the closing date from the projects API's record, and the original
  closing date from the monthly loan history (gold.project_closing_date) when it differs;
- the closing date history: each month the history first showed a new closing date, and how many
  times the date moved, a count the route makes (CLAUDE.md rule 1);
- money: the commitment, disbursed and canceled amounts summed over the project's loans and credits
  (gold.loan), in US$ millions to one decimal, each a column the route works out;
- ratings: the latest ISR's ratings as its own overall ratings table prints them (silver.isr_ratings,
  cited to that table's passage), the projects API's latest Procurement rating, IEG's outcome and
  World Bank performance ratings (gold.ieg_rating), and the Environmental Assessment Category;
- who: the region, the project's one sector in Strata's taxonomy with the projects API's sectors and
  their shares, and the implementing agencies.

Each read uses only what was public on or before the as-of date (ADR 0002). The projects API changes a
record in place, so its values count as public from the day it was last updated (check_plan's
record_is_current); before then the closing date comes from the loan history, and the rest is left out.

RECORD_READERS gives the evidence drawer each kind of record a Summary cites, by the table its
evidence id names (src/strata/server/evidence.py), so a link to a cited record opens it too.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Callable
from decimal import ROUND_HALF_UP, Decimal
from functools import cache
from pathlib import Path

from strata.lakehouse.engine import Engine
from strata.server.projects import display_name
from strata.tools.check_plan import implementing_agencies, record_date, record_is_current

SQL = Path(__file__).resolve().parent / "sql" / "summary"
MILLION, TENTH = Decimal(1_000_000), Decimal("0.1")
ISR_RATINGS = {"Progress towards achievement of PDO": "pdo", "Overall Implementation Progress (IP)": "implementation"}
PROCUREMENT = "27"  # the projects API's code for the Procurement rating
ICR_REVIEW = "ICRR"  # IEG's evaluation type for an ICR Review
LEADS = {"Pipeline": "pipeline", "Dropped": "dropped"}
SECTOR_YEAR = re.compile(r"^FY\d{2} - ")  # the projects API's taxonomy year before each sector's name

PROJECT_RECORD, LOAN_RECORD, HISTORY_RECORD, IEG_RECORD, API_RATING_RECORD = (
    "strata.gold.project", "strata.gold.loan", "strata.gold.project_closing_date", "strata.gold.ieg_rating",
    "strata.gold.project_isr_rating")


@cache
def _query(name: str) -> str:
    return (SQL / f"{name}.sql").read_text()


def _rows(engine: Engine, name: str, **params) -> list[dict]:
    result = engine.run(_query(name), params)
    return [dict(zip(result.columns, row)) for row in result.rows]


def _day(value) -> dt.date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _iso(value) -> str | None:
    day = _day(value)
    return day.isoformat() if day else None


def _money(value) -> Decimal | None:
    return None if value is None or value == "" else Decimal(str(value))


def millions(usd: Decimal | None) -> str | None:
    """US dollars as the Summary writes them, in millions to one decimal: 121630912.89 is 121.6."""
    return None if usd is None else f"{(usd / MILLION).quantize(TENTH, ROUND_HALF_UP):,}"


def _cents(usd: Decimal | None) -> str | None:
    return None if usd is None else str(usd.quantize(Decimal("0.01")))


def _share(percent) -> str:
    value = Decimal(str(percent)).normalize()
    return f"{value:f}%"


# ── The records a Summary cites, as the evidence drawer shows them ─────────

def _record(evidence_id: str, public_from, source_key: str, project_id: str, date, reference: str,
            fields: list[tuple[str, object, str]]) -> dict:
    """A record's evidence event: its fields by key, with the kind each is written as, and its source."""
    return {
        "id": evidence_id, "kind": "record", "tool": None, "stratum": "What", "short_name": None,
        "row": {"evidence_id": evidence_id, "public_from": _iso(public_from), "reference": reference,
                "source": {"source_key": source_key, "project_id": project_id, "document_date": _iso(date)},
                "fields": [{"key": key, "value": value, "kind": kind} for key, value, kind in fields
                           if value is not None and value != ""]},
        "highlights": [],
    }


def _project_record(row: dict, as_of: dt.date) -> dict:
    current = record_is_current(row, as_of)
    pid = row["project_id"]
    values = [("project_name", row["project_name"], "text"), ("country", row["country"], "text")]
    if current:
        values += [("status", row["status"], "text"), ("approval_date", _iso(row["approval_date"]), "date"),
                   ("closing_date", _iso(row["closing_date"]), "date"), ("region", row["region"], "text"),
                   ("implementing_agency", row["implementing_agency"], "text")]
    when = record_date(row) if current else _day(row["public_from"])
    return _record(f"{PROJECT_RECORD}:{pid}", when, "projects_api", pid, when, pid, values)


def _loan_record(project_id: str, row: dict) -> dict:
    return _record(f"{LOAN_RECORD}:{project_id}/{row['loan_number']}", row["public_from"], "loans", project_id, row["as_of"],
                   row["loan_number"],
                   [("original_principal_usd", _cents(_money(row["original_principal_usd"])), "usd"),
                    ("disbursed_usd", _cents(_money(row["disbursed_usd"])), "usd"),
                    ("cancelled_usd", _cents(_money(row["cancelled_usd"])), "usd"),
                    ("snapshot", _iso(row["as_of"]), "date")])


def _history_record(project_id: str, row: dict) -> dict:
    reported = _iso(row["reported_on"])
    return _record(f"{HISTORY_RECORD}:{project_id}/{reported}", row["public_from"], "loan_history", project_id, reported,
                   project_id, [("closing_date", _iso(row["closing_date"]), "date"),
                                ("previous_closing_date", _iso(row["previous_closing_date"]), "date"),
                                ("reported_on", reported, "date")])


def _ieg_record(project_id: str, row: dict) -> dict:
    key = f"{project_id}/{row['evaluation_type']}/{row['evaluation_fy']}"
    return _record(f"{IEG_RECORD}:{key}", row["public_from"], "ieg_ratings", project_id, row["public_from"], project_id,
                   [("evaluation_type", row["evaluation_type"], "text"),
                    ("evaluation_fy", str(row["evaluation_fy"]), "text"),
                    ("outcome", row["outcome"], "text"), ("bank_performance", row["bank_performance"], "text")])


def _api_rating_record(project_id: str, row: dict) -> dict:
    return _record(f"{API_RATING_RECORD}:{project_id}/{row['rating_code']}", row["public_from"], "projects_api_ratings",
                   project_id, row["isr_date"], project_id,
                   [("rating_name", row["rating_name"], "text"), ("value", row["value"], "text"),
                    ("isr_date", _iso(row["isr_date"]), "date")])


def _read(build: Callable[[str, dict], dict], query: str, pick: Callable[[dict, list[str]], bool]):
    """A reader for the evidence drawer: the record a key names, as of the date, or None."""
    def reader(engine: Engine, key: str, as_of: dt.date) -> dict | None:
        parts = key.split("/")
        found = [row for row in _rows(engine, query, project_id=parts[0], as_of=as_of) if pick(row, parts)]
        return None if not found else {"kind": "record", "row": build(parts[0], found[0])["row"]}
    return reader


def _project_reader(engine: Engine, key: str, as_of: dt.date) -> dict | None:
    found = _rows(engine, "project", project_id=key, as_of=as_of)
    return None if not found else {"kind": "record", "row": _project_record(found[0], as_of)["row"]}


RECORD_READERS = {
    PROJECT_RECORD: _project_reader,
    LOAN_RECORD: _read(_loan_record, "loans", lambda row, parts: len(parts) == 2 and row["loan_number"] == parts[1]),
    HISTORY_RECORD: _read(_history_record, "history", lambda row, parts: len(parts) == 2 and _iso(row["reported_on"]) == parts[1]),
    IEG_RECORD: _read(_ieg_record, "ieg", lambda row, parts: len(parts) == 3 and (row["evaluation_type"], str(row["evaluation_fy"]))
               == (parts[1], parts[2])),
    API_RATING_RECORD: _read(_api_rating_record, "api_ratings", lambda row, parts: len(parts) == 2 and row["rating_code"] == parts[1]),
}


# ── The Summary ──────────────────────────────────────────────────────────

class _Sources:
    """The sources the facts cite, each once, in the order the page reads them."""

    def __init__(self):
        self.events: dict[str, dict] = {}

    def cite(self, event: dict | None, **line) -> dict:
        if event is None:
            return {"evidence_id": None, **line}
        self.events.setdefault(event["id"], event)
        return {"evidence_id": event["id"], **line}


def _fact(key: str, value, source: dict, **more) -> dict:
    return {"key": key, "value": value, **more, "source": source}


def summary(engine: Engine, project_id: str, as_of: dt.date) -> dict | None:
    """The project's Summary as of the date, or None when there is no such project then."""
    from strata.server import evidence as evidence_routes  # the drawer's reader for a passage; it reads these records

    found = _rows(engine, "project", project_id=project_id, as_of=as_of)
    if not found:
        return None
    record = found[0]
    current = record_is_current(record, as_of)
    loans = _rows(engine, "loans", project_id=project_id, as_of=as_of)
    history = _rows(engine, "history", project_id=project_id, as_of=as_of)
    isr = _rows(engine, "isr_ratings", project_id=project_id, as_of=as_of)
    api_ratings = _rows(engine, "api_ratings", project_id=project_id, as_of=as_of)
    ieg = _rows(engine, "ieg", project_id=project_id, as_of=as_of)
    sectors = _rows(engine, "sectors", project_id=project_id, as_of=as_of)
    environment = _rows(engine, "environment", project_id=project_id, as_of=as_of)

    sources = _Sources()
    project_event = _project_record(record, as_of)
    when = project_event["row"]["source"]["document_date"]
    record_source = sources.cite(project_event, kind="projects_api", date=when)

    # Dates, and the closing date history.
    closing = _day(record["closing_date"]) if current else (_day(history[-1]["closing_date"]) if history else None)
    dates = [_fact("approval_date", _iso(record["approval_date"]) if current else None, record_source)]
    history_rows = []
    for row in history[1:]:
        event = _history_record(project_id, row)
        history_rows.append({"first_recorded": _iso(row["reported_on"]), "before": _iso(row["previous_closing_date"]),
                             "after": _iso(row["closing_date"]),
                             "source": sources.cite(event, kind="loan_history", date=_iso(row["reported_on"]))})
    if history and _day(history[0]["closing_date"]) != closing:
        first = history[0]
        dates.append(_fact("original_closing_date", _iso(first["closing_date"]), sources.cite(
            _history_record(project_id, first), kind="loan_history", date=_iso(first["reported_on"]))))
    closing_source = record_source if current else (history_rows[-1]["source"] if history_rows else (
        sources.cite(_history_record(project_id, history[0]), kind="loan_history", date=_iso(history[0]["reported_on"]))
        if history else record_source))
    dates.append(_fact("closing_date", _iso(closing), closing_source))

    # Money, summed over the loans and credits.
    money = []
    if loans:
        events = [_loan_record(project_id, row) for row in loans]
        snapshot = max(_day(row["as_of"]) for row in loans)
        for key, column in (("commitment", "original_principal_usd"), ("disbursed", "disbursed_usd"),
                            ("canceled", "cancelled_usd")):
            each = [{"loan_number": row["loan_number"], "value": millions(_money(row[column]) or Decimal(0))}
                    for row in loans]
            total = sum((_money(row[column]) or Decimal(0) for row in loans), Decimal(0))
            first_source = sources.cite(events[0], kind="loans", date=_iso(snapshot), loans=len(loans))
            for event in events[1:]:
                sources.cite(event, kind="loans", date=_iso(snapshot))
            money.append(_fact(key, millions(total), first_source, loans=each,
                               loan_ids=[event["id"] for event in events]))
        disbursed_as_of = _iso(snapshot)
    else:
        disbursed_as_of = None
        if current and record["total_commitment_usd"] is not None:
            money.append(_fact("commitment", millions(_money(record["total_commitment_usd"])), record_source))

    # Ratings, in the order they were written: the ISR, then IEG, then the risk category.
    ratings = []
    latest_isr = [row for row in isr if row["document_id"] == isr[0]["document_id"]] if isr else []
    for row in latest_isr:
        key = ISR_RATINGS.get(row["rating_name"])
        if not key:
            continue
        event = (evidence_routes.read(engine, f"strata.gold.passage:{row['passage_id']}", as_of)
                 if row["passage_id"] else None)
        ratings.append(_fact(key, row["current_rating"], sources.cite(
            event, kind="isr", date=_iso(row["isr_date"]), sequence=row["sequence"])))
    ratings.sort(key=lambda fact: list(ISR_RATINGS.values()).index(fact["key"]))
    for row in api_ratings:
        if row["rating_code"] == PROCUREMENT:
            ratings.append(_fact("procurement", row["value"], sources.cite(
                _api_rating_record(project_id, row), kind="projects_api_ratings", date=_iso(row["isr_date"]))))
    review = next((row for row in ieg if row["evaluation_type"] == ICR_REVIEW), None)
    if review:
        source = sources.cite(_ieg_record(project_id, review), kind="ieg_ratings", date=_iso(review["public_from"]),
                              fiscal_year=review["evaluation_fy"])
        ratings += [_fact("ieg_outcome", review["outcome"], source),
                    _fact("ieg_bank_performance", review["bank_performance"], source)]
    if environment and current:
        ratings.append(_fact("ea_category", environment[0]["ea_category"], record_source))

    # Region, sectors and implementing agencies.
    who = [_fact("region", record["region"] if current else None, record_source),
           _fact("sectors", record["sector_name"] if current else None, record_source,
                 values=[f"{SECTOR_YEAR.sub('', row['sector_name'] or row['sector_code'])}: {_share(row['share_percent'])}"
                         for row in sectors if row["share_percent"] is not None] if current else []),
           _fact("agencies", None, record_source,
                 values=implementing_agencies(record["implementing_agency"]) if current else [])]

    status = record["status"] if current else None
    totals = {fact["key"]: fact["value"] for fact in money}
    return {
        "as_of": as_of.isoformat(),
        "project": {"project_id": project_id, "project_name": record["project_name"],
                    "display_name": display_name(record["project_name"]), "status": status},
        "lead": {"kind": LEADS.get(status) or ("closed" if closing and closing <= as_of else "active"),
                 "closing_date": _iso(closing), "moves": len(history_rows) if history else None,
                 "commitment": totals.get("commitment"), "disbursed": totals.get("disbursed"),
                 "canceled": totals.get("canceled"), "disbursed_as_of": disbursed_as_of},
        "dates": dates,
        "history": {"known": bool(history), "rows": history_rows},
        "money": money,
        "ratings": ratings,
        "who": who,
        "sources": list(sources.events.values()),
    }
