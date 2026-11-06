"""The hindsight test's coding tool (ticket 34): which risks each completion report blamed, read by two people.

ops/hindsight/code.py runs it; it has no screen. For each gate-set project:

- Two coders each read the project's ICR on their own and say which risk factors on the closed list
  (config/lessons.toml) it blamed (code()). Each reading is stored whole, one row per risk factor, blamed or not,
  in strata.ops.hindsight_codings. A coder who reads again replaces their own reading; a third coder is refused,
  so each project has exactly two.
- Where the two differ, one person reads the ICR Review on the factors they differ on (code() with reading
  icr_review), and the ICR Review prevails: the spec's evidence ladder puts IEG's review above the ICR.
- reconcile() writes each project's blamed risks to strata.ops.hindsight_blamed: what both coders agreed on,
  plus what the ICR Review settled. A project with no ICR Review keeps only the risks both coders blamed (a parked
  rule: PLAN.md section 3 counts 49 ICRs but 43 ICR Reviews). A project whose coders differ while its ICR Review is
  still unread waits.
- reconcile() also counts each pair of coders' agreement, factor by factor, with the judging tool's Cohen's kappa
  (strata.knowledge.retrieval.judging.kappa, ticket 32), withheld below retrieval.min_pairs pairs, in
  strata.ops.hindsight_agreement.

Who the coders are, and how many projects they code, is open (docs/STATUS.md, decision 5). The tool accepts any two
different people and records who they were.
"""

from __future__ import annotations

import datetime as dt
import json
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from importlib import resources

from strata.config import LessonLists, Thresholds, load_lesson_lists, load_thresholds
from strata.estimates.past_range import as_date
from strata.lakehouse.engine import Engine
from strata.reader.templates import ICR, ICR_REVIEW

READINGS = ("icr", "icr_review")  # a coder's reading of the ICR, and the reading of the ICR Review that settles
BLAMED, NOT_BLAMED = "blamed", "not_blamed"  # the two answers the agreement statistic counts
CODINGS = "strata.ops.hindsight_codings"
RECONCILED = "strata.ops.hindsight_blamed"
AGREEMENT = "strata.ops.hindsight_agreement"
CODING_COLUMNS = ("coding_id", "project_id", "reading", "document_id", "document_version", "coder", "coder_name",
                  "risk_key", "blamed", "coded_at", "public_from")
RECONCILED_COLUMNS = ("project_id", "blamed", "rule", "settled", "coders", "icr_coding_ids", "review_coding_id",
                      "reconciled_at", "public_from")
AGREEMENT_COLUMNS = ("coder_a", "coder_b", "projects", "pairs", "agree", "kappa", "computed_at", "public_from")
EVERY_DAY = dt.date(9999, 12, 31)  # read every stored row, whenever it was stored

ALL_CODINGS = """
SELECT coding_id, project_id, reading, document_id, document_version, coder, coder_name, risk_key, blamed, coded_at,
  public_from
FROM strata.ops.hindsight_codings
WHERE public_from <= :as_of
ORDER BY coded_at, coding_id, risk_key
"""

ALL_RECONCILED = """
SELECT project_id, blamed, rule, settled, coders, icr_coding_ids, review_coding_id, reconciled_at, public_from
FROM strata.ops.hindsight_blamed
WHERE public_from <= :as_of
ORDER BY reconciled_at, project_id
"""

ALL_AGREEMENT = """
SELECT coder_a, coder_b, projects, pairs, agree, kappa, computed_at, public_from
FROM strata.ops.hindsight_agreement
WHERE public_from <= :as_of
ORDER BY computed_at, coder_a, coder_b
"""


class Refused(ValueError):
    """A reading the tool will not store, with the sentence that says why."""


@dataclass(frozen=True)
class Coder:
    email: str
    name: str


def _rows(engine: Engine, sql: str, **params) -> list[dict]:
    result = engine.run(sql, params)
    return [dict(zip(result.columns, row)) for row in result.rows]


def reports(engine: Engine, projects: Iterable[str], as_of: dt.date) -> dict[str, dict]:
    """Each project's approval date, country, sector, newest ICR (with the passages Prism read from it) and newest
    ICR Review, by project ID (src/strata/estimates/sql/hindsight/reports.sql)."""
    wanted = ",".join(dict.fromkeys(projects))
    if not wanted:
        return {}
    sql = (resources.files("strata.estimates") / "sql" / "hindsight" / "reports.sql").read_text()
    return {row["project_id"]: row for row in _rows(engine, sql, projects=wanted, as_of=as_of, icr=ICR.document_type,
                                                    icr_review=ICR_REVIEW.document_type)}


def _bool(value) -> bool:
    return value if isinstance(value, bool) else str(value).lower() == "true"


