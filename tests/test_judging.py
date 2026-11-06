"""The judging tool (ticket 32), at seam 3: two query judges grade the passages pooled for each query written from an
award notice, each on their own and in an order of their own, and Prism records both judges' grades and their
agreement. The fixture's three queries are in evals/retrieval_queries.toml; Mei and Tomas are the two judges
(tests/fixtures/roles.toml).

The agreement is worked out by hand: on query 2's 25 pooled passages, by passage id, Mei grades the first 10
"Answers it", the next 5 "Partly" and the last 10 "Not relevant". Tomas grades the same, except two of Mei's
"Answers it" as "Partly" and three of her "Not relevant" as "Partly". They agree on 20 of 25 (0.8). By chance they
would agree on (10 x 8 + 5 x 10 + 10 x 7) / 625 = 0.32, so Cohen's kappa is (0.8 - 0.32) / (1 - 0.32) = 0.71.
"""

import pytest

from retrieval_scenario import ANA, MEI, TOMAS, Loop
from strata.knowledge.retrieval import labels

QUERY = "nq-water-works-readiness"


@pytest.fixture
def loop(fixture_db, tmp_path):
    found = Loop(fixture_db, tmp_path)
    yield found
    found.close()


def grades_for(passages: list[str], judge: str) -> dict[str, str]:
    ordered = sorted(passages)
    mei = {passage: "answers" if i < 10 else "partly" if i < 15 else "not_relevant" for i, passage in enumerate(ordered)}
    if judge == "mei":
        return mei
    tomas = dict(mei)
    for passage in ordered[:2] + ordered[15:18]:
        tomas[passage] = "partly"
    return tomas


def grade_all(loop, who, judge: str, passages: list[str]):
    for passage, grade in grades_for(passages, judge).items():
        response = loop.request("PUT", f"/api/judging/queries/{QUERY}/passages/{passage}", who, {"grade": grade})
        assert response.status_code == 200, response.text


def test_the_lessons_frame_shows_each_reviewer_page_only_to_its_role(loop):
    from retrieval_scenario import DANIEL, PRIYA

    tabs = {name: loop.request("GET", "/api/lessons/me", who).json()
            for name, who in (("ana", ANA), ("mei", MEI), ("daniel", DANIEL), ("priya", PRIYA))}

    assert tabs["ana"]["tabs"] == ["library"]
    assert (tabs["mei"]["tabs"], tabs["mei"]["queries_left"]) == (["library", "judging"], 3)
    assert (tabs["daniel"]["tabs"], tabs["daniel"]["reports_waiting"]) == (["library", "reports"], 0)
    # Priya reviews lessons and passages.
    assert tabs["priya"]["tabs"] == ["library", "review", "reports"]


