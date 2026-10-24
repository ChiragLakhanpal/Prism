"""Suppliers resolved on STEP supplier IDs first, names second (ticket 19; docs/PLAN.md section 5).

Each supplier is one record across the contract awards and the award notices:

1. A STEP supplier ID decides first. A row that has one is that supplier, and never enters name
   matching. Two IDs are never merged by name, even when an award notice and the awards give the same
   firm different IDs (docs/PLAN.md section 3).
2. Only a row with no ID is matched by name (strata.knowledge.suppliers.matching): an awarded bidder a
   notice writes with no ID, or a row of the FY2001 to FY2016 awards, whose dataset has no supplier_id
   column. Such a row may join a supplier with an ID, or other rows with no ID.
3. config/thresholds.toml's [supplier_matching] routes each candidate pair by its match probability:
   auto-merge, the model (strata.knowledge.suppliers.judge), or kept apart. A pair the model is not
   sure enough of goes to a person, as does a pair whose merge would join two STEP supplier IDs by
   name. A person's decision (strata.ops.supplier_review_decisions) outranks the thresholds and the
   model.
4. A joint venture stays its own supplier, linked to its members: JV- and its members' supplier IDs,
   as strata.gold.contract keys the awards' joint ventures, so the joint venture an award notice
   lists is the same supplier as the one the awards hold. A row of the FY2001 to FY2016 awards that
   names its members ("X IN JV WITH Y") is read as one row per member.
5. A person hired as an individual consultant is never matched and never named.

resolve() does the work on plain rows and returns plain rows, so the nightly task calls it the same
way on DuckDB and on Databricks (spec, "Data and the lakehouse run"). run() reads the rows and the
decisions, calls resolve(), and writes strata.ops.supplier_pairs and strata.silver.supplier_resolution,
keeping only this run's rows in each. No supplier score, rank or profile is computed.
"""

from __future__ import annotations

import datetime as dt
import hashlib
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, replace
from importlib import resources

from strata.config import ConfigError, SupplierMatching, Thresholds, load_supplier_matching, load_thresholds
from strata.knowledge.suppliers.judge import Judge, Judgement, Question, Side
from strata.knowledge.suppliers.matching import Pair, Record, candidate_pairs
from strata.knowledge.suppliers.names import joint_venture_members
from strata.lakehouse.engine import Engine

ROUTES = ("auto_merge", "model", "person", "kept_apart")
OUTCOMES = ("merge", "no_merge", "waiting")
RESOLVED_SOURCES = ("notices", "awards_fy2001_2016")  # the sources whose rows may lack a STEP supplier ID
SPLIT_SOURCES = ("awards_fy2001_2016",)  # the sources whose one row may name a joint venture's members


@dataclass(frozen=True)
class SupplierRow:
    """One supplier row of one source, as supplier_rows.sql reads it."""

    source: str  # awards, awards_fy2001_2016 or notices
    source_key: str  # the contract number, or the notice ID
    position: int
    contract_id: str | None
    project_id: str | None
    name: str | None
    country: str | None
    step_supplier_id: str | None
    individual_consultant: bool
    contract: str | None  # how a person tells its contract: its STEP reference, contract number or notice ID
    public_from: dt.date

    @property
    def key(self) -> str:
        return f"{self.source_key}/{self.position}"


@dataclass(frozen=True)
class Routing:
    """config/thresholds.toml's [supplier_matching]."""

    candidate_min: float
    model_min: float
    auto_merge_min: float
    model_confidence_min: float

    @classmethod
    def from_thresholds(cls, thresholds: Thresholds) -> Routing:
        def value(name: str) -> float:
            return float(thresholds.value(f"supplier_matching.{name}"))

        routing = cls(value("candidate_min_probability"), value("model_min_probability"),
                      value("auto_merge_min_probability"), value("model_confidence_min"))
        if not 0 < routing.candidate_min <= routing.model_min <= routing.auto_merge_min <= 1:
            raise ConfigError("In thresholds.toml, supplier_matching needs 0 < candidate_min_probability <= "
                              "model_min_probability <= auto_merge_min_probability <= 1.")
        return routing

    def route(self, probability: float) -> str:
        """Where the thresholds send a pair: auto_merge, model or kept_apart."""
        if probability >= self.auto_merge_min:
            return "auto_merge"
        return "model" if probability >= self.model_min else "kept_apart"