def codings(engine: Engine, project_id: str | None = None, as_of: dt.date = EVERY_DAY) -> list[dict]:
    """The newest reading of each coder, per project and reading, with the risk factors it said were blamed, in
    the closed list's order."""
    found: dict[str, dict] = {}
    for row in _rows(engine, ALL_CODINGS, as_of=as_of):
        coding = found.setdefault(row["coding_id"], {
            "coding_id": row["coding_id"], "project_id": row["project_id"], "reading": row["reading"],
            "document_id": str(row["document_id"]), "coder": row["coder"], "coder_name": row["coder_name"],
            "coded_at": row["coded_at"], "answers": {}})
        coding["answers"][row["risk_key"]] = _bool(row["blamed"])
    newest: dict[tuple[str, str, str], dict] = {}
    for coding in found.values():  # oldest first, so a later reading by the same coder replaces an earlier one
        newest[(coding["project_id"], coding["reading"], coding["coder"])] = coding
    order = [item.key for item in load_lesson_lists().risk_factors]
    readings = [{**coding, "blamed": [key for key in order if coding["answers"].get(key)]} for coding in newest.values()]
    return [coding for coding in readings if project_id is None or coding["project_id"] == project_id]


def code(engine: Engine, project_id: str, coder: Coder, blamed: Iterable[str], *, now: dt.datetime,
         reading: str = "icr", lists: LessonLists | None = None) -> str:
    """Store one coder's reading of a project's ICR (or, with reading icr_review, its ICR Review): every risk factor
    on the closed list, blamed or not. It returns the reading's coding_id."""
    lists = lists or load_lesson_lists()
    if reading not in READINGS:
        raise Refused(f"A reading is {' or '.join(READINGS)}, not {reading!r}.")
    keys = list(dict.fromkeys(key.strip() for key in blamed if key.strip()))
    unknown = [key for key in keys if lists.risk_factor(key) is None]
    if unknown:
        raise Refused(f"{', '.join(unknown)} is not on the closed list of risk factors (config/lessons.toml). The "
                      f"keys are {', '.join(item.key for item in lists.risk_factors)}.")
    report = reports(engine, [project_id], now.date()).get(project_id)
    document = None if report is None else (report["icr_document_id"], report["icr_version"]) if reading == "icr" \
        else (report["review_document_id"], report["review_version"])
    if document is None or document[0] in (None, ""):
        what = "an ICR" if reading == "icr" else "an ICR Review"
        raise Refused(f"{project_id} has no {what} that Prism holds, so there is nothing to read.")
    if reading == "icr":
        others = sorted({coding["coder"] for coding in codings(engine, project_id)
                         if coding["reading"] == "icr" and coding["coder"] != coder.email})
        if len(others) >= 2:
            raise Refused(f"{project_id}'s ICR already has two coders, {others[0]} and {others[1]}. Each project is "
                          "read by two people.")
    coding_id = f"coding-{uuid.uuid4().hex[:12]}"
    engine.insert_rows(CODINGS, CODING_COLUMNS, [
        (coding_id, project_id, reading, str(document[0]), int(document[1]), coder.email, coder.name, item.key,
         item.key in keys, now, now.astimezone(dt.UTC).date()) for item in lists.risk_factors])
    return coding_id


@dataclass(frozen=True)
class Reconciliation:
    """What reconcile() found: each reconciled project's blamed risks, the projects still waiting and why, and each
    pair of coders' agreement."""

    reconciled: dict[str, dict]
    waiting: list[dict]
    agreement: list[dict]


def _settle(first: dict, second: dict, review: dict | None, has_review: bool, order: list[str]) -> dict | None:
    """One project's blamed risks from its two readings and the ICR Review's, or None while it must wait."""
    differ = [key for key in order if first["answers"].get(key, False) != second["answers"].get(key, False)]
    agreed = [key for key in order if first["answers"].get(key) and second["answers"].get(key)]
    if not differ:
        return {"blamed": agreed, "rule": "agreed", "settled": {}}
    if review is not None:
        settled = {key: bool(review["answers"].get(key, False)) for key in differ}
        return {"blamed": [key for key in order if key in agreed or settled.get(key)], "rule": "icr_review",
                "settled": settled}
    if not has_review:
        return {"blamed": agreed, "rule": "no_icr_review", "settled": {key: False for key in differ}}
    return None


