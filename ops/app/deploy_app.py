# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0", "pyyaml==6.0.3"]
# ///
"""Build Prism's web app and deploy Prism as the Databricks App that acts as each viewer.

Run it from the main checkout after the wizard and the bundle deploy (ops/bundle/deploy.py):

    uv run --script ops/app/deploy_app.py --env-file .env

It needs npm, which builds the web app. Before step 1, it reads the app's compute and the SQL warehouse's state
through the SDK, with no SQL (ops/bundle/workspace_state.py, ticket 81). When the workspace stopped the app's compute
("due to workspace or account status"), or the warehouse is stopped and will not start when asked, it prints one
sentence that names the state and exits 2 without uploading. On Free Edition the usual cause is the workspace's daily
compute limit. It asks an app the workspace stopped to start first, and refuses only when it will not, as it does the
warehouse; when it cannot read the state at all, it says so in one sentence and exits 2. Then it does these things, in
order:

1. It builds the web app into web/dist (npm --prefix web run build).
2. It finds the app that ops/dayone/dayone.toml names (names.app), or makes it. It replaces the
   day-one probe app that ran there, but it leaves an app that someone else made alone.
3. It gives the app its resources: the SQL warehouse in .env (CAN_USE), the Application
   Insights connection string in the secret scope (READ), the "sql" user authorization
   scope, so the App forwards each viewer's own token for the warehouse, and the Lakebase database
   that holds app state (ADR 0005), on the instance names.app_state_instance in
   ops/dayone/dayone.toml, which it makes or starts first (CAN_CONNECT_AND_CREATE, so the app's own
   service principal makes its tables there when it first needs them). If the workspace cannot make
   or start the instance, it says why and deploys the app without app state, so no packages are kept. When .env has the Foundry
   agent's four keys (FOUNDRY_PROJECT_ENDPOINT, FOUNDRY_TENANT_ID, FOUNDRY_CLIENT_ID and
   FOUNDRY_CLIENT_SECRET), it saves them in the secret scope and gives the app each one (READ),
   so /api/ask answers through the agent. Without all four, it leaves them out of the app.yaml it
   uploads, and /api/ask says there is no agent. It does the same with the two keys of the judge that
   checks each sentence (AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY, src/strata/agent/judge.py);
   without them, the app removes every sentence that needs the judge. With --keep-secrets, it writes
   no secret (see below).
4. It uploads the app, laid out as in the repo: app.yaml and the lean requirements.txt from
   ops/app, src/strata, config and web/dist, to the folder strata-app in your workspace folder.
5. It deploys the app, starting it first if it is stopped, and waits for it. Then it reads the app's deployments
   (apps list-deployments) and stops with exit 1 unless one it did not list just before the deploy call has the state
   SUCCEEDED, naming the deployment and its time: on October 26, 2026 the deploy call came back on a stopped workspace
   with no deployment registered. While that deployment shows IN_PROGRESS, as it may after the app's compute starts cold, it
   reads the deployments again every 10 seconds, for up to 20 minutes, before it stops (October 27, 2026).
6. It grants the app's own service principal what the server needs to write usage events, agent
   runs, opened sources, drafts, decisions and labels on supplier pairs, and the lesson review record,
   and nothing more: USE CATALOG on strata, USE SCHEMA on strata.ops, SELECT and MODIFY on
   strata.ops.usage_events, agent_runs, each run's tool_calls, tool_call_reads and answer_removals
   (ticket 45's lineage), evidence_opened, drafts, draft_states, draft_exports,
   draft_files, follows, ticket 23's disagreement_choices and draft_fields, ticket 44's exposures, SELECT on its view
   draft_fields_latest, SELECT on strata.ops.supplier_pairs, SELECT and MODIFY on
   strata.ops.supplier_review_decisions and strata.ops.supplier_pair_labels, and SELECT and MODIFY on
   ticket 29's lesson_review_acts, lesson_review_items, lesson_versions, lesson_sources and
   lesson_review_notes, ticket 32's candidate_labels, label_decisions, answer_citations,
   retrieval_grades and retrieval_queries, ticket 41's start_here_choices, seeded_examples and
   example_lesson_versions, and ticket 42's viewer_settings. Viewers read as themselves, through the bundle's grants,
   and no reviewer group may write the lesson review record or the retrieval loop's record outside
   the app.
7. It masks the columns that say who sent each passage report and who asked each question
   (strata.lakehouse.masks; ticket 64): one mask function, strata.ops.mask_viewer, gives their values
   only to the app's own service principal and to you, who own the catalog and whose identity runs
   the weekly retrieval job. Every other reader reads NULL there, though the bundle lets them read
   all of strata.ops. Then it puts a row filter on the passage reports and on each answer's sources,
   which keep what people asked and wrote (ticket 63): only the app, you and the passage reviewers'
   workspace group in config/roles.toml read their rows, and every other reader reads none.
   When the SQL warehouse refuses a statement in step 6 or 7, it names the warehouse's state before the warehouse's
   answer and stops with exit 1, because a stopped warehouse refuses every statement with an error, such as
   TABLE_DOES_NOT_EXIST for a table that exists.
8. It prints the app's address.

The grants in bundle/catalog.yml replace any other grants on the strata catalog and its schemas
(bundle/README.md), so the bundle deploy (ops/bundle/deploy.py) gives the app's service principal
its USE CATALOG on strata and USE SCHEMA on strata.ops back right after (ticket 79), and its table
grants stay. Run it again after a bundle deploy that makes a table the app writes, so the app gets
that table's grant.

Only the user may write secrets in the shared workspace. To redeploy new code from a session that may
not write them, once the user has written the secrets, run:

    uv run --script ops/app/deploy_app.py --env-file .env --keep-secrets

Step 3 then writes no secret. It prints the names of the secrets the app reads (the Application
Insights connection string, and the Foundry agent's and the judge's keys when .env has them) and lists
the scope's keys, never their values. When the scope holds them all, the app gets the same resources,
scopes and app.yaml as without the option. When it lacks one, step 3 names it, says how to write it,
and deploys the app without what reads it, as if .env had no value for it: no Foundry agent, no judge,
or no traces to Application Insights. Every other step runs as without the option.

This was written from docs/PLAN.md section 12's description of fairshare's lakehouse/app_deploy.py,
because fairshare could not be read on the build machine.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
import time
from collections.abc import Callable, Collection
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "bundle", HERE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import dayone  # noqa: E402
import workspace_state  # noqa: E402  (ops/bundle/workspace_state.py, ticket 81)
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402

from strata.config import Roles, load_roles  # noqa: E402
from strata.lakehouse.masks import FILTERED, MASK, MASKED, row_filter  # noqa: E402

# The live App's description is how a deploy knows the app is this repo's, so it keeps the old name (ADR 0006).
DESCRIPTION = "Strata, procurement intelligence on World Bank open data"
PROBE_DESCRIPTION = "Strata day-one probe app"  # ops/dayone/live.py's PROBE_APP_DESCRIPTION
FOLDER = "strata-app"
DIST = REPO / "web" / "dist"
# The user authorization scopes: each viewer's forwarded token may run SQL on the warehouse, ask the Genie space as
# that viewer (ask_genie, ticket 33), and query the passage index on AI Search as that viewer (search_passages). Without
# dashboards.genie the forwarded token gets 403 from Genie. Without vector-search it gets 403 from the index, so every
# search_passages call in the App failed as permission from October 28 to October 31, 2026.
SCOPES = ["sql", "dashboards.genie", "vector-search"]
# The secret's name in the scope, which the wizard saved (ops/wizard/strata-setup.sh).
APPINSIGHTS_NAME = "APPLICATIONINSIGHTS_CONNECTION_STRING"
APPINSIGHTS = "appinsights"  # its resource, which app.yaml reads it from
# The Foundry agent's four keys (src/strata/agent/runner.py), each saved in the secret scope under its own
# name and given to the app as the resource app.yaml reads it from.
FOUNDRY = {"FOUNDRY_PROJECT_ENDPOINT": "foundry-endpoint", "FOUNDRY_TENANT_ID": "foundry-tenant",
           "FOUNDRY_CLIENT_ID": "foundry-client-id", "FOUNDRY_CLIENT_SECRET": "foundry-client-secret"}
# The judge of the verifier's check 4 (src/strata/agent/judge.py): its two Azure OpenAI keys, kept the same way.
JUDGE = {"AZURE_OPENAI_ENDPOINT": "azure-openai-endpoint", "AZURE_OPENAI_API_KEY": "azure-openai-key"}
PRINCIPAL = re.compile(r"[0-9a-fA-F-]{36}")
USER = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")  # a user name, which Databricks keeps as an email
GROUP = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._-]*")  # a workspace group's name, as config/roles.toml writes it
# The app state database's resource (ADR 0005). The platform sets PGHOST, PGPORT, PGDATABASE, PGUSER and
# PGSSLMODE from it, which src/strata/server/settings.py reads; the database is the instance's own.
APP_STATE = "app-state"
APP_STATE_DATABASE = "databricks_postgres"
SKIPPED = ("__pycache__", ".DS_Store")


def build_web() -> tuple[int, str]:
    done = subprocess.run(["npm", "--prefix", "web", "run", "--silent", "build"], cwd=REPO,
                          capture_output=True, text=True, timeout=600)
    return done.returncode, (done.stdout + done.stderr).strip()


def _files(root: Path, under: str) -> dict[str, bytes]:
    return {f"{under}/{path.relative_to(root).as_posix()}": path.read_bytes() for path in sorted(root.rglob("*"))
            if path.is_file() and not any(part in SKIPPED for part in path.parts)}


def app_yaml(foundry: bool, judge: bool = True, genie_space: str | None = None, traces: bool = True) -> bytes:
    """ops/app/app.yaml as it is, or without the Foundry agent's keys, or the judge's, or the Application Insights
    connection string, when the app has no secrets for them, because an env entry whose resource the app lacks would
    stop it from starting. With a Genie space, GENIE_SPACE_ID names it, so ask_genie asks it (ticket 33). The space's
    ID is not a secret."""
    text = (HERE / "app.yaml").read_bytes()
    if foundry and judge and traces and not genie_space:
        return text
    left_out = (([] if foundry else list(FOUNDRY.values())) + ([] if judge else list(JUDGE.values()))
                + ([] if traces else [APPINSIGHTS]))
    started = yaml.safe_load(text)
    started["env"] = [entry for entry in started["env"] if entry.get("valueFrom") not in left_out]
    if genie_space:
        started["env"].append({"name": "GENIE_SPACE_ID", "value": genie_space})
    return yaml.safe_dump(started, sort_keys=False).encode()


def has_foundry(env: dict, lacking: Collection[str] = ()) -> bool:
    """.env has the Foundry agent's four keys, and the scope lacks none of them (lacking, under --keep-secrets)."""
    return all((env.get(key) or "").strip() and key not in lacking for key in FOUNDRY)


