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
2. Run seven lanes side by side:
   - The guard lane tests the guard hook.
   - The python lane builds the fixture database from the recorded sources, reads P156634's Procurement Plans into STEP rows, and prints its size. The nightly job's own tasks build bronze, silver, gold and the data readiness measures from the recorded pages. Then the passage reader reads the first 20 documents of P130164 and P156634 into numbered passages, scans and embeds them with the offline stand-ins, and fills `strata.gold.passage`, which the fixture search reads. Then it runs the Python tests that may read that database, on four pytest-xdist workers: the tests under `tests/` and the bundle commands' tests under `ops/bundle/tests/`. They cover the gate, the server (its routes, the data-freshness stamp as each viewer, usage events and traces), the fixture and its ground truth, the ground-truth SQL on DuckDB, the lakehouse run and its fetch, the catalog and its table definitions, the config files, the nightly job, the plan reader, the passage reader, `search_passages` and its live adapters, the answer stream with the scripted agent and the verifier, the agent sync, the recording command and the shield set, and the bundle commands.
   - The ops lane runs the Python tests for the wizard and the day-one probes, on six pytest-xdist workers.
   - The app lane runs the Python tests for the app's deploy, what it uploads, and the Lakebase probe, under `ops/app/tests/`.
   - The lint lane lints the copy and the components. It fails on DESIGN.md section 7's banned words, em dashes and exclamation marks in the copy files and in the words the source registry puts on screen, on a server copy of the Data readiness sentences (`src/strata/tools/data_readiness_copy.json`) that is out of date with the copy file, on text a component renders, passes to a prop or writes into the page that is not from the copy file (words joined with `+` included), on a Term that names a word GLOSSARY.md does not define, and on spacing or colors outside DESIGN.md's tokens. The props that never hold copy, such as `className` and `href`, are listed in `web/lint/rules.ts`.
   - The sql lane lints the SQL (`gates/sql_lint.py`): every query names its tables in three parts and binds its values as parameters.
   - The web lane type checks and bundles the web app, builds the design gallery, then runs the Playwright tests against both, and one test against Vite's dev server, where React's StrictMode runs each effect twice, as `scripts/dev` does.

The gate prints each step's name and time as the step finishes. When a step fails, the gate stops the other lanes, prints the output of the step that failed, and fails. The gate tells uv, npm and Playwright to work offline, and the tests refuse any connection that leaves this computer. It prints its total time and fails when the whole run takes longer than two minutes. When every staged file is Markdown, it runs only the secret scan.

One gate runs at a time on this computer, so gates in other worktrees and sessions cannot slow it past its limit. Before it starts, the gate holds a lock on the file `strata-gate.lock` in your temporary folder (`$TMPDIR` on a Mac), or on the file that `STRATA_GATE_LOCK` names, as the gate's own tests do. A gate that finds another gate running prints that it is waiting, waits up to 20 minutes (`lock_wait_seconds` in `gates/steps.toml`) and then gives up, and its two-minute limit counts from the moment it holds the lock, not from the start of the wait.

The gate tests the files in your working tree. When code is staged, the gate first checks that no tracked file has changes you have not staged, so the tests see what you commit. To add a ground-truth SQL check, add a `.sql` file to `tests/ground_truth/`. Write the query in Databricks SQL, with three-part names such as `strata.ops.pipeline_runs`; the engine adapter rewrites it for DuckDB. Put its expected rows in `-- expect:` lines, one CSV row per line with the header first, and name the source of those values in a comment. A `-- param: name = value` line binds a parameter, and a `-- engines: duckdb, databricks` line marks a query that `ops/bundle/check.py same-rows` also runs on the workspace's SQL warehouse. Values copied from a source, with the page or record they came from, go in `tests/ground_truth/values.toml`, and a test checks each one against the recorded fixture.

The fixture build also creates the strata catalog's schemas and tables from `src/strata/lakehouse/tables/`, and it stops when any table has no `public_from` column. To add a table, add one file there, `<schema>/<table>.sql`, that starts with `CREATE TABLE IF NOT EXISTS strata.<schema>.<table> (`. A view is one file in `src/strata/lakehouse/views/<schema>/<view>.sql` that starts with `CREATE OR REPLACE VIEW strata.<schema>.<view> AS`, created after the tables.

To add a check, add a step to `gates/steps.toml`. A step with no `lane` key runs alone. It waits for every step above it, and every step below it waits for it. To run a step side by side with others, give it a lane, such as `lane = "web"`, and put it among the steps that have lanes. It runs after the steps above it in the same lane. Use a new lane's name when the step needs nothing from the other steps. A step that needs another step's output goes in that step's lane, below it. A new pytest step names the folders it tests, and the gate's own tests check that each folder in `testpaths` in `pyproject.toml` runs in exactly one step. A test folder whose tests read the fixture database goes in the python lane, below the build, and in `FIXTURE_READERS` in `tests/test_gate.py`, which checks that it runs after the build.