def reconcile(engine: Engine, now: dt.datetime, thresholds: Thresholds | None = None,
              lists: LessonLists | None = None) -> Reconciliation:
    """Reconcile every project two coders have read, and count each pair's agreement; store what changed."""
    limits = thresholds or load_thresholds()
    order = [item.key for item in (lists or load_lesson_lists()).risk_factors]
    held = codings(engine)
    by_project: dict[str, dict[str, list[dict]]] = {}
    for coding in held:
        by_project.setdefault(coding["project_id"], {}).setdefault(coding["reading"], []).append(coding)
    found = reports(engine, by_project, now.date())
    stored = reconciled(engine)
    results, waiting, rows = {}, [], []
    pairs: dict[tuple[str, str], dict] = {}
    for project_id, readings in sorted(by_project.items()):
        icr = sorted(readings.get("icr", []), key=lambda coding: coding["coded_at"])[:2]
        if len(icr) < 2:
            waiting.append({"project_id": project_id, "reason": "one_coder"})
            continue
        first, second = sorted(icr, key=lambda coding: coding["coder"])
        reviews = sorted(readings.get("icr_review", []), key=lambda coding: coding["coded_at"])
        review = reviews[-1] if reviews else None
        has_review = bool((found.get(project_id) or {}).get("review_document_id"))
        result = _settle(first, second, review, has_review, order)
        pair = pairs.setdefault((first["coder"], second["coder"]), {"projects": 0, "answers": []})
        pair["projects"] += 1
        pair["answers"] += [(BLAMED if first["answers"].get(key) else NOT_BLAMED,
                             BLAMED if second["answers"].get(key) else NOT_BLAMED) for key in order]
        if result is None:
            waiting.append({"project_id": project_id, "reason": "icr_review_unread"})
            continue
        result = {**result, "coders": [first["coder"], second["coder"]],
                  "icr_coding_ids": [first["coding_id"], second["coding_id"]],
                  "review_coding_id": review["coding_id"] if result["rule"] == "icr_review" else None}
        results[project_id] = result
        before = stored.get(project_id)
        if before is None or any(before[key] != result[key] for key in ("blamed", "rule", "settled", "coders",
                                                                          "icr_coding_ids", "review_coding_id")):
            rows.append((project_id, json.dumps(result["blamed"]), result["rule"], json.dumps(result["settled"],
                         sort_keys=True), json.dumps(result["coders"]), json.dumps(result["icr_coding_ids"]),
                         result["review_coding_id"], now, now.astimezone(dt.UTC).date()))
    if rows:
        engine.insert_rows(RECONCILED, RECONCILED_COLUMNS, rows)
    return Reconciliation(results, waiting, _count_agreement(engine, pairs, now, limits))


def _count_agreement(engine: Engine, pairs: dict, now: dt.datetime, thresholds: Thresholds) -> list[dict]:
    from strata.knowledge.retrieval.judging import kappa

    minimum = int(thresholds.value("retrieval.min_pairs"))
    before = {(row["coder_a"], row["coder_b"]): row for row in agreement(engine)}
    counted, rows = [], []
    for (coder_a, coder_b), pair in sorted(pairs.items()):
        answers = pair["answers"]
        row = {"coder_a": coder_a, "coder_b": coder_b, "projects": pair["projects"], "pairs": len(answers),
               "agree": sum(1 for a, b in answers if a == b),
               "kappa": kappa(answers) if len(answers) >= minimum else None}
        counted.append(row)
        old = before.get((coder_a, coder_b))
        if old is None or any(old[key] != row[key] for key in ("projects", "pairs", "agree", "kappa")):
            rows.append((coder_a, coder_b, row["projects"], row["pairs"], row["agree"], row["kappa"], now,
                         now.astimezone(dt.UTC).date()))
    if rows:
        engine.insert_rows(AGREEMENT, AGREEMENT_COLUMNS, rows)
    return counted


def reconciled(engine: Engine, as_of: dt.date = EVERY_DAY) -> dict[str, dict]:
    """Each project's newest reconciled blamed risks, by project ID."""
    found = {}
    for row in _rows(engine, ALL_RECONCILED, as_of=as_of):  # oldest first, so the newest row of a project stays
        found[row["project_id"]] = {
            "project_id": row["project_id"], "blamed": json.loads(row["blamed"]), "rule": row["rule"],
            "settled": json.loads(row["settled"]), "coders": json.loads(row["coders"]),
            "icr_coding_ids": json.loads(row["icr_coding_ids"]), "review_coding_id": row["review_coding_id"],
            "reconciled_at": row["reconciled_at"], "public_from": as_date(row["public_from"])}
    return found


def agreement(engine: Engine, as_of: dt.date = EVERY_DAY) -> list[dict]:
    """Each pair of coders' newest agreement: the projects both read, the pairs of answers, how many matched, and
    Cohen's kappa (None when withheld)."""
    found: dict[tuple[str, str], dict] = {}
    for row in _rows(engine, ALL_AGREEMENT, as_of=as_of):
        found[(row["coder_a"], row["coder_b"])] = {
            "coder_a": row["coder_a"], "coder_b": row["coder_b"], "projects": row["projects"],
            "pairs": row["pairs"], "agree": row["agree"],
            "kappa": None if row["kappa"] in (None, "") else float(row["kappa"]), "computed_at": row["computed_at"]}
    return list(found.values())
