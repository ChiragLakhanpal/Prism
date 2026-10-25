"""The weekly retrieval run (ticket 32; bundle/retrieval.yml; docs/PLAN.md section 11: "labels weekly").

Each week it:

1. builds the labeled set again from the documents, the judged notice queries and the reviewed feedback
   (strata.knowledge.retrieval.labels), recording each query set's size;
2. at scale (config/thresholds.toml, retrieval.mode), applies the scale rules to the week's passage reports:
   three agreeing people with no dissent make a silver label, with a 10% audit; no one person supplies more
   than 10% of the batch; reports about one's own project go to a person (strata.knowledge.retrieval.reports);
3. measures the loop: "Wrong passage" reports per 100 sources opened, each week, and what each person's
   reports did.

It reads through one engine and writes through the same one, as the job's own identity. The gate's fixture
build runs it once over the fixture (gates/build_fixture.py), so the fixture database holds the labeled set.

    retrieval_task.py --src <synced src folder>     (on Databricks)
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable

from strata.config import Roles, Thresholds, load_roles, load_thresholds
from strata.lakehouse.engine import Engine


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def run(engine: Engine, now: Callable[[], dt.datetime] = _now, thresholds: Thresholds | None = None,
        roles: Roles | None = None) -> dict:
    """One weekly run over engine. Returns what it did, for its log line and the tests."""
    from strata.knowledge.retrieval import labels
    from strata.knowledge.retrieval.judging import Judging
    from strata.knowledge.retrieval.reports import PassageReports

    thresholds = thresholds or load_thresholds()
    roles = roles or load_roles()
    judging = Judging(roles, now=now, thresholds=thresholds)
    reports = PassageReports(roles, now=now, thresholds=thresholds)
    loaded = judging.load(engine, engine)
    triaged = reports.triage(engine, engine)
    sizes = labels.build(engine, engine, now(), {"notice_queries": judging.labels(engine),
                                                 "feedback": reports.labels(engine)})
    measured = reports.measure(engine, engine)
    return {"queries_loaded": loaded, "triage": triaged, "labels": sizes, "measures": measured}


def main(argv: list[str], engine: Engine) -> int:
    """The job's entry point: argv holds only --src, which retrieval_task.py has already read."""
    done = run(engine)
    for name, (queries, count, _documents) in done["labels"].items():
        print(f"{name}: {queries} queries, {count} labels.")
    return 0
