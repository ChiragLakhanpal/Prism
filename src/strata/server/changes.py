"""What changed between a Procurement Plan version and the agency's version before it (the 21 brief,
section 5.4), which the Check a plan page lists and the Procurement tab sums up in one sentence.

The two versions' STEP rows are matched on their Activity Reference No. (an activity whose reference
changed shows as dropped and added), and each activity can change in four ways, in this order:

- added: listed in this version and not in the one before;
- dropped: listed in the one before and not in this version;
- re-dated: a step's planned date in the version before moved, or this version gives the step no date
  ("No date" on screen). A date this version gives for the first time is not a re-dating;
- re-estimated: both versions give an Estimated Amount and the two differ. An estimate this version
  gives for the first time is not a re-estimate.

So a version with none of these may still fill in dates or estimates the version before left blank, and the
screens say it lists the same activities with no planned date moved and no estimate changed, never that its dates
and estimates are the same (ticket 21's verify, finding 4).

The version before is silver.plan_versions' previous_document_id: the agency's version just before it
among the versions Strata holds. When the layout parser did not read that version's tables, there is
nothing to compare, and the answer says so (previous_not_read), as it does for the agency's earliest
version (earliest). The route counts each kind and works out each moved date and changed amount here,
so the screen never counts or subtracts (CLAUDE.md rule 1). Each read uses only what was public on or
before the as-of date (ADR 0002).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from functools import cache
from pathlib import Path

from strata.lakehouse.engine import Engine
from strata.tools.check_plan import agency_id

SQL = Path(__file__).resolve().parent / "sql" / "changes"
KINDS = ("added", "dropped", "redated", "reestimated")
CENTS = Decimal("0.01")


@cache
def _query(name: str) -> str:
    return (SQL / f"{name}.sql").read_text()


def _rows(engine: Engine, name: str, **params) -> list[dict]:
    result = engine.run(_query(name), params)
    return [dict(zip(result.columns, row)) for row in result.rows]


def _day(value) -> dt.date | None:
    if value is None or value == "":
        return None
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _money(value) -> Decimal | None:
    return None if value is None or value == "" else Decimal(str(value)).quantize(CENTS)


def _text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _iso(value: dt.date | None) -> str | None:
    return value.isoformat() if value else None


def versions(engine: Engine, project_id: str) -> list[dict]:
    """Every version of the project's plans, oldest first, typed once."""
    return [{**row, "plan_date": _day(row["plan_date"]), "disclosed_on": _day(row["disclosed_on"]),
             "public_from": _day(row["public_from"]), "activities": int(row["activities"] or 0)}
            for row in _rows(engine, "versions", project_id=project_id)]


def _version(row: dict) -> dict:
    return {"document_id": row["document_id"], "plan_date": _iso(row["plan_date"]),
            "implementing_agency": row["implementing_agency"], "agency_id": agency_id(row["implementing_agency"])}


def _activity(row: dict) -> dict:
    return {"activity_reference_no": row["activity_reference_no"], "description": row["description"],
            "method": row["method"], "market_approach": row["market_approach"],
            "estimated_amount_usd": _text(_money(row["estimated_amount_usd"])), "process_status": row["process_status"]}


def _by_reference(rows: list[dict], document_id: str) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for row in rows:
        if row["document_id"] == document_id:
            found.setdefault(row["activity_reference_no"], row)  # a reference listed twice keeps its first row
    return found


def _steps(rows: list[dict], document_id: str) -> dict[str, dict[str, tuple[int, dt.date | None]]]:
    found: dict[str, dict[str, tuple[int, dt.date | None]]] = {}
    for row in rows:
        if row["document_id"] == document_id:
            found.setdefault(row["activity_reference_no"], {}).setdefault(
                row["step"], (int(row["step_order"]), _day(row["planned_on"])))
    return found


def _redated(was: dict[str, tuple[int, dt.date | None]], now: dict[str, tuple[int, dt.date | None]]) -> list[dict]:
    moved = []
    for step, (order, before) in sorted(was.items(), key=lambda item: item[1][0]):
        after = now.get(step, (order, None))[1]
        if before is None or after == before:
            continue
        days = (after - before).days if after else None
        moved.append({"step": step, "was": _iso(before), "now": _iso(after), "days": abs(days) if days else days,
                      "direction": None if days is None else "later" if days > 0 else "earlier"})
    return moved


def compare(engine: Engine, all_versions: list[dict], version: dict, as_of: dt.date, detail: bool = True) -> dict:
    """What changed in this version since the agency's version before it. With detail=False, only the
    counts, as the Procurement tab's sentence needs."""
    by_id = {row["document_id"]: row for row in all_versions}
    before = by_id.get(version["previous_document_id"] or "")
    answer = {"plan": _version(version), "previous": None, "counts": None, **{kind: [] for kind in KINDS}}
    if before is None or before["public_from"] > as_of:
        return {"state": "earliest", **answer}
    answer["previous"] = _version(before)
    if not before["activities"]:
        return {"state": "previous_not_read", **answer}

    rows = _rows(engine, "rows", now=version["document_id"], was=before["document_id"])
    steps = _rows(engine, "steps", now=version["document_id"], was=before["document_id"])
    now_rows, was_rows = _by_reference(rows, version["document_id"]), _by_reference(rows, before["document_id"])
    now_steps, was_steps = _steps(steps, version["document_id"]), _steps(steps, before["document_id"])
    found = {kind: [] for kind in KINDS}
    found["added"] = [_activity(row) for ref, row in now_rows.items() if ref not in was_rows]
    found["dropped"] = [_activity(row) for ref, row in was_rows.items() if ref not in now_rows]
    for ref, row in now_rows.items():
        if ref not in was_rows:
            continue
        moved = _redated(was_steps.get(ref, {}), now_steps.get(ref, {}))
        if moved:
            found["redated"].append({"activity_reference_no": ref, "description": row["description"], "steps": moved})
        was_amount, now_amount = _money(was_rows[ref]["estimated_amount_usd"]), _money(row["estimated_amount_usd"])
        if was_amount is not None and now_amount is not None and was_amount != now_amount:
            change = now_amount - was_amount
            found["reestimated"].append({"activity_reference_no": ref, "description": row["description"],
                                         "was": _text(was_amount), "now": _text(now_amount),
                                         "change": _text(abs(change)), "direction": "more" if change > 0 else "less"})
    counts = {kind: len(found[kind]) for kind in KINDS}
    return {"state": "compared", **answer, "counts": counts, **(found if detail else {})}


def plan_changes(engine: Engine, project_id: str, agency: str, plan_date: dt.date, as_of: dt.date) -> dict | None:
    """What changed in one agency's dated version, or None when it has no such version public by then."""
    all_versions = versions(engine, project_id)
    mine = [row for row in all_versions if row["implementing_agency"] and agency_id(row["implementing_agency"]) == agency
            and row["plan_date"] == plan_date and row["public_from"] <= as_of]
    if not mine:
        return None
    return {"as_of": as_of.isoformat(), **compare(engine, all_versions, mine[-1], as_of)}