@dataclass(frozen=True)
class Decision:
    """A person's decision on a pair, from strata.ops.supplier_review_decisions."""

    decision: str  # merge or no_merge
    reviewer: str
    reason: str


@dataclass(frozen=True)
class PastJudgement:
    """A judgement an earlier run kept, reused while the judge and both names are the same."""

    model: str
    left_name: str
    right_name: str
    judgement: Judgement


@dataclass(frozen=True)
class SideOfPair:
    key: str
    name: str
    country: str | None
    projects: tuple[str, ...]
    contracts: tuple[str, ...]
    public_from: dt.date
    has_id: bool


@dataclass(frozen=True)
class RoutedPair:
    pair_id: str
    left: SideOfPair
    right: SideOfPair
    probability: float
    weight: float
    name_level: str
    projects_level: str
    route: str
    outcome: str
    decided_by: str | None
    review_reason: str | None = None
    model: str | None = None
    model_judgement: Judgement | None = None
    reviewer: str | None = None
    decision_reason: str | None = None

    @property
    def public_from(self) -> dt.date:
        return max(self.left.public_from, self.right.public_from)


@dataclass(frozen=True)
class Resolved:
    """One row of strata.silver.supplier_resolution."""

    row: SupplierRow
    supplier_id: str | None
    joint_venture_id: str | None
    resolved_on: str  # step_supplier_id, name, unmatched, individual_consultant or no_name


@dataclass(frozen=True)
class Resolution:
    pairs: list[RoutedPair]
    rows: list[Resolved]


def pair_id(left: str, right: str) -> str:
    return f"{left}|{right}"


# ── The rows as name matching compares them ──────────────────────────────

def _members(rows: list[SupplierRow]) -> list[SupplierRow]:
    """Each row, with a row of the FY2001 to FY2016 awards that names a joint venture's members read as
    one row per member, and every contract's rows numbered again from 1."""
    by_key: dict[tuple[str, str], list[SupplierRow]] = defaultdict(list)
    for row in rows:
        names = (joint_venture_members(row.name) if row.source in SPLIT_SOURCES and row.name and
                 not row.individual_consultant else [row.name])
        by_key[(row.source, row.source_key)] += [replace(row, name=name) for name in names]
    return [replace(row, position=number) for members in by_key.values()
            for number, row in enumerate(sorted(members, key=lambda row: row.position), 1)]


def _matched(row: SupplierRow) -> bool:
    """Whether a row with no STEP supplier ID is matched by name: a firm, named."""
    return row.step_supplier_id is None and not row.individual_consultant and bool(row.name)


def _sides(rows: list[SupplierRow]) -> dict[str, SideOfPair]:
    """Each supplier with an ID, by its ID, and each row matched by name, by its own key."""
    by_id: dict[str, list[SupplierRow]] = defaultdict(list)
    sides = {}
    for row in rows:
        if row.step_supplier_id and not row.individual_consultant and row.name:
            by_id[row.step_supplier_id].append(row)
        elif _matched(row):
            sides[row.key] = SideOfPair(row.key, row.name, row.country, (row.project_id,) if row.project_id else (),
                                        (row.contract,) if row.contract else (), row.public_from, False)
    for supplier_id, held in by_id.items():
        # The awards since FY2020 name the supplier first; an ID known only from notices takes a notice's name.
        named = sorted(held, key=lambda row: (row.source != "awards", row.public_from, row.source_key, row.position))
        country = next((row.country for row in named if row.country), None)
        sides[supplier_id] = SideOfPair(
            supplier_id, named[0].name, country, tuple(sorted({row.project_id for row in held if row.project_id})),
            tuple(sorted({row.contract for row in held if row.contract})), min(row.public_from for row in held), True)
    return sides