def has_judge(env: dict, lacking: Collection[str] = ()) -> bool:
    return all((env.get(key) or "").strip() and key not in lacking for key in JUDGE)


def package(dist: Path, foundry: bool = True, judge: bool = True,
            genie_space: str | None = None, traces: bool = True) -> dict[str, bytes]:
    """The app's files, by their path in the app's folder."""
    return {"app.yaml": app_yaml(foundry, judge, genie_space, traces),
            "requirements.txt": (HERE / "requirements.txt").read_bytes(),
            **_files(REPO / "src" / "strata", "src/strata"),
            **{f"config/{path.name}": path.read_bytes() for path in sorted((REPO / "config").glob("*.toml"))},
            **_files(dist, "web/dist")}


def resources(env: dict, scope: str, app_state: str | None = None, lacking: Collection[str] = ()) -> list[dict]:
    """The app's resources. lacking names the secrets the scope lacks under --keep-secrets: the app gets no resource
    that reads one, as if .env had no value for it."""
    found = [{"name": "sql-warehouse", "sql_warehouse": {"id": env["DATABRICKS_WAREHOUSE_ID"], "permission": "CAN_USE"}}]
    if APPINSIGHTS_NAME not in lacking:
        found.append({"name": APPINSIGHTS, "secret": {"scope": scope, "key": APPINSIGHTS_NAME, "permission": "READ"}})
    if app_state:
        found.append({"name": APP_STATE, "database": {"instance_name": app_state, "database_name": APP_STATE_DATABASE,
                                                      "permission": "CAN_CONNECT_AND_CREATE"}})
    if has_foundry(env, lacking):
        found += [{"name": name, "secret": {"scope": scope, "key": key, "permission": "READ"}}
                  for key, name in FOUNDRY.items()]
    if has_judge(env, lacking):
        found += [{"name": name, "secret": {"scope": scope, "key": key, "permission": "READ"}}
                  for key, name in JUDGE.items()]
    return found


