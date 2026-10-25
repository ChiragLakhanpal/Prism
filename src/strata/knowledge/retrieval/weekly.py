"""The weekly retrieval run (ticket 32; bundle/retrieval.yml; docs/PLAN.md section 11: "labels weekly").

Each week it:

1. loads the new queries written from award notices with their pools, where it can search (see run());
2. builds the labeled set again from the documents, the judged notice queries and the reviewed feedback
   (strata.knowledge.retrieval.labels), recording each query set's size;
3. at scale (config/thresholds.toml, retrieval.mode), applies the scale rules to the week's passage reports:
   three agreeing people with no dissent make a silver label, with a 10% audit; no one person supplies more
   than 10% of the batch; reports about one's own project go to a person (strata.knowledge.retrieval.reports);
4. measures the loop: "Wrong passage" reports per 100 sources opened, each week, what each person's reports
   did, and each pair of query judges' agreement.

It reads through one engine and writes through the same one, as the job's own identity. The gate's fixture
build runs it once over the fixture (gates/build_fixture.py), so the fixture database holds the labeled set.

    retrieval_task.py --src <synced src folder>     (on Databricks)
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable

from strata.config import Roles, Thresholds, load_roles, load_thresholds
from strata.knowledge.retrieval.judging import SearcherFor
from strata.knowledge.retrieval.labels import utc_now
from strata.lakehouse.engine import Engine


def run(engine: Engine, now: Callable[[], dt.datetime] = utc_now, thresholds: Thresholds | None = None,
        roles: Roles | None = None, new_id: Callable[[str], str] | None = None, searcher: SearcherFor | None = None) -> dict:
    """One weekly run over engine. Returns what it did, for its log line and the tests. new_id gives the ids of the
    decisions it writes; a test passes one that counts, so its recordings stay the same.

    searcher gives the search that pools a new query's passages. On DuckDB it is the fixture search. On the
    workspace the job's own identity has no AI Search token, so without one it loads no queries (queries_loaded is
    None) and leaves them for ops/retrieval/evaluate_live.py --load-queries; it still triages, builds and measures."""
    from strata.knowledge.retrieval import labels
    from strata.knowledge.retrieval.judging import Judging
    from strata.knowledge.retrieval.reports import PassageReports
    from strata.knowledge.search import FixtureSearch

    if searcher is None and getattr(engine, "name", "") == "duckdb":
        searcher = lambda each_engine, setup: FixtureSearch(each_engine, setup=setup)  # noqa: E731

    thresholds = thresholds or load_thresholds()
    roles = roles or load_roles()
    ids = {"new_id": new_id} if new_id else {}
    judging = Judging(roles, now=now, thresholds=thresholds, **ids)
    reports = PassageReports(roles, now=now, thresholds=thresholds, **ids)
    loaded = judging.load(engine, engine, searcher) if searcher is not None else None
    triaged = reports.triage(engine, engine)
    sizes = labels.build(engine, engine, now(), {"notice_queries": judging.labels(engine),
                                                 "feedback": reports.labels(engine)})
    measured = reports.measure(engine, engine)
    agreement = judging.measure(engine, engine)
    return {"queries_loaded": loaded, "triage": triaged, "labels": sizes, "measures": measured,
            "judge_pairs": agreement}


def main(argv: list[str], engine: Engine) -> int:
    """The job's entry point: argv holds only --src, which retrieval_task.py has already read."""
    done = run(engine)
    if done["queries_loaded"] is None:
        print("I loaded no new queries. Run ops/retrieval/evaluate_live.py --load-queries with the env file.")
    for name, (queries, count, _documents) in done["labels"].items():
        print(f"{name}: {queries} queries, {count} labels.")
    return 0
