# The bundle's notes

Strata's Declarative Automation Bundle is `databricks.yml` at the root of the repo, with the files in this folder. It declares three things on the Free Edition workspace that Strata shares with fairshare.

- `catalog.yml` declares the catalog `strata`, its schemas `bronze`, `silver`, `gold` and `ops`, and the volume `strata.bronze.files`. It also gives the people who use the app read access, so the app can run each query as the viewer (ADR 0003). The bundle variable `readers` names them, and it is `account users`, everyone who can sign in to the workspace.
- `dashboard.yml` declares the AI/BI dashboard `Strata operations` and its test copy `Strata operations (test)`, whose files `dashboards/strata.lvdash.json` and `dashboards/strata_test.lvdash.json` `src/strata/dashboard` writes from code (ticket 45). Its three pages are Data readiness, Governance, and AI quality and adoption, and each KPI on them is defined once, by its query, in `config/kpis.toml`. Its queries run with each viewer's own credentials on the SQL warehouse the deploy passes as the variable `warehouse_id`. The measure task writes `strata.ops.readiness_snapshot`, the Data readiness page as the app builds it, and then "What the measures say" and each loop's indicators (`strata.ops.dashboard_findings` and `strata.ops.loop_indicators`), which the dashboard reads. A new tile is tried on the test copy first: add its entry to `src/strata/dashboard/definition.py`, run `uv run --frozen python -m strata.dashboard --write --test-only` and deploy; once it reads well there, `--write` writes both files and the next deploy gives it to the dashboard people use.
- `costs.yml` declares the job `strata cost pull`, which runs once a day at 05:40 in Washington, after the nightly job, and writes Azure's charges for the resource group in `config/budget.toml` to `strata.ops.azure_costs`, its run to `strata.ops.cost_pulls` and the budget periods to `strata.ops.budget_periods`, for the dashboard's Governance page. It signs in to Azure as the service principal whose keys are in the secret scope (`FOUNDRY_TENANT_ID`, `FOUNDRY_CLIENT_ID`, `FOUNDRY_CLIENT_SECRET`), with the subscription in `AZURE_SUBSCRIPTION_ID`; the service principal needs the Cost Management Reader role on the resource group. It is a job of its own because the nightly job keeps PLAN.md section 11's ten tasks.
- `nightly.yml` declares the job `strata nightly`. Its ten tasks run one at a time, in the order of `docs/PLAN.md` section 11, and each does its work, runs its quality checks and writes one row to `strata.ops.pipeline_runs`. `fetch_by_watermark` fetches every structured source in `config/sources.toml` into bronze from its watermark (for every country; the monthly loan history and the notices for each slice country on its own), `bronze_to_gold` builds silver and gold, `parse_and_embed` runs the plan reader and the passage reader over only the documents bronze does not hold, for at most `ingestion.document_host_minutes` (in `config/thresholds.toml`) of the document host's time a night, `sync_index` syncs `strata.gold.passage` and the AI Search index, `relink` rebuilds the edges, `propose_lessons` sends each new evaluation report to the batch model once, `detect_disagreements` rebuilds the assertions with one query a family for every project, `score` scores every package's time estimate and its what-ifs, counts the rebidding labels, scores packages with the rebidding champion and, once a week on the night `signals.track_record_day` names, replays the signals for their track record, for at most `nightly.score_minutes` a night: it stops after the part that spends them and records the parts left for the next night in `strata.ops.score_parts`, `measure_data_readiness` writes the data readiness measures and each table's size, and `refresh_drafts` marks drafts that cite a lesson a lead has since changed or retired, without changing them. Each task reads its Azure OpenAI and Foundry keys from the secret scope the variable `secret_scope` names (`strata`). The AI Search endpoint is no secret, so it comes as a parameter from the variable `ai_search_endpoint`, which the deploy fills from the env file.

A bundle does not declare tables. Each table is defined once, in `src/strata/lakehouse/tables/<schema>/<table>.sql`, and each view in `src/strata/lakehouse/views/<schema>/<view>.sql`, and the deploy command creates them on the SQL warehouse. The gate builds the same definitions on DuckDB, and it fails when a table has no `public_from` column (ADR 0002).

## Quality checks and reruns

When a task finishes, it checks the tables `config/quality_checks.toml` names for it: each table's row count against its range in `config/thresholds.toml` (`[quality_checks]`), rows missing a key, rows missing a Disclosed date (`public_from`), duplicate rows, and notices still carrying contact details. Every result goes to `strata.ops.quality_checks` with the night, the task, the check, the table and the count found, passed or failed, for the dashboard's Governance page. A failed check never stops the job.

A night can be run again without harm. A Databricks repair run reruns the failed task and the ones after it under the same run id, and each try keeps its own row in `strata.ops.pipeline_runs`; `ops/bundle/check.py job-run` counts a task by its last try. Running the same night twice changes no row in bronze, silver, gold or the app's tables: only the run logs (`nightly.RUN_LOGS` in `src/strata/lakehouse/nightly.py`) gain the second run's own rows, and a request or a page that failed before is tried again. `tests/test_nightly_reruns.py` proves both on the fixture.

## Deploy

You need the Databricks CLI 0.287.0 or later, because only the direct deployment engine can create a catalog. Run this from the main checkout after the wizard has filled `.env`:

    uv run --script ops/bundle/deploy.py --env-file .env

