"""A project's timeline (ticket 23; the 23 brief, sections 4 and 10): What, How and Why in three lanes on one time
axis, from precomputed tables, with no model call.

timeline() gives GET /api/projects/{pid}/timeline everything the Timeline tab draws, as of the page's date
(ADR 0002) and in the page's view:

- items, in the order the arrow keys and the table follow (date order across the lanes; ties go Why, How,
  What, with marks before bands; each disagreement right after its later side):
  - reports (circles): the PAD, the ICR, its reviews and a PPAR in the Why lane, from the documents Strata read
    (strata.silver.documents), each version on its own date; a version a later one replaced by the as-of date is
    marked replaced, and a re-issue says so. ISRs sit in the How lane, but only those isr_marks() picks.
  - events (diamonds) in the How lane: the mid-term review and the restructuring, each dated by the earliest
    public passage that states its date (EVENTS), which the event opens in the drawer.
  - records (squares) in the What lane: each package's earliest signed contract (sql/timeline/signings.sql,
    which reads the award notice when no awards dataset covers the year, as strata.gold.package does). Above
    timeline.what_lane_group_above contracts (config/thresholds.toml), a year with two or more becomes one group.
  - bands: the ISRs' runs of equal ratings of progress towards the PDO, from get_disagreements' trajectories.
  - disagreements: get_disagreements' rows whose two sides are both reports on the chart, each with its sides
    in the order they were written and the side Strata leans on.
- records_disagree: get_disagreements' rows about a package whose two sides are both records (a plan row, a
  contract record, an award notice), which no dashed line can join, listed under the chart (ticket 132).
- table: the same items with every contract on its own row, for "Show the table".
- ratings: the series the bands draw, with its first and last ratings and which way it moved.
- finding and alt: the chart's title and its alt text as segments, written from copy templates
  (timeline_copy.json, which web/lint/server-copy.ts writes from web/src/copy.ts) and the values above, with
  each count a number segment the page writes through Num. The page computes no number.

The public view of a project still under way shows no disagreement (spec, user story 55). Every number comes
from a tool or a table: months, counts and dates arrive from the payload.

READERS give the evidence drawer the four kinds of evidence id the timeline's marks open (doc:, ratings:,
contracts: and disagreement:), so each opens from a link on any page, and a package's signing record for a
contract mark (strata.gold.package:{step_reference}) when the package is no comparable the range chart reads.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from collections.abc import Callable
from functools import cache
from importlib import resources
from pathlib import Path

from strata.agent.verifier import sentence_of
from strata.config import KEY_DATE, ConfigError, TimelineSettings, load_ladder, load_project_page, load_thresholds
from strata.dbx import Viewer
from strata.knowledge.assertions import KEY_DATE_LABELS, PASSAGES, STATUS
from strata.lakehouse.engine import Engine
from strata.server.projects import display_name
from strata.server.viewer_sql import DAILY, data_through
from strata.server.viewer_sql import query as viewer_query
from strata.tools import registry
from strata.tools.check_plan import RECORD_WORDS
from strata.tools.get_disagreements import reads as disagreement_reads
from strata.tools.withheld import WITHHELD, withheld_in

SQL = Path(__file__).resolve().parent / "sql" / "timeline"
DOC, RATINGS, CONTRACTS, DISAGREEMENT = "doc", "ratings", "contracts", "disagreement"
LANES = ("why", "how", "what")
# The lane of each kind of report Strata reads, by its group in config/project_page.toml.
REPORT_LANES = {"pad": "why", "isr": "how", "icr": "why", "icr_review": "why", "ppar": "why"}
PAGE = load_project_page()
GROUPS = PAGE.document_groups
# The one attribute the bands draw (the 23 brief, section 4.3): the ISRs' rating of progress towards the PDO.
BANDED = "pdo_progress"
BANDED_TIER = "isr"


def events_of(settings: TimelineSettings) -> dict[str, list[tuple[str, re.Pattern, str]]]:
    """The events the How lane draws (config/project_page.toml, [[timeline.events]]), each with the words a passage
    must hold and the pattern that reads its date, with the date's format. key_date is the assertions reader's own
    pattern (KEY_DATE_LABELS), so the moment a disagreement is about and the diamond on the chart are dated the same
    way; a kind it has no pattern for is a ConfigError that names the setting."""
    events = {}
    for event in settings.events:
        pattern = KEY_DATE_LABELS.get(event.kind) if event.pattern == KEY_DATE else re.compile(event.pattern)
        if pattern is None:
            raise ConfigError(f"config/project_page.toml: [[timeline.events]] {event.kind} uses key_date, but the "
                              "assertions reader has no key-date pattern for it.")
        events[event.kind] = [(words, pattern, event.date_format) for words in event.words]
    return events


EVENTS = events_of(PAGE.timeline)
SIGNINGS = {"awards": "contract awards", "award_notice": "award notice", "notices": "notices", "usd": "USD",
            "contract_award": "Contract Award"}
ACTIVE = "Active"  # the projects API's status of a project still under way
LANGUAGE = "en"  # the version of a report in two languages that the timeline draws


@cache
def _query(name: str) -> str:
    return (SQL / f"{name}.sql").read_text()


def _rows(engine: Engine, name: str, **params) -> list[dict]:
    result = engine.run(_query(name), params)
    return [dict(zip(result.columns, row)) for row in result.rows]


@cache
def words() -> dict:
    """copy.timeline.server, as web/lint/server-copy.ts copied it."""
    return json.loads((resources.files("strata.server") / "timeline_copy.json").read_text())


def _day(value) -> dt.date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _iso(value) -> str | None:
    day = _day(value)
    return day.isoformat() if day else None


def _amount(value) -> str | None:
    return None if value is None or value == "" else f"{float(value):.2f}"


# ── Segments ─────────────────────────────────────────────────────────────

def fill(template: str, slots: dict) -> list[dict]:
    """A copy template with each {slot} replaced by text or by segments."""
    out: list[dict] = []
    for index, part in enumerate(re.split(r"\{(\w+)\}", template)):
        if index % 2 == 0:
            if part:
                out.append({"text": part})
            continue
        value = slots[part]
        out.extend(value if isinstance(value, list) else [value] if isinstance(value, dict) else [{"text": str(value)}])
    return out


def text_of(segments: list[dict]) -> str:
    """Segments as plain text, each count written as Num writes it in a sentence (DESIGN.md section 7, rule 12)."""
    def one(segment: dict) -> str:
        if "text" in segment:
            return segment["text"]
        if "year" in segment:
            return str(segment["year"])
        if "date" in segment:
            day = dt.date.fromisoformat(segment["date"])
            return f"{day:%B} {day.day}, {day.year}"
        count = segment["number"]
        word = words()["numberWords"][count - 1] if 1 <= count <= 9 else f"{count:,}"
        return word[:1].upper() + word[1:] if segment.get("capital") else word
    return "".join(one(segment) for segment in segments)


def _count(n: int, capital: bool = False) -> dict:
    return {"number": n, "capital": capital} if capital else {"number": n}


def _counted(n: int, forms: dict) -> list[dict]:
    """"no evaluations", "one evaluation" or "four evaluations": the singular for one (DESIGN.md section 7)."""
    return fill(forms["none"] if n == 0 else forms["one"] if n == 1 else forms["many"], {"n": _count(n)})


# ── The marks ────────────────────────────────────────────────────────────

def isr_marks(points: list[dict], isrs: list[dict], sides: set[str], side_of: Callable[[str], str | None]) -> set[str]:
    """Which ISRs get their own circle, by document id: each ISR that is one side of a disagreement on the chart,
    and each ISR whose rating of progress moved to the other side of the scale from the ISR before it. When no
    ISR passes, as when get_disagreements gives no ratings, the newest ISR Strata read does, so the How lane always
    has a report to open. The band row shows every rated ISR.

    This is the 23 brief's rule ("an ISR gets a circle when Strata has read it"), narrowed because the fixture
    records all 13 of P130164's ISRs as documents: 13 circles would crowd the How lane and drop labels. A
    decision parked for the owner."""
    marked = {point["document_id"] for point in points if point["document_id"] in sides}
    for before, point in zip(points, points[1:]):
        if side_of(before["rating"]) and side_of(point["rating"]) and side_of(before["rating"]) != side_of(point["rating"]):
            marked.add(point["document_id"])
    newest = max(isrs, key=lambda item: (item["date"], item["document_id"]), default=None)
    if not marked and newest is not None:
        marked.add(newest["document_id"])
    return marked


def _event(engine: Engine, project_id: str, as_of: dt.date, kind: str, reports: dict[str, dict],
           sequences: dict[str, int]) -> dict | None:
    for needle, pattern, fmt in EVENTS[kind]:
        for row in _rows(engine, "events", project_id=project_id, as_of=as_of, words=needle):
            found = pattern.search(row["text"] or "")
            if not found:
                continue
            try:
                day = dt.datetime.strptime(found.group(1), fmt).date()
            except ValueError:
                continue
            source = reports.get(str(row["document_id"]), {})
            return {"id": f"event:{kind}", "kind": "event", "type": kind, "lane": "how", "date": day.isoformat(),
                    "public_from": _iso(row["public_from"]), "evidence_id": f"{PASSAGES}:{row['passage_id']}",
                    "source": {"type": GROUPS.get(row["document_type"] or "", "other"),
                               "sequence": sequences.get(str(row["document_id"])),
                               "date": _iso(source.get("document_date"))}}
    return None


def _report(row: dict, versions: dict[tuple, dict], as_of: dt.date, sequences: dict[str, int],
            ratings: dict[str, str]) -> dict:
    kind = GROUPS.get(row["document_type"], "other")
    document_id = str(row["document_id"])
    replaced = _day(row["replaced_on"])
    later = versions.get((row["report_number"], (row["version"] or 1) + 1)) if replaced and replaced <= as_of else None
    item = {"id": f"{DOC}:{document_id}", "kind": "report", "type": kind, "lane": REPORT_LANES[kind],
            "date": _iso(row["document_date"]), "public_from": _iso(row["public_from"]),
            "evidence_id": f"{DOC}:{document_id}", "document_id": document_id, "document_type": row["document_type"],
            "report_number": row["report_number"], "version": row["version"], "doc_key": row["doc_key"],
            "sequence": sequences.get(document_id), "rating": ratings.get(document_id),
            "replaced_by": None if later is None else {"evidence_id": f"{DOC}:{later['document_id']}",
                                                       "date": _iso(later["document_date"])},
            "reissued": (row["version"] or 1) > 1}
    return item


def _record(row: dict, project_id: str) -> dict:
    return {"id": f"record:{row['step_reference']}", "kind": "record", "type": "contract", "lane": "what",
            "date": _iso(row["signed_on"]), "public_from": _iso(row["public_from"]),
            "evidence_id": f"strata.gold.package:{row['step_reference']}", "step_reference": row["step_reference"],
            "signed_in": row["signed_in"], "award_notice_id": row["award_notice_id"],
            "signed_amount_usd": _amount(row["signed_amount_usd"]), "project_id": project_id}


def _grouped(records: list[dict], project_id: str, above: int) -> list[dict]:
    """The What lane's marks: every contract, or above the threshold, one group per year that signed two or more."""
    if len(records) <= above:
        return records
    by_year: dict[int, list[dict]] = {}
    for record in records:
        by_year.setdefault(int(record["date"][:4]), []).append(record)
    marks = []
    for year, signed in sorted(by_year.items()):
        if len(signed) == 1:
            marks.extend(signed)
            continue
        marks.append({"id": f"{CONTRACTS}:{project_id}:{year}", "kind": "group", "type": "contracts", "lane": "what",
                      "date": f"{year}-07-01", "public_from": max(record["public_from"] for record in signed),
                      "evidence_id": f"{CONTRACTS}:{project_id}:{year}", "year": year, "count": len(signed)})
    return marks