def _records(sides: dict[str, SideOfPair], rows: list[SupplierRow]) -> list[Record]:
    group = {row.key: row.source_key for row in rows if _matched(row)}
    return [Record(side.key, side.name, side.country, side.projects, side.has_id, group.get(side.key))
            for side in sides.values()]


# ── Routing ──────────────────────────────────────────────────────────────

def _question(pair: Pair, sides: dict[str, SideOfPair]) -> Question:
    def side(key):
        found = sides[key]
        return Side(found.name, found.country, found.projects, found.contracts)
    return Question(pair_id(pair.left, pair.right), side(pair.left), side(pair.right))


def _judged(questions: list[Question], judge: Judge | None,
            past: dict[str, PastJudgement]) -> dict[str, tuple[str, Judgement]]:
    """Each question's judgement and the judge that gave it: kept from an earlier run when the judge and
    both names are the same, or asked now."""
    if judge is None:
        return {}
    found, ask = {}, []
    for question in questions:
        earlier = past.get(question.pair_id)
        if earlier and (earlier.model, earlier.left_name, earlier.right_name) == (
                judge.name, question.left.name, question.right.name):
            found[question.pair_id] = (earlier.model, earlier.judgement)
        else:
            ask.append(question)
    for question, judgement in zip(ask, judge.decide(ask) if ask else [], strict=True):
        found[question.pair_id] = (judge.name, judgement)
    return found


def _routed(pair: Pair, sides: dict[str, SideOfPair], routing: Routing,
            judged: dict[str, tuple[str, Judgement]], decisions: dict[str, Decision]) -> RoutedPair:
    key = pair_id(pair.left, pair.right)
    routed = RoutedPair(key, sides[pair.left], sides[pair.right], pair.probability, pair.weight, pair.name_level,
                        pair.projects_level, routing.route(pair.probability), "no_merge", "threshold")
    if routed.route == "auto_merge":
        routed = replace(routed, outcome="merge")
    elif routed.route == "model":
        model, judgement = judged.get(key, (None, None))
        if judgement is None:
            routed = replace(routed, route="person", outcome="waiting", decided_by=None, review_reason="no_model")
        elif judgement.decision != "unsure" and judgement.confidence >= routing.model_confidence_min:
            routed = replace(routed, outcome=judgement.decision, decided_by="model", model=model,
                             model_judgement=judgement)
        else:
            routed = replace(routed, route="person", outcome="waiting", decided_by=None, review_reason="model_unsure",
                             model=model, model_judgement=judgement)
    return _by_a_person(routed, decisions.get(key))


def _by_a_person(routed: RoutedPair, decision: Decision | None) -> RoutedPair:
    if decision is None:
        return routed
    return replace(routed, outcome=decision.decision, decided_by="person", reviewer=decision.reviewer,
                   decision_reason=decision.reason)


class _Groups:
    """Union-find over side keys."""

    def __init__(self):
        self.parent: dict[str, str] = {}

    def find(self, key: str) -> str:
        self.parent.setdefault(key, key)
        while self.parent[key] != key:
            self.parent[key] = self.parent[self.parent[key]]
            key = self.parent[key]
        return key

    def join(self, one: str, other: str) -> None:
        self.parent[self.find(one)] = self.find(other)


def _groups(pairs: list[RoutedPair]) -> _Groups:
    groups = _Groups()
    for pair in pairs:
        groups.find(pair.left.key)
        groups.find(pair.right.key)
        if pair.outcome == "merge":
            groups.join(pair.left.key, pair.right.key)
    return groups


