"""The judging tool's queries, pools, grades and agreement (ticket 32; the 32 design brief, sections 4.4 and 9).

The search owner writes queries from award notices in evals/retrieval_queries.toml. load() appends each new one
to strata.ops.retrieval_queries with its two query judges from the roles file, in turn, and pools for it the
best pool_depth passages of each setup in POOL_SETUPS, public before the notice's date, in strata.ops.retrieval_pool.

Each judge grades every pooled passage on their own, in an order of their own: the pool shuffled with a seed made
of the judge and the query, so the two judges' orders differ and stay the same each time. A judge never sees a
passage's rank, score or the setup that found it, a report or a demotion from the evidence drawer, or the other
judge's grades before both finish; the reads below carry none of these. A grade may change until both judges
finish the query; the query's grades then lock, and the server shows each judge the other's grades and how often
they matched. Cohen's kappa over every passage both judges graded on queries they both finished is shown beside
its count from min_pairs passages, and withheld below it (config/thresholds.toml).

Once both judges finish a query, its labels join the labeled set (labels()): each passage at the lower of the two
grades, so a passage counts as relevant only as far as both judges said so.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import random
import tomllib
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from strata.config import Person, Roles, SearchSetup, Thresholds, load_search, load_thresholds
from strata.dbx import Viewer
from strata.knowledge.lessons.review import Refused
from strata.knowledge.retrieval.labels import Label, as_date, rows
from strata.lakehouse.engine import Engine

PAGE = "judging"  # the roles file's name for the Judging pages
QUERIES_FILE = Path(__file__).resolve().parents[4] / "evals" / "retrieval_queries.toml"
GRADES = {"answers": 2, "partly": 1, "not_relevant": 0}
QUERY_COLUMNS = ("query_id", "n", "query_text", "notice_id", "notice_ref", "notice_date", "project_id", "judges",
                 "loaded_at", "public_from")
POOL_COLUMNS = ("query_id", "passage_id", "pooled_at", "public_from")
GRADE_COLUMNS = ("grade_id", "query_id", "passage_id", "judge_email", "judge_name", "grade", "graded_at", "public_from")
DAY = dt.timedelta(days=1)


def pool_setups(current: SearchSetup) -> tuple[SearchSetup, ...]:
    """The setups whose best passages make a query's pool: production's, keyword search alone and vector
    search alone, so the judges grade what any of them would rank, not only what production finds."""
    return (current, SearchSetup(current.keyword_weight or 1.0, 0.0, False, current.rerank_depth, current.header_in_words),
            SearchSetup(0.0, current.vector_weight or 1.0, False, current.rerank_depth, current.header_in_words))


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _iso(value) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    return value.isoformat() if isinstance(value, dt.date) else str(value)[:10]


def order_for(judge: str, query_id: str, passages: list[str]) -> list[str]:
    """A judge's own fixed order of a query's pool."""
    seed = int(hashlib.sha256(f"{judge.lower()}|{query_id}".encode()).hexdigest()[:16], 16)
    ordered = sorted(passages)
    random.Random(seed).shuffle(ordered)
    return ordered


def kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Cohen's kappa for two judges' grades on the same passages, at two decimals, a tool column."""
    if not pairs:
        return None
    total = len(pairs)
    observed = sum(1 for a, b in pairs if a == b) / total
    expected = sum((sum(1 for a, _ in pairs if a == grade) / total) * (sum(1 for _, b in pairs if b == grade) / total)
                   for grade in GRADES)
    if expected >= 1:
        return 1.0 if observed >= 1 else 0.0
    return round((observed - expected) / (1 - expected), 2)


@dataclass
class Query:
    query_id: str
    n: int
    text: str
    notice_id: str
    notice_ref: str | None
    notice_date: dt.date
    project_id: str | None
    judges: list[str]
    pool: list[str] = field(default_factory=list)
    grades: dict[str, dict[str, str]] = field(default_factory=dict)  # judge email, then passage id: the latest grade

    def finished(self, judge: str) -> bool:
        mine = self.grades.get(judge.lower(), {})
        return bool(self.pool) and all(passage in mine for passage in self.pool)

    def state(self, judge: str) -> str:
        mine = self.grades.get(judge.lower(), {})
        return "finished" if self.finished(judge) else "started" if mine else "not_started"

    def other(self, judge: str) -> str | None:
        others = [person for person in self.judges if person.lower() != judge.lower()]
        return others[0] if others else None

    @property
    def locked(self) -> bool:
        return len(self.judges) == 2 and all(self.finished(judge) for judge in self.judges)

    def pairs(self) -> list[tuple[str, str]]:
        first, second = (self.grades.get(judge.lower(), {}) for judge in self.judges)
        return [(first[passage], second[passage]) for passage in self.pool if passage in first and passage in second]