# ── The ratings and the disagreements ─────────────────────────────────────

def _bands(trajectory: dict, project_id: str, scale: list[str]) -> dict:
    points = trajectory["points"]
    dates = {point["sequence"]: point["made_at"] for point in points}
    runs = trajectory["runs"]
    bands = []
    for at, run in enumerate(runs):
        end = runs[at + 1]["first_made_at"] if at + 1 < len(runs) else run["last_made_at"]
        key = f"{RATINGS}:{project_id}:{trajectory['attribute']}:{run['first_sequence']}-{run['last_sequence']}"
        bands.append({"id": key, "kind": "band", "lane": "how", "date": run["first_made_at"], "end": end,
                      "public_from": dates[run["last_sequence"]], "evidence_id": key, "rating": run["value"],
                      "first": run["first_sequence"], "last": run["last_sequence"], "count": run["count"]})
    first, last = points[0]["value"], points[-1]["value"]
    rank = {rating: at for at, rating in enumerate(scale)}
    direction = "same" if first == last else "fell" if rank.get(last, 0) > rank.get(first, 0) else "rose"
    return {"attribute": trajectory["attribute"], "field_name": trajectory["field_name"], "bands": bands,
            "points": [{"sequence": point["sequence"], "date": point["made_at"], "rating": point["value"],
                        "document_id": point["document_id"], "evidence_id": f"{DOC}:{point['document_id']}"}
                       for point in points],
            "first_rating": first, "last_rating": last, "direction": direction, "isr_count": len(points)}