# Ticket 29's lesson review record, which the app writes as itself with the reviewer named in each row.
LESSON_REVIEW_TABLES = ("lesson_review_acts", "lesson_review_items", "lesson_versions", "lesson_sources",
                        "lesson_review_notes", "lesson_version_tags")
# Ticket 32's retrieval loop: passage reports (candidate labels), the passage reviewers' decisions, the sources
# each answer cited, the query judges' grades, and the pair of judges a query keeps at its first grade, which the
# app writes as itself with the person in each row. tests/test_judging.py checks that a grade writes only these.
RETRIEVAL_TABLES = ("candidate_labels", "label_decisions", "answer_citations", "retrieval_grades", "retrieval_queries")
# The app's way in to the catalog and to strata.ops, as (securable type, full name, privilege). The bundle's grants
# (bundle/catalog.yml) replace every other grant on strata and its schemas, so the bundle deploy
# (ops/bundle/deploy.py) gives these back to the app's service principal right after (ticket 79). Its table grants
# below are on tables, which the bundle leaves alone.
ACCESS = (("catalog", "strata", "USE_CATALOG"), ("schema", "strata.ops", "USE_SCHEMA"))


def is_strata(app: dict) -> bool:
    """Whether the app that ops/dayone/dayone.toml names is Prism's, or the day-one probe app it replaces, by its
    description. Prism leaves an app that someone else made alone."""
    return app["description"] in (DESCRIPTION, PROBE_DESCRIPTION)


