"""The demo-ready command (ticket 48): one command makes Prism ready for a review.

It starts a stopped app, restarts a running one only when its last start or deploy is restart_after_hours old
(ticket 77), and waits for its health route, warms the SQL warehouse and Genie through ask_genie, asks one smoke
question through the answer contract (ticket 33's runner), rechecks P156634's signals on the fixture and on the
workspace and prints what changed, checks Home's seeds and window, and lists the workspace before and after. With
--fresh-workspace it lists, from code alone, every resource a fresh workspace needs.

The fake workspace stands in for Databricks: its app starts and stops and reports when it last started or was
deployed, as the Apps API's App object does, its health route answers, and its SQL warehouse is the fixture
database or a copy of it, so the real tools, the real /api/ask stream and the real verifier run. Expected values come from tests/ground_truth/values.toml, never from the tools' own arithmetic. The
live run is a workspace step (docs/workspace-catchup.md).

Each scenario runs the whole command once or twice in a module fixture, and several tests read what it printed,
so the file stays within a few seconds.
"""

import contextlib
import dataclasses
import datetime as dt
import importlib.util
import io
import json
import re
import shutil
import sys
import tomllib
from pathlib import Path

import misread_layout
import pytest
import stand_in_agent

from strata.config import load_slice, load_thresholds
from strata.dbx import Viewer
from strata.evals import benchmark
from strata.lakehouse.engine import DuckDBEngine
from strata.server.engines import duckdb_file
from strata.tools import registry

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ops" / "bundle" / "tests"))
from workspace_fakes import (  # noqa: E402  (the workspace's state, shared with the two deploys' tests)
    FREE_DAILY_LIMIT,
    STATE_METHODS,
    STOPPED_BY_THE_WORKSPACE,
    USUAL_CAUSE,
    WorkspaceStateFake,
)