def _disagreement(row: dict, items: dict[str, dict]) -> dict | None:
    """A disagreement the chart can draw: both sides are reports on it. None otherwise."""
    sides = []
    for side in row["sides"]:
        item = items.get(f"{DOC}:{side['document_id']}")
        if item is None:
            return None
        sides.append({"item_id": item["id"], "evidence_id": side["evidence_id"], "assertion_id": side["assertion_id"],
                      "type": item["type"], "sequence": side["sequence"], "document_type": side["document_type"],
                      "paragraph": side["paragraph"] if side["paragraph_numbered"] else None,
                      "made_at": side["made_at"], "public_from": side["public_from"], "lane": item["lane"],
                      "doc_key": side["doc_key"], "leaned": side["assertion_id"] == row["lean_assertion_id"]})
    later = max(sides, key=lambda side: (side["made_at"], side["item_id"]))
    key = f"{DISAGREEMENT}:{row['disagreement_id']}"
    return {"id": key, "kind": "disagreement", "lane": None, "date": later["made_at"], "public_from": row["public_from"],
            "evidence_id": key, "disagreement_id": row["disagreement_id"], "attribute": row["attribute"],
            "rule_id": row["rule_id"], "sides": sides, "after": later["item_id"]}


# Each record a package's disagreement can rest on, in the step tracker's and the plan check's words for it.
RECORD_NAMES = {"plan_row": "plan", **RECORD_WORDS}


