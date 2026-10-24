"""get_disagreements: where two sources disagree about a subject, and which one Strata leans on.

The registry (config/tools.toml) defines the tool's parameters and result shape; this module is its
adapter. It reads what the nightly job's detect_disagreements task wrote (src/strata/knowledge/assertions.py):
strata.gold.disagreement, strata.gold.assertion and strata.ops.assertion_rejections, as the viewer, each only
where it was public on the as-of date (ADR 0002). Its SQL is in src/strata/tools/sql/get_disagreements/.

A subject is a project, with its packages, or one package by its STEP reference. For it the tool returns:

- one row per disagreement, with both sides in the order they were written. A side keeps its source's own
  field name and value word for word, its quote and page when it was read from a report, its date, its
  evidence tier and the evidence id a claim cites. The row names the side Strata leans on and the id of the
  ladder's rule that decided (config/evidence_ladder.toml; brief 23 keys each rule's sentence by it), and
  under if_you_keep the value you would treat as true if you kept the other side. The screens and the
  agent write the rule's sentence and the what-changes line from these values, never a model. When the two
  sides describe a named moment, such as the mid-term review, each side gives how many whole months after
  it the side was made.
- trajectories: for each series of ratings of successive periods, such as one ISR after another, its
  ratings in order and its runs of equal ratings. A trajectory is never a disagreement.
- rejected: how many assertions read from the project's reports the run left out, by reason, such as a
  quote that was not word for word on its cited page.

A report re-issued under the same number replaces its earlier version from the day the re-issue became
public: a disagreement with a replaced side is left out of current answers, and the coverage line counts it.

The call's view (staff, piu or public) is returned with the result but not yet applied: until ticket 40
applies each view's rules, every view gets the World Bank staff result.
"""

from __future__ import annotations

import datetime as dt
from importlib import resources

from strata.config import load_ladder
from strata.knowledge.assertions import (CONTRACT_SIGNING, PASSAGES, REPORT_PERIOD, WHOLE_PROJECT, Assertion, from_row,
                                        overlap, typed)
from strata.tools.registry import Call

TABLE = "strata.gold.disagreement"
NOT_A_MOMENT = (REPORT_PERIOD, WHOLE_PROJECT, CONTRACT_SIGNING)  # periods that name no single moment
PASSAGE_FIELDS = ("paragraph", "paragraph_numbered", "printed_page", "doc_key")


def _sql(name: str) -> str:
    return (resources.files("strata.tools") / "sql" / "get_disagreements" / name).read_text()


def _rows(call: Call, name: str, **params) -> list[dict]:
    result = call.engine.run(_sql(name), params)
    return [dict(zip(result.columns, row)) for row in result.rows]


def _iso(value) -> str | None:
    return None if value is None else value.isoformat()


def _current(assertion: Assertion, as_of: dt.date) -> bool:
    return assertion.replaced_on is None or assertion.replaced_on > as_of


def months_between(start: dt.date, end: dt.date) -> int:
    """Whole months from start to end."""
    return (end.year - start.year) * 12 + end.month - start.month - (1 if end.day < start.day else 0)


def _boolean(value) -> bool | None:
    """A boolean from DuckDB or from the warehouse's text."""
    return None if value is None else value if isinstance(value, bool) else str(value).lower() == "true"


def _side(assertion: Assertion, moment: dt.date | None, passage: dict) -> dict:
    return {
        "assertion_id": assertion.assertion_id,
        "evidence_id": assertion.evidence_id,
        "evidence_tier": assertion.evidence_tier,
        "form": assertion.form,
        "source_key": assertion.source_key,
        "document_id": assertion.document_id,
        "document_type": assertion.document_type,
        "report_number": assertion.report_number,
        "version": assertion.version,
        "sequence": assertion.sequence,
        "passage_id": assertion.passage_id,
        "pdf_page": assertion.pdf_page,
        # For a side that rests on a passage: the paragraph as the report numbers it (or Strata's own count,
        # s4, when paragraph_numbered is false, as in an ISR), its printed page, and the document's key in
        # the source view's address (/projects/:pid/documents/:doc_key). Empty for a record.
        "paragraph": passage.get("paragraph"),
        "paragraph_numbered": _boolean(passage.get("paragraph_numbered")),
        "printed_page": passage.get("printed_page"),
        "doc_key": passage.get("doc_key"),
        "field_name": assertion.field_name,
        "value": assertion.value,
        "value_form": assertion.value_form,
        "judgment": assertion.judgment,
        "quote": assertion.quote,
        "period_start": _iso(assertion.period_start),
        "period_end": _iso(assertion.period_end),
        "made_at": _iso(assertion.made_at),
        "public_from": _iso(assertion.public_from),
        "months_after_event": months_between(moment, assertion.made_at)
        if moment is not None and assertion.made_at >= moment else None,
    }


