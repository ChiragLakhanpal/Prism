"""Make Strata ready for a review, and say what changed: ticket 48's demo-ready command.

Run it from the main checkout before every demo (README, "Before a demo"):

    uv run --with databricks-sdk==0.156.0 python ops/demo/ready.py --env-file .env

It needs DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_WAREHOUSE_ID, GENIE_SPACE_ID, FOUNDRY_PROJECT_ENDPOINT,
AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in the env file, the az command line signed in for the Foundry agent,
and the browser sign-in the wizard saved under the Databricks CLI profile that ops/dayone/dayone.toml names, which
the app's health route needs. It lists the workspace first, then, in order:

1. The app. It finds the app ops/dayone/dayone.toml names and leaves it alone unless it runs Strata's code from
   ops/app/deploy_app.py's folder. It starts a stopped app, and restarts a running one, because an app stops 24
   hours after each start or deploy (docs/PLAN.md section 16). Then it asks GET /api/health until the app answers,
   for at most [demo_ready] health_timeout_seconds in config/thresholds.toml. When day-one test 6 chose the Container
   Apps copy for reviewers, it says that no command checks that copy yet.
2. The SQL warehouse and Genie. It asks the ask_genie question that config/slice.toml's [demo_plan] names, through
   the tool registry as the env file's token, which starts a stopped warehouse first (ticket 33). Then it asks again,
   and that call must answer within [demo_ready] genie_first_call_seconds.
3. The smoke question. It asks the documents question [demo_plan] names through /api/ask with the Foundry agent and
   the live tools, as ticket 33's benchmark runner does (strata.evals.answer_benchmark), and passes it only when the
   verifier's own events say so: all six checks ran, no sentence was removed, and the kept sentences cite what the
   benchmark file expects.
4. The P156634 recheck. It runs project_signals for the demo plan's project twice through the tool registry, on the
   fixture database and on the workspace, prints each check's state and every difference between the two runs, and
   lists the activities whose plan row shows no signed contract while the awards dataset holds one. A closed project
   or a plan that disagrees with the awards is reported, never failed: docs/STATUS.md decisions 4 and 7 stay with
   the user. It never records the fixture again and never edits tests/ground_truth/values.toml.
5. Home. It runs ticket 41's seed command for the reviewing panel's group, and says whether the demo plan's
   Disclosed date falls inside home.window_days of the data-through date, or what the briefing shows instead. Until
   ticket 41 merges, it says that neither is built.
6. It lists the workspace again and prints what changed. A second run prints "No changes."

Then it prints one line per step and exits 0 when every step passed, with the last line "Strata is ready for the
demo.", 1 naming each step that failed, and 2 when the env file is not ready.

With --fresh-workspace it changes nothing and needs no env file. It prints, from code alone, every resource a fresh
workspace needs to reach the demo state, in order, with the command that makes each one: each deployer's own plan
(ops/bundle/deploy.py, ops/app/deploy_app.py, strata.agent.sync and the Genie space in config/genie.toml), so this
list cannot drift from them.

    uv run python ops/demo/ready.py --fresh-workspace
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "bundle", REPO / "ops" / "app", HERE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import dayone  # noqa: E402
import deploy as bundle_deploy  # noqa: E402  (ops/bundle/deploy.py)
import deploy_app  # noqa: E402  (ops/app/deploy_app.py)
import fresh_workspace  # noqa: E402  (ops/demo/fresh_workspace.py, the dry run)
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402

from strata.agent.verifier import ALL_CHECKS  # noqa: E402
from strata.config import Thresholds, load_slice, load_thresholds  # noqa: E402
from strata.evals import answer_benchmark, benchmark  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine  # noqa: E402
from strata.server.viewer_sql import data_through  # noqa: E402
from strata.tools import registry  # noqa: E402

FIXTURE_DB = REPO / "data" / "out" / "fixture.duckdb"
NEEDS = ("DATABRICKS_HOST", "DATABRICKS_TOKEN", "DATABRICKS_WAREHOUSE_ID", "GENIE_SPACE_ID",
         "FOUNDRY_PROJECT_ENDPOINT", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY")
SEED_MODULE = fresh_workspace.SEED_MODULE  # ticket 41's seed command (the 41 brief, section 4.5)
AWARDS_SQL = HERE / "sql" / "awards.sql"
PASSED, FAILED, NOT_BUILT = "passed", "failed", "not built yet"

# What the summary and the recheck call each thing, in GLOSSARY.md's and brief 37's words.
STATUS_WORDS = {"needs_a_look": "Needs a look", "watch": "Watch", "no_signals": "No signals",
                "not_checked": "Not checked"}
PROJECT_WORDS = {"active": "active", "closed": "closed", "pipeline": "in the pipeline", "dropped": "dropped"}
CHECK_NAMES = {"completion_passed": "Planned completion passed", "above_estimate": "Signed far above its estimate",
               "late_direct": "Direct selection added late", "closing_moves": "Closing date moved",
               "restructured": "Restructured", "isr_lowered": "ISR rating lowered",
               "disbursement": "Slow disbursement"}
MISSING_WORDS = {"no_plans": "I hold no Procurement Plan for the project",
                 "no_recent_plans": "no Procurement Plan is recent enough",
                 "no_loan_history": "I hold no loan history for the project",
                 "no_isr": "I hold no ISR for the project", "no_loans": "I hold no loan records for the project"}
# What the workspace listing names each kind of thing: the bundle deploy's kinds, then the app and the rows of
# strata.ops, which the smoke question and the Genie warm-up must leave as they were.
LISTED = {**bundle_deploy.KINDS, "apps": "The app", "genie": "The Genie space", "rows": "The rows of"}


@dataclass
class Setup:
    """What the command reads besides the workspace, so the tests can pin each one."""

    fixture_db: Path = FIXTURE_DB
    thresholds: Thresholds | None = None
    today: dt.date | None = None
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    # Which path day-one test 6 chose for reviewers: "default" (the Databricks App) or "gap fill" (a Container Apps
    # copy behind Entra sign-in).
    reviewer_path: Callable[[], str] = field(default=lambda: dayone.path_kind(6))
    seed_command: Callable[[], bool] = field(default=lambda: importlib.util.find_spec(SEED_MODULE) is not None)

    def limits(self) -> Thresholds:
        return self.thresholds or load_thresholds()

    def day(self) -> dt.date:
        return self.today or registry.today()


@dataclass
class Outcome:
    step: str
    state: str
    summary: str


def one_line(error: BaseException | str) -> str:
    return " ".join(str(error).split())[:400] or type(error).__name__


def long_day(value) -> str:
    if value is None:
        return "no date"
    day = value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])
    return dayone.long_date(day)


def dollars(value) -> str:
    return "an amount it does not give" if value is None else f"US${Decimal(str(value)):,.2f}"


def listed(items: list[str]) -> str:
    if len(items) < 3:
        return " and ".join(items)
    return f"{', '.join(items[:-1])} and {items[-1]}"


def seconds(value: float) -> str:
    whole = round(value)
    return "1 second" if whole == 1 else f"{whole} seconds"


def questions() -> dict[str, dict]:
    return {question["id"]: question for question in benchmark.load()}


# ── 1. The app ───────────────────────────────────────────────────────────

def app_step(workspace, setup: Setup, say) -> Outcome:
    step = "the app"
    name = dayone.load_config()["names"]["app"]
    limits = setup.limits()
    timeout = int(limits.value("demo_ready.health_timeout_seconds"))
    poll = float(limits.value("demo_ready.health_poll_seconds"))
    say(f"1. The app {name}.")
    app = workspace.app(name)
    if app is None:
        return Outcome(step, FAILED, f"I found no app named {name}. Deploy Strata first: uv run --script "
                                     "ops/app/deploy_app.py --env-file .env")
    source = (app.get("source") or "").rstrip("/")
    if app.get("description") != deploy_app.DESCRIPTION or not source.endswith(f"/{deploy_app.FOLDER}"):
        return Outcome(step, FAILED, f"The app {name} runs {source or 'nothing yet'}, not Strata's code from the "
                                     f"{deploy_app.FOLDER} folder, so I left it alone. Deploy Strata with "
                                     "ops/app/deploy_app.py, or set names.app in ops/dayone/dayone.toml.")
    if app.get("running"):
        workspace.stop_app(name)
        workspace.start_app(name)
        say("   It was running. I restarted it, so it runs for 24 hours from now.")
    else:
        workspace.start_app(name)
        say(f"   The app {name} was stopped, so I started it.")
    started, last = setup.clock(), "no answer"
    while True:
        try:
            answer = workspace.health(app["url"])
            if answer.get("status") == "ok":
                break
            last = f"it answered {answer}"
        except Exception as error:  # a container still starting answers 502, or the sign-in fails
            last = one_line(error)
        if setup.clock() - started >= timeout:
            return Outcome(step, FAILED, f"The app did not answer GET /api/health within {timeout} seconds. The "
                                         f"last try said: {last}")
        setup.sleep(poll)
    took = seconds(setup.clock() - started)
    say(f"   GET /api/health answered after {took}, within the {timeout}-second limit, at {app['url']}.")
    if setup.reviewer_path() == "gap fill":
        return Outcome(step, FAILED, "Day-one test 6 chose a Container Apps copy of the app for reviewers, and no "
                                     "command deploys or checks that copy yet, so I could not check the address "
                                     "reviewers open.")
    return Outcome(step, PASSED, f"It answered its health route after {took}.")


# ── 2. The SQL warehouse and Genie ───────────────────────────────────────

def genie_step(workspace, setup: Setup, say) -> Outcome:
    step = "Genie"
    limits = setup.limits()
    limit = float(limits.value("demo_ready.genie_first_call_seconds"))
    question = questions()[load_slice().demo_plan.genie_question]["question"]
    say("2. The SQL warehouse and Genie.")
    with workspace.engine_for(workspace.viewer) as engine:
        context = registry.Context(engine=engine, viewer=workspace.viewer, as_of=setup.day(), thresholds=limits)

        def ask() -> tuple[dict, float]:
            started = setup.clock()
            result = registry.call("ask_genie", {"question": question}, context)
            return result, setup.clock() - started

        first, warmed = ask()
        if first["abstention"]:
            return Outcome(step, FAILED, f"Genie gave no answer to the warm-up question: {first['abstention']}.")
        say(f"   I asked Genie \"{question}\" to start the warehouse and warm Genie. It answered after "
            f"{seconds(warmed)} with {dayone.count_words(len(first['rows']), 'row')}.")
        second, took = ask()
    if second["abstention"]:
        return Outcome(step, FAILED, f"Genie gave no answer the second time: {second['abstention']}.")
    if took > limit:
        return Outcome(step, FAILED, f"The next Genie call took {seconds(took)}, longer than the "
                                     f"{limit:g}-second limit in config/thresholds.toml.")
    say(f"   I asked again, as the first question in the demo will: it answered after {seconds(took)}, within the "
        f"{limit:g}-second limit.")
    return Outcome(step, PASSED, f"Genie answered after {seconds(took)} once warm.")


# ── 3. The smoke question ────────────────────────────────────────────────

def check_problems(events: list[tuple[str, dict]]) -> list[str]:
    """What the verifier's own events say is wrong with the answer: its check line, and the sentences it removed."""
    checks = next((data for kind, data in events if kind == "checks"), None)
    if checks is None:
        return ["The stream has no check line, so I cannot tell whether the verifier ran."]
    problems = []
    skipped = [str(number) for number in ALL_CHECKS if number not in checks.get("checks_run", [])]
    if skipped:
        problems.append(f"The verifier did not run check {listed(skipped)}.")
    removed = [data for kind, data in events if kind == "removed"]
    if removed:
        reasons = listed(sorted({data.get("reason") or "no reason" for data in removed}))
        problems.append(f"The verifier removed {dayone.count_words(len(removed), 'sentence')} ({reasons}).")
    return problems


