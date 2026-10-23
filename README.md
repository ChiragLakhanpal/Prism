# Strata

Strata is procurement intelligence on World Bank open data. It links records of past procurements to the documents that explain how and why they went the way they did. Every claim it makes cites a record or a numbered paragraph, and every number comes from a tool. The plan is in `docs/PLAN.md`, the rules for working here are in `CLAUDE.md`, and the words are in `GLOSSARY.md`.

Strata is an independent demo built on World Bank open data. It is not a World Bank product, and the World Bank has not reviewed or endorsed it.

## Install

You need uv, Node.js 24 or later with npm, git, and python3 3.11 or later, which runs the gate and the guard hook.

Clone Strata outside a temp folder such as `/tmp`. The guard hook lets agents write anywhere in a temp folder, so its own tests fail when the repo sits in one.

After cloning, run this command once, and again in each new worktree:

    scripts/install

It does these things, in order:

1. It installs Python 3.12 and the Python packages with uv.
2. It installs the web app's packages with npm.
3. It downloads the Chromium browser that the Playwright tests use.
4. It sets `core.hooksPath` to `.githooks`, so git runs the gate before every commit.

The install needs the network. The gate and `scripts/dev` do not.

Secrets go in `.env` in the main checkout, never in git. `.env.example` lists the keys. To see which keys are set without printing their values, run `python3 .claude/hooks/guard.py --env-keys`.

## The gate

Git runs the gate before every commit, as CLAUDE.md rule 6 requires. It also runs the gate before a merge commit, through `.githooks/pre-merge-commit`. To run the gate by hand, use this command:

    .githooks/pre-commit

It runs the steps in `gates/steps.toml`. Steps that do not depend on each other run side by side, in lanes. Today it has these steps:

1. Scan the staged changes and the history of the branch for secrets. This step runs alone, before the lanes start.
2. Run five lanes side by side:
   - The guard lane tests the guard hook.
   - The python lane builds the fixture database from the recorded sources, reads P156634's Procurement Plans into STEP rows, and prints its size. The nightly job's own tasks build bronze, silver, gold and the data readiness measures from the recorded pages. Then it runs the Python tests that may read that database, on four pytest-xdist workers: the tests under `tests/` and the bundle commands' tests under `ops/bundle/tests/`. They cover the gate, the server, the fixture and its ground truth, the ground-truth SQL on DuckDB, the lakehouse run and its fetch, the catalog and its table definitions, the config files, the nightly job, the plan reader and the bundle commands.
   - The ops lane runs the Python tests for the wizard and the day-one probes, on six pytest-xdist workers.
   - The web lane type checks and bundles the web app, then runs the Playwright tests against it.
   - The sql lane lints the SQL (`gates/sql_lint.py`): every query names its tables in three parts and binds its values as parameters.

The gate prints each step's name and time as the step finishes. When a step fails, the gate stops the other lanes, prints the output of the step that failed, and fails. The gate tells uv, npm and Playwright to work offline, and the tests refuse any connection that leaves this computer. It prints its total time and fails when the whole run takes longer than two minutes. When every staged file is Markdown, it runs only the secret scan.

The gate tests the files in your working tree. When code is staged, the gate first checks that no tracked file has changes you have not staged, so the tests see what you commit. To add a ground-truth SQL check, add a `.sql` file to `tests/ground_truth/`. Write the query in Databricks SQL, with three-part names such as `strata.ops.pipeline_runs`; the engine adapter rewrites it for DuckDB. Put its expected rows in `-- expect:` lines, one CSV row per line with the header first, and name the source of those values in a comment. A `-- param: name = value` line binds a parameter, and a `-- engines: duckdb, databricks` line marks a query that `ops/bundle/check.py same-rows` also runs on the workspace's SQL warehouse. Values copied from a source, with the page or record they came from, go in `tests/ground_truth/values.toml`, and a test checks each one against the recorded fixture.

The fixture build also creates the strata catalog's schemas and tables from `src/strata/lakehouse/tables/`, and it stops when any table has no `public_from` column. To add a table, add one file there, `<schema>/<table>.sql`, that starts with `CREATE TABLE IF NOT EXISTS strata.<schema>.<table> (`. A view is one file in `src/strata/lakehouse/views/<schema>/<view>.sql` that starts with `CREATE OR REPLACE VIEW strata.<schema>.<view> AS`, created after the tables.

To add a check, add a step to `gates/steps.toml`. A step with no `lane` key runs alone. It waits for every step above it, and every step below it waits for it. To run a step side by side with others, give it a lane, such as `lane = "web"`, and put it among the steps that have lanes. It runs after the steps above it in the same lane. Use a new lane's name when the step needs nothing from the other steps. A step that needs another step's output goes in that step's lane, below it. A new pytest step names the folders it tests, and the gate's own tests check that each folder in `testpaths` in `pyproject.toml` runs in exactly one step. A test folder whose tests read the fixture database goes in the python lane, below the build, and in `FIXTURE_READERS` in `tests/test_gate.py`, which checks that it runs after the build.