def _apart_from_two_ids(pairs: list[RoutedPair]) -> list[RoutedPair]:
    """Send to a person every merge that would join two STEP supplier IDs by name. First the merges the
    thresholds or the model made in such a group; then, if a person's merges still join two IDs, those."""
    for movable in ({"threshold", "model"}, {"threshold", "model", "person"}):
        groups = _groups(pairs)
        ids: dict[str, set[str]] = defaultdict(set)
        for pair in pairs:
            for side in (pair.left, pair.right):
                if side.has_id:
                    ids[groups.find(side.key)].add(side.key)
        crowded = {root for root, held in ids.items() if len(held) > 1}
        pairs = [replace(pair, route="person", outcome="waiting", decided_by=None,
                         review_reason="two_step_supplier_ids", reviewer=None, decision_reason=None)
                 if pair.outcome == "merge" and pair.decided_by in movable and groups.find(pair.left.key) in crowded
                 else pair for pair in pairs]
    return pairs


# ── Each row's supplier ──────────────────────────────────────────────────

def _name_only_key(row: SupplierRow) -> str:
    """The key of a supplier known only by name: N- and a hash of its earliest row, so it stays the same
    while that row does."""
    return "N-" + hashlib.sha256(f"{row.source}|{row.source_key}|{row.position}".encode()).hexdigest()[:12]


def _resolved(rows: list[SupplierRow], pairs: list[RoutedPair]) -> list[Resolved]:
    groups = _groups(pairs)
    by_root: dict[str, list[str]] = defaultdict(list)
    keys = {row.key for row in rows if _matched(row)} | {side.key for pair in pairs for side in (pair.left, pair.right)}
    for key in keys:
        by_root[groups.find(key)].append(key)
    has_id = {side.key for pair in pairs for side in (pair.left, pair.right) if side.has_id}
    earliest = {}
    for row in sorted((row for row in rows if _matched(row)),
                      key=lambda row: (row.public_from, row.source, row.source_key, row.position)):
        earliest.setdefault(groups.find(row.key), row)

    resolved = []
    for row in rows:
        if row.source not in RESOLVED_SOURCES:
            continue
        if row.individual_consultant:
            resolved.append(Resolved(row, row.step_supplier_id, None, "individual_consultant"))
        elif row.step_supplier_id:
            resolved.append(Resolved(row, row.step_supplier_id, None, "step_supplier_id"))
        elif not row.name:
            resolved.append(Resolved(row, None, None, "no_name"))
        else:
            root = groups.find(row.key)
            members = by_root[root]
            with_id = [key for key in members if key in has_id]
            supplier = with_id[0] if with_id else _name_only_key(earliest[root])
            resolved.append(Resolved(row, supplier, None, "name" if len(members) > 1 else "unmatched"))
    return _with_joint_ventures(resolved)


def _with_joint_ventures(resolved: list[Resolved]) -> list[Resolved]:
    """Link each member of a contract's joint venture to it: JV- and its members' supplier IDs, sorted as
    strata.gold.contract sorts them."""
    by_contract: dict[tuple[str, str], set[str]] = defaultdict(set)
    for item in resolved:
        if item.supplier_id:
            by_contract[(item.row.source, item.row.source_key)].add(item.supplier_id)
    ventures = {key: "JV-" + "-".join(sorted(ids)) for key, ids in by_contract.items() if len(ids) > 1}
    return [replace(item, joint_venture_id=ventures.get((item.row.source, item.row.source_key)))
            if item.supplier_id else item for item in resolved]


def resolve(rows: list[SupplierRow], routing: Routing, model: SupplierMatching, judge: Judge | None,
            decisions: dict[str, Decision] | None = None,
            past: dict[str, PastJudgement] | None = None) -> Resolution:
    """Every candidate pair with its route and outcome, and every notice bidder and FY2001 to FY2016 row
    with the supplier it resolves to."""
    members = _members(rows)
    sides = _sides(members)
    found = candidate_pairs(_records(sides, members), model, routing.candidate_min)
    questions = [_question(pair, sides) for pair in found if routing.route(pair.probability) == "model"]
    judged = _judged(questions, judge, past or {})
    pairs = _apart_from_two_ids([_routed(pair, sides, routing, judged, decisions or {}) for pair in found])
    return Resolution(pairs, _resolved(members, pairs))


# ── Reading and writing the tables ───────────────────────────────────────

