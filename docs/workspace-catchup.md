# Workspace catch-up

Some steps must run on the shared Databricks workspace or in Azure. They could not run when their ticket merged, because `.env` had no credentials yet. Run them in order once the wizard from ticket 03 has filled `.env`. Each block names the ticket, the command to run, and what shows that it worked.

Check which keys are set first:

    python3 .claude/hooks/guard.py --env-keys

The merger appends a block below each time it parks a step.

## Ticket 03, step 1 of 4: the unit of a Global Batch capacity

The merger parked this step on October 23, 2026, after squash commit 43ed569. It needs the Azure sign-in.

Run this from the main checkout:

    az cognitiveservices account deployment show -g WorldBank-demo -n wb-strata --deployment-name gpt-5.4-nano --query sku -o json

It worked if the capacity in the output, times 1,000, equals the enqueued-token limit that the Azure portal shows for gpt-5.4-nano. If the two differ, change `capacity_unit` in `ops/dayone/dayone.toml` to the portal's limit divided by the capacity.

## Ticket 03, step 2 of 4: bound names and paths on the warehouse

The merger parked this step on October 23, 2026, after squash commit 43ed569. It needs the keys that the wizard writes to `.env`.

Run these two commands from the main checkout, one after the other:

    uv run --script ops/dayone/probe_parse_pad.py --env-file .env
    uv run --script ops/dayone/probe_ai_search.py --env-file .env

It worked if tests 3 and 4 in `docs/day-one-results.md` show a status other than "not run", and no evidence line says the warehouse refused `IDENTIFIER(:table)` or `READ_FILES(:path, ...)`. The wizard now always gives `AI_SEARCH_ENDPOINT` a value, so the test 4 probe has an endpoint name to use.

## Ticket 03, step 3 of 4: the probes' own schema

The merger parked this step on October 23, 2026, after squash commit 43ed569. Run it after step 2, because the two probes in step 2 make the schema `workspace.strata_dayone`.

Run this from the main checkout:

    databricks schemas get workspace.strata_dayone

It worked if the command returns the schema. The command line uses its default profile. If that profile points at a different workspace, add `-p strata`, the profile that the wizard's stage 4 signs in.

## Ticket 03, step 4 of 4: what the probe app's secret resource grants

The merger parked this step on October 23, 2026, after squash commit 43ed569. Run it after the probes have deployed the app `strata`.

Run this from the main checkout:

    databricks secrets list-acls strata

It worked if the app's service principal has READ on the scope `strata`. If it is not listed, Databricks granted the app only the one key. In that case, change the last bullet of `docs/day-one-results.md`, under "What the probes leave in the workspace", back to naming only `APPLICATIONINSIGHTS_CONNECTION_STRING`. As in step 3, add `-p strata` if the default profile points at a different workspace.

## Ticket 04, step 1 of 4: deploy the bundle twice

The merger parked this step on October 23, 2026, after merge commit 01a7286. It needs the Databricks keys in `.env` and the Databricks CLI 0.287.0 or later. If a catalog named `strata` already exists, run `databricks bundle deployment bind strata strata` first.

Run this command from the main checkout, and then run it a second time:

    uv run --script ops/bundle/deploy.py --env-file .env

It worked if both runs exit 0. The first run lists the catalog, the four schemas, `strata.bronze.files`, `strata.ops.pipeline_runs`, the grants and the job as new. Since ticket 08 merged, it also lists that ticket's 13 tables in `strata.bronze`, `strata.silver` and `strata.ops` as new. Since ticket 07 merged, it also lists that ticket's 13 tables as new: `strata.bronze.api_pages`, `strata.silver.awards`, `strata.silver.notices` (with its `fiscal_year` column), `strata.silver.projects`, `strata.silver.project_loans`, and the eight gold tables `strata.gold.country`, `project`, `project_loan`, `package`, `notice`, `contract`, `contract_supplier` and `supplier`. The line "Each of these exists now" also names the view `strata.silver.awards_current`, and `strata.ops.data_readiness` is created with ticket 07's `as_of` and `detail` columns. The second run prints "No changes.". Each run also prints "fairshare's catalog lists the same before and after the deploy: ..." (criteria 1 and 7). If fairshare's catalog has another name, add `--fairshare-catalog <name>`.

## Ticket 04, step 2 of 4: run the nightly job by hand

The merger parked this step on October 23, 2026, after merge commit 01a7286. Run it after step 1, because the deploy makes the job and `strata.ops.pipeline_runs`.

Run this from the main checkout:

    uv run --script ops/bundle/check.py job-run --env-file .env

It worked if the command exits 0 and prints "Run <id> wrote one row per task to strata.ops.pipeline_runs, in the bundle's order." That means ten rows in the order of `docs/PLAN.md` section 11 (criterion 2). Since ticket 07 merged, three of the tasks do real work, so the run takes longer and needs the World Bank's public APIs. `fetch_by_watermark` fetches Kenya's awards, notices and projects into `strata.bronze.api_pages`. `bronze_to_gold` fills `strata.silver.awards`, `notices`, `projects` and `project_loans`, and the eight gold tables `strata.gold.country`, `project`, `project_loan`, `package`, `notice`, `contract`, `contract_supplier` and `supplier`. `measure_data_readiness` writes Kenya's measures to `strata.ops.data_readiness`. Ticket 07's steps below read what this run wrote.