def smoke_step(workspace, setup: Setup, say) -> Outcome:
    step = "the smoke question"
    question = questions()[load_slice().demo_plan.smoke_question]
    say(f"3. The smoke question, {question['id']} in evals/benchmark.yaml: \"{' '.join(question['question'].split())}\"")
    [(asked, scored)] = answer_benchmark.run([question], workspace.agent_for, workspace.engine_for,
                                             judge=workspace.judge, viewer=workspace.viewer,
                                             today=lambda: setup.day())
    problems = list(scored.problems) + check_problems(asked.events)
    if problems:
        return Outcome(step, FAILED, f"The answer did not pass. {' '.join(problems)}")
    checks = next(data for kind, data in asked.events if kind == "checks")
    kept, numbers, quotes = checks["sentences"]["kept"], checks["numbers"], checks["quotes"]
    counted = [f"{numbers['matched']} of {numbers['total']} numbers match records"] if numbers["total"] else []
    counted += [f"{quotes['found']} of {quotes['total']} quotes are on their pages"] if quotes["total"] else []
    say(f"   The verifier ran all six checks and kept {dayone.count_words(kept, 'sentence')}, removing none. "
        + (f"{listed(counted)}. " if counted else "")
        + f"The answer cites {listed(question['cites'])}, as the benchmark file expects.")
    return Outcome(step, PASSED, f"A cited answer passed the six checks, citing {listed(question['cites'])}.")