def grants(principal: str) -> list[str]:
    """What the app's own service principal needs to write usage events, agent runs, opened sources, drafts
    with their states, exports and files (ticket 35), decisions and labels on supplier pairs, and the
    lesson review record (ticket 29), which it writes for every reviewer."""
    if not PRINCIPAL.fullmatch(principal):
        raise ValueError(f"{principal!r} is not a service principal's application id.")
    # follows (ticket 37): the projects each World Bank staff viewer follows, kept as the app. disagreement_choices
    # (ticket 23): the report each person kept on a disagreement, for an answer or a draft, which the drafts' hold
    # reads too (ticket 36). draft_fields (ticket 36): the values people set on a draft's fields, read through its
    # latest-value view. exposures (ticket 44): each past range or time estimate the app showed in the staff view.
    # uploads and upload_rows (ticket 38): an implementing agency team's uploads of its plan, kept as the app and
    # read only through its team rule. lesson_visits and draft_lesson_choices (ticket 39): each reader's visits to
    # Lessons, and what a draft's author chose for a row whose lesson changed, both kept as the app.
    # start_here_choices, seeded_examples and example_lesson_versions (ticket 41): whether each viewer keeps Home's
    # Start here strip, the examples the seed command set up for each viewer, and the example lesson versions only
    # their viewer sees, all kept as the app. tool_calls, tool_call_reads and answer_removals (ticket 45's lineage,
    # ticket 84): each run's tool calls, the tables they read and the reasons its sentences were removed, which
    # src/strata/agent/runs.py writes beside the run row. viewer_settings (ticket 42): the language of answers and
    # drafts each viewer chose, kept as the app. ops/app/tests/test_app_grants.py reads every table the app writes as
    # itself from the code and fails when one is missing here.
    tables = ("usage_events", "agent_runs", "tool_calls", "tool_call_reads", "answer_removals", "evidence_opened",
              "drafts", "draft_states", "draft_exports",
              "draft_files", "follows", "disagreement_choices", "draft_fields", "exposures", "uploads",
              "upload_rows", "lesson_visits", "draft_lesson_choices", "start_here_choices", "seeded_examples",
              "example_lesson_versions", "viewer_settings")
    return [*[f"GRANT {privilege.replace('_', ' ')} ON {kind.upper()} {name} TO `{principal}`"
              for kind, name, privilege in ACCESS],
            *[f"GRANT SELECT, MODIFY ON TABLE strata.ops.{table} TO `{principal}`" for table in tables],
            f"GRANT SELECT ON TABLE strata.ops.draft_fields_latest TO `{principal}`",
            f"GRANT SELECT ON TABLE strata.ops.supplier_pairs TO `{principal}`",
            f"GRANT SELECT, MODIFY ON TABLE strata.ops.supplier_review_decisions TO `{principal}`",
            f"GRANT SELECT, MODIFY ON TABLE strata.ops.supplier_pair_labels TO `{principal}`",
            *[f"GRANT SELECT, MODIFY ON TABLE strata.ops.{table} TO `{principal}`" for table in LESSON_REVIEW_TABLES],
            *[f"GRANT SELECT, MODIFY ON TABLE strata.ops.{table} TO `{principal}`" for table in RETRIEVAL_TABLES],
            # Ticket 39: the Lessons page reads each reader's own counts from the weekly retrieval run.
            f"GRANT SELECT ON TABLE strata.ops.retrieval_feedback_viewers TO `{principal}`"]


