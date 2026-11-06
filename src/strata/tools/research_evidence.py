"""research_evidence (ticket 148): what Prism's latest deep research run read about one project, for the research
brief's writer and verifier, and for the agent.

Each row is one item a run kept (ticket 147's one item shape), read back from strata.ops.research_items. The summary
record holds the counts a sentence may state (CLAUDE.md rule 1): the items by kind, the project's closing date, the
contract awards in the config/thresholds.toml research.late_award_days before it and those by direct selection, the
last award's date and the days from it to closing, and each source reached or not with its note. The award counts
come from the notices in strata.gold.notice, the records the notice reader turns into items, so they never depend on
how an item's title is written.

A project with no run public by the call's date gets the abstention not_fetched: the brief is written only from a
run, and the agent says no run was made rather than guess.
"""

from __future__ import annotations

import datetime as dt
import json

from strata.tools import common
from strata.tools import project_signals as signals
from strata.tools.registry import Call

FOLDER = "research_evidence"
TABLE = "strata.research.item"  # the table an item's evidence id names before its colon (ticket 147)
DIRECT = "Direct Selection"
SUMMARY = ("items_total", "counts_by_kind", "closing_date", "late_award_days", "awards_in_window",
           "direct_awards_in_window", "last_award_date", "days_from_last_award_to_closing", "sources_reached",
           "sources_not_reached")


def _json(value, empty=None):
    if value is None or value == "":
        return empty
    return json.loads(value) if isinstance(value, str) else value


def _flag(value) -> bool:
    return value if isinstance(value, bool) else str(value).lower() == "true"


def item_of(row: dict) -> dict:
    """One strata.ops.research_items row as the one item shape (ticket 147): its JSON columns read, its dates as ISO."""
    return {"evidence_id": row["evidence_id"], "public_from": common.iso(row["public_from"]),
            "source": _json(row["source"], {}), "kind": row["kind"], "title": row["title"], "text": row["text"],
            "url": row["url"], "published": common.iso(row["published"]), "date_known": _flag(row["date_known"]),
            "observed": common.iso(row["observed"]), "location": _json(row["location"]),
            "image_urls": _json(row["image_urls"], []), "author": row["author"], "read_on": common.iso(row["read_on"])}


def _sources(run: dict) -> tuple[list[dict], list[dict]]:
    """The sources the run reached, each with how many items it gave and its note, and those it did not reach, each
    with the note that says why, in the order the run asked them. Each has its label and kind from the registry
    (config/research.toml), unless the run's notes name its label."""
    from strata.config import load_research

    asked, reached = _json(run["sources_asked"], []), set(_json(run["reached"], []))
    notes, registry = _json(run["source_notes"], {}), load_research()
    found, missed = [], []
    for key in asked:
        note, source = notes.get(key) or {}, registry.get(key)
        entry = {"key": key, "label": note.get("label") or (source.label if source else key),
                 "kind": source.kind if source else None, "note": note.get("note")}
        if key in reached:
            found.append({**entry, "items": note.get("items")})
        else:
            missed.append(entry)
    return found, missed


def _awards(call: Call, project_id: str, closing: dt.date | None) -> dict:
    """The contract awards in the late_award_days before closing, those by direct selection, and the last one."""
    days = int(call.thresholds.value("research.late_award_days"))
    if closing is None:
        return {"late_award_days": days, "awards_in_window": None, "direct_awards_in_window": None,
                "last_award_date": None, "days_from_last_award_to_closing": None}
    start = closing - dt.timedelta(days=days)
    notices = [row for row in common.rows(call, FOLDER, "awards", project_id=project_id)
               if start <= signals._date(row["notice_date"]) <= closing]
    last = max((signals._date(row["notice_date"]) for row in notices), default=None)
    return {"late_award_days": days, "awards_in_window": len(notices),
            "direct_awards_in_window": sum(row["procurement_method"] == DIRECT for row in notices),
            "last_award_date": common.iso(last), "days_from_last_award_to_closing": (closing - last).days if last else None}


def research_evidence(call: Call, project_id: str) -> dict:
    """The latest run's items for the project as rows, and its counts as the summary, as of call.as_of."""
    found = common.rows(call, FOLDER, "latest_run", project_id=project_id)
    if not found:
        return {"rows": [], "coverage": {"matched": 0, "used": 0, "not_used": []}, "run": None,
                **dict.fromkeys(SUMMARY), "abstention": {"reason": "not_fetched", "project_id": project_id}}
    run = found[0]
    every = common.rows(call, FOLDER, "run_items", run_id=run["run_id"])
    rows = [item_of(row) for row in every if common.flag(row["public_by_as_of"])]
    reached, not_reached = _sources(run)
    project = signals._project(call, project_id, signals._rows(call, "history.sql", project_id=project_id))
    closing = signals._date(project["closing_date"]) if project else None
    counts: dict[str, int] = {}
    for item in rows:
        counts[item["kind"]] = counts.get(item["kind"], 0) + 1
    left_out = []
    if not_reached:
        left_out.append({"reason": "not_reached", "count": len(not_reached),
                         "sources": [source["key"] for source in not_reached]})
    if len(rows) < len(every):
        left_out.append({"reason": "after_as_of", "count": len(every) - len(rows)})
    return {"rows": rows, "coverage": {"matched": len(every), "used": len(rows), "not_used": left_out},
            "run": {"run_id": run["run_id"], "as_of": common.iso(run["as_of"]), "note": run["note"],
                    "finished": run["finished"].isoformat() if isinstance(run["finished"], dt.datetime)
                    else run["finished"]},
            "items_total": len(rows), "counts_by_kind": dict(sorted(counts.items())),
            "closing_date": common.iso(closing), **_awards(call, project_id, closing),
            "sources_reached": reached, "sources_not_reached": not_reached, "abstention": None}


def read_item(engine, key: str, as_of: dt.date) -> dict | None:
    """One item by the key after its evidence id's colon, as the latest finished run kept it, for the evidence drawer
    (src/strata/server/evidence.py): a record, whose url the drawer's "Open the source" link opens."""
    result = engine.run(common.sql(FOLDER, "item"), {"evidence_id": f"{TABLE}:{key}", "as_of": as_of})
    if not result.rows:
        return None
    return {"kind": "record", "row": item_of(dict(zip(result.columns, result.rows[0], strict=True)))}