def test_two_judges_grade_a_query_alone_and_strata_records_their_agreement(loop):
    start = loop.request("GET", "/api/judging/queries", MEI).json()
    assert (start["total"], start["mine_done"], start["counts"]["to_judge"]) == (3, 0, 3)
    assert start["agreement"] == {"agree": 0, "pairs": 0, "both_done": 0, "kappa": None, "withheld": True, "min_pairs": 20}

    mine = loop.request("GET", f"/api/judging/queries/{QUERY}", MEI).json()
    theirs = loop.request("GET", f"/api/judging/queries/{QUERY}", TOMAS).json()
    passages = [found["passage_id"] for found in mine["passages"]]
    assert len(passages) == mine["pool"] == 25
    # Each judge sees the same pool in an order of their own, with no rank, score or setup.
    assert sorted(passages) == sorted(found["passage_id"] for found in theirs["passages"])
    assert passages != [found["passage_id"] for found in theirs["passages"]]
    assert not {"rank", "score"} & set(mine["passages"][0]["passage"])
    assert all(found["other_grade"] is None for found in mine["passages"])

    grade_all(loop, MEI, "mei", passages)
    halfway = loop.request("GET", f"/api/judging/queries/{QUERY}", MEI).json()
    # Mei has finished, Tomas has not: her grades can still change, and his stay hidden from her.
    assert (halfway["my_state"], halfway["other_state"], halfway["locked"]) == ("finished", "not_started", False)
    grade_all(loop, TOMAS, "tomas", passages)

    done = loop.request("GET", f"/api/judging/queries/{QUERY}", MEI).json()
    assert (done["locked"], done["agree"]) == (True, 20)
    assert sum(1 for found in done["passages"] if found["other_grade"] != found["my_grade"]) == 5
    listing = loop.request("GET", "/api/judging/queries", MEI, params={"show": "finished_by_both"}).json()
    assert listing["agreement"] == {"agree": 20, "pairs": 25, "both_done": 1, "kappa": 0.71, "withheld": False,
                                    "min_pairs": 20}
    assert [query["query_id"] for query in listing["queries"]] == [QUERY]
    rows = loop.rows(f"SELECT DISTINCT judge_email FROM strata.ops.retrieval_grades WHERE query_id = '{QUERY}'")
    assert sorted(row["judge_email"] for row in rows) == ["mei.tanaka@worldbank.example", "tomas.rivera@worldbank.example"]

    locked = loop.request("PUT", f"/api/judging/queries/{QUERY}/passages/{passages[0]}", MEI, {"grade": "partly"})
    assert (locked.status_code, locked.json()["code"]) == (409, "locked")
    assert loop.request("GET", "/api/judging/queries", ANA).json()["code"] == "not_a_judge"

    # The finished query joins the labeled set: each passage at the lower of the two grades, when at least "Partly".
    loop.weekly()
    judged = [label for label in labels.latest(loop.database.cursor()) if label.query_set == "notice_queries"]
    assert {label.query_id for label in judged} == {QUERY} and len(judged) == 15
    assert {label.origin for label in judged} == {"judged"}
    # The weekly run records the two judges' agreement as it was that day.
    [agreement] = loop.rows("SELECT judge_a, judge_b, both_done, pairs, agree, kappa FROM strata.ops.retrieval_agreement")
    assert agreement == {"judge_a": "mei.tanaka@worldbank.example", "judge_b": "tomas.rivera@worldbank.example",
                         "both_done": 1, "pairs": 25, "agree": 20, "kappa": 0.71}


def test_a_query_keeps_its_two_judges_once_one_grades_it_when_another_judge_joins(loop, tmp_path):
    """The fixture's queries were loaded before the roles file named any judges, so each takes its pair from the
    roster. Once a judge grades one, its pair is written down: a third judge joining later changes no earlier pair,
    so no one loses a half-graded query."""
    from retrieval_scenario import ROLES, ROOT
    from strata.config import load_roles
    from strata.dbx import Viewer
    from strata.knowledge.retrieval.judging import Judging

    passage = loop.request("GET", f"/api/judging/queries/{QUERY}", MEI).json()["passages"][0]["passage_id"]
    assert loop.request("PUT", f"/api/judging/queries/{QUERY}/passages/{passage}", MEI, {"grade": "partly"}).status_code == 200
    before = Judging(ROLES).desk(loop.database.cursor()).queries[QUERY].judges

    joined = tmp_path / "roles.toml"
    joined.write_text((ROOT / "tests" / "fixtures" / "roles.toml").read_text() + '\n[[people]]\n'
                      'email = "ines.costa@worldbank.example"\nname = "Ines Costa"\ngroups = ["query_judge"]\n'
                      'regions = []\nprojects = []\n')
    three = Judging(load_roles(joined), now=loop.now, thresholds=loop.thresholds)
    desk = three.desk(loop.database.cursor())

    assert sorted(before) == ["mei.tanaka@worldbank.example", "tomas.rivera@worldbank.example"]
    assert desk.queries[QUERY].judges == before
    mine = three.query(loop.database.cursor(), Viewer(email="mei.tanaka@worldbank.example", token="not-a-real-token"), QUERY)
    assert next(found for found in mine["passages"] if found["passage_id"] == passage)["my_grade"] == "partly"
    # A query nobody has graded takes its pair from the roster as it is now.
    assert "ines.costa@worldbank.example" in desk.queries["nq-sanitation-equipment"].judges



