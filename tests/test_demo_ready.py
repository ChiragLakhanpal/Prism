"""The demo-ready command (ticket 48): one command makes Strata ready for a review.

It restarts the app and waits for its health route, warms the SQL warehouse and Genie through ask_genie, asks
one smoke question through the answer contract (ticket 33's runner), rechecks P156634's signals on the fixture
and on the workspace and prints what changed, checks Home's seeds and window, and lists the workspace before and
after. With --fresh-workspace it lists, from code alone, every resource a fresh workspace needs.

The fake workspace stands in for Databricks: its app starts and stops, its health route answers, and its SQL
warehouse is the fixture database or a copy of it, so the real tools, the real /api/ask stream and the real
verifier run. Expected values come from tests/ground_truth/values.toml, never from the tools' own arithmetic. The
live run is a workspace step (docs/workspace-catchup.md).

Each scenario runs the whole command once or twice in a module fixture, and several tests read what it printed,
so the file stays within a few seconds.
"""

import contextlib
import dataclasses
import datetime as dt
import importlib.util
import io
import re
import shutil
import sys
import tomllib
from pathlib import Path

import pytest
import stand_in_agent

from strata.config import load_slice, load_thresholds
from strata.dbx import Viewer
from strata.evals import benchmark
from strata.lakehouse.engine import DuckDBEngine
from strata.server.engines import duckdb_file
from strata.tools import registry