def masks(principal: str, owner: str, roles: Roles | None = None) -> list[str]:
    """The column mask on each column of strata.ops that says who sent a passage report or asked a question
    (strata.lakehouse.masks, MASKED; ticket 64). The readers group may read every table in strata.ops
    (bundle/catalog.yml), so the mask gives each value only to the app's own service principal, which reads the
    reports back to tell a viewer's own, and to the owner, the user who deploys, whose identity runs the weekly
    retrieval job; everyone else reads NULL. A mask's SQL cannot take bound values, so both names are checked first,
    as grants() checks the principal.

    Then the row filter on each table whose rows only one reviewer group reads (FILTERED; ticket 63): the passage
    reports and each answer's sources keep what people asked and wrote, so only the app, the owner and the members of
    the group's workspace group in the roles file read their rows; everyone else reads none. The group's name is
    checked the same way."""
    if not PRINCIPAL.fullmatch(principal):
        raise ValueError(f"{principal!r} is not a service principal's application id.")
    if not (USER.fullmatch(owner) or PRINCIPAL.fullmatch(owner)):
        raise ValueError(f"{owner!r} is not a user name or an application id I can write into a mask.")
    roles = roles or load_roles()
    function = (f"CREATE OR REPLACE FUNCTION {MASK}(value STRING) RETURNS STRING "
                "COMMENT 'Who sent a passage report or asked a question: only the app and the owner read it.' "
                f"RETURN CASE WHEN current_user() IN ('{principal}', '{owner}') THEN value END")
    statements = [function, *[f"ALTER TABLE {table} ALTER COLUMN {column} SET MASK {MASK}"
                              for table, columns in MASKED.items() for column in columns]]
    for key in dict.fromkeys(FILTERED.values()):
        group = roles.groups[key]
        if not GROUP.fullmatch(group.workspace_group):
            raise ValueError(f"{group.workspace_group!r} is not a workspace group name I can write into a row filter.")
        statements.append(f"CREATE OR REPLACE FUNCTION {row_filter(key)}() RETURNS BOOLEAN "
                          f"COMMENT 'What people asked and reported: only the app, the owner and the {group.role}s "
                          "read it.' "
                          f"RETURN current_user() IN ('{principal}', '{owner}') "
                          f"OR is_account_group_member('{group.workspace_group}')")
        statements += [f"ALTER TABLE {table} SET ROW FILTER {row_filter(key)} ON ()"
                       for table, reader in FILTERED.items() if reader == key]
    return statements


def plan() -> list[tuple[str, str]]:
    """What a first deploy makes, read from the repo alone, as (what, name) pairs, with the Foundry agent's and the
    judge's keys in the env file, as the wizard fills it. The demo-ready command's dry run prints it
    (ops/demo/ready.py --fresh-workspace), so its list cannot drift from this deploy."""
    names = dayone.load_config()["names"]
    scope, instance = names["secret_scope"], names["app_state_instance"]
    filled = {"DATABRICKS_WAREHOUSE_ID": "the env file's", **dict.fromkeys((*FOUNDRY, *JUDGE), "set")}
    example = "00000000-0000-0000-0000-000000000000"  # the app's service principal, known only once it exists
    return ([("The app", f"{names['app']} ({DESCRIPTION})"), ("Its code", f"/Workspace/Users/<you>/{FOLDER}"),
             ("The Lakebase instance", instance)]
            + [("The app resource", resource["name"]) for resource in resources(filled, scope, instance)]
            + [("The user authorization scope", name) for name in SCOPES]
            + [("The secret", f"{scope}/{key}") for key in (*FOUNDRY, *JUDGE)]
            + [("The grants to the app's service principal", f"{len(grants(example))} grants on strata.ops"),
               ("The column mask", f"{MASK}, on {sum(len(columns) for columns in MASKED.values())} columns")]
            + [("The row filter", f"{row_filter(key)}, on {', '.join(t for t, k in FILTERED.items() if k == key)}")
               for key in dict.fromkeys(FILTERED.values())])


def secret_names(env: dict, scope: str) -> list[str]:
    """The secrets the app reads from the scope, by their names there: the ones resources() gives it."""
    return [resource["secret"]["key"] for resource in resources(env, scope) if "secret" in resource]


def write_secrets(scope: str, keys: list[str]) -> str:
    """What to write into the scope so the next deploy gives the app what it lacks. The Databricks CLI asks for each
    value, so none is ever typed into a command line."""
    commands = " and ".join(f"databricks secrets put-secret {scope} {key}" for key in keys)
    return f"Write {'it' if len(keys) == 1 else 'them'} with {commands}, then deploy again."