The Python tests run on pytest-xdist workers, so each test runs beside others in separate processes that share this computer's files and ports. A test must write only under its own `tmp_path` or a throwaway repo, open the fixture database read-only (the `fixture_db` fixture in `tests/conftest.py` gives its path), never change the working folder or set an environment variable, and listen on a port the system picks (port 0). A test that must name its port takes one from below the system's range, as `free_port` in `tests/test_server_start.py` does. When a test cannot run beside the others, mark it with `@pytest.mark.xdist_group("<name>")`, say why in a comment, and add `--dist loadgroup` to its step, so the tests in that group run on one worker.

When a lane gets slow again, first run `uv run --frozen pytest --durations=15 <its folders>` to find the slowest tests. A single slow test sets a floor that no number of workers can lower. Then try more workers on that lane's step (`--numprocesses`), and keep the number that gives the lower total gate time over three runs by hand. The lanes share this computer's processors, so more workers in one lane can slow the others. You can also move a folder that does not read the fixture database to a lane of its own.

To run the nightly job's tasks in order on an empty DuckDB database, over the recorded pages, and see the rows they write, run `uv run --frozen python -m strata.lakehouse.nightly`. To deploy the catalog and the job to the shared workspace, follow `bundle/README.md`.

A query that code builds from table or column names, never values, says so on any line of the statement that builds it with `# sql-lint: names only`. Every other query is a fixed text with `:name` parameters.

## Merge a ticket

Git runs the gate before a merge commit too. The gate tests the merged files with the packages that this checkout has installed, and a merge can bring packages that are not installed yet. To merge a ticket branch, use these steps:

1. Run `git merge --no-ff --no-commit <branch>`.
2. Run `scripts/install`, so this checkout has every package that `uv.lock` and `web/package-lock.json` name.
3. Run `git commit --no-edit`. Git runs the gate before it makes the merge commit.

If the gate stopped a merge, the merge is still in progress. Run steps 2 and 3 to finish it, or run `git merge --abort` to undo it.

## Run the app

    scripts/dev

This starts the server and the web app's dev server and prints the web app's address. The server listens on `STRATA_SERVER_PORT` and the web app on `STRATA_WEB_PORT`. When a variable is unset, the script picks a free port, so copies from several worktrees can run side by side. The web app passes `/api` calls on to the server.

To start only the server, run `uv run python -m strata.server`. It prints the address it listens on. Its routes today:

- `GET /api/health` says the server is up.
- `GET /api/me` names the viewer that the Databricks App forwarded. It never returns the viewer's token.
- `POST /api/ask` takes `{"question": "..."}` and streams the run's events as `text/event-stream`, ending with a `done` event that carries the run id. Until the agent exists, the run sends one `error` event with the code `no_agent`.
- `GET /api/projects/{project_id}/procurement/{agency_id}` checks an implementing agency's latest Procurement Plan, and `GET /api/projects/{project_id}/procurement/{agency_id}/{version}` checks the version with that plan date, such as `2026-10-09`. Each runs the tool registry's `check_plan` as the viewer and returns its result as JSON. Both take `?asof=` (a date) and `?view=` (`staff`, `piu` or `public`). Until ticket 40 applies each view's rules, every view gets the World Bank staff result. A viewer whose token cannot read the strata catalog gets HTTP 403 with the code `permission` and no rows. When the data service fails, or its database file cannot be opened, the answer is HTTP 503 with the code `data_service` and a reference to look up in the server log. When a tool breaks its contract, the answer is HTTP 500 with the code `tool_contract` and a reference.

The server reads its data as each viewer, from one of two places, chosen when it starts:

- `STRATA_DATABASE_FILE` names a DuckDB file, which each request opens read-only. To run against the gate's fixture, set it to `data/out/fixture.duckdb`.
- Otherwise, `DATABRICKS_HOST` and `DATABRICKS_WAREHOUSE_ID` name the workspace and its SQL warehouse, and each query runs with the token the Databricks App forwarded for the viewer.

With neither, the routes that need data answer HTTP 503 with the code `no_data_service`.

## Where things live

Each part of the spec has one home. Folders marked "later" do not exist yet. The ticket that builds a part creates its folder.