## Ticket 04, step 3 of 4: the same rows on DuckDB and on the SQL warehouse

The merger parked this step on October 23, 2026, after merge commit 01a7286. Run it after step 2, because `pipeline_runs_columns.sql` reads the table that the job writes. Since ticket 08 merged, this command also checks `delay_from_first_published_planned_date.sql` and `data_notes_actual_amount_zero.sql`, which read the plan tables. Those tables stay empty until ticket 08's step 1 has run, and until then the command exits 1 on those two files even when the deploy is fine. So run this step after ticket 08's step 1, below. Since ticket 07 merged, it also checks `kenya_step_reference_link_rate.sql`, which reads what step 2's job run wrote. Ticket 08's step 2 and ticket 07's step 2 are the same command, and one run covers all three tickets.

Run this from the main checkout:

    uv run --script ops/bundle/check.py same-rows --env-file .env

It worked if the command exits 0, and for each of `showcase_fiscal_years.sql`, `pipeline_runs_columns.sql`, `delay_from_first_published_planned_date.sql`, `data_notes_actual_amount_zero.sql` and `kenya_step_reference_link_rate.sql` in `tests/ground_truth/` it prints "DuckDB and the SQL warehouse returned the same ... rows, and they are the rows the file expects." (criterion 4).

## Ticket 04, step 4 of 4: record both nightly schedules

The merger parked this step on October 23, 2026, after merge commit 01a7286. Run it after step 2, and after fairshare's nightly job has finished at least one run.

Run this from the main checkout:

    uv run --script ops/bundle/check.py schedules --env-file .env --write

If the name of fairshare's job does not contain "fairshare", add `--fairshare-job <name>`. It worked if the command exits 0 and the `bundle:schedules` block in `bundle/README.md` records both jobs with "- Overlap: none" (criterion 3). Then commit `bundle/README.md` on `build/strata`. If the check finds that the two windows meet, change the hour in `bundle/nightly.yml` and run step 1 again.

## Ticket 08, step 1 of 2: read P156634's Procurement Plans on the warehouse

The merger parked this step on October 23, 2026, after merge commit eba87ed. It needs the Databricks keys in `.env`. Run it after ticket 04's step 1, because the deploy makes the plan tables and the volume `strata.bronze.files`. Run it after ticket 03's step 2 too, because day-one test 3 decides the layout parser. If test 3 failed in `docs/day-one-results.md`, stop here: Strata has an adapter only for `ai_parse_document`, so a Content Understanding adapter must first join `PARSERS` in `src/strata/reader/layout.py`.

Run this from the main checkout:

    uv run --script ops/plans/run_live.py --env-file .env

It worked if the command exits 0 and prints "Run plans-P156634-... read N plan versions of P156634 ...". In the measures it prints below that, `plan_versions_read`, `pages_read_route_b` and `latest_activities_with_first_listing_read` each show a count equal to the number after "of". `pages_read_route_b` may fall short only if the run also printed "It stopped at the cap ...". On the warehouse, `strata.ops.parse_runs` has a row for P156634 with `pages_parsed` above 0, and `strata.ops.data_readiness` has the run's six measures. The run also proves that real `ai_parse_document` output has the version 2.0 shape the tests were written against. Then run the same command a second time on the same day, in UTC. It worked if that run parses 0 pages (criterion 5).

If a fetch from the World Bank's hosts or an upload to the volume fails, the script stops with a Python traceback, not a one-line message. The pages it parsed before that stay in bronze, so run it again.

## Ticket 08, step 2 of 2: the plan's queries on DuckDB and on the SQL warehouse

The merger parked this step on October 23, 2026, after merge commit eba87ed. Run it after step 1, because the two plan files read the tables that step 1 fills. It is the same command as ticket 04's step 3, and one run covers both tickets.

Run this from the main checkout:

    uv run --script ops/bundle/check.py same-rows --env-file .env

It worked if the command exits 0 and prints "DuckDB and the SQL warehouse returned the same one row, and they are the rows the file expects." for `tests/ground_truth/delay_from_first_published_planned_date.sql`, with 2021-04-21, 2021-07-01, 2022-01-03, 186 and 1245092.76 (criterion 2). It must also print "... the same two rows, and they are the rows the file expects." for `tests/ground_truth/data_notes_actual_amount_zero.sql`, with KE-NWWDA-503455-CW-RFQ Signed 0.00 and KE-NWWDA-541061-CW-RFQ Completed 0.00 (criterion 4).

## Ticket 07, step 1 of 3: the job fetched Kenya into bronze

The merger parked this step on October 23, 2026, after merge commit dbc054a. Run it after ticket 04's steps 1 and 2, because the deploy makes `strata.bronze.api_pages` and the job run fills it. Deploy from `build/strata` at dbc054a or later, so that the first deploy creates `strata.silver.notices` with its `fiscal_year` column and `strata.ops.data_readiness` with `as_of` and `detail`. Each table is defined with `CREATE TABLE IF NOT EXISTS`, so a table that already exists keeps its old columns.