class Desk:
    """Every query, pool and grade, read once for a request."""

    def __init__(self, engine: Engine):
        self.queries: dict[str, Query] = {}
        for row in rows(engine, "queries"):
            self.queries[row["query_id"]] = Query(row["query_id"], int(row["n"]), row["query_text"], row["notice_id"],
                                                  row["notice_ref"], as_date(row["notice_date"]), row["project_id"],
                                                  json.loads(row["judges"]))
        for row in rows(engine, "pool"):
            if row["query_id"] in self.queries:
                self.queries[row["query_id"]].pool.append(row["passage_id"])
        for row in rows(engine, "grades"):
            query = self.queries.get(row["query_id"])
            if query is not None:
                query.grades.setdefault(row["judge_email"].lower(), {})[row["passage_id"]] = row["grade"]

    def ordered(self) -> list[Query]:
        return sorted(self.queries.values(), key=lambda query: query.n)


@dataclass
class Judging:
    roles: Roles
    now: Callable[[], dt.datetime] = _now
    thresholds: Thresholds | None = None

    def __post_init__(self):
        self.thresholds = self.thresholds or load_thresholds()

    def value(self, name: str):
        return self.thresholds.value(f"retrieval.{name}")

    def judges(self) -> list[Person]:
        return [person for person in self.roles.people if PAGE in person.pages(self.roles)]

    def pair(self, number: int) -> list[str]:
        """The two query judges of the query with this number, in turn through the roles file's judges, or none
        while it names fewer than two (a query loaded then gets its judges when the file names them)."""
        judges = [person.email for person in self.judges()]
        if len(judges) < 2:
            return []
        return [judges[(number - 1) % len(judges)], judges[number % len(judges)]]

    def desk(self, engine: Engine) -> Desk:
        desk = Desk(engine)
        for query in desk.queries.values():
            if len(query.judges) < 2:
                query.judges = self.pair(query.n)
        return desk

    def judge(self, viewer: Viewer) -> Person | None:
        person = self.roles.person(viewer.email)
        return person if person is not None and PAGE in person.pages(self.roles) else None

    def _require(self, viewer: Viewer) -> Person:
        person = self.judge(viewer)
        if person is None:
            raise Refused(403, "not_a_judge")
        return person

    # ── Loading the queries and their pools ──────────────────────────────

    def load(self, engine: Engine, writer: Engine, path: Path = QUERIES_FILE, setup: SearchSetup | None = None) -> int:
        """Load each query in the file not yet loaded, with its two judges and its pool. Returns how many."""
        from types import SimpleNamespace

        from strata.estimates.harness import HARNESS
        from strata.knowledge.search import Filters, searcher_for

        written = tomllib.loads(path.read_text()).get("query", [])
        desk = self.desk(engine)
        depth = int(self.value("pool_depth"))
        setups = pool_setups(setup or load_search().setup)
        at, loaded = self.now(), 0
        for number, entry in enumerate(written, 1):
            if entry["id"] in desk.queries:
                continue
            [notice] = rows(engine, "notice", notice_id=entry["notice_id"]) or [None]
            if notice is None:
                continue
            date = as_date(notice["notice_date"])
            pair = self.pair(number)
            pooled: list[str] = []
            for each in setups:
                searcher = searcher_for(SimpleNamespace(engine=engine, viewer=HARNESS), setup=each)
                for hit in searcher.search(entry["text"], Filters(date - DAY, project_id=notice["project_id"]), depth).hits:
                    if hit.passage_id not in pooled:
                        pooled.append(hit.passage_id)
            day = at.astimezone(dt.UTC).date()
            writer.insert_rows("strata.ops.retrieval_queries", QUERY_COLUMNS, [(
                entry["id"], number, entry["text"], entry["notice_id"],
                notice["step_reference"] or notice["bid_reference_no"], date, notice["project_id"], json.dumps(pair),
                at, day)])
            writer.insert_rows("strata.ops.retrieval_pool", POOL_COLUMNS, [(entry["id"], passage, at, day)
                                                                           for passage in pooled])
            loaded += 1
        return loaded

    # ── What the pages read ──────────────────────────────────────────────

    def me(self, engine: Engine, viewer: Viewer) -> dict:
        person = self.judge(viewer)
        if person is None:
            return {"is_judge": False, "queries_left": None}
        desk = self.desk(engine)
        mine = [query for query in desk.ordered() if person.email.lower() in (j.lower() for j in query.judges)]
        return {"is_judge": True, "queries_left": sum(1 for query in mine if not query.finished(person.email))}

    def agreement(self, desk: Desk, person: Person) -> dict:
        both = [query for query in desk.ordered()
                if person.email.lower() in (j.lower() for j in query.judges) and query.locked]
        pairs = [pair for query in both for pair in query.pairs()]
        minimum = int(self.value("min_pairs"))
        return {"agree": sum(1 for a, b in pairs if a == b), "pairs": len(pairs), "both_done": len(both),
                "kappa": kappa(pairs) if len(pairs) >= minimum else None, "withheld": len(pairs) < minimum,
                "min_pairs": minimum}

    def _summary(self, query: Query, person: Person) -> dict:
        mine = query.grades.get(person.email.lower(), {})
        other = query.other(person.email)
        return {"query_id": query.query_id, "n": query.n, "query_text": query.text, "notice_id": query.notice_id,
                "notice_ref": query.notice_ref, "notice_date": _iso(query.notice_date), "query_date": _iso(query.notice_date),
                "pool": len(query.pool), "graded": sum(1 for passage in query.pool if passage in mine),
                "my_state": query.state(person.email), "other_state": query.state(other) if other else "not_started",
                "agree": sum(1 for a, b in query.pairs() if a == b) if query.locked else None,
                "locked": query.locked}

    def queries(self, engine: Engine, viewer: Viewer, show: str = "to_judge", page: int = 1) -> dict:
        person = self._require(viewer)
        desk = self.desk(engine)
        mine = [query for query in desk.ordered() if person.email.lower() in (j.lower() for j in query.judges)]
        filters = {
            "to_judge": [query for query in mine if not query.finished(person.email)],
            "finished_by_you": [query for query in mine if query.finished(person.email)],
            "finished_by_both": [query for query in mine if query.locked],
        }
        show = show if show in filters else "to_judge"
        shown = filters[show]
        size = int(self.value("page_size"))
        pages = max(1, -(-len(shown) // size))
        page = min(max(page, 1), pages)
        on_page = shown[(page - 1) * size: page * size]
        others_done = sum(1 for query in mine if (other := query.other(person.email)) and query.finished(other))
        next_query = next((query.query_id for query in mine if not query.finished(person.email)), None)
        return {"total": len(mine), "mine_done": len(filters["finished_by_you"]), "other_done": others_done,
                "agreement": self.agreement(desk, person), "show": show,
                "counts": {key: len(value) for key, value in filters.items()}, "next_query": next_query,
                "page": page, "pages": pages, "from": (page - 1) * size + 1 if on_page else 0,
                "to": (page - 1) * size + len(on_page), "queries": [self._summary(query, person) for query in on_page]}

    def query(self, engine: Engine, viewer: Viewer, wanted: str) -> dict:
        from strata.tools.search_passages import read_passage

        person = self._require(viewer)
        desk = self.desk(engine)
        query = desk.queries.get(wanted)
        if query is None:
            raise Refused(404, "unknown_query", {"query_id": wanted})
        if person.email.lower() not in (judge.lower() for judge in query.judges):
            raise Refused(403, "not_assigned")
        mine = query.grades.get(person.email.lower(), {})
        other = query.other(person.email)
        theirs = query.grades.get(other.lower(), {}) if other and query.locked else {}
        passages = []
        for passage in order_for(person.email, query.query_id, query.pool):
            found = read_passage(engine, passage, query.notice_date - DAY) or read_passage(engine, passage, self.now().date())
            if found is None:
                continue
            # Never a rank, a score, a setup's name, a report or a demotion (the 32 brief, section 4.4).
            found = {key: value for key, value in found.items() if key not in {"rank", "score"}}
            passages.append({"passage_id": passage, "passage": found, "my_grade": mine.get(passage),
                             "other_grade": theirs.get(passage) if query.locked else None})
        total = len([q for q in desk.ordered() if person.email.lower() in (j.lower() for j in q.judges)])
        mine_all = [q for q in desk.ordered() if person.email.lower() in (j.lower() for j in q.judges)]
        return {**self._summary(query, person), "total": total, "passages": passages,
                "next_query": next((q.query_id for q in mine_all if q.query_id != query.query_id
                                    and not q.finished(person.email)), None)}

    def grade(self, engine: Engine, viewer: Viewer, wanted: str, passage: str, grade: str, writer: Engine) -> dict:
        person = self._require(viewer)
        if grade not in GRADES:
            raise Refused(422, "bad_grade")
        desk = self.desk(engine)
        query = desk.queries.get(wanted)
        if query is None:
            raise Refused(404, "unknown_query", {"query_id": wanted})
        if person.email.lower() not in (judge.lower() for judge in query.judges):
            raise Refused(403, "not_assigned")
        if passage not in query.pool:
            raise Refused(404, "unknown_passage")
        if query.locked:
            raise Refused(409, "locked")
        at = self.now()
        writer.insert_rows("strata.ops.retrieval_grades", GRADE_COLUMNS, [(
            f"grd-{uuid.uuid4().hex[:12]}", query.query_id, passage, person.email, person.name, grade, at,
            at.astimezone(dt.UTC).date())])
        query.grades.setdefault(person.email.lower(), {})[passage] = grade
        return {"saved": True, "graded": sum(1 for p in query.pool if p in query.grades[person.email.lower()]),
                "pool": len(query.pool), "my_state": query.state(person.email), "locked": query.locked}

    # ── The labeled set ──────────────────────────────────────────────────

    def labels(self, engine: Engine) -> tuple[list[Label], int | None]:
        """The judged labels: on each query both judges finished, each passage at the lower of their two grades,
        when that is at least "partly"."""
        found = []
        for query in self.desk(engine).ordered():
            if not query.locked:
                continue
            first, second = (query.grades[judge.lower()] for judge in query.judges)
            for passage in query.pool:
                grade = min(GRADES[first[passage]], GRADES[second[passage]])
                if grade > 0:
                    found.append(Label("notice_queries", query.query_id, query.text, query.notice_date,
                                       query.project_id, passage, grade, "judged"))
        return found, None