# ── 4. The P156634 recheck ───────────────────────────────────────────────

def recheck(engine, viewer, day: dt.date) -> dict:
    """project_signals for the demo plan's project, check_plan for the demo plan, and the awards' contracts for each
    activity whose plan row shows no signed contract, all as the viewer on one engine."""
    demo = load_slice().demo_plan
    context = registry.Context(engine=engine, viewer=viewer, as_of=day)
    signals = registry.call("project_signals", {"project_id": demo.project_id}, context)
    plan = registry.call("check_plan", {"project_id": demo.project_id, "implementing_agency": demo.implementing_agency,
                                        "plan_date": demo.plan_date.isoformat()}, context)
    awards = {}
    for row in plan["rows"]:
        if row.get("signed_on") is None:
            found = engine.run(AWARDS_SQL.read_text(), {"step_reference": row["activity_reference_no"], "as_of": day})
            contracts = [dict(zip(found.columns, values, strict=True)) for values in found.rows]
            if contracts:
                awards[row["activity_reference_no"]] = contracts
    return {"signals": signals, "plan": plan, "awards": awards}


def _item(check: str, item: dict) -> str:
    if item.get("activity_reference_no"):
        return item["activity_reference_no"]
    if check == "closing_moves":
        return f"the move to {long_day(item.get('closing_date'))}, first shown {long_day(item.get('reported_on'))}"
    if check == "restructured":
        return f"the restructuring of {long_day(item.get('restructured_on'))}"
    if check == "disbursement":
        return f"loan {item.get('loan_number')}"
    return item.get("evidence_id", "a record")