TRUTH = {entry["id"]: entry for entry in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
DEMO = load_slice().demo_plan
QUESTIONS = {question["id"]: question for question in benchmark.load()}
ANA = Viewer(email="ana.example@worldbank.org", name="Ana Example", user_id="ana", token="token-for-ana-only")
TODAY = dt.date(2026, 10, 25)
NOW = dt.datetime(2026, 10, 25, 8, 0, tzinfo=dt.UTC)  # 08:00 UTC on TODAY, the morning of a demo
EARLIER_THIS_MORNING = NOW - dt.timedelta(hours=3)
URL = "https://strata-1234.aws.databricksapps.com"
AFTER_CLOSING = dt.date(2026, 11, 6)  # the Round 2 date the PM counts on (docs/STATUS.md, decision 4)
NUMBER_WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")  # DESIGN.md 7, rule 12
ENV = {"DATABRICKS_HOST": "https://example.cloud.databricks.com", "DATABRICKS_TOKEN": "not-a-real-key",
       "DATABRICKS_WAREHOUSE_ID": "abc123", "GENIE_SPACE_ID": "space-1",
       "FOUNDRY_PROJECT_ENDPOINT": "https://example.services.ai.azure.com/api/projects/Strata",
       "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com", "AZURE_OPENAI_API_KEY": "not-a-real-key"}


def long_day(day: dt.date) -> str:
    return f"{day:%B} {day.day}, {day.year}"


def dollars(amount) -> str:
    return f"US${float(amount):,.2f}"


def test_the_demo_config_names_a_documents_question_with_its_citations_a_genie_question_and_a_package():
    smoke, genie = QUESTIONS[DEMO.smoke_question], QUESTIONS[DEMO.genie_question]

    assert smoke["kind"] == "documents" and smoke["cites"]
    assert genie["tool"] == "ask_genie"
    assert DEMO.package.startswith(f"KE-{DEMO.agency_short_name}-")


def test_the_demo_package_has_enough_comparables_for_a_past_range(fixture_db):
    """Brief 47 asks the demo config for an NWWDA activity with at least 20 comparables."""
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        found = registry.call("find_comparables", {"step_reference": DEMO.package},
                              registry.Context(engine=engine, viewer=ANA, as_of=dt.date(2026, 10, 22)))

    assert found["coverage"]["matched"] >= load_thresholds().value("past_range.min_comparables")


# ── The fake workspace ───────────────────────────────────────────────────

def command():
    """ops/demo/ready.py, by its path: the ops folders are not a package."""
    if "strata_demo_ready" not in sys.modules:
        spec = importlib.util.spec_from_file_location("strata_demo_ready", ROOT / "ops" / "demo" / "ready.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules["strata_demo_ready"] = module
        spec.loader.exec_module(module)
    return sys.modules["strata_demo_ready"]


class Clock:
    """A clock that moves when the command sleeps, and one second each time it is read."""

    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        self.now += 1
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def live_adapter():
    """ops/demo/demo_live.py, which the command's folder puts on the path."""
    command()
    import demo_live

    return demo_live


def ops_tables() -> list[str]:
    from strata.lakehouse import catalog

    return [definition.full_name for definition in catalog.table_definitions() if definition.schema == "ops"]


class FakeWorkspace(WorkspaceStateFake):
    """Prism's app, stopped or running, with the time of its last start or deploy (None when the Apps API gives
    none; a start sets it to NOW), whose health route answers after a number of tries once it runs; the SQL
    warehouse as the fixture database or a copy; the stand-in agent; the examples' seed command, which may write
    rows; and a listing that holds the app, the strata.ops tables the workspace has, and their row counts, counted
    by the live adapter's own code. An app whose deployment the platform dropped (deployed=False, ticket 109) has no
    source, and its health route never answers until ops/app/deploy_app.py deploys it again (redeploy_app, which
    answers with deploy_answer: the deploy's exit code and what it printed)."""

    def __init__(self, live_db, running=False, started=EARLIER_THIS_MORNING, source=None, health_after=1,
                 healthy=True, agent=None, seeded=(0, ""), listing_error=None, seed_writes=(), missing_tables=(),
                 deployed=True, deploy_answer=(0, ""), **state):
        app = command().deploy_app
        self.folder = f"/Workspace/Users/ana.example@worldbank.org/{app.FOLDER}"
        self.apps = {"strata": {"description": app.DESCRIPTION, "running": running, "started": started,
                                "source": (source or self.folder) if deployed else None, "url": URL,
                                "deployed": deployed}}
        self.deploy_answer = deploy_answer
        self.calls: list[tuple] = []
        self.health_after, self.healthy, self.tries = health_after, healthy, 0
        self.viewer = dataclasses.replace(ANA, token="not-a-real-key")
        self.live_db = live_db
        self.engine_for = duckdb_file(live_db)
        self.judge = stand_in_agent.Agrees()
        self.agent = agent
        self.seeded = seeded
        self.listing_error = listing_error
        self.seed_writes, self.missing_tables = seed_writes, set(missing_tables)
        # Ticket 81: the App's compute and the env file's SQL warehouse (workspace_fakes.py).
        self.hold_state(warehouse_id=ENV["DATABRICKS_WAREHOUSE_ID"], **state)

    def app(self, name):
        found = self.apps.get(name)
        return dict(found) if found else None

    def stop_app(self, name):
        self.calls.append(("stop", name))
        self.apps[name]["running"] = False

    def app_started(self, name):
        self.calls.append(("start", name))
        self.apps[name]["running"] = True
        self.apps[name]["started"] = NOW
        self.tries = 0

    def health(self, url):
        self.calls.append(("health", url))
        self.tries += 1
        app = self.apps["strata"]
        if not (self.healthy and app["running"] and app["deployed"] and self.tries >= self.health_after):
            raise RuntimeError("HTTP Error 502: Bad Gateway")
        return {"status": "ok"}

    def redeploy_app(self, name):
        self.calls.append(("redeploy", name))
        code, _ = self.deploy_answer
        if code in (0, 1):  # exit 1: the deployment was still IN_PROGRESS when the deploy's wait ended
            self.apps[name].update(deployed=True, source=self.folder, started=NOW)
            self.tries = 0
        return self.deploy_answer

    def agent_for(self, turn):
        if self.agent is None:
            with self.engine_for(self.viewer) as engine:
                self.agent = stand_in_agent.for_question(QUESTIONS[DEMO.smoke_question], engine, self.viewer)
        return self.agent

    def seed(self):
        self.calls.append(("seed",))
        if self.seed_writes:
            with DuckDBEngine.open(self.live_db) as engine:
                for statement in self.seed_writes:
                    engine.run(statement)
        return self.seeded

    def snapshot(self):
        if self.listing_error:
            raise RuntimeError(self.listing_error)
        found = {("apps", name): dict(app) for name, app in self.apps.items()}
        found |= {("tables", name): [] for name in ops_tables() if name not in self.missing_tables}
        with self.engine_for(self.viewer) as engine:
            return found | live_adapter().ops_rows(engine, found)


def setup(fixture_db, **changed):
    clock = changed.pop("clock", Clock())
    options = {"fixture_db": fixture_db, "today": TODAY, "now": lambda: NOW, "clock": clock, "sleep": clock.sleep,
               "reviewer_path": lambda: "default", "seed_command": lambda: False, **changed}
    return command().Setup(**options)


def run(workspace, env_file, fixture_db, *argv, **changed) -> tuple[int, str]:
    """One run of the command against the fake workspace: its exit code and what it printed."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = command().main(["--env-file", str(env_file), *argv], workspace=workspace,
                              setup=setup(fixture_db, **changed))
    return code, out.getvalue()


def write_env(folder: Path) -> Path:
    path = folder / ".env"
    path.write_text("".join(f"{key}={value}\n" for key, value in ENV.items()))
    return path


def copy_of(fixture_db, folder: Path, *statements: str) -> Path:
    """The fixture database copied, with statements run on the copy only, so a test can make the workspace's records
    or the recorded fixture differ."""
    path = folder / "copy.duckdb"
    shutil.copyfile(fixture_db, path)
    with DuckDBEngine.open(path) as engine:
        for statement in statements:
            engine.run(statement)
    return path


def with_values(**sections) -> object:
    defaults = load_thresholds()
    values = {**defaults.values, **{name: {**defaults.values.get(name, {}), **table} for name, table in sections.items()}}
    return dataclasses.replace(defaults, values=values)


# ── 1. The app ───────────────────────────────────────────────────────────

# The app step's limits, pinned so each sentence below is known: 12 hours and 900 seconds are the values ticket 77
# sets in config/thresholds.toml, which a test below holds the file to.
APP_LIMITS = {"restart_after_hours": 12, "health_timeout_seconds": 900, "health_poll_seconds": 5}


def app_step(workspace, fixture_db, **changed):
    said = []
    changed.setdefault("thresholds", with_values(demo_ready=APP_LIMITS))
    outcome = command().app_step(workspace, setup(fixture_db, **changed), said.append)
    return outcome, "\n".join(said)


def test_a_running_app_started_less_than_restart_after_hours_ago_is_left_running_and_the_output_says_why(fixture_db):
    workspace = FakeWorkspace(fixture_db, running=True, started=NOW - dt.timedelta(hours=11, minutes=59), health_after=3)

    outcome, said = app_step(workspace, fixture_db)

    assert outcome.state == "passed", outcome
    assert [call for call in workspace.calls if call[0] != "health"] == []
    assert workspace.calls.count(("health", URL)) == 3
    assert ("   It was running, and it last started or was deployed at 20:01 UTC on October 24, 2026, 11 hours and "
            "59 minutes ago. That is less than the 12 hours in [demo_ready] restart_after_hours, so I left it "
            "running. The platform stops it at 20:01 UTC on October 25, 2026, 24 hours after that start.") in said
    assert "GET /api/health answered after " in said and "within the 900-second limit" in said
    assert outcome.summary.startswith("I left it running, since it last started 11 hours and 59 minutes ago. It "
                                      "answered its health route after ")


def test_a_running_app_that_last_started_restart_after_hours_ago_or_earlier_is_restarted_and_the_output_says_why(fixture_db):
    workspace = FakeWorkspace(fixture_db, running=True, started=NOW - dt.timedelta(hours=12), health_after=3)

    outcome, said = app_step(workspace, fixture_db)

    assert outcome.state == "passed", outcome
    assert [call for call in workspace.calls if call[0] != "health"] == [("stop", "strata"), ("start", "strata")]
    assert workspace.calls[2:] == [("health", URL)] * 3
    assert ("   It was running, and it last started or was deployed at 20:00 UTC on October 24, 2026, 12 hours ago. "
            "That is at least the 12 hours in [demo_ready] restart_after_hours, so I restarted it, and it runs for 24 "
            "hours from now.") in said
    assert "within the 900-second limit" in said
    assert outcome.summary.startswith("I restarted it, since it last started 12 hours ago. It answered its health "
                                      "route after ")


def test_a_running_app_whose_last_start_the_apps_api_does_not_give_is_restarted(fixture_db):
    workspace = FakeWorkspace(fixture_db, running=True, started=None)

    outcome, said = app_step(workspace, fixture_db)

    assert outcome.state == "passed", outcome
    assert [call for call in workspace.calls if call[0] != "health"] == [("stop", "strata"), ("start", "strata")]
    assert ("   It was running, and the Apps API gave no time for its last start or deploy, so I restarted it, and it "
            "runs for 24 hours from now.") in said


def test_a_stopped_app_is_started_whenever_it_last_ran_and_the_output_says_why(fixture_db):
    workspace = FakeWorkspace(fixture_db, running=False, started=NOW - dt.timedelta(hours=1), health_after=3)

    outcome, said = app_step(workspace, fixture_db)

    assert outcome.state == "passed", outcome
    assert [call for call in workspace.calls if call[0] != "health"] == [("start", "strata")]
    assert workspace.calls[1:] == [("health", URL)] * 3
    assert "   The app strata was stopped, so I started it. It runs for 24 hours from now." in said
    assert "within the 900-second limit" in said
    assert outcome.summary.startswith("I started it, since it was stopped. It answered its health route after ")


@pytest.mark.parametrize(("running", "started", "done"), [
    (True, EARLIER_THIS_MORNING, "I left it running, since it last started three hours ago."),
    (True, NOW - dt.timedelta(hours=20), "I restarted it, since it last started 20 hours ago."),
    (False, NOW - dt.timedelta(hours=30), "I started it, since it was stopped."),
], ids=["left running", "restarted", "started"])
def test_in_each_case_the_step_waits_for_health_up_to_the_timeout_and_its_message_names_the_last_answer(
        fixture_db, running, started, done):
    clock = Clock()
    workspace = FakeWorkspace(fixture_db, running=running, started=started, healthy=False)

    outcome, _ = app_step(workspace, fixture_db, clock=clock)

    assert outcome.state == "failed"
    assert outcome.summary == (f"{done} Then it did not answer GET /api/health within 900 seconds. The last try said: "
                               "HTTP Error 502: Bad Gateway")
    # It asked every five seconds until 900 seconds had passed, and no longer.
    assert 900 <= clock.now <= 900 + 2 * APP_LIMITS["health_poll_seconds"]
    assert workspace.calls.count(("health", URL)) >= 900 // (APP_LIMITS["health_poll_seconds"] + 2)


def test_an_app_that_does_not_run_strata_s_code_is_never_started_or_stopped(fixture_db):
    workspace = FakeWorkspace(fixture_db, running=True, source="/Workspace/Users/someone/fairshare-app")

    outcome, _ = app_step(workspace, fixture_db)

    assert outcome.state == "failed"
    assert workspace.calls == []
    assert "/Workspace/Users/someone/fairshare-app" in outcome.summary and "I left it alone" in outcome.summary


@pytest.mark.parametrize("choice", ["default", "gap fill"])
def test_the_app_step_checks_the_databricks_app_whatever_day_one_test_6_chose_and_names_the_choice_in_its_sentence(
        fixture_db, choice):
    """Day-one test 6 was recorded as partly passed on October 27, 2026, and dayone.path_kind(6) still answers "gap
    fill", though no ticket built a Container Apps copy. The workspace holds the Databricks App, so the step checks it
    either way, and only its sentence names the choice (ticket 109)."""
    outcome, said = app_step(FakeWorkspace(fixture_db), fixture_db, reviewer_path=lambda: choice)

    assert outcome.state == "passed", outcome
    assert outcome.summary.startswith("I started it, since it was stopped. It answered its health route after ")
    named = "Day-one test 6 chose a Container Apps copy for reviewers, which no command checks, so I checked the " \
            "Databricks App, which the workspace holds."
    assert (named in outcome.summary) == (choice == "gap fill")
    assert "Container Apps" not in said


def test_a_stopped_app_whose_deployment_the_platform_dropped_is_started_and_deployed_again(fixture_db):
    """On October 27, 2026 (11:35 and 18:48 UTC) the platform stopped the App's compute "due to workspace or account
    status" and dropped its deployment, so a start alone runs nothing. The step starts the compute, deploys Prism
    again with ops/app/deploy_app.py --keep-secrets, then waits for the health route (ticket 109)."""
    workspace = FakeWorkspace(fixture_db, running=False, deployed=False, health_after=2)

    outcome, said = app_step(workspace, fixture_db)

    assert outcome.state == "passed", outcome
    assert workspace.calls == [("start", "strata"), ("redeploy", "strata"), ("health", URL), ("health", URL)]
    assert ("   The app strata's compute was stopped and it had no active deployment, so a start alone would run "
            "nothing. I started its compute and deployed Prism again with ops/app/deploy_app.py --keep-secrets.") in said
    assert outcome.summary.startswith("I deployed Prism again, since the platform had dropped its deployment. It "
                                      "answered its health route after ")


@pytest.mark.parametrize(("answer", "state", "health"), [
    ((1, "Step 5. The deployment 01f1 is still IN_PROGRESS.\nI stop here."), "passed", True),
    ((2, "I changed nothing, because the SQL warehouse abc123 is STOPPED."), "failed", False),
], ids=["deployment still in progress", "deploy refused"])
def test_a_redeploy_that_exits_with_an_error_is_said_and_only_one_that_made_a_deployment_waits_for_health(
        fixture_db, answer, state, health):
    """The deploy exits 1 when its deployment is still IN_PROGRESS as its wait ends, which a cold start can outlast
    (October 27, 2026, 12:31 UTC), so the health route decides. It exits 2 when it changed nothing."""
    workspace = FakeWorkspace(fixture_db, running=False, deployed=False, deploy_answer=answer)

    outcome, said = app_step(workspace, fixture_db)

    code, printed = answer
    assert outcome.state == state, outcome
    assert (("health", URL) in workspace.calls) == health
    last = printed.splitlines()[-1]
    if health:
        assert (f"   The deploy exited {code}, and its last line said: {last} I waited for the health route anyway, "
                "since a deployment after a cold start can outlast the deploy's own wait.") in said
    else:
        assert outcome.summary == (f"I started its compute, and the deploy exited {code} without deploying, saying: "
                                   f"{last}")


def test_a_health_route_that_answers_another_status_is_said_in_words(fixture_db):
    class Starting(FakeWorkspace):
        def health(self, url):
            return {"status": "starting"}

    outcome, _ = app_step(Starting(fixture_db), fixture_db)

    assert outcome.state == "failed"
    assert outcome.summary.endswith("The last try said: it answered with the status starting.")


def test_the_thresholds_file_restarts_an_app_after_12_hours_and_waits_longer_than_the_measured_restart():
    """Ticket 77: on October 26, 2026 a restart of the App took about eight and a half minutes, from its last 200 at
    09:39:47 UTC to the next at 09:48:12 (docs/workspace-catchup.md, ticket 48, step 2), against a 300-second wait.
    Each value's comment names where it comes from."""
    section = (ROOT / "config" / "thresholds.toml").read_text().split("[demo_ready]\n")[1].split("\n[")[0]
    comments, above = {}, []
    for line in section.splitlines():
        if line.startswith("#"):
            above.append(line.lstrip("# "))
        elif "=" in line:
            comments[line.split("=")[0].strip()] = " ".join(above)
            above = []
    limits = load_thresholds()
    measured = (dt.datetime(2026, 10, 26, 9, 48, 12) - dt.datetime(2026, 10, 26, 9, 39, 47)).total_seconds()

    assert limits.value("demo_ready.restart_after_hours") == 12
    assert limits.value("demo_ready.health_timeout_seconds") == 900 > measured
    assert "eight and a half minutes" in comments["health_timeout_seconds"]
    assert "docs/workspace-catchup.md" in comments["health_timeout_seconds"]
    assert "24 hours after each start or deploy" in comments["restart_after_hours"]


# ── 2. Genie ─────────────────────────────────────────────────────────────

class InItsOwnWords:
    """The live agent's second run of the smoke question on October 27, 2026 (ticket 109): it found ICR paragraph 54
    and wrote the sentence in its own words, with the passage's words only in quote.text. Asked to rewrite, it sends
    the same answer again."""

    name, version = "strata-orchestrator", "9"
    claim = {"sentence": "In P130164, 108 of 328 works contracts went through rebidding because the estimates were "
                         "not based on market rates.", "kind": "quote",
             "evidence_ids": ["strata.gold.passage:31525018/v1/54"], "numbers": ["108", "328"], "dates": [],
             "quote": {"text": "108 of 328 cases had to go through rebidding",
                       "passage_id": "strata.gold.passage:31525018/v1/54"}}

    def respond(self, items, previous_response_id):
        if previous_response_id is None:
            return stand_in_agent.reply([{"type": "function_call", "call_id": "call-1", "name": "search_passages",
                                          "arguments": json.dumps(QUESTIONS[DEMO.smoke_question]["arguments"])}], 1)
        return stand_in_agent.reply(stand_in_agent.said([self.claim]), 2)


def test_a_failed_smoke_question_prints_each_removed_sentence_with_its_quote_and_reasons(fixture_db):
    """The codes alone did not say what went wrong on October 27, 2026: the step prints each sentence the verifier
    removed, the words it quoted and from where, and each reason with what it is about (ticket 109)."""
    said = []

    outcome = command().smoke_step(FakeWorkspace(fixture_db, agent=InItsOwnWords()), setup(fixture_db), said.append)

    assert outcome.state == "failed"
    assert "The verifier removed one sentence (quote_not_in_sentence)." in outcome.summary
    assert ('      Removed: "In P130164, 108 of 328 works contracts went through rebidding because the estimates were '
            'not based on market rates." It quoted "108 of 328 cases had to go through rebidding" from '
            'strata.gold.passage:31525018/v1/54. Reasons: quote_not_in_sentence (strata.gold.passage:31525018/v1/54), '
            'number_not_in_records (108), number_not_in_records (328).') in said


def test_genie_s_abstention_is_said_as_a_sentence_with_its_reason_not_as_a_dict(fixture_db):
    said = []
    outcome = command().genie_step(FakeWorkspace(fixture_db), setup(fixture_db, today=dt.date(2020, 1, 1)), said.append)

    assert outcome.state == "failed"
    assert re.fullmatch(r"Genie gave no answer to the warm-up question \(as_of_before_records\): its records run "
                        r"through \w+ \d+, \d{4}\.", outcome.summary), outcome.summary


# ── Two runs in a row ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def two_runs(tmp_path_factory, fixture_db):
    """The command run twice against a stopped app, as on a morning after the app stopped."""
    env_file = write_env(tmp_path_factory.mktemp("two-runs"))
    workspace = FakeWorkspace(fixture_db, running=False, health_after=3)
    first = run(workspace, env_file, fixture_db)
    first_calls = list(workspace.calls)
    second = run(workspace, env_file, fixture_db)
    return {"first": first, "second": second, "first_calls": first_calls}


def test_a_stopped_app_is_started_and_answers_its_health_route_within_the_timeout(two_runs):
    code, out = two_runs["first"]

    assert code == 0, out
    assert [call for call in two_runs["first_calls"] if call[0] != "health"] == [("start", "strata")]
    assert "The app strata was stopped, so I started it." in out
    assert f"within the {load_thresholds().value('demo_ready.health_timeout_seconds')}-second limit" in out


def test_after_the_warm_up_the_next_genie_call_answers_within_the_stated_threshold(two_runs):
    _, out = two_runs["first"]

    limit = load_thresholds().value("demo_ready.genie_first_call_seconds")
    assert f"I asked again, as the first question in the demo will: it answered after 1 second, within the {limit}-second limit." in out
    assert "   Genie: passed." in out


def test_the_smoke_question_returns_a_cited_answer_that_passed_the_six_checks(two_runs):
    _, out = two_runs["first"]
    cited = ", ".join(QUESTIONS[DEMO.smoke_question]["cites"])

    assert "The verifier ran all six checks and kept one sentence, removing none." in out
    assert f"The answer cites {cited}, as the benchmark file expects." in out
    assert "   The smoke question: passed." in out


def test_the_recheck_prints_each_signal_s_current_state_with_the_recorded_values(two_runs):
    _, out = two_runs["first"]

    # Ticket 132: KE-NWWDA-541055-CW-RFB's planned completion passed with no signed contract in the plan, but the
    # contract awards say it was signed (values.toml, award-541055-signed), so the plan check names it moved on since
    # the plan and the completion check finds nothing.
    assert TRUTH["plan-541055-no-signed-contract"]["value"] == "no signed contract"
    assert "Planned completion passed: ran and found nothing." in out
    assert re.search(r"KE-NWWDA-229129-CW-RFB was signed at about \d+ times its estimate: "
                     + re.escape(f"{dollars(TRUTH['plan-229129-actual']['value'])} against "
                                 f"{dollars(TRUTH['plan-229129-estimated']['value'])}."), out)
    assert f"first appears in the plan of {long_day(TRUTH['plan-cwsb-567630-first-listed']['value'])}." in out
    moves = [key for key in TRUTH if re.fullmatch(r"closing-p156634-move-\d", key)]
    first_shown = re.search(r"end_of_period=\d+-\w+-(\d{4})", TRUTH["closing-p156634-move-1"]["at"]).group(1)
    assert (f"Closing date moved: The closing date has moved {NUMBER_WORDS[len(moves)]} times since {first_shown}."
            in out)
    for check in ("Restructured", "ISR rating lowered", "Slow disbursement"):
        assert f"{check}: ran and found nothing." in out
    assert f"It closes on {long_day(TRUTH['closing-date-p156634']['value'])}." in out
    assert "Nothing changed since the fixture was recorded." in out
    assert "   The P156634 recheck: passed. Needs a look on the workspace, with no changes since the fixture." in out


def test_every_check_project_signals_runs_is_named_as_web_src_copy_ts_names_it():
    """The recheck names each check as the Following screen does (brief 37, section 9.5), and a check added to
    project_signals fails here before it reaches a demo morning."""
    from strata.tools import project_signals

    copy = (ROOT / "web" / "src" / "copy.ts").read_text()
    named = {key: re.search(rf'\b{key}: \{{\s*name: "([^"]+)"', copy).group(1) for key in project_signals.CHECKS}

    assert command().CHECK_NAMES == named


def test_a_check_the_command_has_no_name_for_is_named_by_its_key_and_does_not_stop_the_recheck():
    signals = {"rows": [], "checks": [{"key": "new_check", "ran": True, "missing": None}], "project": {},
               "status": "no_signals", "counts": {"signals": 0}}

    assert command().check_states(signals) == ["new_check: ran and found nothing."]
    assert command().changes({"signals": signals, "awards": {}}, {"signals": signals, "awards": {}}, "P156634") == []


def test_the_output_uses_the_glossary_s_signal_words_and_none_it_avoids(two_runs, after_closing, failing_run):
    """GLOSSARY.md's Signal entry and brief 37: Needs a look, Watch, No signals and Not checked; never flag, alert,
    watchlist or at risk, nor DESIGN.md section 7's other words."""
    said = " ".join([two_runs["first"][1], after_closing[1], failing_run[1]]).lower()

    assert [word for word in ("flag", "alert", "watchlist", "at risk", "risk score", "approve", "clearance",
                              "slippage", "the bank", "—", "!") if word in said] == []


def test_the_recheck_reports_the_plan_and_the_award_rows_disagreeing_as_known_and_decides_nothing(two_runs):
    _, out = two_runs["first"]

    signed = long_day(TRUTH["award-541055-signed"]["value"])
    assert (f"KE-NWWDA-541055-CW-RFB: the plan of {long_day(DEMO.plan_date)} shows no signed contract, and the awards "
            f"dataset shows contract 1903781, signed on {signed} for {dollars(TRUTH['award-541055-amount']['value'])}. "
            "The fixture holds it too.") in out
    assert f"KE-NWWDA-541062-CW-RFQ: the plan of {long_day(DEMO.plan_date)} shows no signed contract" in out
    assert f"signed on {long_day(TRUTH['award-541062-signed']['value'])}" in out


def read_as_the_workspace_did(fixture_db, folder: Path, misread_characters: int) -> Path:
    """A copy of the fixture with the demo plan's table pages parsed again by a layout parser that misreads the
    showcase reference, as ai_parse_document did on October 26, 2026, then its plan rows written with the plan
    reader's check against the plan's text set to misread_characters, and strata.gold.package synced, as the nightly
    job's parse_and_embed task does (ticket 78). The plan reader reads every plan version, as the fixture build does
    (ingestion.plan_versions = "all"), so the fixture's other versions stay as they were."""
    from strata.fixture import recorded as fmt
    from strata.lakehouse import gold, plans
    from strata.reader.documents import RecordedDocuments

    path, manifest = copy_of(fixture_db, folder), fmt.load_manifest()
    with DuckDBEngine.open(path) as engine:
        engine.run("DELETE FROM strata.bronze.layout_pages WHERE document_id IN (SELECT document_id FROM "
                   "strata.silver.plan_versions WHERE implementing_agency = :agency AND plan_date = :plan_date)",
                   {"agency": DEMO.implementing_agency, "plan_date": DEMO.plan_date})
        plans.run(engine, RecordedDocuments(manifest), misread_layout.MisreadsTheShowcaseReference(manifest),
                  DEMO.project_id, thresholds=with_values(ingestion={"reference_misread_characters": misread_characters,
                                                                     "plan_versions": plans.EVERY_VERSION}))
        gold.sync(engine, "package")
    return path


@pytest.mark.parametrize("misread_characters", [0, load_thresholds().value("ingestion.reference_misread_characters")],
                         ids=["as-on-october-26-with-the-check-off", "with-the-check-config-sets"])
def test_the_recheck_names_the_showcase_package_as_the_fixture_does_when_the_workspace_misread_its_reference(
        fixture_db, tmp_path, misread_characters):
    """Ticket 78. On October 26, 2026 the workspace's layout parser read KE-NWWDA-229129-CW-RFB on the October 9, 2026
    plan as -RFQ, and the recheck reported the signal on both names. With the plan reader's check against the plan's
    text off, this reproduces that report; with it on, the recheck finds nothing changed."""
    workspace = FakeWorkspace(read_as_the_workspace_did(fixture_db, tmp_path, misread_characters))
    said = []
    command().recheck_step(workspace, setup(fixture_db), said.append, {})
    out = "\n".join(said)

    misread, written = misread_layout.ON_THE_WORKSPACE, misread_layout.SHOWCASE["value"]
    reported = (f"Signed far above its estimate: {misread} fired on the workspace and not in the fixture." in out,
                f"Signed far above its estimate: {written} no longer fired on the workspace." in out)
    assert reported == ((True, True) if misread_characters == 0 else (False, False)), out
    assert (misread in out, "Nothing changed since the fixture was recorded." in out) == (
        (True, False) if misread_characters == 0 else (False, True)), out


def test_without_the_seed_command_home_says_so_and_checks_the_demo_plan_against_the_seven_day_window(two_runs):
    """The runs pin the seed command off. Home's window is the thresholds file's seven days (ticket 41), ending on the
    fixture's data-through date, October 23, 2026, so the plan disclosed on October 9 falls outside it."""
    _, out = two_runs["first"]

    assert "The seed command, python -m strata.seed_examples, is not built yet (ticket 41)" in out
    assert (f"The plan of {long_day(DEMO.plan_date)}, disclosed on {long_day(DEMO.plan_date)}, falls outside Home's "
            "window, the seven days from October 17, 2026 to October 23, 2026.") in out
    assert "   Home: not built yet." in out


def test_two_runs_in_a_row_both_succeed_and_the_second_leaves_nothing_different(two_runs):
    (first_code, first), (second_code, second) = two_runs["first"], two_runs["second"]

    assert (first_code, second_code) == (0, 0), second
    assert "6. What changed on the workspace.\n   The app strata runs now, and was stopped before.\n   Genie" in first
    assert "less than a minute ago. That is less than the 12 hours in [demo_ready] restart_after_hours, so I left it running." in second
    assert "6. What changed on the workspace.\n   No changes." in second
    assert first.rstrip().splitlines()[-1] == second.rstrip().splitlines()[-1] == "Prism is ready for the demo."


# ── The workspace's state, read first (ticket 81) ───────────────────────

# The Apps API's answer to a start on a stopped workspace was not recorded, so the warehouses' answer stands in for it.
@pytest.mark.parametrize(("stopped", "said"), [
    ({"compute": STOPPED_BY_THE_WORKSPACE, "app_answer": FREE_DAILY_LIMIT},
     "I changed nothing, because the app strata's compute is STOPPED with the message \"App compute was stopped due to "
     f"workspace or account status.\" and would not start when I asked, saying \"{FREE_DAILY_LIMIT}\", {USUAL_CAUSE}"),
    ({"warehouse": "STOPPED", "warehouse_answer": FREE_DAILY_LIMIT},
     "I changed nothing, because the SQL warehouse abc123 is STOPPED and would not start when I asked, saying "
     f"\"{FREE_DAILY_LIMIT}\", {USUAL_CAUSE}")], ids=["app compute", "warehouse"])
def test_a_workspace_that_stopped_the_app_or_the_warehouse_stops_the_command_first_with_one_sentence(
        tmp_path, fixture_db, stopped, said):
    workspace = FakeWorkspace(fixture_db, **stopped)

    code, out = run(workspace, write_env(tmp_path), fixture_db)

    assert code == 2
    assert out.splitlines() == [said]
    assert workspace.calls == []


def test_an_app_the_workspace_stopped_with_its_deployment_dropped_is_no_refusal_and_step_1_deploys_it_again(
        tmp_path, fixture_db):
    """What apps get strata showed at 12:12 UTC on October 27, 2026 on the paid workspace: the compute STOPPED "due to
    workspace or account status" and no active deployment (docs/workspace-catchup.md). Step 1 cures that, so the
    command does not stop first (ticket 109)."""
    workspace = FakeWorkspace(fixture_db, running=False, deployed=False, compute=STOPPED_BY_THE_WORKSPACE)

    code, out = run(workspace, write_env(tmp_path), fixture_db)

    assert code == 0, out
    assert [call for call in workspace.calls if call[0] in ("start", "stop", "redeploy")] == [
        ("start", "strata"), ("redeploy", "strata")]
    assert "6. What changed on the workspace.\n   The app strata runs now, and was stopped before.\n   The app strata " \
           "was deployed again, after the platform dropped its deployment.\n" in out


def test_a_warehouse_that_stopped_when_it_sat_idle_starts_first_and_the_command_prints_what_it_printed_before(
        two_runs, tmp_path, fixture_db):
    workspace = FakeWorkspace(fixture_db, running=False, health_after=3, warehouse="STOPPED")

    found = run(workspace, write_env(tmp_path), fixture_db)

    assert workspace.warehouse_starts == 1
    assert found == two_runs["first"]


def test_a_workspace_state_the_command_cannot_read_is_said_once_and_the_steps_still_run(two_runs, tmp_path, fixture_db):
    workspace = FakeWorkspace(fixture_db, running=False, health_after=3,
                              warehouse_answer=RuntimeError("HTTP Error 503: Service Unavailable"))

    code, out = run(workspace, write_env(tmp_path), fixture_db)

    assert code == 0
    assert out == ("I could not read the app's compute or the SQL warehouse's state first: RuntimeError: HTTP Error 503: "
                   f"Service Unavailable\n{two_runs['first'][1]}")


def test_the_live_adapter_reads_the_app_s_compute_and_the_warehouse_as_the_fake_does():
    assert STATE_METHODS <= set(vars(live_adapter().LiveDemo))


def test_a_restart_is_listed_as_a_change_with_the_time_the_app_started_again():
    app = {"description": "Prism", "running": True, "source": "/Workspace/strata-app", "url": URL}
    before = {("apps", "strata"): {**app, "started": NOW - dt.timedelta(hours=20)}}
    after = {("apps", "strata"): {**app, "started": NOW}}

    assert command().app_changes(before, after) == ["The app strata started again at 08:00 UTC on October 25, 2026."]


# ── Demo day after P156634 closed ────────────────────────────────────────

@pytest.fixture(scope="module")
def after_closing(tmp_path_factory, fixture_db):
    """Demo day on November 6, 2026: the workspace lists P156634 as closed, Home's window is seven days, the seed
    command exists and writes a follow for the panel, and the workspace is one bundle deploy behind the repo, so it
    lacks strata.ops.viewer_settings."""
    folder = tmp_path_factory.mktemp("after-closing")
    live = copy_of(fixture_db, folder, "UPDATE strata.gold.project SET status = 'Closed' WHERE project_id = 'P156634'")
    workspace = FakeWorkspace(live, running=True, missing_tables=("strata.ops.viewer_settings",), seed_writes=(
        "INSERT INTO strata.ops.follows VALUES ('panel', 'P156634', true, TIMESTAMP '2026-11-06 08:00:00', "
        "DATE '2026-11-06')",))
    code, out = run(workspace, write_env(folder), fixture_db, today=AFTER_CLOSING, seed_command=lambda: True,
                    thresholds=with_values(home={"window_days": 7}))
    return code, out, workspace


def test_a_closed_p156634_is_the_first_change_the_recheck_prints_and_never_a_failure(after_closing):
    code, out, _ = after_closing
    changed = out.split("What changed since the fixture was recorded:\n")[1].splitlines()

    assert code == 0, out
    assert changed[0].strip() == "P156634 is closed on the workspace, and was active in the fixture."
    closing = long_day(TRUTH["closing-date-p156634"]["value"])
    assert f"In the fixture: Needs a look, with three signals. Its closing date was {closing}." in out
    assert (f"On the workspace: Not checked: the project is closed, and the checks run only on active projects. "
            f"It closed on {closing}.") in out
    assert "   The P156634 recheck: passed. Not checked on the workspace, with " in out


def test_a_row_the_run_wrote_to_strata_ops_is_listed_as_a_change(after_closing):
    """The listing counts the rows of strata.ops before and after, so a step that wrote a row cannot pass as 'No
    changes.'"""
    code, out, _ = after_closing

    assert code == 0, out
    assert "6. What changed on the workspace.\n   The rows of strata.ops.follows changed.\n" in out


def test_a_strata_ops_table_the_workspace_lacks_is_named_and_the_other_tables_are_still_counted(after_closing):
    code, out, _ = after_closing

    assert code == 0, out
    assert ("The workspace lacks one table the repo defines in strata.ops, strata.ops.viewer_settings, so I counted "
            "the rows of the others. Deploy the bundle to make it: uv run --script ops/bundle/deploy.py --env-file "
            ".env") in out
    assert out.count("The workspace lacks one table") == 1
    assert "   The workspace listing: passed. One change, listed above." in out


def test_home_s_seeds_run_and_the_october_9_plan_falls_outside_a_seven_day_window(after_closing):
    _, out, workspace = after_closing

    assert ("seed",) in workspace.calls
    assert "I ran python -m strata.seed_examples for the reviewing panel's group." in out
    assert (f"The plan of {long_day(DEMO.plan_date)}, disclosed on {long_day(DEMO.plan_date)}, falls outside Home's "
            "window, the seven days from") in out
    assert "so it will not list this plan's activities." in out


# ── A run with failures ──────────────────────────────────────────────────

@pytest.fixture(scope="module")
def failing_run(tmp_path_factory, fixture_db):
    """Genie answers slower than the limit, the agent cites a passage no tool returned, the workspace cannot be
    listed, and the fixture was recorded before the awards dataset showed KE-NWWDA-541055-CW-RFB's contract."""
    folder = tmp_path_factory.mktemp("failing")
    recorded = copy_of(fixture_db, folder, "DELETE FROM strata.gold.contract WHERE contract_id = '1903781'")
    smoke = QUESTIONS[DEMO.smoke_question]
    agent = stand_in_agent.StandIn("search_passages", smoke["arguments"], cite_ids=["strata.gold.passage:99999999/v1/1"])
    workspace = FakeWorkspace(fixture_db, agent=agent, listing_error="PERMISSION_DENIED on strata.ops")
    return run(workspace, write_env(folder), recorded, thresholds=with_values(demo_ready={"genie_first_call_seconds": 0.5}))


def test_a_failed_smoke_question_and_a_slow_genie_exit_with_an_error_naming_each_failed_step(failing_run):
    code, out = failing_run

    assert code == 1
    assert out.rstrip().splitlines()[-1] == ("Prism is not ready for the demo. These steps failed: Genie, the smoke "
                                             "question and the workspace listing.")
    assert "I could not list the workspace: RuntimeError: PERMISSION_DENIED on strata.ops" in out
    assert "The next Genie call took 1 second, longer than the 0.5-second limit" in out
    assert f"Its kept sentences do not cite {QUESTIONS[DEMO.smoke_question]['cites'][0]}." in out
    assert "The verifier removed one sentence (id_not_returned)." in out


def test_a_package_signed_since_the_fixture_was_recorded_is_printed_as_a_change(failing_run):
    _, out = failing_run

    signed = long_day(TRUTH["award-541055-signed"]["value"])
    assert (f"The awards dataset on the workspace shows contract 1903781 for KE-NWWDA-541055-CW-RFB, signed on "
            f"{signed}, and the fixture does not.") in out


# ── The fresh-workspace dry run ──────────────────────────────────────────

def dry_run(**changed) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = command().fresh_workspace.show(print, **changed) if changed else command().main(["--fresh-workspace"])
    return code, out.getvalue()


def test_the_dry_run_lists_every_resource_from_code_alone_with_the_command_that_makes_it():
    """Each name comes from the file that defines it, read here on its own: the bundle's jobs, the app and the AI
    Search endpoint in ops/dayone/dayone.toml, the index in config/models.toml, the space in config/genie.toml and
    the agents in config/agents.toml."""
    import yaml

    code, out = dry_run()

    jobs = [job["name"] for path in sorted((ROOT / "bundle").glob("*.yml"))
            for job in ((yaml.safe_load(path.read_text()) or {}).get("resources") or {}).get("jobs", {}).values()]
    names = tomllib.loads((ROOT / "ops" / "dayone" / "dayone.toml").read_text())["names"]
    agents = tomllib.loads((ROOT / "config" / "agents.toml").read_text())["agents"]
    expected = [*jobs, "The catalog strata", f"{names['app']} (", "/Workspace/Users/<you>/strata-app",
                names["ai_search_endpoint"], tomllib.loads((ROOT / "config" / "models.toml").read_text())["search"]["index"],
                tomllib.loads((ROOT / "config" / "genie.toml").read_text())["space"]["title"],
                *(agent["name"] for agent in agents.values())]
    # The order that works: the Genie space before the app, because the space deploy saves Prism's space id in the
    # env file and the app deploy writes that id into app.yaml (ops/genie/deploy_space.py, ops/app/deploy_app.py).
    commands = ["uv run --script ops/bundle/deploy.py --env-file .env",
                "uv run --script ops/dayone/probe_ai_search.py --env-file .env",
                "uv run python ops/genie/deploy_space.py --env-file .env",
                "uv run --script ops/app/deploy_app.py --env-file .env",
                "uv run --script ops/bundle/check.py job-run --env-file .env",
                *(f"uv run --script ops/agent/sync.py --env-file .env --agent {key}" for key in agents)]
    assert out.startswith("How a fresh workspace reaches the demo state, from code alone. I changed nothing.")
    assert [name for name in expected + commands if name not in out] == []
    assert [out.index(command) for command in commands[:5]] == sorted(out.index(command) for command in commands[:5])


def test_the_dry_run_names_the_seed_command_and_the_examples_it_sets_up():
    """Ticket 41's seed command gives its plan (strata.seed_examples.plan), so every resource deploys from code."""
    code, out = dry_run()

    assert code == 0
    assert "uv run python -m strata.seed_examples --env-file .env" in out
    assert "follows on P156634 and P130164" in out and "with no risk owner set" in out
    assert out.rstrip().splitlines()[-1] == "Every resource above deploys from code, with no manual step."


def test_once_the_seed_command_has_a_plan_every_resource_deploys_from_code():
    code, out = dry_run(seeds=[("The example", "follows on P156634")])

    assert code == 0
    assert "uv run python -m strata.seed_examples --env-file .env" in out and "follows on P156634" in out
    assert out.rstrip().splitlines()[-1] == "Every resource above deploys from code, with no manual step."


# ── The README ───────────────────────────────────────────────────────────

def test_the_readme_documents_the_command_its_dry_run_and_the_last_line_it_prints_when_it_passes(two_runs):
    section = (ROOT / "README.md").read_text().split("## Before a demo\n")[1].split("\n## ")[0]
    _, out = two_runs["first"]
    _, dry = dry_run()

    ready_line = next(line.split(": ", 1)[1] for line in dry.splitlines() if "Then make it ready" in line)
    assert f"    {ready_line}\n" in section
    assert "    uv run python ops/demo/ready.py --fresh-workspace\n" in section
    assert f"`{out.rstrip().splitlines()[-1]}`" in section
    assert "`No changes.`" in section
    # When it restarts the app (ticket 77): only a running app whose last start or deploy is restart_after_hours old.
    first_step = section.split("\n1. ")[1].split("\n2. ")[0]
    assert "`demo_ready.restart_after_hours`" in first_step and "`demo_ready.health_timeout_seconds`" in first_step
    assert "leaves it running" in first_step


# ── The live adapter ─────────────────────────────────────────────────────

def test_the_live_adapter_takes_the_app_s_last_start_or_deploy_from_its_active_deployment_s_times():
    """The Apps API's App object names no start time. Its active deployment has a create_time (a deploy makes a new
    one) and an update_time, as ISO 8601 strings; a start runs that deployment again (the SDK's apps.start). The
    later of the two is the last start or deploy, in UTC, and an app with no active deployment has none."""
    from types import SimpleNamespace

    def app(**times):
        return SimpleNamespace(active_deployment=SimpleNamespace(**{"create_time": None, "update_time": None, **times}))

    last_start = live_adapter().last_start

    assert last_start(app(create_time="2026-10-26T10:25:31Z", update_time="2026-10-26T10:33:02.481Z")) == \
        dt.datetime(2026, 10, 26, 10, 33, 2, 481000, tzinfo=dt.UTC)
    assert last_start(app(create_time="2026-10-26T10:25:31Z")) == dt.datetime(2026, 10, 26, 10, 25, 31, tzinfo=dt.UTC)
    assert last_start(app(create_time="2026-10-26T12:25:31+02:00")) == dt.datetime(2026, 10, 26, 10, 25, 31, tzinfo=dt.UTC)
    assert last_start(app()) is None
    assert last_start(SimpleNamespace(active_deployment=None)) is None


def test_the_live_adapter_says_an_app_is_deployed_while_it_has_an_active_or_a_pending_deployment_and_redeploys_it_from_the_repo():
    """On October 27, 2026 apps get showed no active deployment after the platform's stop, and a deploy whose wait
    ended left its deployment IN_PROGRESS, which the Apps API holds as the pending one (ticket 109). The redeploy is
    ops/app/deploy_app.py with --keep-secrets, from the checkout the command runs in, with the env file it was given."""
    from types import SimpleNamespace

    adapter = live_adapter()
    deployed = adapter.deployed
    some = SimpleNamespace(deployment_id="01f1")

    assert deployed(SimpleNamespace(active_deployment=some, pending_deployment=None)) is True
    assert deployed(SimpleNamespace(active_deployment=None, pending_deployment=some)) is True
    assert deployed(SimpleNamespace(active_deployment=None, pending_deployment=None)) is False
    assert adapter.redeploy_command(Path("/repo/.env")) == [
        "uv", "run", "--script", "ops/app/deploy_app.py", "--env-file", "/repo/.env", "--keep-secrets"]
    assert {"app", "redeploy_app", "health"} <= set(vars(FakeWorkspace)) & set(vars(adapter.LiveDemo))
    assert "start_app" in vars(adapter.LiveDemo)


# ── The live listing ─────────────────────────────────────────────────────

def test_the_live_listing_counts_the_rows_of_every_strata_ops_table_in_one_statement(fixture_db):
    """The workspace listing before and after holds each strata.ops table's row count, so a run that wrote a row
    shows up as a change. Its one statement runs on DuckDB as it does on the warehouse."""
    from strata.lakehouse import catalog

    command()
    import demo_live

    tables = [definition.full_name for definition in catalog.table_definitions() if definition.schema == "ops"]
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        counted = engine.run(demo_live.row_counts_sql(tables))

    assert list(counted.columns) == [name.split(".")[-1] for name in tables]
    assert len(counted.rows) == 1 and all(isinstance(count, int) for count in counted.rows[0])


# ── The env file ─────────────────────────────────────────────────────────

def test_without_an_env_file_the_command_stops_with_one_sentence_before_it_reaches_the_workspace(tmp_path, fixture_db):
    workspace = FakeWorkspace(fixture_db)

    code, out = run(workspace, tmp_path / ".env", fixture_db)

    assert code == 2
    assert workspace.calls == []
    assert out.startswith(f"There is no env file at {tmp_path / '.env'}.")