def records_disagree(rows: list[dict]) -> list[dict]:
    """Where the records disagree (ticket 132): get_disagreements' rows about a package whose two sides are both
    records, such as a plan row that still says pending and the contract awards that say the contract was signed,
    which no dashed line on the chart joins. Each gives its STEP reference, its attribute and both sides in the order
    they were written, with each side's record, field name, value, date and evidence id, and the side Strata leans
    on: a plan that still says pending first, then the newest first. The plan check cites the same disagreement by
    its id, so both pages name one fact (CLAUDE.md rule 4)."""
    found = []
    for row in rows:
        if row["subject_kind"] != "package" or any(side["form"] not in RECORD_NAMES for side in row["sides"]):
            continue
        sides = [{"record": RECORD_NAMES[side["form"]], "form": side["form"], "field_name": side["field_name"],
                  "value": side["value"], "value_form": side["value_form"], "made_at": side["made_at"],
                  "public_from": side["public_from"], "evidence_id": side["evidence_id"],
                  "leaned": side["assertion_id"] == row["lean_assertion_id"]} for side in row["sides"]]
        key = f"{DISAGREEMENT}:{row['disagreement_id']}"
        found.append({"id": key, "evidence_id": key, "disagreement_id": row["disagreement_id"],
                      "step_reference": row["subject_id"], "attribute": row["attribute"], "rule_id": row["rule_id"],
                      "date": max(side["made_at"] for side in sides), "public_from": row["public_from"], "sides": sides})
    # A plan that still says pending first, since the plan check names those rows moved on since the plan; then the
    # newest first, since the latest plan's are the ones a reader acts on; then by reference.
    found.sort(key=lambda one: (one["step_reference"], one["disagreement_id"]))
    found.sort(key=lambda one: one["date"], reverse=True)
    return sorted(found, key=lambda one: not any(side["value_form"] == STATUS for side in one["sides"]))


LANE_ORDER = {lane: at for at, lane in enumerate(LANES)}
KIND_ORDER = {"report": 0, "event": 0, "record": 0, "group": 0, "band": 1}


def ordered(marks: list[dict], disagreements: list[dict]) -> list[dict]:
    """Date order across the lanes; ties go Why, How, What, with marks before bands; each disagreement right
    after its later side (the 23 brief, section 8.2)."""
    out = []
    for item in sorted(marks, key=lambda item: (item["date"], LANE_ORDER[item["lane"]], KIND_ORDER[item["kind"]],
                                                item["id"])):
        out.append(item)
        out.extend(found for found in disagreements if found["after"] == item["id"])
    return out


# ── The finding and the alt text ──────────────────────────────────────────

def _side_name(side: dict) -> str:
    template = words()["short"].get(side["type"], words()["short"]["other"])
    return template.replace("{sequence}", str(side.get("sequence") or ""))


def _ratings_clause(ratings: dict | None) -> list[dict] | None:
    if ratings is None:
        return None
    finding = words()["finding"]
    if ratings["direction"] == "same":
        return fill(finding["same"], {"rating": ratings["first_rating"]})
    return fill(finding[ratings["direction"]], {"first": ratings["first_rating"], "last": ratings["last_rating"]})


