# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0", "pyyaml==6.0.3", "duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5",
#                 "pypdf==6.21.2"]
# ///
"""Read assertions from the reports with the live batch model: ticket 20's live run, and the command that
records the batch answers the gate replays.

The live run. Run it from the main checkout, after ops/documents/run_live.py has read the documents into
passages on the shared workspace:

    uv run --script ops/assertions/batch_live.py --env-file .env

It runs the nightly job's detect_disagreements work on the SQL warehouse, with the deployment
config/models.toml names for the batch role on Azure OpenAI's Global Batch: every ISR rating, record and
IEG rating becomes an assertion, the batch model reads the ICRs, ICR Reviews, PPARs and PADs, and an
assertion whose quote is not word for word on its cited page is rejected and counted. Then it asks
get_disagreements its benchmark question through the tool registry, with the env file's own token as the
viewer, and checks that ISR 7 and the ICR's paragraph 78 come back as one disagreement leaning on the ICR.
It exits 0 when they do, 1 when the run finished but they did not, or the batch was still running when the
run stopped waiting (run it again later: it waits for the same batch, and answers already held are not
asked for again), and 2 when it could not run. Then check the ground-truth queries on both engines:

The run is the nightly's, over every project with documents or records, unless --projects names the projects to
run it for, joined by commas, such as the five demo projects (ticket 135):

    uv run --script ops/assertions/batch_live.py --env-file .env --projects P156634,P130164,P161305,P155350,P113151

For each project it prints what became assertions (from the ISRs' ratings tables, the records, the IEG ratings
dataset and the reports the batch model read) and what went to the batch model. The run reads the warehouse
within its limit on one statement's result (config/thresholds.toml, warehouse.statement_result_bytes): on
October 29, 2026 it read every project's records in one statement, and the warehouse refused it with "Inline byte
limit exceeded".

    uv run --script ops/bundle/check.py same-rows --env-file .env

The recording. With --record, it asks the live batch model the requests the gate's recording answers
(tests/fixtures/azure/batch_assertions.json), built from the fixture database the gate builds
(data/out/fixture.duckdb), and writes their answers over the hand-written ones, keeping the assertion
planted by hand so the gate still proves the rejection. It needs only AZURE_OPENAI_ENDPOINT and
AZURE_OPENAI_API_KEY. Run the gate after it: a live answer that reads more than the hand-written one (such
as item 8.b of the ICR Reviews, which restates what the mid-term review found) can change what the tests
expect, and the tests then say which value moved. When the batch is still running after an hour, it prints
the batch's id; run it again with --batch and that id to wait for the same batch instead of asking again.

The live run needs DATABRICKS_HOST, DATABRICKS_WAREHOUSE_ID, DATABRICKS_TOKEN, AZURE_OPENAI_ENDPOINT and
AZURE_OPENAI_API_KEY.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "bundle"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import yaml  # noqa: E402

from strata.config import load_ladder  # noqa: E402
from strata.knowledge import assertions, batch  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine, EngineError, WarehouseEngine, http_transport  # noqa: E402
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402

QUESTION = "get-disagreements-p130164"
FIXTURE_DB = REPO / "data" / "out" / "fixture.duckdb"
AZURE = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY")
WORKSPACE = ("DATABRICKS_HOST", "DATABRICKS_WAREHOUSE_ID", "DATABRICKS_TOKEN")


def record(model: batch.AzureOpenAIBatch, resume: str | None = None) -> int:
    """Ask the live model the requests the recording answers, and write its answers as the new recording."""
    if not FIXTURE_DB.exists():
        print(f"There is no fixture database at {FIXTURE_DB.relative_to(REPO)}. Run the gate first "
              "(.githooks/pre-commit), which builds it.")
        return 2
    held = json.loads(batch.RECORDING.read_text())
    wanted = {line["custom_id"] for line in held["lines"]}
    ladder = load_ladder()
    with DuckDBEngine.open(FIXTURE_DB, read_only=True) as engine:
        projects = assertions.default_projects(engine)
        rows = assertions.ProjectRows(engine, projects, ladder)  # one query a family for every project
        asked = [assertions.request(report, ladder) for project_id in projects
                 for report in assertions.reports(engine, project_id, ladder, rows)]
    requests = [request for request in asked if request.custom_id in wanted]
    print(f"I'm asking {model.deployment} about {len(requests)} reports on Global Batch.")
    try:
        written = batch.recording(model.output_lines(requests, resume), held, dt.date.today().isoformat())
    except batch.BatchPending as error:
        print(f"{error} Run this again later with --batch {error.batch_id} to wait for it.")
        return 1
    except batch.BatchError as error:
        print(f"The recording stopped: {error}")
        return 2
    batch.RECORDING.write_text(json.dumps(written, indent=1, ensure_ascii=False) + "\n")
    where = batch.RECORDING.relative_to(REPO) if batch.RECORDING.is_relative_to(REPO) else batch.RECORDING
    print(f"I wrote {len(written['lines'])} answers to {where}. Run the gate next.")
    return 0


def counted(number: int, word: str) -> str:
    return f"{number} {word}" if number == 1 else f"{number} {word}s"


def what_it_became(each: assertions.ProjectReport) -> str:
    """One project's line: what became assertions, and what went to the batch model."""
    line = (f"{each.project_id}: {counted(each.assertions, 'assertion')} ({each.isr_ratings} from ISR ratings, "
            f"{each.records} from records, {each.ieg_ratings} from the IEG ratings dataset, {each.from_reports} read "
            f"from reports), and the check rejected {counted(each.rejected, 'assertion')} read from reports.")
    if not each.reports:
        return f"{line} {each.project_id} has no report for the batch model."
    return (f"{line} Of {each.project_id}'s {counted(each.reports, 'report')}, the batch model had answered "
            f"{each.answered_before} before, {each.sent} went to it in this run, and {each.waiting} "
            f"{'is' if each.waiting == 1 else 'are'} still in a running batch.")