| Part | Where |
|---|---|
| The gate | `.githooks/pre-commit` and `.githooks/pre-merge-commit`, which run `gates/offline.py` over `gates/steps.toml` |
| The guard hook and its tests | `.claude/hooks/` |
| Viewer identity | `src/strata/dbx.py` |
| The harness: each turn's evidence and the stream helpers | `src/strata/harness/` |
| The app server | `src/strata/server/` |
| The web app, with its `api`, `sse`, `store` and `export` libraries | `web/src/` and `web/src/lib/` |
| The copy file, for now | `web/src/copy.ts` |
| Python tests for seams 1, 2, 3 and 5, and for the gate | `tests/` |
| The guard that keeps every Python test off the network | `conftest.py` at the root |
| Screen tests (seam 4) | `web/tests/` |
| Responses recorded once and shared by the server and screen tests | `tests/fixtures/api/` |
| Fixture inputs, and the fixture database the gate builds | `data/fixture/`, and `data/out/`, which git ignores |
| The list of recorded sources, and the recorded files. This `sources.toml` lists recorded copies of public pages, grouped by dataset. The source registry, `config/sources.toml`, lists what the nightly job fetches, and each of its entries names, in `fixture_dataset`, the dataset here whose files stand in for it in the gate | `data/fixture/sources.toml` and `data/fixture/recorded/` (see `data/fixture/README.md`) |
| The recording command, which refetches the fixture and prints a diff | `src/strata/fixture/` (`uv run python -m strata.fixture.record`) |
| Ground-truth SQL, and the ground-truth values with their sources | `tests/ground_truth/` (`*.sql` and `values.toml`) |
| The engine adapter, which runs one Databricks SQL query on the SQL warehouse, in a job and on DuckDB | `src/strata/lakehouse/engine.py` |
| The table definitions, one `CREATE TABLE IF NOT EXISTS` file per table, and the view definitions, one `CREATE OR REPLACE VIEW` file per view, built by the gate and the deploy | `src/strata/lakehouse/tables/<schema>/` and `src/strata/lakehouse/views/<schema>/` |
| The nightly job's tasks | `src/strata/lakehouse/nightly.py` |
| The bundle: the strata catalog, its schemas, the volume, the grants and the nightly job, with its notes | `databricks.yml` and `bundle/` |
| The deploy command and the workspace checks for the bundle | `ops/bundle/` |
| The lakehouse: where pages come from (the live APIs, or the recorded fixture in the gate), bronze and the contact details it never keeps, the cleaning rules, silver's transforms, gold's tables (one SQL query each), and the data readiness measures (one SQL file per source) | `src/strata/lakehouse/`: `pages.py`, `bronze.py` and `contacts.py`, `clean.py`, `silver/`, `gold/`, `readiness/` |
| The SQL lint: three-part names and bound parameters | `gates/sql_lint.py` |
| The plan reader: a project's Procurement Plans into STEP rows, with delay from the first published planned date and data notes, under the daily page cap | `src/strata/lakehouse/plans.py` and `src/strata/lakehouse/sql/plans/` (`uv run --frozen python -m strata.lakehouse.plans` runs it on the fixture) |
| The document reader: documents and their pages, the layout parser (Route B, offline and live) and STEP's words | `src/strata/reader/` |
| The live plan run on the workspace | `ops/plans/run_live.py` |
| The knowledge model | `src/strata/knowledge/` (later) |
| The tool registry: one entry per tool, with its parameters (always an optional `as_of` date), adapter, benchmark question and result shape. Adding a tool is one entry plus its adapter | `config/tools.toml` |
| The registry at work (the agent's tool list, calling a tool by name, the tool contract) and the tools, with their SQL. `check_plan` is the first | `src/strata/tools/` |
| Which engine runs a viewer's queries in the server | `src/strata/server/engines.py` |
| The agent: instructions, sync, the answer loop, the verifier and workflows | `src/strata/agent/` (later) |
| The estimates: comparables, models and the replay harness | `src/strata/estimates/` (later) |
| The registry and config files for the change drill: the source registry, the slice file, the model file, the thresholds file and the tool registry, each read by one function in `src/strata/config.py` | `config/` |
| The rest of the change drill's config files: the evidence ladder, the package form and roles | `config/` (later) |
| The benchmark file, with one question per tool so far. Ticket 33 adds the runner and the other kinds of question | `evals/benchmark.yaml` |
| The other evaluation sets | `evals/` (later) |
| The dashboard definition | `dashboard/` (later) |
| The credentials wizard and the day-one probes | `ops/` (ticket 03) |

## Ports at a glance

| Variable | Used by | When unset |
|---|---|---|
| `STRATA_SERVER_PORT` | the server, and the web app's dev server to reach it | a free port |
| `STRATA_SERVER_HOST` | the server, and the web app's dev server to reach it | `127.0.0.1` |
| `STRATA_WEB_PORT` | the web app's dev server | a free port |

The Playwright tests always pick their own free port, so they never clash with a running dev server.