The Python tests run on pytest-xdist workers, so each test runs beside others in separate processes that share this computer's files and ports. A test must write only under its own `tmp_path` or a throwaway repo, open the fixture database read-only (the `fixture_db` fixture in `tests/conftest.py` gives its path), never change the working folder, set an environment variable only through pytest's `monkeypatch`, which puts it back after the test, and listen on a port the system picks (port 0). A test that must name its port takes one from below the system's range, as `free_port` in `tests/test_server_start.py` does. When a test cannot run beside the others, mark it with `@pytest.mark.xdist_group("<name>")`, say why in a comment, and add `--dist loadgroup` to its step, so the tests in that group run on one worker.

When a lane gets slow again, first run `uv run --frozen pytest --durations=15 <its folders>` to find the slowest tests. A single slow test sets a floor that no number of workers can lower. Then try more workers on that lane's step (`--numprocesses`), and keep the number that gives the lower total gate time over three runs by hand. The lanes share this computer's processors, so more workers in one lane can slow the others. You can also move a folder that does not read the fixture database to a lane of its own.

To run the nightly job's tasks in order on an empty DuckDB database, over the recorded pages, and see the rows they write, run `uv run --frozen python -m strata.lakehouse.nightly`. To read the first documents into passages the same way and see their data readiness measures, run `uv run --frozen python -m strata.lakehouse.passages`. To deploy the catalog and the job to the shared workspace, follow `bundle/README.md`.

The gate never calls the agent. The scripted agent replays the Foundry agent's recorded answers for each case in `tests/fixtures/agent/cases.toml`, and the tools it asks for run on the fixture. A case can plant what a model might get wrong, such as a number no record holds, and its test checks that the verifier removes that sentence. On the workspace, three commands keep the agent and its recordings in step with the repo. Run `uv run --script ops/agent/sync.py --env-file .env` after a change to `config/agents.toml`, the agent's instructions in `src/strata/agent/instructions/`, its model or a tool. It makes the Foundry agent and its guardrail match the repo, and a second run reports no difference. Run `uv run --script ops/agent/record.py --env-file .env` to re-record every scripted case from the live agent. It prints the change as a diff, which you review with `git diff tests/fixtures/agent` before the gate replays it. Run `uv run --script ops/agent/shields_live.py --env-file .env` to send the five passages in `evals/shield_passages.toml` through the live agent, so a Prompt Shields refusal on rule-like report text shows up before a viewer meets it.