def projects_named(given: str) -> list[str]:
    """The projects --projects names, joined by commas, each once, in the order given."""
    return list(dict.fromkeys(one.strip() for one in given.split(",") if one.strip()))


def run_live(env: dict, model: batch.AzureOpenAIBatch, projects: list[str] | None = None) -> int:
    """The detect_disagreements work on the warehouse, for the projects named or else the nightly's, then
    get_disagreements' benchmark question."""
    from bundle_live import LiveWorkspace  # the Databricks SDK, which only the live run needs

    from strata.dbx import Viewer
    from strata.tools import registry

    engine = LiveWorkspace(env).engine()
    run_id = f"live-{dt.datetime.now(dt.UTC):%Y%m%dT%H%M%S}"
    try:
        report = assertions.run(engine, projects or assertions.default_projects(engine), model=model, run_id=run_id)
    except (EngineError, batch.BatchError) as error:
        print(f"The run stopped: {error}")
        return 2
    print(f"Run {run_id} holds {report.assertions} assertions and {report.disagreements} disagreements, and "
          f"rejected {report.rejected} assertions read from text.")
    for each in report.projects:
        print(f"  {what_it_became(each)}")
    if report.left_out:
        print(f"I left out {', '.join(report.left_out)}: each project's own rows pass the warehouse's limit on one "
              "statement's result (config/thresholds.toml, warehouse.statement_result_bytes), so it keeps the "
              "assertions the tables held.")
    if report.pending:
        print(f"The answers about {report.pending} reports are still in a running batch. Run this again later: "
              "it waits for the same batch, and the answers already held are not asked for again.")
        return 1

    questions = yaml.safe_load((REPO / "evals" / "benchmark.yaml").read_text())["questions"]
    question = next(q for q in questions if q["id"] == QUESTION)
    arguments = {name: given for name, given in question["arguments"].items() if name != "as_of"}
    viewer = WarehouseEngine(env["DATABRICKS_WAREHOUSE_ID"], http_transport(env["DATABRICKS_HOST"],
                                                                            env["DATABRICKS_TOKEN"]))
    context = registry.Context(engine=viewer, viewer=Viewer(name="the env file's token", token=env["DATABRICKS_TOKEN"]))
    try:
        result = registry.call(question["tool"], arguments, context)
    except (EngineError, LookupError, RuntimeError) as error:
        print(f"I could not ask get_disagreements: {error}")
        return 2
    evidence = {side["assertion_id"]: side["evidence_id"] for row in result["rows"] for side in row["sides"]}
    found = [[side["evidence_id"] for side in row["sides"]] for row in result["rows"]]
    leans = [evidence.get(row["lean_assertion_id"]) for row in result["rows"]]
    for sides, lean, row in zip(found, leans, result["rows"]):
        print(f"  {sides[0]} and {sides[1]}: I lean on {lean} ({row['rule_id']}).")
    expected = question["expected"]
    matched = found == expected["disagreements"] and leans == expected["leans_on"]
    print("The showcase disagreement came back as the benchmark expects." if matched else
          f"The benchmark expects {expected['disagreements']} leaning on {expected['leans_on']}.")
    return 0 if matched else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ops/assertions/batch_live.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", help="the env file with the workspace's address, warehouse, token and keys")
    parser.add_argument("--record", action="store_true",
                        help="write the live answers to the gate's recording instead of running on the warehouse")
    parser.add_argument("--batch", help="with --record: the id of a batch an earlier recording left running, to "
                                        "wait for it instead of asking again")
    parser.add_argument("--projects", help="the live run's projects, joined by commas, such as P156634,P130164; "
                                           "without it the run is the nightly's, over every project with documents "
                                           "or records")
    args = parser.parse_args(argv)
    projects = projects_named(args.projects) if args.projects is not None else None
    if projects is not None and (args.record or not projects):
        print("--projects names the live run's projects, joined by commas, such as P156634,P130164. "
              "The recording asks about the requests it holds, so it takes no --projects.")
        return 2
    try:
        env = load_workspace_env(Path(args.env_file) if args.env_file else None)
    except WorkspaceEnvError as error:
        print(error)
        return 2
    missing = [key for key in AZURE + (() if args.record else WORKSPACE) if not env.get(key)]
    if missing:
        print(f"The env file has no value for {', '.join(missing)}. Run the setup wizard first "
              "(ops/wizard/strata-setup.sh).")
        return 2
    model = batch.from_environment(env)
    return record(model, args.batch) if args.record else run_live(env, model, projects)


if __name__ == "__main__":
    sys.exit(main())