def and_list(items: Collection[str]) -> str:
    """"a, b and c"."""
    *rest, last = items
    return f"{', '.join(rest)} and {last}" if rest else last


def at(moment: dt.datetime) -> str:
    """A time as the deploy says it, such as "14:55:02 UTC on October 26, 2026"."""
    moment = moment.astimezone(dt.UTC)
    return f"{moment:%H:%M:%S} UTC on {dayone.long_date(moment.date())}"


STOPPED_AT_STEP_5 = "I stopped here and granted nothing."
# After a cold start of the app's compute, the app's deployments can still show step 5's deployment IN_PROGRESS when the
# deploy call comes back: the redeploy of 12:19 UTC on October 27, 2026 stopped on that, and the deployment succeeded a
# few minutes later. So step 5 reads them again every STEP_5_POLL_SECONDS, for up to STEP_5_WAIT_MINUTES, before it stops.
IN_PROGRESS = "IN_PROGRESS"
STEP_5_POLL_SECONDS = 10
STEP_5_WAIT_MINUTES = 20


def newest_first(found: list[dict]) -> list[dict]:
    """Deployments by their creation time, newest first, with one the Apps API gave no time first of all."""
    latest = dt.datetime.max.replace(tzinfo=dt.UTC)
    return sorted(found, key=lambda deployment: deployment.get("created") or latest, reverse=True)


def made(deployment: dict) -> str:
    """", made at 14:59:33 UTC on October 26, 2026," for a deployment the Apps API gave a time, or nothing."""
    return f", made at {at(deployment['created'])}," if deployment.get("created") else ""


def registered(name: str, found: list[dict], listed: Collection[str], started: dt.datetime) -> tuple[bool, str]:
    """Whether step 5 registered a deployment that succeeded, and the sentence that says so, from the app's
    deployments as apps list-deployments gives them. Only a deployment whose id was not listed just before the deploy
    call counts: on a stopped workspace the deploy call came back with nothing registered (October 26, 2026, ticket
    81). The ids, not this computer's clock, tell a new one, so a clock ahead of the workspace's, or a deployment with
    no creation time, does not fail a good deploy (ticket 81's review, follow-up 3); the time is only for the sentence."""
    new = newest_first([deployment for deployment in found if deployment["id"] not in listed])
    succeeded = [deployment for deployment in new if deployment["state"] == "SUCCEEDED"]
    if succeeded:
        return True, f"   The deployment {succeeded[0]['id']}{made(succeeded[0])} succeeded."
    if new:
        newest = new[0]
        said = f" with the message \"{' '.join(newest['message'].split())}\"" if newest.get("message") else ""
        return False, (f"Step 5's deployment {newest['id']}{made(newest)} has the state "
                       f"{newest['state']}{said}. {STOPPED_AT_STEP_5}")
    if not found:
        return False, f"The app {name} lists no deployment at all, so step 5 registered nothing. {STOPPED_AT_STEP_5}"
    newest = newest_first(found)[0]
    return False, (f"The app {name} has no deployment made since this run started at {at(started)}, so step 5 "
                   f"registered nothing. Its newest deployment is {newest['id']}{made(newest)} with the state "
                   f"{newest['state']}. {STOPPED_AT_STEP_5}")


def in_progress(found: list[dict], listed: Collection[str]) -> dict | None:
    """Step 5's newest deployment when it is still in progress and no new one has succeeded."""
    new = newest_first([deployment for deployment in found if deployment["id"] not in listed])
    if not new or new[0]["state"] != IN_PROGRESS or any(d["state"] == "SUCCEEDED" for d in new):
        return None
    return new[0]