The draft writers work the same way (ticket 35). The scripted writer replays the review notes writer's recorded answer for each case in `tests/fixtures/agent/writers.toml`, and a case can plant a note that takes the place of the recorded one, such as a note whose every sentence fails a check. On the workspace, add `--agent review_notes_writer` to the sync to make the Foundry writer match the repo, and `--writers` to the recording command to re-record the writer's cases from the live writer.

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
- `GET /api/me/warehouse` runs one query as the viewer and returns the user the warehouse says ran it.
- `GET /api/freshness` returns the data-freshness stamp's day, read from `strata.ops` as the viewer: the earliest day a daily source was last loaded, or `null` before any has loaded. It answers 401 when no viewer was forwarded, 403 with the code `permission` when the warehouse refuses the viewer, 504 after `app.stamp_timeout_seconds` in `config/thresholds.toml`, and 502 when the warehouse fails.
- `POST /api/ask` takes `{"question": "...", "scope": "P130164", "asof": "2026-10-23", "view": "staff", "lang": "en"}`, where only the question is required, and streams the run's events as `text/event-stream`. It sends `step` events while the agent works, then the answer's `sentence` events with their evidence ids, an `evidence` event for each row or passage they cite, one `checks` event with the verifier's counts, a `removed` event for each sentence the checks removed with its reason codes, and last a `done` event with the run id and, when the request was traced, its trace ids. The verifier runs in the stream on every answer (CLAUDE.md rule 1). The copy file has each reason code's list item and clause, under `removed.reasons`. Each run is written to `strata.ops.agent_runs`. A run that cannot answer sends one `error` event with a code from `ERROR_CODES` in `src/strata/harness/turn.py` (`no_agent` when the environment names no Foundry agent, `agent_unavailable`, `content_filter`, `agent_output`, `data_service` or `internal`), and the copy file has a sentence for each, under `answer.errors`. Each `evidence` event also names its stratum (`Why`, `How` or `What`, from the reader's templates) and its document's short name, such as `ICR`. `tests/fixtures/api/ask-*.sse` are the recorded streams the screen tests play: the showcase answer, the same answer with one sentence removed, the same answer with a fourth sentence that quotes an ISR section, one that found nothing to cite, one whose every sentence failed a check, one with no model connected, one where the agent did not respond, and one that a content filter stopped. `uv run --frozen python -m strata.agent.scripted <case>` prints a scripted case's stream, and `--error <code>` prints a run that stops with that code.
- `GET /api/lookup/loan?q=` and `GET /api/lookup/activity?q=` are the one box's lookups (ticket 14), as the viewer and as of `?asof=`: the project a loan number finances, in any of its forms, and the latest published Procurement Plan that lists a STEP reference, with whether it is its agency's latest. One that finds nothing answers 404 with the code `unknown_loan` or `unknown_activity`. Their SQL is in `src/strata/server/sql/lookup/`.
- `GET /api/evidence?id=` gives one source by its evidence id, in the shape of the stream's `evidence` event, for an evidence drawer opened from a link, or 404 with the code `unknown_evidence`. `POST /api/evidence/opened` takes `{"evidence_id": "...", "run_id": "...", "route": "...", "view": "staff"}` and records, as the app's own service principal, that the viewer opened that source: one row per viewer and evidence id in `strata.ops.evidence_opened`, written with a `MERGE`. A preview of another view, or a request with no forwarded viewer, records nothing and answers `{"recorded": false}`. `GET /api/evidence/opened?id=...&id=...` says which of those the viewer has opened.
- The draft routes (ticket 35, `src/strata/server/drafts.py`). `POST /api/drafts` takes `{"kind": "review_notes", "project_id": "P156634", "agency_id": "northern-water-works-development-agency", "plan_date": "2026-10-09", "idempotency_key": "..."}` and streams the writing as `text/event-stream`: `step` events (`read`, `write`, `check`, `save`), then a `draft` event with the saved draft's id, or a `nothing_survived` event with the removed sentences when none passed the checks, or an `error` event with a code from `WRITE_ERRORS` in `src/strata/drafts/runtime.py`, and last a `done` event. The check-a-plan workflow reads `check_plan` as the viewer, as of today; the writer agent (`review_notes_writer` in `config/agents.toml`) drafts one note per activity with a signal; the verifier checks every sentence; and only then is the draft saved in `strata.ops.drafts` with its author's team. A second request with the same idempotency key opens the same draft. `GET /api/drafts` lists the viewer's team's drafts and their own under `to_check`, `checked` and `exported`, and the viewer's own discarded ones. `GET /api/drafts/existing?kind=&project_id=&agency_id=&plan_date=` names the newest open draft of that kind the team has on that plan version; with no `plan_date`, it answers `by_plan_date`, the newest open draft on each version of that agency's plans, so the plan check with no version in its address can ask at once. `GET /api/drafts/{draft_id}` gives one draft as its page shows it, with how many of its sources the viewer opened since it was saved. `POST /api/drafts/{draft_id}/check`, `/export`, `/discard` and `/restore` take `{"expected_state": "draft"}` and move the draft on; only its author acts, a preview acts on nothing, and a refusal answers 403 (`not_author`, `preview`) or 409 (`stale`, `draft_state`, `held`) with the state the draft is in now. Export makes the Word file (one footnote per citation) and the evidence pack's PDF and CSV, keeps them in `strata.ops.draft_files`, and sends nothing anywhere; `GET /api/drafts/{draft_id}/files/{name}` downloads one. A draft another team made is not found, and an author always sees their own drafts. The one access rule is `src/strata/server/access.py`, which reads each viewer's workspace groups and `config/roles.toml`.
- The Lessons routes (ticket 29, `src/strata/knowledge/lessons/review.py`). `GET /api/lessons/me` says which Lessons pages the viewer may open (`tabs`), from `config/roles.toml`, and how many items wait in their regions. `GET /api/lessons?page=` is the library: current lessons and those being re-checked, eight a page, newest decision first, naming roles and never people. `GET /api/lessons/review?page=` is the review queue, with the server's lead sentence and quote-check sentence as segments for Num, the rows grouped `you` and `others`, and the decisions of the last 90 days; `GET /api/lessons/review/{item_id}` is one item's review page. Both answer 403 `not_a_reviewer` to anyone the roles file does not name. `POST /api/lessons/review/{item_id}/recommend`, `/decide` and `/cross-check` take `{"expected_stage": "recommendation", "outcome": "add", "reason": "..."}` (or `"agree": true` for a cross-check) and record the act with the viewer as its actor, written as the app's own service principal (reads stay the viewer's; no reviewer may write the review tables outside the app, and without the app's identity the answer is 503 `not_recorded`); a refusal answers 403 (`same_person`, `own_project`, `not_a_lead`, `other_region`, `same_region`), 409 (`stale` with the item as it is now, `recheck_open`) or 422. `POST /api/lessons/review/{item_id}/summary` writes the lesson review writer's note again, and `POST /api/lessons/{lesson_id}/recheck` takes `{"reason": "..."}`.
- `GET /api/suppliers/review` lists each candidate pair of supplier name matching that waits for a person, with both names, countries and contracts, read as the viewer. `POST /api/suppliers/review` takes `{"pair_id": "...", "decision": "merge", "reason": "..."}` and records it with the viewer as the reviewer and the two names the viewer saw, as the app's own service principal. The next nightly run applies it while the pair's names are the same. `GET /api/suppliers/labels?limit=20` gives the next unlabeled pairs, without where Strata sent them, and `POST /api/suppliers/labels` takes `{"pair_id": "...", "label": "no_merge"}`. A write answers 401 `no_identity` with no forwarded viewer, 404 `unknown_pair` for a pair the latest run did not find, and 503 `not_recorded` when the app has no service principal of its own. Their code is `src/strata/server/suppliers.py`, with its SQL in `src/strata/server/sql/suppliers/`.
- `GET /api/projects?q=&page=` lists the projects Strata holds a record for, 20 a page (`app.page_size` in `config/thresholds.toml`): an exact project ID first, then active ones, then by name, found by part of a name, a project ID with or without its P, or a country, ignoring case and accents. The answer counts the matches and the page's range, with the day the projects API was last fetched. `GET /api/projects/{project_id}` gives a project page's header (its display name, which leaves out a final "Project", country, status and implementing agencies) and each implementing agency's Procurement Plan versions, newest first, with how many activities each read version lists, which ones show before "Show all", the baseline saved for that agency's plans, and what changed in its latest version since the one before; or HTTP 404 with the code `unknown_project`. Ticket 21 adds, each read as the viewer and as of `?asof=`: `GET /api/projects/{project_id}/summary`, every value of the Summary with its source and each source as the evidence drawer shows it, from precomputed records and no model; `GET /api/projects/{project_id}/packages?q=&page=`, every activity in each agency's latest read plan, 20 a page, searched by STEP reference or description; `GET /api/projects/{project_id}/documents`, every document listed for the project, grouped by type with its dates and pages read; `GET /api/projects/{project_id}/documents/{doc}?page=&para=&passage=`, one page of a document's passages, where `{doc}` is its key such as `icr-2019-10-10`, a type such as `icr`, or its documents API id, with any correction to the address; `GET /api/projects/{project_id}/procurement/{agency_id}/{version}/changes`, what changed since the agency's version before it (added, dropped, re-dated and re-estimated, matched on STEP reference), or 404 `unknown_plan`; and `PUT` or `DELETE /api/projects/{project_id}/procurement/{agency_id}/baseline` (`{"plan_date": "2025-07-21"}`), which save or remove the agency's shared baseline as the viewer in `strata.ops.plan_baselines` and `strata.ops.plan_baseline_steps`, refused with 401 `no_identity` or 403 `preview` outside the World Bank staff view. Every route answers a refused or failed read as the plan check does. Their SQL is in `src/strata/server/sql/projects/`, `summary/`, `documents/`, `changes/` and `baseline/`. The routes the router tags as calling a model are listed by `model_routes(app)` and recorded in `tests/fixtures/api/model-routes.json`.
- `GET /api/packages/{step_reference}` gives the package workspace's header: the package as its newest public Procurement Plan row states it, with that plan and its project, or HTTP 404 with the code `unknown_package`. `GET /api/packages/{step_reference}/comparables` runs the tool registry's `find_comparables` as the viewer for the workspace's section 1, with the tool's criteria as query parameters (such as `?review_type=Prior` or `?category=any`), `?asof=` and `?view=`. Both answer a refused or failed read as the plan check does.
- The planned package routes (ticket 15, `src/strata/server/packages.py`). `POST /api/planned-packages` takes `{"sentence": "rural roads, Kenya, about US$15 million", "read": true, "view": "staff"}` and streams the plan-a-package workflow as `text/event-stream`: a `form` event with the package form schema, `step` events (`read`, `compute`, `save`, `compare`), a `package` event with the saved package, a `comparables` event with `find_comparables`' result, or an `error` event, and last a `done` event. With `"read": false` the person sets the criteria themselves. `GET /api/planned-packages` lists the Packages tab's rows: the viewer's packages and the plans they checked, newest first. `GET /api/planned-packages/{id}` gives one package with the schema, and `POST /api/planned-packages/{id}` takes one change, such as `{"field": "method", "action": "set", "value": "ICB"}`, and saves it as a new save; changes to one package are made one at a time. `GET /api/comparables` runs `find_comparables` as the viewer for a package with no STEP row, with the tool's criteria as query parameters. Only the person who made a package reads or changes it; a preview changes nothing (403 `preview`). Packages and plan checks live in Lakebase (ADR 0005), or in `STRATA_APP_STATE_FILE` on this computer.
- Section 3 of the package workspace, procurement risks and what helped (ticket 30, `src/strata/server/risks.py`). `GET /api/packages/{step_reference}/risks` (with section 1's criteria as query parameters) and `GET /api/planned-packages/{id}/risks` run the risk-table builder as the viewer, with `?asof=` and `?view=`. `PUT /api/packages/{step_reference}/risk-selection` and `PUT /api/planned-packages/{id}/risk-selection` take `{"changes": {"cost_estimates": true}}` and keep the viewer's selection in Lakebase (`strata.app.risk_selections`), changed by a `MERGE`, so unselecting deletes nothing. A preview changes nothing (403 `preview`).
- `GET /api/projects/{project_id}/procurement/{agency_id}` checks an implementing agency's latest Procurement Plan, and `GET /api/projects/{project_id}/procurement/{agency_id}/{version}` checks the version with that plan date, such as `2026-10-09`. Each runs the tool registry's `check_plan` as the viewer and returns its result as JSON. Both take `?asof=` (a date) and `?view=` (`staff`, `piu` or `public`). Until ticket 40 applies each view's rules, every view gets the World Bank staff result. A viewer whose token cannot read the strata catalog gets HTTP 403 with the code `permission` and no rows. When the data service fails, or its database file cannot be opened, the answer is HTTP 503 with the code `data_service` and a reference. When a tool breaks its contract, the answer is HTTP 500 with the code `tool_contract` and a reference. The reference is the request's trace id, so it finds the request in the server log, in Application Insights and in its usage event. A warehouse query that runs longer than `app.stamp_timeout_seconds` counts as the data service failing.
- `GET /api/data/readiness` runs the tool registry's `data_readiness_for` as the viewer and returns the Data readiness page as JSON: the latest measure behind every cell, the known gaps, what each kind of question is ready for, the fixes ranked by the projects each would add evidence to, and the headline. It takes `?sources=` (source registry keys, separated by commas), `?from=` (the tool whose coverage line named them) and `?asof=`. It answers 401, 403 with the code `permission`, 504 with the code `timeout` and the seconds it waited, and 502, as the stamp does.
- `GET /api/data/sources` lists each dataset's attribution and the document collections from the source registry, and counts the Data readiness page's rows, without the warehouse.
- Every other address outside `/api` gets the built web app (`web/dist`, or `STRATA_WEB_DIST`), whose router shows the page or the not-found page.

The server reads its data as each viewer, from one of two places, chosen when it starts:

- `STRATA_DATABASE_FILE` names a DuckDB file, which each request opens read-only. To run against the gate's fixture, set it to `data/out/fixture.duckdb`. `STRATA_APP_STATE_FILE` can name a second, writable DuckDB file that keeps the sources each viewer opened and the drafts, so drafts work on this computer too.
- Otherwise, `DATABRICKS_HOST` and `DATABRICKS_WAREHOUSE_ID` name the workspace and its SQL warehouse, and each query runs with the token the Databricks App forwarded for the viewer.

With neither, the routes that need data answer HTTP 503 with the code `no_data_service`.

On this computer no Databricks App forwards a viewer, so `/api/freshness` answers 401 and the app shows the alert that says so. The screen tests in `web/tests/` answer `/api` from the recordings in `tests/fixtures/api` instead, as `npm --prefix web run capture` does.

Each request a viewer makes, except `/api/health` and the web app's files, writes one usage event to `strata.ops.usage_events` and sends one trace, whatever the route answers. An error that no route expects, such as a bug, answers HTTP 500 with the code `internal` and a reference, and its details stay in the server log. `src/strata/server/settings.py` says which environment variables set the app's own credentials for the usage events, the run log and the opened sources, the Foundry agent, the Application Insights connection string and the web app. Without the app's credentials, as on this computer, the server keeps no usage events and writes each run to the server log only.

## Deploy the app

Strata runs as a Databricks App that acts as each viewer. After the wizard and the bundle deploy, run this from the main checkout:

    uv run --script ops/app/deploy_app.py --env-file .env

It takes these steps, in order:

1. It builds the web app into `web/dist`.
2. It finds the app that `ops/dayone/dayone.toml` names, or makes it.
3. It gives the app the SQL warehouse, the Application Insights secret and each viewer's SQL token.
4. It uploads the app with its lean requirements file (`ops/app/requirements.txt`) and `ops/app/app.yaml`.
5. It deploys the app and waits for it.
6. It lets the app's own service principal write usage events and agent runs.
7. It prints the app's address.

Run it again after every bundle deploy. The bundle's grants replace the app's grants on the `strata` catalog and the `strata.ops` schema, and without them the server can't write usage events or agent runs.

Before ticket 15 writes the first app state, run the Lakebase probe, which records where app state lives in `docs/app-state.md`:

    uv run --script ops/app/probe_lakebase.py --env-file .env

## Where things live

Each part of the spec has one home. Folders marked "later" do not exist yet. The ticket that builds a part creates its folder.

| Part | Where |
|---|---|
| The gate | `.githooks/pre-commit` and `.githooks/pre-merge-commit`, which run `gates/offline.py` over `gates/steps.toml` |
| The guard hook and its tests | `.claude/hooks/` |
| Viewer identity | `src/strata/dbx.py` |
| The harness: each turn's evidence and the stream helpers | `src/strata/harness/` |
| The app server, its settings from the environment, and the queries it runs as the viewer | `src/strata/server/` (`settings.py`, `viewer_sql.py` and `sql/`) |
| The app's deploy, its `app.yaml` and its lean requirements file, and the Lakebase probe | `ops/app/`, with the probe's result in `docs/app-state.md` |
| The web app, with its `api`, `sse`, `store`, `export`, `router` and `freshness` libraries | `web/src/` and `web/src/lib/` |
| The app's routes: which page an address opens and the tab it selects | `web/src/routes.ts` |
| The World Bank Group logo, with where and when it was downloaded | `web/src/assets/` |
| The copy file: every string a person reads | `web/src/copy.ts` |
| The design tokens: DESIGN.md sections 2 to 4 as the Tailwind theme, and the self-hosted fonts | `web/src/styles/app.css` |
| The components, and the number and date rules Num follows | `web/src/components/` and `web/src/lib/format.ts` |
| The design gallery, for development only, with its own copy file | `web/src/gallery/` |
| The copy lint, the string lint and the class lint | `web/lint/`, with its rules in `web/lint/rules.ts` |
| The screenshot command's list of pages and states | `web/capture/shots.ts` |
| Python tests for seams 1, 2, 3 and 5, and for the gate | `tests/` |
| The guard that keeps every Python test off the network | `conftest.py` at the root |
| Screen tests (seam 4) | `web/tests/` |
| Responses recorded once and shared by the server and screen tests | `tests/fixtures/api/` |
| Answers in the shape Azure OpenAI, Prompt Shields and AI Search document, which the live adapters' tests read until a live run records real ones | `tests/fixtures/azure/` and `tests/fixtures/ai_search/` |
| Fixture inputs, and the fixture database the gate builds | `data/fixture/`, and `data/out/`, which git ignores |
| The list of recorded sources, and the recorded files. This `sources.toml` lists recorded copies of public pages, grouped by dataset. The source registry, `config/sources.toml`, lists what the nightly job fetches, and each of its entries names, in `fixture_dataset`, the dataset here whose files stand in for it in the gate | `data/fixture/sources.toml` and `data/fixture/recorded/` (see `data/fixture/README.md`) |
| The recording command, which refetches the fixture and prints a diff | `src/strata/fixture/` (`uv run python -m strata.fixture.record`) |
| Ground-truth SQL, and the ground-truth values with their sources | `tests/ground_truth/` (`*.sql` and `values.toml`) |
| The engine adapter, which runs one Databricks SQL query on the SQL warehouse, in a job and on DuckDB | `src/strata/lakehouse/engine.py` |
| The table definitions, one `CREATE TABLE IF NOT EXISTS` file per table, and the view definitions, one `CREATE OR REPLACE VIEW` file per view, built by the gate and the deploy | `src/strata/lakehouse/tables/<schema>/` and `src/strata/lakehouse/views/<schema>/` |
| The nightly job's tasks | `src/strata/lakehouse/nightly.py` |
| The bundle: the strata catalog, its schemas, the volume, the grants, the nightly job and the dashboard, with its notes | `databricks.yml` and `bundle/` |
| The deploy command and the workspace checks for the bundle | `ops/bundle/` |
| The lakehouse: where pages come from (the live APIs, or the recorded fixture in the gate), bronze and the contact details it never keeps, the cleaning rules, silver's transforms, gold's tables (one SQL query each), the data readiness measures (one SQL file per silver transform), each table's size, and governance scores as of a date | `src/strata/lakehouse/`: `pages.py`, `bronze.py` and `contacts.py`, `clean.py`, `silver/`, `gold/`, `readiness/`, `storage.py`, `governance.py` |
| The SQL lint: three-part names and bound parameters | `gates/sql_lint.py` |
| The plan reader: a project's Procurement Plans into STEP rows, with delay from the first published planned date and data notes, under the daily page cap | `src/strata/lakehouse/plans.py` and `src/strata/lakehouse/sql/plans/` (`uv run --frozen python -m strata.lakehouse.plans` runs it on the fixture) |
| The document reader: documents and their pages, Route A's numbered passages and each document type's template (`passages.py`, `templates.py`), the layout parser (Route B, offline and live) and STEP's words | `src/strata/reader/` |
| The passage reader: the first documents into numbered passages, Prompt Shields' results, vectors and `strata.gold.passage`, with data readiness measures | `src/strata/lakehouse/passages.py` (`uv run --frozen python -m strata.lakehouse.passages` runs it on the fixture) |
| The live plan run on the workspace | `ops/plans/run_live.py` |
| The live passage run on the workspace, which also makes and syncs the AI Search index, and the live check that asks `search_passages` its benchmark question through AI Search | `ops/documents/run_live.py` and `ops/documents/search_live.py` |
| The live check that asks the judge role's deployment about the fixture's uncertain supplier pairs | `ops/suppliers/judge_live.py` |
| The knowledge model: the sector words, the embedding and Prompt Shields adapters, hybrid search (AI Search live, the fixture search offline), suppliers resolved on STEP supplier IDs first and names second (`suppliers/`), the batch model's adapter (`batch.py`, Global Batch live, a recording offline), assertions and the disagreements between them, each decided by the evidence ladder (`assertions.py`), and the knowledge loop for lessons (`lessons/`, ticket 29): proposed lessons whose quotes are on their cited pages, the review queue's rules and acts, the lesson review writer's verified notes and the quarterly cross-check. Links come later | `src/strata/knowledge/` |
| The retrieval loop (ticket 32): the kinds of question, the labeled set (silver labels from ICR Reviews and PADs, the judged notice queries, the reviewed feedback), passage reports and the passage reviewers' decisions with the rules for scale, the ranking-lower rule search_passages applies, the judging tool, and the weekly run that builds the set and measures the loop (`bundle/retrieval.yml`) | `src/strata/knowledge/retrieval/`, with its lists in `config/retrieval.toml` and the queries written from award notices in `evals/retrieval_queries.toml` |
| Retrieval evaluation in the replay harness (precision at 10, recall at 20, nDCG at 10 per query set) and the tuning gate | `src/strata/estimates/retrieval.py` |
| The feedback row's, Passage reports' and Judging's recorded answers, which their screens and the gallery play | `tests/fixtures/api/feedback-*`, `passage-report*`, `judging-*` and `retrieval-me-*` (written by `uv run --frozen python tests/record_retrieval_api.py`) |
| The live assertion run on the workspace, which also checks `get_disagreements`' benchmark question, and the command that records the batch answers the gate replays (`--record`) | `ops/assertions/batch_live.py` |
| The tool registry: one entry per tool, with its parameters (always an optional `as_of` date), adapter, benchmark question and result shape. Adding a tool is one entry plus its adapter | `config/tools.toml` |
| The registry at work (the agent's tool list, calling a tool by name, the tool contract) and the tools, with their SQL: `check_plan`, `search_passages`, `data_readiness_for`, `find_comparables` and `get_lessons` | `src/strata/tools/` |
| Which engine runs a viewer's queries in the server | `src/strata/server/engines.py` |
| The agent registry: each Foundry agent, its model role, its instructions file and its guardrail (content filters and Prompt Shields), read by `load_agent` | `config/agents.toml` |
| The agent: its instructions (`instructions/`), its Foundry definition and the sync that makes Foundry match it (`definition.py`, `sync.py`, `foundry.py`), the answer loop (`loop.py`), the verifier's checks 1 to 3 (`verifier.py`), the run log in `strata.ops.agent_runs` (`runs.py`), the scripted agent (`scripted.py`), the recording command (`record.py`) and the shield check (`shields.py`). Workflows come later | `src/strata/agent/` |
| The scripted cases and the Foundry agent's recorded answers that the scripted agent replays | `tests/fixtures/agent/` |
| The agent's live commands for the workspace: the sync, the recording command, the showcase question and the shield check | `ops/agent/` |
| Drafts: the draft runtime (writing, states, what the pages read), the check-a-plan workflow's review notes, the exported files (a Word writer with real footnotes, and the evidence pack's PDF in Open Sans and CSV), the holds, the server's copy of the files' words and the fonts with their licenses | `src/strata/drafts/` |
| The draft-kind registry: each kind's writer, columns, holds and files. Adding a kind is one entry | `config/drafts.toml` |
| The roles file: the teams that share drafts, by workspace group, read by the one access rule; and the lesson reviewer groups with their people, regions and projects, read by the lesson review (ticket 29) | `config/roles.toml`, `src/strata/server/access.py` and `src/strata/knowledge/lessons/review.py` |
| The lesson lists (risk factors, stages, kinds and the extractor's example projects) and the editions of the procurement rules a project followed | `config/lessons.toml` and `config/editions.toml` |
| The project page's lists: the documents API's type for each Documents group in project-cycle order, the groups re-issued under one report number, and the ISR ratings and Procurement rating code the Summary shows, read by `load_project_page` | `config/project_page.toml` |
| The quarterly lesson cross-check job | `bundle/lessons.yml` |
| The Lessons routes' recorded answers, which the Lessons screens and the gallery play | `tests/fixtures/api/lessons-*` (written by `uv run --frozen python tests/record_lessons_api.py`) and the lesson review writer's cases, `tests/fixtures/agent/lesson_review.toml` |
| The draft writers' scripted cases, replayed by the scripted writer, and the recorded answers the draft screens play | `tests/fixtures/agent/writers.toml` and `tests/fixtures/api/drafts-*` (written by `uv run --frozen python tests/record_drafts_api.py`) |
| The estimates: the past range (Kaplan-Meier over comparables, with packages still open kept as censored), the replay harness that freezes Strata at a cutoff and stores each scorer's results in `strata.ops.evaluation_result` (`harness.py`), the time estimate's model with its conformal ranges and abstentions (`time_estimate.py`), its rolling backtests, registration and track record (`backtest.py`), the model card (`model_card.py`), and MLflow with Unity Catalog or their offline stand-in (`tracking.py`) | `src/strata/estimates/` |
| The time estimate's live backtests for 2021 to 2025 on the workspace, which log to MLflow and register the model in Unity Catalog | `ops/estimates/backtest_live.py` |
| The registry and config files for the change drill: the source registry, the slice file, the sector taxonomy, the model file, the thresholds file, the tool registry and the agent registry, each read by one function in `src/strata/config.py` | `config/` |
| The evidence ladder: the rules that choose the assertion Strata leans on when two disagree (outcome judgments, then moments, then the two ties), the evidence tiers, and the attributes an assertion can be about with their rating scales, read by `load_ladder`. Reordering a rule is a change to this file only | `config/evidence_ladder.toml` |
| The package form schema: each field of a package planned from a sentence, one chip each, in its group (What, Where, How), read by `load_package_form` in `src/strata/config.py`. Adding a field is one entry | `config/package_form.toml` |
| Packages planned from a sentence (ticket 15): the values a field takes and the form's payload (`form.py`), the criteria and their provenance (`criteria.py`), review type and market approach from the thresholds file (`compute.py`), the package reader's adapter (`reader.py`), the plan-a-package workflow (`workflow.py`) and the store (`store.py`), with its SQL in `sql/` | `src/strata/packages/` |
| App state in Lakebase (ADR 0005): the engine that reaches it as the app's own service principal, and the app state tables, one definition each | `src/strata/appstate/` (`lakebase.py` and `tables/app/`) |
| The risk-table builder (ticket 30): section 3 of the package workspace, the procurement risks that came up in the completion reports of comparable packages' projects, each with a current lesson on what helped, ranked by fit and evidence and checked by the verifier; a workflow step the hindsight test reuses with an as-of date (`risks.py`). Its routes are `src/strata/server/risks.py`, and the viewer's selection is kept in `strata.app.risk_selections` | `src/strata/packages/risks.py` |
| The risks section's recorded answers, which section 3's screens and the gallery play | `tests/fixtures/api/risks-*` and `evidence-icr-review-p130164-10b.json` (written by `uv run --frozen python tests/record_risks_api.py`) |
| The planned package routes' recorded answers, which the package workspace's screens and the gallery play | `tests/fixtures/api/planned-package*`, `package-plan-*.sse`, `comparables-planned-*` and `evidence-package-*` (written by `uv run --frozen python tests/record_packages_api.py`), and the package reader's cases, `tests/fixtures/agent/packages.toml` |
| The benchmark file, with one question per tool so far. Ticket 33 adds the runner and the other kinds of question | `evals/benchmark.yaml` |
| The shield set: five real passages with rule-like sentences that must reach the agent without a Prompt Shields refusal | `evals/shield_passages.toml` |
| The other evaluation sets | `evals/` (later) |
| The dashboard definition: its pages and tiles as code, the queries of its datasets, and the file it writes, which the bundle deploys (`uv run --frozen python -m strata.dashboard --write` writes it again) | `src/strata/dashboard/`, `bundle/dashboard.yml` and `bundle/dashboards/strata.lvdash.json` |
| The Data tab's pages: Data readiness, Sources and licenses and How Strata works | `web/src/pages/data/` |
| The server's copy of the Data readiness sentences, written from `web/src/copy.ts` by `node web/lint/server-copy.ts --write` | `src/strata/tools/data_readiness_copy.json` |
| The recorded answers of the Data tab's routes, written again by `uv run --frozen python tests/record_api.py` | `tests/fixtures/api/data-*.json` |
| The credentials wizard and the day-one probes | `ops/` (ticket 03) |

## Ports at a glance

| Variable | Used by | When unset |
|---|---|---|
| `STRATA_SERVER_PORT` | the server, and the web app's dev server to reach it | a free port |
| `STRATA_SERVER_HOST` | the server, and the web app's dev server to reach it | `127.0.0.1` |
| `STRATA_WEB_PORT` | the web app's dev server | a free port |
| `DATABRICKS_APP_PORT` | the server, on the Databricks App, when `STRATA_SERVER_PORT` is unset | the platform sets it |

The Playwright tests always pick their own free ports, so they never clash with a running dev server, even the one `web/tests/dev.spec.ts` starts.

## The design gallery and screenshots

The design gallery shows every component in each of its states. Start `scripts/dev` and open `/gallery` at the address it prints. Only development builds and the gallery build have it; the production build leaves it out, and a test checks that.

To take screenshots of every gallery page and of the hover, focus and open states, at 1440, 1024 and 390 px, run this command:

    npm --prefix web run capture

It builds the app and the gallery, answers `/api` from the recordings in `tests/fixtures/api`, and saves the pictures in `web/screenshots`, or in the folder that `STRATA_CAPTURE_DIR` names. It takes about 10 seconds. It is not a gate step. To capture a new screen, add its routes and states to `web/capture/shots.ts`.