PAIR_COLUMNS = ("run_id", "pair_id", "left_key", "right_key", "left_name", "left_country", "left_contracts",
                "right_name", "right_country", "right_contracts", "match_probability", "match_weight", "name_level",
                "projects_level", "route", "review_reason", "model", "model_decision", "model_confidence",
                "model_reason", "outcome", "decided_by", "reviewer", "decision_reason", "matched_at", "public_from")
RESOLUTION_COLUMNS = ("run_id", "source", "source_key", "position", "contract_id", "project_id", "name", "country",
                      "step_supplier_id", "individual_consultant", "supplier_id", "joint_venture_id", "resolved_on",
                      "public_from")


def _sql(name: str) -> str:
    return (resources.files("strata.knowledge.suppliers") / "sql" / name).read_text()


def _dicts(engine: Engine, name: str) -> list[dict]:
    result = engine.run(_sql(name))
    return [dict(zip(result.columns, row, strict=True)) for row in result.rows]


def read_rows(engine: Engine) -> list[SupplierRow]:
    return [SupplierRow(row["source"], row["source_key"], int(row["position"]), row["contract_id"], row["project_id"],
                        row["name"], row["country"], row["step_supplier_id"], bool(row["individual_consultant"]),
                        row["contract"], row["public_from"]) for row in _dicts(engine, "supplier_rows.sql")]


def read_decisions(engine: Engine) -> dict[str, Decision]:
    return {row["pair_id"]: Decision(row["decision"], row["reviewer"], row["reason"])
            for row in _dicts(engine, "latest_decisions.sql")}


def read_past_judgements(engine: Engine) -> dict[str, PastJudgement]:
    return {row["pair_id"]: PastJudgement(row["model"], row["left_name"], row["right_name"], Judgement(
        row["model_decision"], float(row["model_confidence"]), row["model_reason"]))
            for row in _dicts(engine, "past_judgements.sql")}


def _pair_row(run_id: str, matched_at: dt.datetime, pair: RoutedPair) -> tuple:
    judged = pair.model_judgement
    return (run_id, pair.pair_id, pair.left.key, pair.right.key, pair.left.name, pair.left.country,
            ", ".join(pair.left.contracts) or None, pair.right.name, pair.right.country,
            ", ".join(pair.right.contracts) or None, pair.probability, pair.weight, pair.name_level,
            pair.projects_level, pair.route, pair.review_reason, pair.model, judged.decision if judged else None,
            judged.confidence if judged else None, judged.reason if judged else None, pair.outcome, pair.decided_by,
            pair.reviewer, pair.decision_reason, matched_at, pair.public_from)


def _resolution_row(run_id: str, item: Resolved) -> tuple:
    row = item.row
    return (run_id, row.source, row.source_key, row.position, row.contract_id, row.project_id,
            None if row.individual_consultant else row.name, row.country, row.step_supplier_id,
            row.individual_consultant, item.supplier_id, item.joint_venture_id, item.resolved_on, row.public_from)


def run(engine: Engine, run_id: str, judge: Judge | None,
        clock: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.UTC),
        thresholds: Thresholds | None = None, model: SupplierMatching | None = None) -> int:
    """Resolve every supplier row and write this run's pairs and resolution. Returns the rows written."""
    resolution = resolve(read_rows(engine), Routing.from_thresholds(thresholds or load_thresholds()),
                         model or load_supplier_matching(), judge, read_decisions(engine), read_past_judgements(engine))
    matched_at = clock()
    written = engine.insert_rows("strata.ops.supplier_pairs", PAIR_COLUMNS,
                                 [_pair_row(run_id, matched_at, pair) for pair in resolution.pairs])
    written += engine.insert_rows("strata.silver.supplier_resolution", RESOLUTION_COLUMNS,
                                  [_resolution_row(run_id, item) for item in resolution.rows])
    engine.run("DELETE FROM strata.ops.supplier_pairs WHERE run_id <> :run_id", {"run_id": run_id})
    engine.run("DELETE FROM strata.silver.supplier_resolution WHERE run_id <> :run_id", {"run_id": run_id})
    return written