ROOT = Path(__file__).resolve().parents[1]
TRUTH = {entry["id"]: entry for entry in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
DEMO = load_slice().demo_plan
QUESTIONS = {question["id"]: question for question in benchmark.load()}
ANA = Viewer(email="ana.example@worldbank.org", name="Ana Example", user_id="ana", token="token-for-ana-only")
TODAY = dt.date(2026, 10, 25)
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


class FakeWorkspace:
    """Strata's app, stopped or running, whose health route answers after a number of tries once it runs; the SQL
    warehouse as the fixture database or a copy; the stand-in agent; and the examples' seed command."""

    def __init__(self, live_db, running=False, source=None, health_after=1, healthy=True, agent=None, seeded=(0, ""),
                 listing_error=None):
        app = command().deploy_app
        self.apps = {"strata": {"description": app.DESCRIPTION, "running": running,
                                "source": source or f"/Workspace/Users/ana.example@worldbank.org/{app.FOLDER}",
                                "url": "https://strata-1234.aws.databricksapps.com"}}
        self.calls: list[tuple] = []
        self.health_after, self.healthy, self.tries = health_after, healthy, 0
        self.viewer = dataclasses.replace(ANA, token="not-a-real-key")
        self.engine_for = duckdb_file(live_db)
        self.judge = stand_in_agent.Agrees()
        self.agent = agent
        self.seeded = seeded
        self.listing_error = listing_error

    def app(self, name):
        found = self.apps.get(name)
        return dict(found) if found else None

    def stop_app(self, name):
        self.calls.append(("stop", name))
        self.apps[name]["running"] = False

    def start_app(self, name):
        self.calls.append(("start", name))
        self.apps[name]["running"] = True
        self.tries = 0

    def health(self, url):
        self.calls.append(("health", url))
        self.tries += 1
        if not (self.healthy and self.apps["strata"]["running"] and self.tries >= self.health_after):
            raise RuntimeError("HTTP Error 502: Bad Gateway")
        return {"status": "ok"}

    def agent_for(self, turn):
        if self.agent is None:
            with self.engine_for(self.viewer) as engine:
                self.agent = stand_in_agent.for_question(QUESTIONS[DEMO.smoke_question], engine, self.viewer)
        return self.agent

    def seed(self):
        self.calls.append(("seed",))
        return self.seeded

    def snapshot(self):
        if self.listing_error:
            raise RuntimeError(self.listing_error)
        return {("apps", name): dict(app) for name, app in self.apps.items()}


def setup(fixture_db, **changed):
    clock = changed.pop("clock", Clock())
    options = {"fixture_db": fixture_db, "today": TODAY, "clock": clock, "sleep": clock.sleep,
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

def app_step(workspace, fixture_db, **changed):
    said = []
    outcome = command().app_step(workspace, setup(fixture_db, **changed), said.append)
    return outcome, "\n".join(said)


def test_a_running_app_is_restarted_so_it_runs_24_hours_from_now(fixture_db):
    workspace = FakeWorkspace(fixture_db, running=True)

    outcome, said = app_step(workspace, fixture_db)

    assert outcome.state == "passed", outcome
    assert [call for call in workspace.calls if call[0] != "health"] == [("stop", "strata"), ("start", "strata")]
    assert "I restarted it, so it runs for 24 hours from now." in said


def test_an_app_that_never_answers_its_health_route_fails_after_the_timeout(fixture_db):
    outcome, _ = app_step(FakeWorkspace(fixture_db, healthy=False), fixture_db)

    timeout = load_thresholds().value("demo_ready.health_timeout_seconds")
    assert outcome.state == "failed"
    assert outcome.summary.startswith(f"The app did not answer GET /api/health within {timeout} seconds.")
    assert "502" in outcome.summary


def test_an_app_that_does_not_run_strata_s_code_is_never_started_or_stopped(fixture_db):
    workspace = FakeWorkspace(fixture_db, running=True, source="/Workspace/Users/someone/fairshare-app")

    outcome, _ = app_step(workspace, fixture_db)

    assert outcome.state == "failed"
    assert workspace.calls == []
    assert "/Workspace/Users/someone/fairshare-app" in outcome.summary and "I left it alone" in outcome.summary


def test_when_day_one_test_6_chose_the_container_apps_copy_the_app_step_says_nothing_checks_it_yet(fixture_db):
    outcome, _ = app_step(FakeWorkspace(fixture_db), fixture_db, reviewer_path=lambda: "gap fill")

    assert outcome.state == "failed"
    assert "Container Apps copy" in outcome.summary


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

    completion = long_day(TRUTH["plan-541055-planned-completion"]["value"])
    assert (f"Planned completion passed: KE-NWWDA-541055-CW-RFB passed its planned completion ({completion}) with no "
            "signed contract.") in out
    assert TRUTH["plan-541055-no-signed-contract"]["value"] == "no signed contract"
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


def test_until_ticket_41_merges_home_says_its_seed_command_and_window_are_not_built(two_runs):
    _, out = two_runs["first"]

    assert "The seed command, python -m strata.seed_examples, is not built yet (ticket 41)" in out
    assert "home.window_days in config/thresholds.toml, is not set yet (ticket 41)" in out
    assert "   Home: not built yet." in out


def test_two_runs_in_a_row_both_succeed_and_the_second_leaves_nothing_different(two_runs):
    (first_code, first), (second_code, second) = two_runs["first"], two_runs["second"]

    assert (first_code, second_code) == (0, 0), second
    assert "The app strata runs now, and was stopped before." in first
    assert "6. What changed on the workspace.\n   No changes." in second
    assert first.rstrip().splitlines()[-1] == second.rstrip().splitlines()[-1] == "Strata is ready for the demo."


# ── Demo day after P156634 closed ────────────────────────────────────────

@pytest.fixture(scope="module")
def after_closing(tmp_path_factory, fixture_db):
    """Demo day on November 6, 2026: the workspace lists P156634 as closed, Home's window is seven days, and the
    seed command exists."""
    folder = tmp_path_factory.mktemp("after-closing")
    live = copy_of(fixture_db, folder, "UPDATE strata.gold.project SET status = 'Closed' WHERE project_id = 'P156634'")
    workspace = FakeWorkspace(live, running=True)
    code, out = run(workspace, write_env(folder), fixture_db, today=AFTER_CLOSING, seed_command=lambda: True,
                    thresholds=with_values(home={"window_days": 7}))
    return code, out, workspace


def test_a_closed_p156634_is_the_first_change_the_recheck_prints_and_never_a_failure(after_closing):
    code, out, _ = after_closing
    changed = out.split("What changed since the fixture was recorded:\n")[1].splitlines()

    assert code == 0, out
    assert changed[0].strip() == "P156634 is closed on the workspace, and was active in the fixture."
    closing = long_day(TRUTH["closing-date-p156634"]["value"])
    assert f"In the fixture: Needs a look, with four signals. Its closing date was {closing}." in out
    assert (f"On the workspace: Not checked: the project is closed, and the checks run only on active projects. "
            f"It closed on {closing}.") in out


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
    assert out.rstrip().splitlines()[-1] == ("Strata is not ready for the demo. These steps failed: Genie, the smoke "
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
    commands = ["uv run --script ops/bundle/deploy.py --env-file .env",
                "uv run --script ops/dayone/probe_ai_search.py --env-file .env",
                "uv run --script ops/app/deploy_app.py --env-file .env",
                "uv run --script ops/bundle/check.py job-run --env-file .env",
                "uv run python ops/genie/deploy_space.py --env-file .env",
                *(f"uv run --script ops/agent/sync.py --env-file .env --agent {key}" for key in agents)]
    assert out.startswith("How a fresh workspace reaches the demo state, from code alone. I changed nothing.")
    assert [name for name in expected + commands if name not in out] == []
    assert [out.index(command) for command in commands[:5]] == sorted(out.index(command) for command in commands[:5])


def test_until_ticket_41_merges_the_dry_run_names_the_examples_as_the_one_resource_with_no_deployer():
    code, out = dry_run()

    assert code == 1
    assert "The examples for the reviewing panel: no deployer yet. Ticket 41 adds python -m strata.seed_examples." in out
    assert out.rstrip().splitlines()[-1] == "One resource has no deployer yet, so a fresh workspace still needs it: the examples for the reviewing panel."


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
