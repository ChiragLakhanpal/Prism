# The bundle's notes

Strata's Declarative Automation Bundle is `databricks.yml` at the root of the repo, with the files in this folder. It declares two things on the Free Edition workspace that Strata shares with fairshare.

- `catalog.yml` declares the catalog `strata`, its schemas `bronze`, `silver`, `gold` and `ops`, and the volume `strata.bronze.files`. It also gives the people who use the app read access, so the app can run each query as the viewer (ADR 0003). The bundle variable `readers` names them, and it is `account users`, everyone who can sign in to the workspace.
- `nightly.yml` declares the job `strata nightly`. Its ten tasks run one at a time, in the order of `docs/PLAN.md` section 11, and each writes one row to `strata.ops.pipeline_runs`. Three tasks have their work: `fetch_by_watermark` fetches every structured source in `config/sources.toml` into bronze, for every country (the monthly loan history for the slice's countries), `bronze_to_gold` builds silver and gold from them, and `measure_data_readiness` writes the data readiness measures to `strata.ops.data_readiness` and each table's size to `strata.ops.table_sizes`. The other seven do nothing yet.

A bundle does not declare tables. Each table is defined once, in `src/strata/lakehouse/tables/<schema>/<table>.sql`, and each view in `src/strata/lakehouse/views/<schema>/<view>.sql`, and the deploy command creates them on the SQL warehouse. The gate builds the same definitions on DuckDB, and it fails when a table has no `public_from` column (ADR 0002).

## Deploy

You need the Databricks CLI 0.287.0 or later, because only the direct deployment engine can create a catalog. Run this from the main checkout after the wizard has filled `.env`:

    uv run --script ops/bundle/deploy.py --env-file .env

It lists what the workspace holds, deploys the bundle, creates the tables, and prints what changed. A second run prints "No changes." It also lists fairshare's catalog before and after, and fails if the two listings differ. If fairshare's catalog has another name, pass it with `--fairshare-catalog`.

Then run these three checks, also from the main checkout:

    uv run --script ops/bundle/check.py job-run --env-file .env
    uv run --script ops/bundle/check.py same-rows --env-file .env
    uv run --script ops/bundle/check.py schedules --env-file .env --write

The first runs the nightly job by hand and checks its rows in `strata.ops.pipeline_runs`. The second runs the two sample queries, `tests/ground_truth/showcase_fiscal_years.sql` and `tests/ground_truth/pipeline_runs_columns.sql`, on DuckDB and on the SQL warehouse and compares the rows. The third reads both nightly jobs and how long their recent runs took, and writes the result in the block below.

Some things to know before the first deploy:

- If a catalog named `strata` already exists, the deploy cannot create it. Bind it to the bundle first with `databricks bundle deployment bind strata strata`.
- The target has no development mode on purpose. Development mode would put a prefix on the schema names, and Strata's SQL names them `strata.bronze` and so on.
- The grants in `catalog.yml` replace any other grants on Strata's own catalog, schemas and volume. They never touch fairshare's.
- SELECT on `strata.ops` reaches every future table in that schema. A table that holds uploads (CLAUDE.md rule 8) needs a row filter on the uploader's team, or a schema without this grant.

## The nightly window

The job starts at 05:00 in Washington (`America/New_York`) and stops after 150 minutes, at 07:30 at the latest. These are the reasons.

- **Review hours.** The panel works in Washington. The job stops by 07:30, half an hour before review hours start at 08:00, so no task is running when a review starts. I have not checked when the daily compute quota resets. The workspace catch-up records it.
- **fairshare's job.** I could not read fairshare's files on the build machine, so I chose this window without fairshare's schedule. The window misses any job that starts at an hour from 18:00 to midnight in Washington, or at midnight UTC, and finishes within four hours. That holds on every day of the year, including the night the clocks go forward, when midnight to 05:00 lasts only four hours. `tests/test_nightly.py` checks it for each day of a year.
- **The daily quota.** The two jobs share one daily compute quota and five concurrent job tasks. Strata's tasks run one at a time, so the job never uses more than one of the five.

The block below records both schedules and how long each job's runs took, as measured on the workspace. Fill it with the `schedules` check above. If the check finds that the two meet, change the hour in `nightly.yml` and run the deploy again.

<!-- bundle:schedules -->
- fairshare's job: Not measured yet. I could not read fairshare's files on the build machine, and the check needs the credentials in `.env`.
- Strata's job: strata nightly, daily at 05:00 America/New_York. It stops after 150 minutes. Nobody has measured its runs yet.
- Overlap: not checked yet.
- Measured: never. Run `uv run --script ops/bundle/check.py schedules --env-file .env --write`.
<!-- /bundle:schedules -->

To keep the job to manual runs, set the default of `nightly_pause_status` in `databricks.yml` to `PAUSED` and deploy again.