def finding(ratings: dict | None, disagreements: list[dict], status: str) -> list[dict]:
    """The chart's title (the 23 brief, section 7.2)."""
    templates = words()["finding"]
    if status == "failed":
        return fill(templates["failed"], {})
    clause = _ratings_clause(ratings)
    if status == "hidden":
        return fill(templates["hiddenRatings"], {"ratings": clause}) if clause else fill(templates["hiddenNone"], {})
    lead = (fill(templates["leadOne"], {}) if len(disagreements) == 1
            else fill(templates["leadSeveral"], {"count": _count(len(disagreements), capital=True)}))
    if disagreements and clause:
        return fill(templates["disagreeRatings"], {"lead": lead, "ratings": clause})
    if clause:
        return fill(templates["ratingsOnly"], {"ratings": clause})
    if disagreements:
        return fill(templates["disagreeOnly"], {"lead": lead})
    return fill(templates["neither"], {})


def alt_text(project_id: str, dated: list[dict], ratings: dict | None, disagreements: list[dict],
             status: str, asked: dt.date | None = None) -> list[dict]:
    """The drawn layer's name (the 23 brief, section 4.11), counting every dated item, each contract on its own.
    When the page asked for a date, it ends by naming it, since the drawn "As of" label is inside the image."""
    alt = words()["alt"]
    as_of = [{"text": " "}, *fill(alt["asOf"], {"date": {"date": asked.isoformat()}})] if asked else []
    if not dated:
        return fill(alt["empty"], {"pid": project_id}) + as_of
    counts = {lane: sum(item["lane"] == lane for item in dated) for lane in LANES}
    years = sorted(int(item["date"][:4]) for item in dated)
    out = fill(alt["populated"], {
        "pid": project_id, "first": {"year": years[0]}, "last": {"year": years[-1]},
        "why": _counted(counts["why"], alt["evaluations"]), "how": _counted(counts["how"], alt["operations"]),
        "what": _counted(counts["what"], alt["records"])})
    out.append({"text": " "})
    if status == "failed":
        out.extend(fill(alt["ratingsFailed"], {}))
    elif ratings is None:
        out.extend(fill(alt["noRatings"], {}))
    elif ratings["direction"] == "same":
        out.extend(fill(alt["ratingsSame"], {"rating": ratings["first_rating"], "count": _count(ratings["isr_count"])}))
    else:
        out.extend(fill(alt["ratings"], {"first": ratings["first_rating"], "last": ratings["last_rating"],
                                         "count": _count(ratings["isr_count"])}))
    if status == "ok":
        for found in disagreements:
            out.append({"text": " "})
            out.extend(fill(alt["line"], {"side1": _side_name(found["sides"][0]), "side2": _side_name(found["sides"][1])}))
        if not disagreements:
            out.append({"text": " "})
            out.extend(fill(alt["noLines"], {}))
    return out + as_of


# ── The timeline ─────────────────────────────────────────────────────────

def reads(project_id: str, as_of: dt.date, view: str = "staff") -> list[tuple[str, dict]]:
    """Every statement timeline() runs, get_disagreements' among them, for the route that sends them as one batch
    (ticket 125). A project ID is held in capitals, so the reads after the first name it so."""
    pid = project_id.strip().upper()
    each = {"project_id": pid, "as_of": as_of}
    return [(_query("project"), each),
            *disagreement_reads(pid, as_of, view),
            (_query("reports"), {**each, "language": LANGUAGE}),
            *[(_query("events"), {**each, "words": words}) for kind in EVENTS for words, _, _ in EVENTS[kind]],
            (_query("signings"), {**each, **SIGNINGS}),
            (viewer_query("data_through"), {"cadence": DAILY})]


def _project(engine: Engine, project_id: str, as_of: dt.date) -> dict | None:
    found = _rows(engine, "project", project_id=project_id.strip().upper(), as_of=as_of)
    return found[0] if found else None