The command signs the Databricks CLI in with the host and token (or service principal) from the environment file alone: it points the CLI's config file at nothing, so the default profile in `~/.databrickscfg` never applies. On October 26, 2026 a deploy meant for the new paid workspace landed on the old one because the CLI's bundle commands took that default profile over the environment (ticket 82).

It lists what the workspace holds, deploys the bundle, gives the app back its way in to the catalog (below), creates the tables, and prints what changed, a dashboard the bundle rewrote among them. A second run prints "No changes." It also lists fairshare's catalog before and after, and fails if the two listings differ. If fairshare's catalog has another name, pass it with `--fairshare-catalog`.

Then run these four checks, also from the main checkout:

    uv run --script ops/bundle/check.py job-run --env-file .env
    uv run --script ops/bundle/check.py same-rows --env-file .env
    uv run --script ops/bundle/check.py readiness --env-file .env
    uv run --script ops/bundle/check.py schedules --env-file .env --write

The first runs the nightly job by hand and checks its rows in `strata.ops.pipeline_runs`: one per task in the bundle's order, each task's duration, rows changed and quality checks, and that the run finished inside its window. Pass `--run-id` to check a scheduled run instead. The second runs the two sample queries, `tests/ground_truth/showcase_fiscal_years.sql` and `tests/ground_truth/pipeline_runs_columns.sql`, on DuckDB and on the SQL warehouse and compares the rows. The third builds the Data readiness page on the SQL warehouse and checks that its awards row's rows held and STEP-reference link rate match a direct query on `strata.ops.data_readiness`. The fourth reads both nightly jobs and how long their recent runs took, and writes the result in the block below.

Some things to know before the first deploy:

- If a catalog named `strata` already exists, the deploy cannot create it. Bind it to the bundle first with `databricks bundle deployment bind strata strata`.
- The target has no development mode on purpose. Development mode would put a prefix on the schema names, and Strata's SQL names them `strata.bronze` and so on.
- The grants in `catalog.yml` replace any other grants on Strata's own catalog, schemas and volume. They never touch fairshare's. They would also take away the app's USE CATALOG on `strata` and USE SCHEMA on `strata.ops`, so right after the bundle deploys, the deploy command gives both back to the app's own service principal, which it reads from the app that `ops/dayone/dayone.toml` names (ticket 79). The two privileges are defined once, as `ACCESS` in `ops/app/deploy_app.py`. With no app yet, the deploy says so and grants nothing for it. The app's table grants are on tables, which the bundle leaves alone.
- SELECT on `strata.ops` reaches every future table in that schema. A table that holds uploads (CLAUDE.md rule 8) needs a row filter on the uploader's team, or a schema without this grant.
- Who sent each passage report (`strata.ops.candidate_labels`, `viewer_id` and `viewer_email`) and who asked each question (`strata.ops.answer_citations`, `viewer_id`) are masked: readers read NULL there. `src/strata/lakehouse/masks.py` lists those columns, and the app's deploy, `ops/app/deploy_app.py`, puts the mask `strata.ops.mask_viewer` on each, because only it knows the app's service principal. Only that principal and you, who run the deploy, read the values. A bundle deploy leaves the masks in place.

## The nightly window

The job starts at 03:00 in Washington (`America/New_York`) and stops after 150 minutes, at 05:30 at the latest. These are the reasons.

- **fairshare's job.** fairshare's job runs daily at 06:00 in Chicago, which is 07:00 in Washington, and its longest run took 21 minutes (the block below). Strata's window ends ninety minutes before it starts, and would miss it even if it ran four hours. The window also misses any job that starts at an hour from 18:00 to 22:00 in Washington, or at midnight UTC, and finishes within four hours. That holds on every day of the year, on both sides of the clock changes; 23:00 is left out because on the night the clocks go forward four hours from 23:00 end at 04:00. `tests/test_nightly.py` checks each of these for each day of a year. The job first ran at 05:00; the `schedules` check found that window reaching into fairshare's on every day, and the hour moved on October 24, 2026. 03:00 exists on every night in Washington, which 02:00 does not on the night the clocks go forward.
- **Review hours.** The panel works in Washington. The job stops by 05:30, two and a half hours before review hours start at 08:00, so no task is running when a review starts. I have not checked when the daily compute quota resets. The workspace catch-up records it.
- **The daily quota.** The two jobs share one daily compute quota and five concurrent job tasks. Strata's tasks run one at a time, so the job never uses more than one of the five.

The block below records both schedules and how long each job's runs took, as measured on the workspace. Fill it with the `schedules` check above. If the check finds that the two meet, change the hour in `nightly.yml` and run the deploy again.

<!-- bundle:schedules -->
- fairshare's job: fairshare nightly, daily at 06:00 America/Chicago. Its longest of the last 19 runs took 21 minutes.
- Strata's job: strata nightly, daily at 03:00 America/New_York. Its longest of the last eight runs took 151 minutes, and it stops after 150 minutes.
- Overlap: none. With these durations the two jobs share no minute on any day from October 26, 2026 to October 26, 2027, and the same holds if Strata's job runs to its limit.
- Measured: October 26, 2026, with `uv run --script ops/bundle/check.py schedules --env-file .env --write`.
<!-- /bundle:schedules -->

To keep the job to manual runs, set the default of `nightly_pause_status` in `databricks.yml` to `PAUSED` and deploy again.