def signal_line(row: dict) -> str:
    """One signal as brief 37's lines say it (web/src/copy.ts, following.signals.line), filled from the tool's row."""
    check, items, values, count = row["check"], row["items"], row["values"], row["count"]
    refs = listed([_item(check, item) for item in items])
    if check == "completion_passed":
        if len(items) == 1:
            return (f"{refs} passed its planned completion ({long_day(items[0]['planned_completion_on'])}) with no "
                    "signed contract.")
        return f"{dayone.count_words(count, 'activity', 'activities')} passed their planned completion with no signed contract: {refs}."
    if check == "above_estimate" and len(items) == 1:
        item = items[0]
        return (f"{refs} was signed at about {item['ratio']} times its estimate: {dollars(item['actual_amount_usd'])} "
                f"against {dollars(item['estimated_amount_usd'])}.")
    if check == "late_direct" and len(items) == 1:
        item = items[0]
        return (f"{refs}, a US${item['amount_millions']} million direct-selection activity, first appears in the plan "
                f"of {long_day(item['first_plan_date'])}.")
    if check == "closing_moves":
        times = "once" if count == 1 else f"{dayone.count_words(count, 'time')}"
        return f"The closing date has moved {times} since {values.get('since_year')}."
    if check == "disbursement":
        return (f"{values.get('percent')} percent of the money committed and not canceled was disbursed, with "
                f"{values.get('months_left')} months left before closing.")
    return f"It fired on {refs}."


def project_line(project: dict | None) -> str:
    if not project:
        return "I hold no record of the project."
    kind, closing = project.get("closing_kind"), long_day(project.get("closing_date"))
    if kind == "closes":
        return f"It closes on {closing}."
    if kind == "past_closing":
        return f"Its closing date was {closing}."
    if kind == "closed":
        return f"It closed on {closing}."
    return f"It is {PROJECT_WORDS.get(project.get('status'), 'listed with no status')}."


def state_line(signals: dict) -> str:
    project = signals.get("project") or {}
    if (signals.get("abstention") or {}).get("reason") == "not_active":
        word = PROJECT_WORDS.get(project.get("status"), "not active")
        return f"Not checked: the project is {word}, and the checks run only on active projects. {project_line(project)}"
    status = STATUS_WORDS.get(signals.get("status"), "Not checked")
    return f"{status}, with {dayone.count_words(signals['counts']['signals'], 'signal')}. {project_line(project)}"