def _row(found: dict, sides: tuple[Assertion, Assertion], passages: dict[str, dict]) -> dict:
    first, second = sides
    start, end = typed("period_start", found["period_start"]), typed("period_end", found["period_end"])
    moment = start if start == end and found["period_event"] not in NOT_A_MOMENT else None
    leaned = found["lean_assertion_id"]
    other = next((side for side in sides if side.assertion_id != leaned), None) if leaned else None
    return {
        "evidence_id": f"{TABLE}:{found['disagreement_id']}",
        "public_from": _iso(typed("public_from", found["public_from"])),
        "source": {"table": TABLE, "project_id": found["project_id"], "subject_id": found["subject_id"],
                   "evidence_ids": [first.evidence_id, second.evidence_id]},
        "disagreement_id": found["disagreement_id"],
        "subject_kind": found["subject_kind"],
        "subject_id": found["subject_id"],
        "project_id": found["project_id"],
        "attribute": found["attribute"],
        "attribute_kind": first.attribute_kind,
        "period": {"event": found["period_event"], "start": _iso(start), "end": _iso(end)},
        "sides": [_side(first, moment, passages[first.assertion_id]),
                  _side(second, moment, passages[second.assertion_id])],
        "lean_assertion_id": leaned,
        "other_assertion_id": other.assertion_id if other else None,
        "rule_id": found["rule_id"],
        "if_you_keep": None if other is None else {
            "assertion_id": other.assertion_id, "attribute": other.attribute, "value": other.value,
            "value_form": other.value_form, "judgment": other.judgment, "field_name": other.field_name,
            "period_event": found["period_event"]},
    }


def trajectories(held: list[Assertion]) -> list[dict]:
    """Each series of ratings of successive periods from one tier of source, such as the ISRs, with at least two
    ratings and no two of its periods overlapping, in date order, with its runs of equal ratings."""
    series: dict[tuple, list[Assertion]] = {}
    for assertion in held:
        if assertion.value_form == "rating":
            series.setdefault((assertion.subject_kind, assertion.subject_id, assertion.attribute,
                               assertion.evidence_tier), []).append(assertion)
    found = []
    for (kind, subject, attribute, tier), points in series.items():
        points.sort(key=lambda point: (point.period_end, point.made_at, point.assertion_id))
        if len(points) < 2 or any(overlap(a, b) for at, a in enumerate(points) for b in points[at + 1:]):
            continue
        runs: list[dict] = []
        for point in points:
            if runs and runs[-1]["value"] == point.value:
                runs[-1].update(last_sequence=point.sequence, last_made_at=_iso(point.made_at),
                                count=runs[-1]["count"] + 1)
            else:
                runs.append({"value": point.value, "first_sequence": point.sequence, "last_sequence": point.sequence,
                             "first_made_at": _iso(point.made_at), "last_made_at": _iso(point.made_at), "count": 1})
        found.append({
            "subject_kind": kind, "subject_id": subject, "attribute": attribute, "evidence_tier": tier,
            "field_name": points[-1].field_name,
            "points": [{"assertion_id": point.assertion_id, "evidence_id": point.evidence_id,
                        "document_id": point.document_id, "sequence": point.sequence, "value": point.value,
                        "period_start": _iso(point.period_start), "period_end": _iso(point.period_end),
                        "made_at": _iso(point.made_at)} for point in points],
            "runs": runs,
        })
    return found


def get_disagreements(call: Call, subject_id: str, attribute: str | None = None) -> dict:
    """The disagreements and trajectories about the subject, as of call.as_of."""
    subject_id = subject_id.strip()
    subject_id = subject_id.upper() if subject_id[:1].lower() == "p" and subject_id[1:].isdigit() else subject_id
    common = {"subject_id": subject_id, "package": "package"}
    empty = {"rows": [], "coverage": {"matched": 0, "used": 0, "not_used": []}, "trajectories": [],
             "rejected": {"count": 0, "reasons": []}}
    held = _rows(call, "subject.sql", project="project", **common)
    if not held:
        return {**empty, "subject": None, "abstention": {"reason": "unknown_subject", "subject_id": subject_id}}
    kind = "project" if any(row["subject_kind"] == "project" for row in held) else "package"
    project_id = held[0]["project_id"]
    subject = {"kind": kind, "id": subject_id, "project_id": project_id}
    if attribute is not None and attribute not in load_ladder().attributes:
        return {**empty, "subject": subject, "abstention": {"reason": "unknown_attribute", "attribute": attribute}}

    held = _rows(call, "assertions.sql", as_of=call.as_of, passages=f"{PASSAGES}:", **common)
    assertions = [from_row(row) for row in held]
    by_id = {assertion.assertion_id: assertion for assertion in assertions}
    passages = {row["assertion_id"]: {key: row[key] for key in PASSAGE_FIELDS} for row in held}
    current = [assertion for assertion in assertions if _current(assertion, call.as_of)
               and (attribute is None or assertion.attribute == attribute)]
    reasons = [{"reason": row["reason"], "count": int(row["rejected"])}
               for row in _rows(call, "rejections.sql", project_id=project_id, as_of=call.as_of)]
    rejected = {"count": sum(reason["count"] for reason in reasons), "reasons": reasons}

    found = [row for row in _rows(call, "disagreements.sql", as_of=call.as_of, **common)
             if attribute is None or row["attribute"] == attribute]
    replaced = [row for row in found if (day := typed("replaced_on", row["replaced_on"])) and day <= call.as_of]
    rows = [_row(row, (by_id[row["first_assertion_id"]], by_id[row["second_assertion_id"]]), passages)
            for row in found if row not in replaced]
    not_used = [{"reason": "replaced_by_later_version", "count": len(replaced),
                 "evidence_ids": [f"{TABLE}:{row['disagreement_id']}" for row in replaced]}] if replaced else []
    abstention = None if current or rows else {"reason": "no_assertions", "subject_id": subject_id}
    return {"rows": rows, "coverage": {"matched": len(found), "used": len(rows), "not_used": not_used},
            "abstention": abstention, "subject": subject, "trajectories": [] if abstention else trajectories(current),
            "rejected": rejected}
