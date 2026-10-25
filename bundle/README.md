# The bundle's notes

Strata's Declarative Automation Bundle is `databricks.yml` at the root of the repo, with the files in this folder. It declares three things on the Free Edition workspace that Strata shares with fairshare.

- `catalog.yml` declares the catalog `strata`, its schemas `bronze`, `silver`, `gold` and `ops`, and the volume `strata.bronze.files`. It also gives the people who use the app read access, so the app can run each query as the viewer (ADR 0003). The bundle variable `readers` names them, and it is `account users`, everyone who can sign in to the workspace.
- `dashboard.yml` declares the AI/BI dashboard `Strata`, whose file `dashboards/strata.lvdash.json` `src/strata/dashboard` writes from code. Its first page is Data readiness. Its queries run with each viewer's own credentials on the SQL warehouse the deploy passes as the variable `warehouse_id`. The measure task writes `strata.ops.readiness_snapshot`, the Data readiness page as the app builds it, which the dashboard reads.
- `nightly.yml` declares the job `strata nightly`. Its ten tasks run one at a time, in the order of `docs/PLAN.md` section 11, and each writes one row to `strata.ops.pipeline_runs`. Three tasks have their work: `fetch_by_watermark` fetches every structured source in `config/sources.toml` into bronze, for every country (the monthly loan history for the slice's countries), `bronze_to_gold` builds silver and gold from them, and `measure_data_readiness` writes the data readiness measures to `strata.ops.data_readiness` and each table's size to `strata.ops.table_sizes`. The other seven do nothing yet.

A bundle does not declare tables. Each table is defined once, in `src/strata/lakehouse/tables/<schema>/<table>.sql`, and each view in `src/strata/lakehouse/views/<schema>/<view>.sql`, and the deploy command creates them on the SQL warehouse. The gate builds the same definitions on DuckDB, and it fails when a table has no `public_from` column (ADR 0002).

## Deploy

You need the Databricks CLI 0.287.0 or later, because only the direct deployment engine can create a catalog. Run this from the main checkout after the wizard has filled `.env`:

    uv run --script ops/bundle/deploy.py --env-file .env

It lists what the workspace holds, deploys the bundle, creates the tables, and prints what changed. A second run prints "No changes." It also lists fairshare's catalog before and after, and fails if the two listings differ. If fairshare's catalog has another name, pass it with `--fairshare-catalog`.

Then run these four checks, also from the main checkout:

    uv run --script ops/bundle/check.py job-run --env-file .env
    uv run --script ops/bundle/check.py same-rows --env-file .env
    uv run --script ops/bundle/check.py readiness --env-file .env
    uv run --script ops/bundle/check.py schedules --env-file .env --write

The first runs the nightly job by hand and checks its rows in `strata.ops.pipeline_runs`. The second runs the two sample queries, `tests/ground_truth/showcase_fiscal_years.sql` and `tests/ground_truth/pipeline_runs_columns.sql`, on DuckDB and on the SQL warehouse and compares the rows. The third builds the Data readiness page on the SQL warehouse and checks that its awards row's rows held and STEP-reference link rate match a direct query on `strata.ops.data_readiness`. The fourth reads both nightly jobs and how long their recent runs took, and writes the result in the block below.

Some things to know before the first deploy:

- If a catalog named `strata` already exists, the deploy cannot create it. Bind it to the bundle first with `databricks bundle deployment bind strata strata`.
- The target has no development mode on purpose. Development mode would put a prefix on the schema names, and Strata's SQL names them `strata.bronze` and so on.
- The grants in `catalog.yml` replace any other grants on Strata's own catalog, schemas and volume. They never touch fairshare's.
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
- Strata's job: strata nightly, daily at 03:00 America/New_York. Its longest of the last four runs took 122 minutes, and it stops after 150 minutes.
- Overlap: none. With these durations the two jobs share no minute on any day from October 24, 2026 to October 24, 2027, and the same holds if Strata's job runs to its limit.
- Measured: October 24, 2026, with `uv run --script ops/bundle/check.py schedules --env-file .env --write`.
<!-- /bundle:schedules -->

To keep the job to manual runs, set the default of `nightly_pause_status` in `databricks.yml` to `PAUSED` and deploy again.