def granted_to_the_app(monkeypatch) -> set[str]:
    """The strata.ops tables ops/app/deploy_app.py grants the app's own service principal MODIFY on."""
    import importlib.util
    import sys

    from retrieval_scenario import ROOT

    monkeypatch.setattr(sys, "path", list(sys.path))
    spec = importlib.util.spec_from_file_location("deploy_app_grants", ROOT / "ops" / "app" / "deploy_app.py")
    deploy_app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(deploy_app)
    found = set()
    for grant in deploy_app.grants("6f1c2d3e-4b5a-4c6d-8e7f-90a1b2c3d4e5"):
        if grant.startswith("GRANT SELECT, MODIFY ON TABLE "):
            found.add(grant.split()[5])
    return found


def test_a_judges_first_grade_writes_only_tables_the_deploy_lets_the_app_write(loop, monkeypatch):
    """On the workspace the app writes a grade as its own service principal, which can write only the tables
    ops/app/deploy_app.py grants it (RETRIEVAL_TABLES). A query loaded before the roles file named judges takes its
    pair from the roster, so its first grade writes that pair down too: both tables must be granted. DuckDB has no
    grants, so this test is what catches the next table the app writes without one."""
    from strata.lakehouse.engine import DuckDBEngine

    written: list[str] = []
    insert_rows = DuckDBEngine.insert_rows

    def recording(self, table, columns, rows, *args, **kwargs):
        written.append(table)
        return insert_rows(self, table, columns, rows, *args, **kwargs)

    passage = loop.request("GET", f"/api/judging/queries/{QUERY}", MEI).json()["passages"][0]["passage_id"]
    monkeypatch.setattr(DuckDBEngine, "insert_rows", recording)
    response = loop.request("PUT", f"/api/judging/queries/{QUERY}/passages/{passage}", MEI, {"grade": "partly"})

    assert response.status_code == 200, response.text
    assert set(written) == {"strata.ops.retrieval_queries", "strata.ops.retrieval_grades"}
    assert set(written) <= granted_to_the_app(monkeypatch)


class OnTheWorkspace:
    """The fixture copy's engine, named as the workspace's SparkEngine is, so a search there would need AI Search."""

    name = "databricks"

    def __init__(self, engine):
        self.engine = engine

    def __getattr__(self, attribute):
        return getattr(self.engine, attribute)


def test_on_the_workspace_the_weekly_run_loads_no_queries_without_a_searcher_and_still_builds_and_measures(
        loop, tmp_path, monkeypatch):
    """The weekly job runs as its own identity, which has no AI Search token: it leaves new queries for
    ops/retrieval/evaluate_live.py --load-queries, and still builds the labeled set and writes the loop's measures."""
    from retrieval_scenario import ROLES
    from strata.knowledge import search
    from strata.knowledge.retrieval import judging, weekly

    written = tmp_path / "retrieval_queries.toml"
    written.write_text(judging.QUERIES_FILE.read_text() + '\n[[query]]\nid = "nq-new-on-the-workspace"\n'
                       'notice_id = "OP00044090"\ntext = "How long did the rural road works take to award?"\n')
    monkeypatch.setattr(judging, "QUERIES_FILE", written)

    def no_token(*_args, **_kwargs):
        raise KeyError("AZURE_OPENAI_ENDPOINT")

    assert loop.report(ANA, loop.ask(ANA)).status_code == 200  # a report this week, for the measures to count
    monkeypatch.setattr(search, "searcher_for", no_token)
    count = lambda sql: loop.rows(sql)[0]["n"]  # noqa: E731
    before = {"builds": count("SELECT count(DISTINCT build_id) AS n FROM strata.ops.retrieval_label_builds"),
              "weekly": count("SELECT count(*) AS n FROM strata.ops.retrieval_feedback_weekly"),
              "queries": count("SELECT count(*) AS n FROM strata.ops.retrieval_queries")}

    done = weekly.run(OnTheWorkspace(loop.database.cursor()), now=loop.now, thresholds=loop.thresholds, roles=ROLES,
                      new_id=loop.new_id)

    assert done["queries_loaded"] is None
    assert count("SELECT count(DISTINCT build_id) AS n FROM strata.ops.retrieval_label_builds") == before["builds"] + 1
    assert count("SELECT count(*) AS n FROM strata.ops.retrieval_feedback_weekly") > before["weekly"]
    assert count("SELECT count(*) AS n FROM strata.ops.retrieval_queries") == before["queries"]