def check_states(signals: dict) -> list[str]:
    rows = {row["check"]: row for row in signals["rows"]}
    lines = []
    for check in signals["checks"]:
        key = check["key"]
        if key in rows:
            strong = " A strong signal." if rows[key]["strong"] else ""
            lines.append(f"{CHECK_NAMES[key]}: {signal_line(rows[key])}{strong}")
        elif check["ran"]:
            lines.append(f"{CHECK_NAMES[key]}: ran and found nothing.")
        else:
            lines.append(f"{CHECK_NAMES[key]}: could not run, because {MISSING_WORDS.get(check['missing'], check['missing'])}.")
    return lines


def changes(fixture: dict, live: dict, project_id: str) -> list[str]:
    """Every difference between the fixture's run and the workspace's, the project's status and closing date first."""
    before, after = fixture["signals"], live["signals"]
    was, now = before.get("project") or {}, after.get("project") or {}
    lines = []
    if was.get("status") != now.get("status"):
        lines.append(f"{project_id} is {PROJECT_WORDS.get(now.get('status'), 'not listed')} on the workspace, and was "
                     f"{PROJECT_WORDS.get(was.get('status'), 'not listed')} in the fixture.")
    if was.get("closing_date") != now.get("closing_date"):
        lines.append(f"Its closing date is {long_day(now.get('closing_date'))} on the workspace, and was "
                     f"{long_day(was.get('closing_date'))} in the fixture.")
    if not lines and before.get("status") != after.get("status"):
        lines.append(f"Its status is {STATUS_WORDS.get(after.get('status'), 'Not checked')} on the workspace, and was "
                     f"{STATUS_WORDS.get(before.get('status'), 'Not checked')} in the fixture.")
    plans_before = {plan["implementing_agency"]: plan["plan_date"] for plan in before.get("plans") or []}
    for plan in after.get("plans") or []:
        agency, dated = plan["implementing_agency"], plan["plan_date"]
        if plans_before.get(agency) != dated:
            lines.append(f"The {agency}'s latest Procurement Plan is dated {long_day(dated)} on the workspace, and was "
                         f"{long_day(plans_before.get(agency)) if agency in plans_before else 'not there'} in the fixture.")
    if (after.get("abstention") or {}).get("reason") != "not_active":
        rows_before = {row["check"]: row for row in before["rows"]}
        rows_after = {row["check"]: row for row in after["rows"]}
        ran_before = {check["key"]: check for check in before["checks"]}
        for check in after["checks"]:
            key, name = check["key"], CHECK_NAMES[check["key"]]
            if key in rows_after and key not in rows_before:
                lines.append(f"{name} fired on the workspace and not in the fixture: {signal_line(rows_after[key])}")
            elif key in rows_before and key not in rows_after:
                lines.append(f"{name} no longer fired on the workspace. In the fixture: {signal_line(rows_before[key])}")
            elif key in rows_after:
                items_before = {_item(key, item) for item in rows_before[key]["items"]}
                items_after = {_item(key, item) for item in rows_after[key]["items"]}
                for gone in sorted(items_before - items_after):
                    lines.append(f"{name}: {gone} no longer fired on the workspace.")
                for new in sorted(items_after - items_before):
                    lines.append(f"{name}: {new} fired on the workspace and not in the fixture.")
            if not check["ran"] and ran_before.get(key, {}).get("ran"):
                lines.append(f"{name} could not run on the workspace, because "
                             f"{MISSING_WORDS.get(check['missing'], check['missing'])}.")
    for reference, contracts in live["awards"].items():
        known = {contract["contract_id"] for contract in fixture["awards"].get(reference, [])}
        for contract in contracts:
            if contract["contract_id"] not in known:
                lines.append(f"The awards dataset on the workspace shows contract {contract['contract_id']} for "
                             f"{reference}, signed on {long_day(contract['contract_signing_date'])}, and the fixture "
                             "does not.")
    for reference in fixture["awards"]:
        if reference not in live["awards"]:
            lines.append(f"{reference}: the plan and the awards dataset no longer disagree on the workspace.")
    return lines


