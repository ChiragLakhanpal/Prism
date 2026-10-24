"""The quarterly cross-check: a sample of each region's lesson decisions goes to reviewers in another region
(ticket 29; docs/PLAN.md section 11, "a quarterly 10% cross-check by another region"; spec story 94).

A run, on the first days of a quarter, looks back at the quarter before it:

1. It finds every decision a lead made in that quarter on a new lesson or a re-check
   (strata.ops.lesson_review_acts), grouped by the region that decided.
2. From each region it draws config/thresholds.toml's lesson_review.cross_check_share of those decisions,
   rounded up, so a region with any decision gets at least one. The draw is a fixed shuffle keyed by the
   quarter and each item's id, so running the job twice draws the same decisions and writes nothing new.
3. It assigns each drawn decision to another region whose lesson reviewers may cross-check (the roles
   file), taking the region with the fewest assignments so far, then the first by name, so no region's
   reviewers check their own region's decisions.
4. It writes one cross-check item per drawn decision to strata.ops.lesson_review_items, due
   lesson_review.cross_check_business_days business days after the run, for the assigned region.

Every row is new; nothing changes or leaves. On Databricks, bundle/lessons.yml runs cross_check_task.py
each quarter; on this computer, tests call run() on a copy of the fixture database.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import logging
import math
from collections.abc import Callable

from strata.config import Roles, Thresholds, load_roles, load_thresholds
from strata.knowledge.lessons.propose import item_id
from strata.knowledge.lessons.review import ITEM_COLUMNS, Store, _date, _int, nth_business_day
from strata.lakehouse.engine import Engine

log = logging.getLogger("strata.lessons")


def quarter_before(day: dt.date) -> tuple[dt.date, dt.date]:
    """The first and last days of the calendar quarter before the one that holds day."""
    first_of_this = dt.date(day.year, 3 * ((day.month - 1) // 3) + 1, 1)
    last = first_of_this - dt.timedelta(days=1)
    return dt.date(last.year, 3 * ((last.month - 1) // 3) + 1, 1), last


def _order(quarter: dt.date, key: str) -> str:
    return hashlib.sha256(f"{quarter.isoformat()}|{key}".encode()).hexdigest()


def checking_regions(roles: Roles) -> list[str]:
    """Every region with at least one person who may cross-check, by name."""
    return sorted({region for person in roles.people if "cross_check" in person.acts(roles) for region in person.regions})


def run(engine: Engine, today: dt.date, now: Callable[[], dt.datetime] | None = None, roles: Roles | None = None,
        thresholds: Thresholds | None = None) -> int:
    """One quarterly run. Returns the cross-check items it wrote."""
    roles, thresholds = roles or load_roles(), thresholds or load_thresholds()
    now = now or (lambda: dt.datetime.combine(today, dt.time(), tzinfo=dt.UTC))
    share = float(thresholds.value("lesson_review.cross_check_share"))
    holidays = frozenset(thresholds.value("lesson_review.holidays"))
    due = nth_business_day(today, int(thresholds.value("lesson_review.cross_check_business_days")), holidays)
    start, end = quarter_before(today)
    store = Store(engine)

    decided: dict[str, list[dict]] = {}
    for item in store.items.values():
        decision = store.act(item, "decide")
        if item["kind"] == "cross_check" or decision is None or not start <= _date(decision["acted_at"]) <= end:
            continue
        decided.setdefault(item["region"], []).append(item)
    checked = {item["decided_item_id"] for item in store.items.values() if item["kind"] == "cross_check"}
    regions = checking_regions(roles)
    assigned = dict.fromkeys(regions, 0)

    rows = []
    for region in sorted(decided):
        items = sorted(decided[region], key=lambda item: _order(start, item["item_id"]))
        drawn = items[:math.ceil(share * len(items))]
        others = [other for other in regions if other != region]
        if not others:
            log.warning("I drew %s decisions from %s to cross-check, but no other region has a reviewer who may "
                        "cross-check them.", len(drawn), region)
            continue
        for item in drawn:
            if item["item_id"] in checked:
                continue
            target = min(others, key=lambda other: (assigned[other], other))
            assigned[target] += 1
            lesson_id = store.lesson_of(item) or (store.act(item, "decide") or {}).get("repeat_of")
            latest = store.latest(lesson_id) if lesson_id else None
            row = {"item_id": item_id("cross", f"{item['item_id']}|{start.isoformat()}"), "kind": "cross_check",
                   "proposal_id": item["proposal_id"], "lesson_id": lesson_id,
                   "version": _int(latest["version"]) if latest else _int(item["version"]),
                   "decided_item_id": item["item_id"], "project_id": item["project_id"], "region": target,
                   "decided_region": region, "origin": "quarterly", "origin_by": None, "origin_by_name": None,
                   "origin_reason": None, "origin_item_id": None, "entered_on": today, "due_on": due,
                   "created_at": now(), "public_from": today}
            rows.append(tuple(row[column] for column in ITEM_COLUMNS))
    return engine.insert_rows("strata.ops.lesson_review_items", ITEM_COLUMNS, rows) if rows else 0


def main(argv: list[str], engine: Engine) -> int:
    """The quarterly job's task on Databricks: today's run, in UTC."""
    written = run(engine, dt.datetime.now(dt.UTC).date())
    log.warning("I wrote %s cross-check items.", written)
    return 0