def step_5_result(workspace, name: str, listed: Collection[str], started: dt.datetime,
                  sleep: Callable[[float], None]) -> tuple[bool, str]:
    """Whether step 5's deployment succeeded, and the sentence that says so. While the app's deployments show it in
    progress, read them again every STEP_5_POLL_SECONDS, for up to STEP_5_WAIT_MINUTES."""
    found = workspace.deployments(name)
    waiting = in_progress(found, listed)
    if waiting:
        print(f"   The deployment {waiting['id']} is still {IN_PROGRESS}, as it may be after the app's compute starts "
              f"cold, so I read its state again every {STEP_5_POLL_SECONDS} seconds, for up to "
              f"{dayone.count_words(STEP_5_WAIT_MINUTES, 'minute')}.")
        for _ in range(STEP_5_WAIT_MINUTES * 60 // STEP_5_POLL_SECONDS):
            sleep(STEP_5_POLL_SECONDS)
            found = workspace.deployments(name)
            if not in_progress(found, listed):
                break
    succeeded, said = registered(name, found, listed, started)
    if in_progress(found, listed):
        said += (f" It was still {IN_PROGRESS} after {dayone.count_words(STEP_5_WAIT_MINUTES, 'minute')}. Run "
                 f"`databricks apps get {name}`, and once its deployment shows SUCCEEDED, deploy again so steps 6 and 7 "
                 "run.")
    return succeeded, said


def run_statements(workspace, statements: list[str], stopped: str) -> bool:
    """Run each statement on the SQL warehouse, in order. When the warehouse refuses one, say the warehouse's state
    before its answer (ticket 81), then what stopping here leaves undone, and run no more."""
    for statement in statements:
        try:
            workspace.run_sql(statement)
        except Exception as error:  # the warehouse refused the statement, or the workspace refused the call
            lines, running = workspace_state.refused_statement(workspace, statement, error)
            for line in lines:
                print(line)
            print(stopped if running else f"{stopped} Deploy again once the SQL warehouse runs.")
            return False
    return True


def deploy(workspace, env: dict, build_web: Callable[[], tuple[int, str]] = build_web, dist: Path = DIST,
           keep_secrets: bool = False, now: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.UTC),
           sleep: Callable[[float], None] = time.sleep) -> int:
    started = now()
    names = dayone.load_config()["names"]
    name, scope = names["app"], names["secret_scope"]

    try:
        stopped = workspace_state.refusal(workspace, app=name)
    except Exception as error:  # the Apps or warehouses API refused the read itself
        stopped = workspace_state.unreadable(error)
    if stopped:
        print(stopped)
        return 2

    print("1. Building the web app.")
    code, output = build_web()
    if code != 0 or not (dist / "index.html").is_file():
        print("The web app did not build, so I left the workspace alone. npm said:")
        print("".join(f"    {line}\n" for line in output.splitlines()), end="")
        return 1

    print(f"2. Finding the app {name}.")
    app = workspace.app(name)
    existed = app is not None
    if app is None:
        workspace.create_app(name, DESCRIPTION)
        app = workspace.app(name)
        print(f"   I made the app {name}.")
    elif not is_strata(app):
        print(f"The app {name} is not Prism's: its description is {app['description']!r} and it runs "
              f"{app['source'] or 'nothing yet'}. I left it alone. Set names.app in ops/dayone/dayone.toml "
              "to a free app name.")
        return 1

    print("3. Giving it the SQL warehouse, the Application Insights connection string, each viewer's SQL token "
          "and the app state database.")
    lacking: set[str] = set()  # the secrets the app reads that the scope lacks, under --keep-secrets
    if keep_secrets:
        expected = secret_names(env, scope)
        print(f"   I wrote no secret, because you asked me to keep them (--keep-secrets). I expect these secrets in "
              f"the scope {scope}: {', '.join(expected)}.")
        listed = set(workspace.secret_keys(scope))
        lacking = {key for key in expected if key not in listed}
    traces = APPINSIGHTS_NAME not in lacking
    if not traces:
        print(f"   The secret scope {scope} has no {APPINSIGHTS_NAME}, so the app sends no traces to Application "
              f"Insights. {write_secrets(scope, [APPINSIGHTS_NAME])}")
    foundry = has_foundry(env, lacking)
    if foundry and keep_secrets:
        print("   The Foundry agent's four keys are in the secret scope, so /api/ask answers through the agent.")
    elif foundry:
        for key in FOUNDRY:
            workspace.put_secret(scope, key, env[key].strip())
        print("   I saved the Foundry agent's four keys in the secret scope, so /api/ask answers through the agent.")
    elif has_foundry(env):
        absent = [key for key in FOUNDRY if key in lacking]
        print(f"   The secret scope {scope} has no {', '.join(absent)}, so the app gets no Foundry agent and /api/ask "
              f"says there is no agent. {write_secrets(scope, absent)}")
    else:
        missing = ", ".join(key for key in FOUNDRY if not (env.get(key) or "").strip())
        print(f"   .env has no {missing}, so the app gets no Foundry agent and /api/ask says there is no agent.")
    judge = has_judge(env, lacking)
    if judge and keep_secrets:
        print("   The two Azure OpenAI keys are in the secret scope, so the model that judges sentences checks "
              "each answer.")
    elif judge:
        for key in JUDGE:
            workspace.put_secret(scope, key, env[key].strip())
        print("   I saved the two Azure OpenAI keys in the secret scope, so the model that judges sentences checks "
              "each answer.")
    elif has_judge(env):
        absent = [key for key in JUDGE if key in lacking]
        print(f"   The secret scope {scope} has no {', '.join(absent)}, so the app gets no judge and removes every "
              f"sentence that needs one. {write_secrets(scope, absent)}")
    else:
        missing = ", ".join(key for key in JUDGE if not (env.get(key) or "").strip())
        print(f"   .env has no {missing}, so the app gets no judge and removes every sentence that needs one.")
    genie_space = (env.get("GENIE_SPACE_ID") or "").strip() or None
    if genie_space:
        print(f"   The app asks the Genie space {genie_space} as each viewer.")
    else:
        print("   .env has no GENIE_SPACE_ID, so ask_genie says Genie is unavailable.")
    instance = names["app_state_instance"]
    try:
        workspace.app_state_database(instance)
        print(f"   The Lakebase instance {instance} is running, so the app keeps app state there.")
    except Exception as error:  # a workspace without Lakebase, a quota, or an instance that would not start
        reason = " ".join(str(error).split()) or type(error).__name__
        print(f"   I could not make or start the Lakebase instance {instance}: {reason}. The app gets no app state "
              "database, so it keeps no packages.")
        instance = None
    workspace.configure_app(name, DESCRIPTION, resources(env, scope, instance, lacking), SCOPES)

    folder = f"/Workspace/Users/{workspace.me()}/{FOLDER}"
    files = package(dist, foundry, judge, genie_space, traces)
    print(f"4. Uploading {len(files)} files to {folder}.")
    workspace.upload(folder, files)

    print("5. Deploying the app. This takes a few minutes.")
    if not app["running"]:
        workspace.start_app(name)
    listed = {deployment["id"] for deployment in workspace.deployments(name)}
    url = workspace.deploy(name, folder)
    succeeded, said = step_5_result(workspace, name, listed, started, sleep)
    print(said)
    if not succeeded:
        return 1

    print("6. Letting the app's own service principal write usage events, agent runs, opened sources and drafts to "
          f"strata.ops, with the lesson review record ({and_list(LESSON_REVIEW_TABLES)}) and the retrieval loop's record "
          f"({and_list(RETRIEVAL_TABLES)}).")
    if not run_statements(workspace, grants(app["principal"]),
                          "I stopped at step 6, so the app's own service principal may lack some of its grants."):
        return 1

    print("7. Masking who sent each passage report and who asked each question from everyone but the app and you.")
    if not run_statements(workspace, masks(app["principal"], workspace.me()),
                          "I stopped at step 7, so some columns may lack their mask."):
        return 1

    if existed:
        # A browser keeps the app session it opened before this deploy, with that session's token and scopes, until it
        # expires; a session consented before the app had the sql scope (the day-one probe app, an older deploy) gets 403
        # from the warehouse on every page (ticket 83, October 26, 2026).
        print("   The app existed before this deploy. Anyone who opened its address earlier, before it had the user "
              "authorization scopes, keeps that window's old session: the pages say the account cannot read the data until "
              "they sign out of the app once, or clear the site's cookies, and open it again from the workspace's Apps page.")
    print(f"Prism is running at {url}")
    return 0


def main(argv: list[str] | None = None, workspace=None, **options) -> int:
    """The command. The tests pass a fake workspace, and through options a stand-in for the web build."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env-file", type=Path, default=None,
                        help="The main checkout's .env, which the wizard filled. That file is the default.")
    parser.add_argument("--keep-secrets", action="store_true",
                        help="Write no secret. Check instead that the secret scope already holds each secret the app "
                             "reads, and name any it lacks; the app then gets nothing that reads that secret. Use it "
                             "to redeploy new code from a session that may not write secrets, once the user has "
                             "written them.")
    args = parser.parse_args(argv)
    try:
        env = load_workspace_env(args.env_file)
    except WorkspaceEnvError as error:
        print(error, file=sys.stderr)
        return 2
    if workspace is None:
        from app_live import LiveApps

        workspace = LiveApps(env)
    return deploy(workspace, env, keep_secrets=args.keep_secrets, **options)


if __name__ == "__main__":
    sys.exit(main())
