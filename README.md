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

It runs the steps in `gates/steps.toml` in order and stops at the first one that fails. Today it has these steps:

1. Scan the staged changes and the history of the branch for secrets.
2. Test the guard hook.
3. Build the fixture database.
4. Run the Python tests. They cover the gate, the ground-truth SQL on DuckDB, the catalog and its table definitions, the config files, the nightly job, the bundle commands and the server.
5. Type check and bundle the web app.
6. Run the Playwright tests against the built web app.

The gate tells uv, npm and Playwright to work offline, and the tests refuse any connection that leaves this computer. It prints its total time and fails when a run takes longer than two minutes. When every staged file is Markdown, it runs only the secret scan.

The gate tests the files in your working tree. When code is staged, the gate first checks that no tracked file has changes you have not staged, so the tests see what you commit. To add a check, add a step to `gates/steps.toml`. To add a ground-truth SQL check, add a `.sql` file to `tests/ground_truth/`. Write the query in Databricks SQL, with three-part names such as `strata.ops.pipeline_runs`; the engine adapter rewrites it for DuckDB. Put its expected rows in `-- expect:` lines, one CSV row per line with the header first, and name the source of those values in a comment. A `-- param: name = value` line binds a parameter, and a `-- engines: duckdb, databricks` line marks a query that `ops/bundle/check.py same-rows` also runs on the workspace's SQL warehouse.

The fixture build also creates the strata catalog's schemas and tables from `src/strata/lakehouse/tables/`, and it stops when any table has no `public_from` column. To add a table, add one file there, `<schema>/<table>.sql`, that starts with `CREATE TABLE IF NOT EXISTS strata.<schema>.<table> (`.

To run the nightly job's tasks in order on an empty DuckDB database and see the rows they write, run `uv run --frozen python -m strata.lakehouse.nightly`. To deploy the catalog and the job to the shared workspace, follow `bundle/README.md`.

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
| Screen tests (seam 4) | `web/tests/` |
| Responses recorded once and shared by the server and screen tests | `tests/fixtures/api/` |
| Fixture inputs, and the fixture database the gate builds | `data/fixture/`, and `data/out/`, which git ignores |
| Ground-truth SQL | `tests/ground_truth/` |
| The engine adapter, which runs one Databricks SQL query on the SQL warehouse, in a job and on DuckDB | `src/strata/lakehouse/engine.py` |
| The table definitions, one `CREATE TABLE IF NOT EXISTS` file per table, built by the gate and the deploy | `src/strata/lakehouse/tables/<schema>/` |
| The nightly job's tasks | `src/strata/lakehouse/nightly.py` |
| The bundle: the strata catalog, its schemas, the volume, the grants and the nightly job, with its notes | `databricks.yml` and `bundle/` |
| The deploy command and the workspace checks for the bundle | `ops/bundle/` |
| The lakehouse: sources, transforms and data readiness | `src/strata/lakehouse/` (sources and transforms later) |
| The document reader | `src/strata/reader/` (later) |
| The knowledge model | `src/strata/knowledge/` (later) |
| The tool registry and its tools | `src/strata/tools/` (later) |
| The agent: instructions, sync, the answer loop, the verifier and workflows | `src/strata/agent/` (later) |
| The estimates: comparables, models and the replay harness | `src/strata/estimates/` (later) |
| The registry and config files for the change drill: the source registry, the slice file, the model file and the thresholds file, each read by one function in `src/strata/config.py` | `config/` |
| The rest of the change drill's config files: the evidence ladder, the package form and roles | `config/` (later) |
| The benchmark and evaluation sets | `evals/` (later) |
| The dashboard definition | `dashboard/` (later) |
| The credentials wizard and the day-one probes | `ops/` (ticket 03) |

## Ports at a glance

| Variable | Used by | When unset |
|---|---|---|
| `STRATA_SERVER_PORT` | the server, and the web app's dev server to reach it | a free port |
| `STRATA_SERVER_HOST` | the server, and the web app's dev server to reach it | `127.0.0.1` |
| `STRATA_WEB_PORT` | the web app's dev server | a free port |

The Playwright tests always pick their own free port, so they never clash with a running dev server.
