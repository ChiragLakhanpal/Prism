# Strata

Strata is procurement intelligence on World Bank open data. It links records of past procurements to the documents that explain how and why they went the way they did. Every claim it makes cites a record or a numbered paragraph, and every number comes from a tool. The plan is in `docs/PLAN.md`, the rules for working here are in `CLAUDE.md`, and the words are in `GLOSSARY.md`.

Strata is an independent demo built on World Bank open data. It is not a World Bank product, and the World Bank has not reviewed or endorsed it.

## Install

You need uv, Node.js 24 or later with npm, git, and python3 3.11 or later, which runs the gate and the guard hook. Then run this once after cloning, and again in each new worktree:

    scripts/install

It installs Python 3.12 and the Python packages with uv, installs the web app's packages with npm, downloads the Chromium browser that the Playwright tests use, and sets `core.hooksPath` to `.githooks` so git runs the gate before every commit. It needs the network. Nothing after it does.

Secrets go in `.env` in the main checkout, never in git. `.env.example` lists the keys. To see which keys are set without printing their values, run `python3 .claude/hooks/guard.py --env-keys`.

## The gate

The gate runs before every commit (CLAUDE.md rule 6). Run it by hand the same way:

    .githooks/pre-commit

It runs the steps in `gates/steps.toml` in order and stops at the first one that fails. Today it scans the staged changes and the whole history of the branch for secrets, runs the guard hook's own tests, builds the fixture database, runs the Python tests (the gate itself, the ground-truth SQL on DuckDB and the server) and runs the Playwright tests against the built web app. It switches the network off for uv, npm and the tests, prints its total time, and fails when a run takes longer than two minutes. When every staged file is Markdown, it runs only the secret scan.

The gate tests the files in your working tree, so a change you have not staged still counts. To add a check, add a step to `gates/steps.toml`. To add a ground-truth SQL check, add a `.sql` file to `tests/ground_truth/`. Put its expected rows in `-- expect:` lines, one CSV row per line with the header first, and name the source of those values in a comment.

## Run the app

    scripts/dev

This starts the server and the web app's dev server and prints the web app's address. The server listens on `STRATA_SERVER_PORT` and the web app on `STRATA_WEB_PORT`. When a variable is unset, the script picks a free port, so copies from several worktrees can run side by side. The web app passes `/api` calls on to the server.

To start only the server, run `uv run python -m strata.server`. It prints the address it listens on. Its routes today:

- `GET /api/health` says the server is up.
- `GET /api/me` names the viewer that the Databricks App forwarded. It never returns the viewer's token.
- `POST /api/ask` takes `{"question": "..."}` and streams the run's events as `text/event-stream`, ending with a `done` event that carries the run id. Until the agent exists, the run sends one `error` event with the code `no_agent`.

## Where things live

Each part of the spec has one home. Folders marked "later" do not exist yet; the ticket that builds the part creates it there.

| Part | Where |
|---|---|
| The gate | `.githooks/pre-commit`, which runs `gates/offline.py` over `gates/steps.toml` |
| The guard hook and its tests | `.claude/hooks/` |
| Viewer identity | `src/strata/dbx.py` |
| The harness: each turn's evidence and the stream helpers | `src/strata/harness/` |
| The app server | `src/strata/server/` |
| The web app, with its `api`, `sse`, `store` and `export` libraries | `web/src/` and `web/src/lib/` |
| The copy file, for now | `web/src/copy.ts` |
| Python tests for seams 1, 2, 3 and 5, and for the gate | `tests/` |
| Screen tests (seam 4) | `web/tests/` |
| Responses recorded once and shared by the server and screen tests | `tests/fixtures/api/` |
| Fixture inputs, and the fixture database the gate builds | `data/fixture/` and `data/out/` (not in git) |
| Ground-truth SQL | `tests/ground_truth/` |
| The lakehouse: sources, transforms and data readiness | `src/strata/lakehouse/` (later) |
| The document reader | `src/strata/reader/` (later) |
| The knowledge model | `src/strata/knowledge/` (later) |
| The tool registry and its tools | `src/strata/tools/` (later) |
| The agent: instructions, sync, the answer loop, the verifier and workflows | `src/strata/agent/` (later) |
| The estimates: comparables, models and the replay harness | `src/strata/estimates/` (later) |
| The registry and config files for the change drill (sources, thresholds, slice, models, evidence ladder, package form, roles) | `config/` (later) |
| The benchmark and evaluation sets | `evals/` (later) |
| The dashboard definition | `dashboard/` (later) |
| The credentials wizard and the day-one probes | `ops/` (ticket 03) |

## Ports at a glance

| Variable | Used by | When unset |
|---|---|---|
| `STRATA_SERVER_PORT` | the server, and the web app's dev server to reach it | a free port |
| `STRATA_SERVER_HOST` | the server | `127.0.0.1` |
| `STRATA_WEB_PORT` | the web app's dev server | a free port |

The Playwright tests always pick their own free port, so they never clash with a running dev server.