def timeline(engine: Engine, viewer: Viewer, project_id: str, as_of: dt.date, view: str = "staff",
             asked: dt.date | None = None) -> dict | None:
    """The Timeline tab's answer, or None when Strata has no record of the project as of then."""
    project = _project(engine, project_id, as_of)
    if project is None:
        return None
    pid = project["project_id"]
    ladder = load_ladder()
    try:
        found = registry.call("get_disagreements", {"subject_id": pid}, registry.Context(engine, viewer, view, as_of))
        # The tool applies the view: the public view of a project under way on the page's date gets no disagreement.
        status = "hidden" if (found.get("abstention") or {}).get("reason") == WITHHELD else "ok"
    except Exception:  # the tool did not answer: the marks still draw, with no dashed lines and no bands
        found, status = {"rows": [], "trajectories": [], "rejected": {"count": 0}}, "failed"
    trajectory = next((one for one in found.get("trajectories") or []
                       if one["attribute"] == BANDED and one["evidence_tier"] == BANDED_TIER
                       and one["subject_kind"] == "project"), None)
    scale = list(ladder.scales[ladder.attribute(BANDED).scale].ratings)
    ratings = _bands(trajectory, pid, scale) if trajectory else None
    rated = {point["document_id"]: point["rating"] for point in ratings["points"]} if ratings else {}

    rows = [row for row in _rows(engine, "reports", project_id=pid, as_of=as_of, language=LANGUAGE)
            if GROUPS.get(row["document_type"]) in REPORT_LANES]
    # Each ISR's sequence number as its first page prints it, and as get_disagreements gives it when it answers.
    sequences = {str(row["document_id"]): row["sequence"] for row in rows if row["sequence"] is not None}
    sequences.update({point["document_id"]: point["sequence"] for point in ratings["points"]} if ratings else {})
    reports = {str(row["document_id"]): row for row in rows}
    versions = {(row["report_number"], row["version"] or 1): row for row in rows if row["report_number"]}
    every = {f"{DOC}:{document_id}": _report(row, versions, as_of, sequences, rated) for document_id, row in reports.items()}

    shown_rows = [] if status != "ok" else found["rows"]
    disagreements = [one for row in shown_rows if (one := _disagreement(row, every)) is not None]
    sides = {side["item_id"].removeprefix(f"{DOC}:") for found_one in disagreements for side in found_one["sides"]}
    isrs = [item for item in every.values() if item["type"] == "isr"]
    marked = isr_marks(ratings["points"] if ratings else [], isrs, sides, lambda rating: ladder.side(BANDED, rating))
    report_items = [item for item in every.values() if item["type"] != "isr" or item["document_id"] in marked]
    events = [event for kind in EVENTS if (event := _event(engine, pid, as_of, kind, reports, sequences)) is not None]
    signings = [_record(row, pid) for row in _rows(engine, "signings", project_id=pid, as_of=as_of, **SIGNINGS)]
    above = int(load_thresholds().value("timeline.what_lane_group_above"))
    bands = ratings["bands"] if ratings else []
    marks = [*report_items, *events, *_grouped(signings, pid, above), *bands]
    items = ordered(marks, disagreements)
    dated = [*report_items, *events, *signings]  # every dated item, each contract on its own
    table = ordered([*dated, *bands], disagreements)
    for found_one in disagreements:
        for side in found_one["sides"]:
            item = every[side["item_id"]]
            item.setdefault("disagrees_with", []).append(found_one["id"])
    return {
        "project": {"project_id": pid, "project_name": project["project_name"],
                    "display_name": display_name(project["project_name"]), "status": project["status"]},
        "as_of": as_of.isoformat(), "asked_as_of": _iso(asked), "view": view,
        "items": items, "table": table, "ratings": ratings,
        "disagreements": {"status": status, "count": len(disagreements)},
        # The disagreements between a package's records, listed under the chart (ticket 132).
        "records_disagree": records_disagree(shown_rows),
        # The state a dashed line takes when no answer or draft open on the page depends on it (config).
        "disagreement_line_state": PAGE.timeline.disagreement_line_state,
        "rejected": {"count": int((found.get("rejected") or {}).get("count") or 0)} if status != "failed" else None,
        "counts": {lane: sum(item["lane"] == lane for item in dated) for lane in LANES},
        "finding": finding(ratings, disagreements, status),
        "alt": alt_text(pid, dated, ratings, disagreements, status, asked),
        "sources": ["documents", "notices", "awards"],
        # The data-freshness stamp's day, which the source line ends with ("through October 23, 2026").
        "data_through": _iso(data_through(engine)),
    }


# ── The evidence drawer's views (the 23 brief, section 6) ─────────────────

def _tool(engine: Engine, project_id: str, as_of: dt.date) -> dict:
    """get_disagreements about the project, through the registry, on an engine that already reads as the viewer."""
    return registry.call("get_disagreements", {"subject_id": project_id}, registry.Context(engine, Viewer(), "staff", as_of))


def _stratum(kind: str) -> str:
    return {"why": "Why", "how": "How", "what": "What"}[REPORT_LANES.get(kind, "why")]


def _place(row: dict) -> dict:
    return {"paragraph": row["paragraph"] if row.get("paragraph_numbered") else None,
            "section": row.get("section_path") or None, "pdf_page": row.get("pdf_page")}