def disagreements(fixture: dict, live: dict) -> list[str]:
    plan_date = long_day(live["plan"]["plan"]["plan_date"]) if live["plan"].get("plan") else "the demo plan"
    lines = []
    for reference, contracts in live["awards"].items():
        named = listed([f"contract {contract['contract_id']}, signed on {long_day(contract['contract_signing_date'])} "
                        f"for {dollars(contract['contract_amount_usd'])}" for contract in contracts])
        held = " The fixture holds it too." if reference in fixture["awards"] else ""
        lines.append(f"{reference}: the plan of {plan_date} shows no signed contract, and the awards dataset shows "
                     f"{named}.{held}")
    return lines


def recheck_step(workspace, setup: Setup, say, kept: dict) -> Outcome:
    step = f"the {load_slice().demo_plan.project_id} recheck"
    project_id, day = load_slice().demo_plan.project_id, setup.day()
    say(f"4. Rechecking {project_id}'s signals as of {long_day(day)}, on the fixture database and on the workspace "
        f"as {workspace.viewer.email}.")
    if not Path(setup.fixture_db).is_file():
        return Outcome(step, FAILED, f"There is no fixture database at {setup.fixture_db}. Build it first: uv run "
                                     "--frozen python gates/build_fixture.py")
    with DuckDBEngine.open(setup.fixture_db, read_only=True) as engine:
        fixture = recheck(engine, workspace.viewer, day)
    with workspace.engine_for(workspace.viewer) as engine:
        live = recheck(engine, workspace.viewer, day)
    kept["live"] = live
    say(f"   In the fixture: {state_line(fixture['signals'])}")
    say(f"   On the workspace: {state_line(live['signals'])}")
    for line in check_states(live["signals"]):
        say(f"      {line}")
    found = changes(fixture, live, project_id)
    say("   What changed since the fixture was recorded:" if found else "   Nothing changed since the fixture was recorded.")
    for line in found:
        say(f"      {line}")
    known = disagreements(fixture, live)
    if known:
        say("   Where the plan and the awards dataset disagree. I report this and decide nothing (docs/STATUS.md, "
            "decision 7):")
        for line in known:
            say(f"      {line}")
    status = state_line(live["signals"]).split(":")[0].split(",")[0]
    return Outcome(step, PASSED, f"{status} on the workspace, with {dayone.count_words(len(found), 'change')} since "
                                 "the fixture.")


# ── 5. Home ──────────────────────────────────────────────────────────────

def home_step(workspace, setup: Setup, say, kept: dict) -> Outcome:
    step = "Home"
    limits, built = setup.limits(), True
    say("5. Home's examples and its briefing window.")
    if setup.seed_command():
        code, output = workspace.seed()
        if code != 0:
            return Outcome(step, FAILED, f"The seed command failed: {one_line(output) or 'it said nothing'}")
        say(f"   I ran python -m {SEED_MODULE} for the reviewing panel's group. It makes only the examples that are "
            "missing.")
    else:
        built = False
        say(f"   The seed command, python -m {SEED_MODULE}, is not built yet (ticket 41), so I seeded no examples.")
    if "home" not in limits.values:
        built = False
        say("   Home's briefing window, home.window_days in config/thresholds.toml, is not set yet (ticket 41), so I "
            "did not check the demo plan against it.")
    else:
        days = int(limits.value("home.window_days"))
        plan = ((kept.get("live") or {}).get("plan") or {}).get("plan")
        with workspace.engine_for(workspace.viewer) as engine:
            through = data_through(engine)
        if plan is None or through is None:
            say("   I could not read the demo plan's Disclosed date or the data-through date, so I did not check "
                "Home's window.")
        else:
            disclosed = dt.date.fromisoformat(plan["disclosed_on"])
            start = through - dt.timedelta(days=days - 1)
            window = f"the {dayone.count_words(days, 'day')} from {long_day(start)} to {long_day(through)}"
            if start <= disclosed <= through:
                say(f"   The plan of {long_day(plan['plan_date'])}, disclosed on {long_day(disclosed)}, falls inside "
                    f"Home's window, {window}, so the briefing lists its activities.")
            else:
                say(f"   The plan of {long_day(plan['plan_date'])}, disclosed on {long_day(disclosed)}, falls outside "
                    f"Home's window, {window}. The briefing lists only what was disclosed in those days, so it will "
                    "not list this plan's activities.")
    if not built:
        return Outcome(step, NOT_BUILT, "Ticket 41 adds the seed command and Home's window.")
    return Outcome(step, PASSED, "The examples are seeded and the window is checked.")


# ── The run ──────────────────────────────────────────────────────────────