Run this query in the workspace's SQL editor, on the SQL warehouse:

    SELECT source, count(*) AS pages FROM strata.bronze.api_pages WHERE country_code = 'KE' GROUP BY source ORDER BY source

It worked if it returns three rows, `awards`, `notices` and `projects`, each with one page or more (criterion 8).

## Ticket 07, step 2 of 3: the link rate in strata.ops equals a direct count over gold

The merger parked this step on October 23, 2026, after merge commit dbc054a. Run it after step 1. It is the same command as ticket 04's step 3 and ticket 08's step 2, and one run covers all three tickets.

Run this from the main checkout:

    uv run --script ops/bundle/check.py same-rows --env-file .env

It worked if the command exits 0 and prints "kenya_step_reference_link_rate.sql: DuckDB and the SQL warehouse returned the same one row, and they are the rows the file expects." That row is `linked_step_reference,true` (criterion 8). The file compares the link rate that the job's last run wrote to `strata.ops.data_readiness` with a direct count of Kenya's contracts in `strata.gold.contract` that carry a STEP reference. Offline it was 528 of 603 on the fixture. The warehouse's counts will be larger, because the job fetches every Kenya award since FY2020, but the file returns only true or false.

## Ticket 07, step 3 of 3: a second run adds no award pages

The merger parked this step on October 23, 2026, after merge commit dbc054a. Run it after step 2, on the same day as ticket 04's step 2.

First run this query in the workspace's SQL editor, and note the count:

    SELECT count(*) AS pages FROM strata.bronze.api_pages WHERE source = 'awards'

Then run the nightly job a second time from the main checkout:

    uv run --script ops/bundle/check.py job-run --env-file .env

Then run the query again. It worked if the job run exits 0 and the count is the same as before (the verifier's observation O2). A page's records are now hashed in a fixed order, so the same awards in a new order make no new page. If the count grew, read `newest_record_on` in the new rows before you call it a failure, because Finances One may have published new awards between the two runs.

## Ticket 09, step 1 of 3: turn on user authorization for the App

The merger parked this step on October 23, 2026, after merge commit f9cc969. It needs the Databricks keys in `.env`. Run it after ticket 06 has deployed the App `strata` from `build/strata` at f9cc969 or later, with `DATABRICKS_WAREHOUSE_ID` set in the App's environment. Without that variable, the plan-check routes answer HTTP 503 with the code `no_data_service`.

Run this from the main checkout:

    databricks apps update strata --json '{"user_api_scopes": ["sql"]}'

If the command line refuses the field, open the App in the workspace, choose Configure, then User authorization, and add the scope `sql`. Each user signs in to the App again to agree to the new scope.

It worked if `databricks apps get strata -o json` lists `sql` under `effective_user_api_scopes`, and `GET /api/me` on the App, opened in a browser as a signed-in user, returns `"has_token": true`. That shows each request now carries `X-Forwarded-Access-Token`. As in ticket 03's steps, add `-p strata` if the default profile points at a different workspace.

## Ticket 09, step 2 of 3: a user who cannot read strata gets a permission error

The merger parked this step on October 23, 2026, after merge commit f9cc969. Run it after step 1. The App's address is the `url` field of `databricks apps get strata -o json`.

Sign in to the App in a browser as a user with no USE CATALOG on `strata`, and open:

    <App url>/api/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09?asof=2026-10-22

It worked if the answer is HTTP 403 with the body `{"code": "permission"}` and no rows. That also shows the warehouse's error text matches `PERMISSION_MARKERS` in `src/strata/lakehouse/engine.py`.

Then open the same address as a user who has USE CATALOG and USE SCHEMA on `strata` but no SELECT. It should also be HTTP 403. If it is HTTP 503 with the code `data_service`, find the answer's reference in the server log. If the warehouse said `TABLE_OR_VIEW_NOT_FOUND`, add that marker to `PERMISSION_MARKERS`, so this user gets the permission error instead.

## Ticket 09, step 3 of 3: the plan check on the warehouse equals the recorded answer

The merger parked this step on October 23, 2026, after merge commit f9cc969. Run it after step 1, and after ticket 08's step 1 (`ops/plans/run_live.py`) has filled the plan tables on the warehouse.

Sign in to the App in a browser as a user with USE CATALOG, USE SCHEMA and SELECT on `strata`, and open:

    <App url>/api/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09?asof=2026-10-22

It worked if the answer is HTTP 200 and its body equals `tests/fixtures/api/check-plan-p156634-nwwda-2026-10-09.json`. Its counts say 9 activities were checked: 1 `needs_a_look`, 2 `watch`, 3 `data_note` and 3 with no mark. This one call also proves that check_plan's four SQL files in `src/strata/tools/sql/check_plan/` run on the SQL warehouse without transpiling (`GREATEST` over columns that may be empty, and a correlated subquery in `project.sql`).