def read_document(engine: Engine, key: str, as_of: dt.date) -> dict | None:
    """doc:{document_id}: one report as the timeline's mark opens it (section 6.4): its type, number, dates and
    pages, what it rated with the passage each rating rests on, the disagreements it is a side of, and the re-issue
    that replaced it, as of the date."""
    found = _rows(engine, "document", document_id=key, as_of=as_of)
    if not found:
        return None
    row = found[0]
    kind = GROUPS.get(row["document_type"], "other")
    pid = row["project_id"]
    tool = _tool(engine, pid, as_of)
    sequences = {point["document_id"]: point["sequence"] for trajectory in tool.get("trajectories") or []
                 for point in trajectory["points"]}
    later = None
    if _day(row["replaced_on"]) and _day(row["replaced_on"]) <= as_of:
        later = next((other for other in _rows(engine, "reports", project_id=pid, as_of=as_of, language=LANGUAGE)
                      if other["report_number"] == row["report_number"] and other["version"] == (row["version"] or 1) + 1),
                     None)
    ratings = [{"field_name": rating["field_name"], "value": rating["value"], "evidence_id": rating["evidence_id"],
                "doc_key": rating["doc_key"], **_place(rating)}
               for rating in _rows(engine, "document_ratings", document_id=key, as_of=as_of, passages=f"{PASSAGES}:")
               if rating["value"]]
    involved = []
    for disagreement in tool["rows"]:
        mine = [side for side in disagreement["sides"] if side["document_id"] == key]
        if not mine:
            continue
        other = next(side for side in disagreement["sides"] if side is not mine[0])
        involved.append({"evidence_id": f"{DISAGREEMENT}:{disagreement['disagreement_id']}",
                         "attribute": disagreement["attribute"], "period_event": disagreement["period"]["event"],
                         "other": {"type": GROUPS.get(other["document_type"] or "", "other"), "sequence": other["sequence"]}})
    return {"kind": "document", "stratum": _stratum(kind), "short_name": None, "row": {
        "evidence_id": f"{DOC}:{key}", "public_from": _iso(row["public_from"]), "document_id": key, "project_id": pid,
        "type": kind, "document_type": row["document_type"], "report_number": row["report_number"],
        "version": row["version"], "document_date": _iso(row["document_date"]), "pdf_pages": row["pdf_pages"],
        "doc_key": row["doc_key"], "sequence": sequences.get(key), "reissued": (row["version"] or 1) > 1,
        "replaced_by": None if later is None else {"evidence_id": f"{DOC}:{later['document_id']}",
                                                   "date": _iso(later["document_date"]), "doc_key": later["doc_key"]},
        "ratings": ratings, "disagreements": involved,
        "source": {"source_key": "documents", "project_id": pid, "document_date": _iso(row["document_date"])}}}


def read_ratings(engine: Engine, key: str, as_of: dt.date) -> dict | None:
    """ratings:{pid}:{attribute}:{first}-{last}: one run of a series of ISR ratings, as the band opens it (section
    6.2), each ISR with its date, its rating and its document."""
    parts = key.split(":")
    if len(parts) != 3 or not re.fullmatch(r"\d+-\d+", parts[2]):
        return None
    pid, attribute, span = parts
    first, last = (int(number) for number in span.split("-"))
    trajectory = next((one for one in _tool(engine, pid, as_of).get("trajectories") or []
                       if one["attribute"] == attribute and one["evidence_tier"] == BANDED_TIER), None)
    if trajectory is None:
        return None
    run = next((one for one in trajectory["runs"] if (one["first_sequence"], one["last_sequence"]) == (first, last)), None)
    if run is None:
        return None
    points = [point for point in trajectory["points"] if first <= point["sequence"] <= last]
    return {"kind": "ratings", "stratum": "How", "short_name": None, "row": {
        "evidence_id": f"{RATINGS}:{key}", "public_from": points[-1]["made_at"], "project_id": pid,
        "attribute": attribute, "field_name": trajectory["field_name"], "rating": run["value"], "first": first,
        "last": last, "count": run["count"],
        "rows": [{"sequence": point["sequence"], "date": point["made_at"], "rating": point["value"],
                  "evidence_id": f"{DOC}:{point['document_id']}"} for point in points],
        "source": {"source_key": "documents", "project_id": pid}}}


def read_contracts(engine: Engine, key: str, as_of: dt.date) -> dict | None:
    """contracts:{pid}:{year}: the contracts a project signed in one year, as a group mark opens them (section 6.3)."""
    pid, _, year = key.partition(":")
    if not year.isdigit():
        return None
    signed = [row for row in _rows(engine, "signings", project_id=pid, as_of=as_of, **SIGNINGS)
              if _day(row["signed_on"]).year == int(year)]
    if not signed:
        return None
    return {"kind": "contracts", "stratum": "What", "short_name": None, "row": {
        "evidence_id": f"{CONTRACTS}:{key}", "public_from": max(_iso(row["public_from"]) for row in signed),
        "project_id": pid, "year": int(year), "count": len(signed),
        "rows": [{"step_reference": row["step_reference"], "signed_on": _iso(row["signed_on"]),
                  "signed_amount_usd": _amount(row["signed_amount_usd"]),
                  "evidence_id": f"strata.gold.package:{row['step_reference']}"} for row in signed],
        "source": {"source_key": "awards", "project_id": pid}}}


