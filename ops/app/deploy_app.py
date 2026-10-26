# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0", "pyyaml==6.0.3"]
# ///
"""Build Strata's web app and deploy Strata as the Databricks App that acts as each viewer.

Run it from the main checkout after the wizard and the bundle deploy (ops/bundle/deploy.py):

    uv run --script ops/app/deploy_app.py --env-file .env

It needs npm, which builds the web app. It does these things, in order:

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
5. It deploys the app, starting it first if it is stopped, and waits for it.
6. It grants the app's own service principal what the server needs to write usage events, agent
   runs, opened sources, drafts, decisions and labels on supplier pairs, and the lesson review record,
   and nothing more: USE CATALOG on strata, USE SCHEMA on strata.ops, SELECT and MODIFY on
   strata.ops.usage_events, agent_runs, evidence_opened, drafts, draft_states, draft_exports,
   draft_files, follows, ticket 23's disagreement_choices and draft_fields, ticket 44's exposures, SELECT on its view
   draft_fields_latest, SELECT on strata.ops.supplier_pairs, SELECT and MODIFY on
   strata.ops.supplier_review_decisions and strata.ops.supplier_pair_labels, and SELECT and MODIFY on
   ticket 29's lesson_review_acts, lesson_review_items, lesson_versions, lesson_sources and
   lesson_review_notes, and ticket 32's candidate_labels, label_decisions, answer_citations,
   retrieval_grades and retrieval_queries. Viewers read as themselves, through the bundle's grants,
   and no reviewer group may write the lesson review record or the retrieval loop's record outside
   the app.
7. It masks the columns that say who sent each passage report and who asked each question
   (strata.lakehouse.masks; ticket 64): one mask function, strata.ops.mask_viewer, gives their values
   only to the app's own service principal and to you, who own the catalog and whose identity runs
   the weekly retrieval job. Every other reader reads NULL there, though the bundle lets them read
   all of strata.ops.
8. It prints the app's address.

Run it again after every bundle deploy. The grants in bundle/catalog.yml replace any other
grants on the strata catalog and its schemas (bundle/README.md), so a bundle deploy removes the
app's USE CATALOG and USE SCHEMA, and its usage events, agent runs, opened sources, drafts, decisions
and labels stop being written.

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
import re
import subprocess
import sys
from collections.abc import Callable, Collection
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "bundle", HERE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import dayone  # noqa: E402
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402

from strata.lakehouse.masks import MASK, MASKED  # noqa: E402

DESCRIPTION = "Strata, procurement intelligence on World Bank open data"
PROBE_DESCRIPTION = "Strata day-one probe app"  # ops/dayone/live.py's PROBE_APP_DESCRIPTION
FOLDER = "strata-app"
DIST = REPO / "web" / "dist"
# The user authorization scopes: each viewer's forwarded token may run SQL on the warehouse, and ask the Genie space
# as that viewer (ask_genie, ticket 33). Without dashboards.genie the forwarded token gets 403 from Genie.
SCOPES = ["sql", "dashboards.genie"]
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
    tables = ("usage_events", "agent_runs", "evidence_opened", "drafts", "draft_states", "draft_exports",
              "draft_files", "follows", "disagreement_choices", "draft_fields", "exposures", "uploads",
              "upload_rows", "lesson_visits", "draft_lesson_choices")
    return [f"GRANT USE CATALOG ON CATALOG strata TO `{principal}`",
            f"GRANT USE SCHEMA ON SCHEMA strata.ops TO `{principal}`",
            *[f"GRANT SELECT, MODIFY ON TABLE strata.ops.{table} TO `{principal}`" for table in tables],
            f"GRANT SELECT ON TABLE strata.ops.draft_fields_latest TO `{principal}`",
            f"GRANT SELECT ON TABLE strata.ops.supplier_pairs TO `{principal}`",
            f"GRANT SELECT, MODIFY ON TABLE strata.ops.supplier_review_decisions TO `{principal}`",
            f"GRANT SELECT, MODIFY ON TABLE strata.ops.supplier_pair_labels TO `{principal}`",
            *[f"GRANT SELECT, MODIFY ON TABLE strata.ops.{table} TO `{principal}`" for table in LESSON_REVIEW_TABLES],
            *[f"GRANT SELECT, MODIFY ON TABLE strata.ops.{table} TO `{principal}`" for table in RETRIEVAL_TABLES],
            # Ticket 39: the Lessons page reads each reader's own counts from the weekly retrieval run.
            f"GRANT SELECT ON TABLE strata.ops.retrieval_feedback_viewers TO `{principal}`"]


def masks(principal: str, owner: str) -> list[str]:
    """The column mask on each column of strata.ops that says who sent a passage report or asked a question
    (strata.lakehouse.masks, MASKED; ticket 64). The readers group may read every table in strata.ops
    (bundle/catalog.yml), so the mask gives each value only to the app's own service principal, which reads the
    reports back to tell a viewer's own, and to the owner, the user who deploys, whose identity runs the weekly
    retrieval job; everyone else reads NULL. A mask's SQL cannot take bound values, so both names are checked first,
    as grants() checks the principal."""
    if not PRINCIPAL.fullmatch(principal):
        raise ValueError(f"{principal!r} is not a service principal's application id.")
    if not (USER.fullmatch(owner) or PRINCIPAL.fullmatch(owner)):
        raise ValueError(f"{owner!r} is not a user name or an application id I can write into a mask.")
    function = (f"CREATE OR REPLACE FUNCTION {MASK}(value STRING) RETURNS STRING "
                "COMMENT 'Who sent a passage report or asked a question: only the app and the owner read it.' "
                f"RETURN CASE WHEN current_user() IN ('{principal}', '{owner}') THEN value END")
    return [function, *[f"ALTER TABLE {table} ALTER COLUMN {column} SET MASK {MASK}"
                        for table, columns in MASKED.items() for column in columns]]


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
               ("The column mask", f"{MASK}, on {sum(len(columns) for columns in MASKED.values())} columns")])


def secret_names(env: dict, scope: str) -> list[str]:
    """The secrets the app reads from the scope, by their names there: the ones resources() gives it."""
    return [resource["secret"]["key"] for resource in resources(env, scope) if "secret" in resource]


def write_secrets(scope: str, keys: list[str]) -> str:
    """What to write into the scope so the next deploy gives the app what it lacks. The Databricks CLI asks for each
    value, so none is ever typed into a command line."""
    commands = " and ".join(f"databricks secrets put-secret {scope} {key}" for key in keys)
    return f"Write {'it' if len(keys) == 1 else 'them'} with {commands}, then deploy again."


def deploy(workspace, env: dict, build_web: Callable[[], tuple[int, str]] = build_web, dist: Path = DIST,
           keep_secrets: bool = False) -> int:
    names = dayone.load_config()["names"]
    name, scope = names["app"], names["secret_scope"]

    print("1. Building the web app.")
    code, output = build_web()
    if code != 0 or not (dist / "index.html").is_file():
        print("The web app did not build, so I left the workspace alone. npm said:")
        print("".join(f"    {line}\n" for line in output.splitlines()), end="")
        return 1

    print(f"2. Finding the app {name}.")
    app = workspace.app(name)
    if app is None:
        workspace.create_app(name, DESCRIPTION)
        app = workspace.app(name)
        print(f"   I made the app {name}.")
    elif app["description"] not in (DESCRIPTION, PROBE_DESCRIPTION):
        print(f"The app {name} is not Strata's: its description is {app['description']!r} and it runs "
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
        workspace.start(name)
    url = workspace.deploy(name, folder)

    print("6. Letting the app's own service principal write usage events, agent runs, opened sources and drafts to strata.ops.")
    for statement in grants(app["principal"]):
        workspace.run_sql(statement)

    print("7. Masking who sent each passage report and who asked each question from everyone but the app and you.")
    for statement in masks(app["principal"], workspace.me()):
        workspace.run_sql(statement)

    print(f"Strata is running at {url}")
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