def app_changes(before: dict, after: dict) -> list[str]:
    """What changed about each app between the two listings, in words: whether it runs, and anything else."""
    lines = []
    for kind, name in sorted(key for key in set(before) | set(after) if key[0] == "apps"):
        was, now = before.get((kind, name)), after.get((kind, name))
        if was is None or now is None:
            lines.append(f"The app {name} is {'new' if was is None else 'gone'}.")
            continue
        if bool(was.get("running")) != bool(now.get("running")):
            lines.append(f"The app {name} runs now, and was stopped before." if now.get("running")
                         else f"The app {name} is stopped now, and was running before.")
        lines += [f"The app {name}'s {field} changed." for field in sorted((set(was) | set(now)) - {"running"})
                  if was.get(field) != now.get(field)]
    return lines


def listing(workspace, say) -> dict | None:
    try:
        return workspace.snapshot()
    except Exception as error:  # the warehouse or the API refused: the steps still run, and the summary says so
        say(f"   I could not list the workspace: {type(error).__name__}: {one_line(error)}")
        return None


def ready(workspace, setup: Setup, say: Callable[[str], None] = print) -> int:
    before = listing(workspace, say)
    if before is not None:
        say("I listed the workspace before I changed anything.")
    kept: dict = {}
    outcomes = []
    steps = [("the app", lambda: app_step(workspace, setup, say)),
             ("Genie", lambda: genie_step(workspace, setup, say)),
             ("the smoke question", lambda: smoke_step(workspace, setup, say)),
             (f"the {load_slice().demo_plan.project_id} recheck", lambda: recheck_step(workspace, setup, say, kept)),
             ("Home", lambda: home_step(workspace, setup, say, kept))]
    for step, run in steps:
        try:
            outcome = run()
        except Exception as error:  # a service that is down or refused: the other steps still run
            outcome = Outcome(step, FAILED, f"It stopped: {type(error).__name__}: {one_line(error)}")
        if outcome.state != PASSED:
            say(f"   {outcome.summary}")
        outcomes.append(outcome)
    say("6. What changed on the workspace.")
    after = listing(workspace, say)
    if before is None or after is None:
        outcomes.append(Outcome("the workspace listing", FAILED, "I could not list the workspace before and after the "
                                                                 "steps, so I cannot say what changed."))
    else:
        found = app_changes(before, after) + bundle_deploy.changes(
            {key: value for key, value in before.items() if key[0] != "apps"},
            {key: value for key, value in after.items() if key[0] != "apps"}, LISTED)
        for line in found or ["No changes."]:
            say(f"   {line}")
        say("   Genie keeps the conversations I started, and the warehouse its query history. The listing leaves both "
            "out.")
        counted = dayone.count_words(len(found), "change")
        outcomes.append(Outcome("the workspace listing", PASSED,
                                f"{counted[0].upper()}{counted[1:]}, listed above." if found else "No changes."))
    say("Summary:")
    for outcome in outcomes:
        say(f"   {outcome.step[0].upper()}{outcome.step[1:]}: {outcome.state}. {outcome.summary}")
    failed = [outcome.step for outcome in outcomes if outcome.state == FAILED]
    if failed:
        which = "This step" if len(failed) == 1 else "These steps"
        say(f"Strata is not ready for the demo. {which} failed: {listed(failed)}.")
        return 1
    say("Strata is ready for the demo.")
    return 0


def main(argv: list[str] | None = None, workspace=None, setup: Setup | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ops/demo/ready.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", type=Path, default=None,
                        help="The main checkout's .env, which the wizard filled. That file is the default.")
    parser.add_argument("--fresh-workspace", action="store_true",
                        help="Change nothing: list every resource a fresh workspace needs, from code alone.")
    args = parser.parse_args(argv)
    if args.fresh_workspace:
        return fresh_workspace.show(print)
    try:
        env = load_workspace_env(args.env_file)
    except WorkspaceEnvError as error:
        print(error, file=sys.stderr)
        return 2
    missing = dayone.missing_keys(env, list(NEEDS))
    if missing:
        print(f"{args.env_file or dayone.default_env_path()} has no value for {', '.join(missing)}. "
              f"{dayone.WIZARD_FIRST}", file=sys.stderr)
        return 2
    if workspace is None:
        from demo_live import LiveDemo

        workspace = LiveDemo(env, args.env_file or dayone.default_env_path())
    return ready(workspace, setup or Setup())


if __name__ == "__main__":
    sys.exit(main())