def disagreement_row(row: dict) -> dict:
    """A disagreement as the card draws it on the timeline and in the drawer: get_disagreements' row, each side with
    its kind of report, the evidence id of its document view and the whole sentence that holds its quote."""
    sides = [{**side, "type": GROUPS.get(side["document_type"] or "", "other"), "document": f"{DOC}:{side['document_id']}",
              "sentence": sentence_of(side.get("text"), side.get("quote")),
              "leaned": side["assertion_id"] == row["lean_assertion_id"]} for side in row["sides"]]
    return {"evidence_id": f"{DISAGREEMENT}:{row['disagreement_id']}", "public_from": row["public_from"],
            "disagreement_id": row["disagreement_id"], "project_id": row["project_id"], "attribute": row["attribute"],
            "period": row["period"], "rule_id": row["rule_id"], "lean_assertion_id": row["lean_assertion_id"],
            "other_assertion_id": row["other_assertion_id"], "if_you_keep": row["if_you_keep"], "sides": sides,
            "source": {"table": row["source"]["table"], "project_id": row["project_id"]}}


def read_disagreement(engine: Engine, key: str, as_of: dt.date) -> dict | None:
    """disagreement:{id}: both sides of a disagreement, as the timeline's dashed line opens it (section 6.1). None
    when no disagreement has the id, or its two sides were not both public on the date."""
    found = _rows(engine, "disagreement", disagreement_id=key, as_of=as_of)
    if not found:
        return None
    row = next((one for one in _tool(engine, found[0]["project_id"], as_of)["rows"] if one["disagreement_id"] == key),
               None)
    if row is None:
        return None
    sides = {_stratum(GROUPS.get(side["document_type"] or "", "other")) for side in row["sides"]}
    # Two records about a package (ticket 132) are the What lane's, as a contract mark is; two reports keep their own.
    records = all(side["evidence_tier"] == "record" for side in row["sides"])
    stratum = "What" if records else "Why" if sides == {"Why"} else None
    return {"kind": "disagreement", "stratum": stratum, "short_name": None, "row": disagreement_row(row)}


def read_signing(engine: Engine, key: str, as_of: dt.date) -> dict | None:
    """strata.gold.package:{step_reference} for a package the range chart does not read: its earliest signed contract
    as a record, with the award notice that dates it when no awards dataset does (a contract mark on the timeline)."""
    found = _rows(engine, "package_project", step_reference=key)
    if not found or not found[0]["project_id"]:
        return None
    pid = found[0]["project_id"]
    row = next((one for one in _rows(engine, "signings", project_id=pid, as_of=as_of, **SIGNINGS)
                if one["step_reference"] == key), None)
    if row is None:
        return None
    fields = [("contract_signed_on", _iso(row["signed_on"]), "date"), ("award_notice_id", row["award_notice_id"], "text"),
              ("procurement_method", row["procurement_method"], "text"),
              ("procurement_category", row["procurement_category"], "text"),
              ("signed_amount_usd", _amount(row["signed_amount_usd"]), "usd")]
    return {"kind": "record", "row": {
        "evidence_id": f"strata.gold.package:{key}", "public_from": _iso(row["public_from"]), "reference": key,
        "fields": [{"key": name, "value": value, "kind": kind} for name, value, kind in fields if value not in (None, "")],
        "source": {"source_key": "award_notices" if row["award_notice_id"] else "awards", "project_id": pid,
                   "document_date": _iso(row["signed_on"])}}}


def in_view(engine: Engine, found: dict, view: str, as_of: dt.date) -> dict | None:
    """A drawer view as a preview shows it: the public view of a project still under way shows no disagreement
    (spec, user story 55), from a link as on the timeline. A disagreement gives None; a document view keeps its
    report and loses the disagreements it is a side of. Any other view, or any other preview, is unchanged. Whether the
    project was under way is judged as of the page's date (strata.tools.withheld, ticket 40)."""
    if found["kind"] not in ("disagreement", "document") or not withheld_in(
            engine, view, as_of, "disagreements_on_active_projects", found["row"]["project_id"]):
        return found
    return None if found["kind"] == "disagreement" else {**found, "row": {**found["row"], "disagreements": []}}


READERS: dict[str, Callable[[Engine, str, dt.date], dict | None]] = {
    DOC: read_document, RATINGS: read_ratings, CONTRACTS: read_contracts, DISAGREEMENT: read_disagreement,
}
