# Workspace catch-up

Some steps must run on the shared Databricks workspace or in Azure. They could not run when their ticket merged, because `.env` had no credentials yet. Run them in order once the wizard from ticket 03 has filled `.env`. Each block names the ticket, the command to run, and what shows that it worked.

Check which keys are set first:

    python3 .claude/hooks/guard.py --env-keys

The merger appends a block below each time it parks a step.

## Ticket 03, before every other step: the wizard, the day-one probes and the pay-as-you-go check

The orchestrator added this block on October 23, 2026, after the P0 phase gate found it missing. Ticket 03 is ready-for-human: its criteria 2, 3, 4 and 5 are parked until you run these. Every block below needs the `.env` that the wizard writes, so this comes first.

Run this from the main checkout, in this order:

    bash ops/wizard/strata-setup.sh
    bash ops/dayone/run-probes.sh --env-file .env
    bash ops/wizard/strata-setup.sh

The first wizard run fills `.env` and the human-only tests. The probes run tests 1, 2, 3, 4, 5 and 10 and write their results. The second wizard run finishes test 6.

It worked if `grep -c "None yet. The command above fills it." docs/day-one-results.md` prints 0, and `python3 ops/dayone/dayone.py show` lists ten tests, each with a status other than "not run" and a chosen path (criteria 2 and 4).

Then run:

    uv run --script ops/dayone/probe_caps.py --env-file .env

It worked if it exits 0, prints a limit for each of the four deployments, and prints "Status: capped" with a budget line that names its alerts (criterion 3).

Then, before the free credit ends on November 10, 2026, run the wizard's pay-as-you-go stage (stage 12), or `probe_caps.py` again after the upgrade. It worked if `python3 ops/dayone/dayone.py field payg Status` prints "Done on ...", "The subscription showed pay-as-you-go on ...", or "Planned for" a date before November 10, 2026, and the Who field is filled (criterion 5).

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

It worked if both runs exit 0. The first run lists the catalog, the four schemas, `strata.bronze.files`, `strata.ops.pipeline_runs`, the grants and the job as new. Since ticket 08 merged, it also lists that ticket's 13 tables in `strata.bronze`, `strata.silver` and `strata.ops` as new. Since ticket 07 merged, it also lists that ticket's 13 tables as new: `strata.bronze.api_pages`, `strata.silver.awards`, `strata.silver.notices` (with its `fiscal_year` column), `strata.silver.projects`, `strata.silver.project_loans`, and the eight gold tables `strata.gold.country`, `project`, `project_loan`, `package`, `notice`, `contract`, `contract_supplier` and `supplier`. The line "Each of these exists now" also names the view `strata.silver.awards_current`, and `strata.ops.data_readiness` is created with ticket 07's `as_of` and `detail` columns. Since ticket 17 merged, it also lists that ticket's 12 tables as new: `strata.silver.awards_fy2001_2016`, `ieg_ratings`, `loans`, `loan_history`, `indicators` and `project_isr_ratings`, `strata.gold.ieg_rating`, `loan`, `project_closing_date`, `governance_score` and `project_isr_rating`, and `strata.ops.table_sizes`. It also creates `strata.gold.contract` keyed by `contract_id`, with `wb_contract_number` allowed to be empty, `strata.silver.awards` with `market_approach`, `strata.silver.notices` and `strata.gold.notice` with `contract_fiscal_year`, and `strata.silver.projects` and `strata.gold.project` with `major_sector_code`, `sector` and `sector_name`. Since ticket 13 merged, it also lists `strata.ops.agent_runs` as new, where each answer's run is logged. Each table is defined with `CREATE TABLE IF NOT EXISTS`, so if an earlier deploy already made one of these tables, add its missing columns with `ALTER TABLE ... ADD COLUMNS` before the job runs. The second run prints "No changes.". Each run also prints "fairshare's catalog lists the same before and after the deploy: ..." (criteria 1 and 7). If fairshare's catalog has another name, add `--fairshare-catalog <name>`.

## Ticket 04, step 2 of 4: run the nightly job by hand

The merger parked this step on October 23, 2026, after merge commit 01a7286. Run it after step 1, because the deploy makes the job and `strata.ops.pipeline_runs`.

Run this from the main checkout:

    uv run --script ops/bundle/check.py job-run --env-file .env

It worked if the command exits 0 and prints "Run <id> wrote one row per task to strata.ops.pipeline_runs, in the bundle's order." That means ten rows in the order of `docs/PLAN.md` section 11 (criterion 2). Since ticket 07 merged, three of the tasks do real work, so the run takes longer and needs the World Bank's public APIs. Since ticket 17 merged, `fetch_by_watermark` fetches every structured source in `config/sources.toml` into `strata.bronze.api_pages`, for every country: contract awards since FY2020, contract awards FY2001 to FY2016, IEG ratings, IDA credits and IBRD loans, procurement notices, projects, CPIA and WGI. Only the monthly loan history (`ida_credit_history` and `ibrd_loan_history`) is fetched for the slice's countries alone. `bronze_to_gold` fills ticket 07's silver and gold tables (`strata.silver.awards`, `notices`, `projects` and `project_loans`, and `strata.gold.country`, `project`, `project_loan`, `package`, `notice`, `contract`, `contract_supplier` and `supplier`) and ticket 17's tables, which step 1 lists. `measure_data_readiness` writes every source's measures to `strata.ops.data_readiness` and each table's size to `strata.ops.table_sizes`. The first run makes about 1,900 requests and may come close to the job's 2.5-hour timeout. If it stops, run the command again: bronze keeps each page as it arrives, and the watermark counts only fetches that finished. Ticket 07's steps below read what this run wrote.

## Ticket 04, step 3 of 4: the same rows on DuckDB and on the SQL warehouse

The merger parked this step on October 23, 2026, after merge commit 01a7286. Run it after step 2, because `pipeline_runs_columns.sql` reads the table that the job writes. Since ticket 08 merged, this command also checks `delay_from_first_published_planned_date.sql` and `data_notes_actual_amount_zero.sql`, which read the plan tables. Those tables stay empty until ticket 08's step 1 has run, and until then the command exits 1 on those two files even when the deploy is fine. So run this step after ticket 08's step 1, below. Since ticket 07 merged, it also checks `kenya_step_reference_link_rate.sql`, which reads what step 2's job run wrote. Since ticket 17 merged, it also checks that ticket's three files, which read what the job wrote for every country. Ticket 08's step 2 and ticket 07's step 2 are the same command, and one run covers all three tickets.

Run this from the main checkout:

    uv run --script ops/bundle/check.py same-rows --env-file .env

It worked if the command exits 0, and for each of `showcase_fiscal_years.sql`, `pipeline_runs_columns.sql`, `delay_from_first_published_planned_date.sql`, `data_notes_actual_amount_zero.sql` and `kenya_step_reference_link_rate.sql` in `tests/ground_truth/` it prints "DuckDB and the SQL warehouse returned the same ... rows, and they are the rows the file expects." (criterion 4). The same must hold for ticket 17's `every_source_holds_the_rows_its_api_reported.sql`, `gap_years_contracts_from_award_notices.sql` and `structured_data_under_the_limit.sql`. Ticket 17's step 1 below gives the rows each must return. Its projection puts structured data at 1.57 GB at full scale, over the 0.5 GB limit, so expect the size file to fail until you answer decision 18 in `docs/STATUS.md`.

## Ticket 04, step 4 of 4: record both nightly schedules

The merger parked this step on October 23, 2026, after merge commit 01a7286. Run it after step 2, and after fairshare's nightly job has finished at least one run.

Run this from the main checkout:

    uv run --script ops/bundle/check.py schedules --env-file .env --write

If the name of fairshare's job does not contain "fairshare", add `--fairshare-job <name>`. It worked if the command exits 0 and the `bundle:schedules` block in `bundle/README.md` records both jobs with "- Overlap: none" (criterion 3). Then commit `bundle/README.md` on `build/strata`. If the check finds that the two windows meet, change the hour in `bundle/nightly.yml` and run step 1 again.

## Ticket 08, step 1 of 2: read P156634's Procurement Plans on the warehouse

The merger parked this step on October 23, 2026, after merge commit eba87ed. It needs the Databricks keys in `.env`. Run it after ticket 04's step 1, because the deploy makes the plan tables and the volume `strata.bronze.files`. Run it after ticket 03's step 2 too, because day-one test 3 decides the layout parser. If test 3 failed in `docs/day-one-results.md`, stop here: Strata has an adapter only for `ai_parse_document`, so a Content Understanding adapter must first join `PARSERS` in `src/strata/reader/layout.py`.

Run this from the main checkout:

    uv run --script ops/plans/run_live.py --env-file .env

It worked if the command exits 0 and prints "Run plans-P156634-... read N plan versions of P156634 ...". In the measures it prints below that, `plan_versions_read`, `pages_read_route_b` and `latest_activities_with_confirmed_first_listing_read` each show a count equal to the number after "of". `pages_read_route_b` may fall short only if the run also printed "It stopped at the cap ...". On the warehouse, `strata.ops.parse_runs` has a row for P156634 with `pages_parsed` above 0, and `strata.ops.data_readiness` has the run's six measures. The run also proves that real `ai_parse_document` output has the version 2.0 shape the tests were written against. Then run the same command a second time on the same day, in UTC. It worked if that run parses 0 pages (criterion 5).

If a fetch from the World Bank's hosts or an upload to the volume fails, the script exits 2 and prints "The run stopped before it finished: ...". The pages it parsed before that stay in bronze, so run it again.

## Ticket 08, step 2 of 2: the plan's queries on DuckDB and on the SQL warehouse

The merger parked this step on October 23, 2026, after merge commit eba87ed. Run it after step 1, because the two plan files read the tables that step 1 fills. It is the same command as ticket 04's step 3, and one run covers both tickets.

Run this from the main checkout:

    uv run --script ops/bundle/check.py same-rows --env-file .env

It worked if the command exits 0 and prints "DuckDB and the SQL warehouse returned the same one row, and they are the rows the file expects." for `tests/ground_truth/delay_from_first_published_planned_date.sql`, with 2021-04-21, 2021-07-01, 2022-01-03, 186 and 1245092.76 (criterion 2). It must also print "... the same two rows, and they are the rows the file expects." for `tests/ground_truth/data_notes_actual_amount_zero.sql`, with KE-NWWDA-503455-CW-RFQ Signed 0.00 and KE-NWWDA-541061-CW-RFQ Completed 0.00 (criterion 4).

## Ticket 07, step 1 of 3: the job fetched Kenya into bronze

The merger parked this step on October 23, 2026, after merge commit dbc054a. Run it after ticket 04's steps 1 and 2, because the deploy makes `strata.bronze.api_pages` and the job run fills it. Deploy from `build/strata` at f5c933d (ticket 17's merge) or later, so that the first deploy creates `strata.silver.notices` with its `fiscal_year` column, `strata.ops.data_readiness` with `as_of` and `detail`, and ticket 17's tables and columns, which ticket 04's step 1 lists. Each table is defined with `CREATE TABLE IF NOT EXISTS`, so a table that already exists keeps its old columns.

Run this query in the workspace's SQL editor, on the SQL warehouse:

    SELECT source, count(*) AS pages FROM strata.bronze.api_pages WHERE source IN ('awards', 'notices', 'projects') GROUP BY source ORDER BY source

Since ticket 17 merged, the job asks for these three sources for every country at once, and such a page has no `country_code`, so the query no longer filters on Kenya. Kenya's records come in those pages.

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

## Ticket 11, step 1 of 4: read the first 20 documents into passages and sync the AI Search index

The merger parked this step on October 23, 2026, after merge commit e0721da. It needs the Databricks keys, `AI_SEARCH_ENDPOINT`, `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` in `.env`. Run it after ticket 04's step 1, because the deploy makes the passage tables, and after ticket 04's step 2, because the nightly job fills `strata.gold.project`.

Run this from the main checkout:

    uv run --script ops/documents/run_live.py --env-file .env

It worked if the command exits 0 and its last line says the index `strata.gold.passage_index` "holds N of the N passages in strata.gold.passage and is ready", with both numbers the same (criterion 7). Exit 1 means the run finished but the index did not catch up within 30 minutes. Run the command again, and it syncs the index again.

The measures it prints come from `strata.ops.data_readiness` on the warehouse. `documents_read_route_a_text` must add up to 20 across P130164 and P156634. Each project must also show `document_pages_route_a`, `document_pages_route_b`, `document_pages_paragraph_numbering_found` and `contact_details_removed`. On the fixture, the run read 20 documents into 733 passages, and the measures read:

| Measure | P130164 | P156634 |
|---|---|---|
| documents_read_route_a_text | 16 of 17 | 4 of 4 |
| document_pages_route_a | 177 of 287 | 127 of 133 |
| document_pages_route_b | 110 of 287 | 6 of 133 |
| document_pages_paragraph_numbering_found | 67 of 83 | 78 of 92 |
| contact_details_removed | 1 of 17 | 1 of 4 |

The warehouse's counts may differ if the World Bank's hosts now list newer ISRs. Read `contact_details_removed` from the first run only: a second run writes it as 0 of 0, because it counts only the documents fetched in that run (review round 2, P1, not fixed yet).

## Ticket 11, step 2 of 4: paragraph 54's passage on DuckDB and on the SQL warehouse

The merger parked this step on October 23, 2026, after merge commit e0721da. Run it after step 1. It is the same command as ticket 04's step 3, ticket 07's step 2 and ticket 08's step 2. If you ran it before step 1, run it again now, because `tests/ground_truth/icr_paragraph_54_passage.sql` reads `strata.gold.passage`, which step 1 fills.

Run this from the main checkout:

    uv run --script ops/bundle/check.py same-rows --env-file .env

It worked if the command exits 0 and prints "icr_paragraph_54_passage.sql: DuckDB and the SQL warehouse returned the same one row, and they are the rows the file expects." with the row `31525018/v1/54`, `III.B`, 23, 66, `19 of 62`, 1, 2019-11-02 (criterion 7).

## Ticket 11, step 3 of 4: search_passages finds paragraph 54 through AI Search

The merger parked this step on October 23, 2026, after merge commit e0721da. Run it after step 1, once the index holds every passage. It needs `DATABRICKS_TOKEN` to be a person's token, because the tool acts as the viewer. A service principal's sign-in is not enough.

Run this from the main checkout:

    uv run --script ops/documents/search_live.py --env-file .env

It worked if the command exits 0, its first line starts "search_passages ranked with AI Search: AI Search's hybrid query, words and vector, with its reranker", `strata.gold.passage:31525018/v1/54` is one of the three passages it lists, and its last line reads "1 of the 1 expected passages are in the top three." (criterion 3, workspace half).

Then replace `tests/fixtures/ai_search/query.json` with a recorded answer. No script records it yet. Save the JSON that `POST /api/2.0/vector-search/indexes/strata.gold.passage_index/query` returned for this question under `"response"`, set `"recorded"` to `true`, and change `"about"` to say when it was recorded. The tests in `tests/test_knowledge_adapters.py` check the hand-written ids and scores (`31525018/v1/54` 0.0327, `34056616/v2/10.b` 0.0322, `31525018/v1/55` 0.0301), so change them to the recorded ones in the same commit. It worked if the gate passes with the recorded file.

## Ticket 11, step 4 of 4: Prompt Shields and the embeddings ran on every passage

The merger parked this step on October 23, 2026, after merge commit e0721da. It has no command of its own: step 1's run scans every passage with Prompt Shields on the Foundry resource and embeds it with `text-embedding-3-large`. Read the output of step 1.

It worked if the run's summary line says "Prompt Shields scanned N new passage texts and text-embedding-3-large embedded N.", and, for both P130164 and P156634, `passages_screened` and `passages_embedded` each show a count equal to the number after "of" (criterion 8, live half). On the fixture these read 392 of 392 and 341 of 341. Then run this in the workspace's SQL editor:

    SELECT shield, count(*) AS texts, count_if(attack_detected) AS attacks FROM strata.silver.passage_shields GROUP BY shield

It worked if it returns one row, with the shield `Prompt Shields`. Its `texts` can be lower than the number of passages, because passages with the same header and text are scanned once (on the fixture, 650 texts for 733 passages). If `attacks` is above 0, `passages_prompt_shields_hit` must be above 0 for at least one of the two projects. Any attack found is kept, counted and left out of search, so a number above 0 is not a failure. Read those passages before the demo.

## Ticket 06, step 1 of 6: deploy the App and see its address

The merger parked this step on October 23, 2026, after merge commit a976b81. It needs the Databricks keys in `.env`, `DATABRICKS_WAREHOUSE_ID` among them, and the Application Insights connection string that the wizard saved in the secret scope. Run it after ticket 04's step 1, because the bundle deploy makes `strata.ops.usage_events`. Run it before ticket 09's three steps above, because they need the App it deploys. The deploy also asks for the `sql` user authorization scope, so ticket 09's step 1 may only need its check.

Run this from the main checkout:

    uv run --script ops/app/deploy_app.py --env-file .env

It worked if the command exits 0 and its last line reads `Strata is running at https://...`, and the App's Logs tab in the workspace shows that it installed `ops/app/requirements.txt` and that the server is serving (criterion 1). The logs should not show the agent-framework metapackage installed, because the lean requirements file leaves it out.

Run this command again after every bundle deploy. The bundle's grants replace the App's USE CATALOG and USE SCHEMA on `strata`, so its usage events stop being written until the App's deploy grants them again.

## Ticket 06, step 2 of 6: the identity route shows your own account

The merger parked this step on October 23, 2026, after merge commit a976b81. Run it after step 1. The App's address is the one step 1 printed, or the `url` field of `databricks apps get strata -o json`.

Sign in to the workspace in a browser and open:

    <App url>/api/me

It worked if the answer holds your own email and `"has_token": true`, and never the token itself. Ticket 01's verifier asked for this check. If `has_token` is false, run ticket 09's step 1, sign in to the App again and reload.

## Ticket 06, step 3 of 6: two users each read the stamp as themselves

The merger parked this step on October 23, 2026, after merge commit a976b81. Run it after step 1. It needs two workspace users who can read `strata.ops`.

Each of the two users signs in and opens these two addresses:

    <App url>/
    <App url>/api/me/warehouse

The first page reads the stamp through `src/strata/server/sql/data_through.sql` with that user's own token. The second answers with the user name the warehouse saw.

It worked if each user's `/api/me/warehouse` answer names that user and not the other one, and the SQL warehouse's query history shows the `data_through.sql` query run once by each of them, under their own names and not the App's service principal (criterion 2).

## Ticket 06, step 4 of 6: an outside reviewer opens the App (day-one test 6)

The merger parked this step on October 23, 2026, after merge commit a976b81. Run it after step 1, so the App exists. Before that, the wizard records test 6 as waiting.

Run this from the main checkout, and follow the stage "An outside reviewer in the workspace (test 6)":

    bash ops/wizard/strata-setup.sh

Then check the result:

    python3 ops/dayone/dayone.py field test-6 Status

It worked if it prints `passed`, and a reviewer with an outside email opens `<App url>` and sees the navy bar, the stamp and their own email in the view popover (criterion 4).

If it prints `failed`, the plan is a Container Apps copy of the same build behind Entra sign-in, and the reviewer opens that copy after signing in. No script in the repo builds that copy yet, because test 6 has not run. Tell the orchestrator, so it becomes its own ticket before the Round 2 date.

## Ticket 06, step 5 of 6: a request to the App appears in Application Insights

The merger parked this step on October 23, 2026, after merge commit a976b81. Run it after step 1. It needs the Application Insights resource that the wizard made (test 10).

Open `<App url>/` once in a browser. Wait 10 seconds, which is how long the App holds its usage events before it writes them (`usage_flush_seconds` under `[app]` in `config/thresholds.toml`). Then run this in the workspace's SQL editor:

    SELECT route, requested_at, trace_id FROM strata.ops.usage_events WHERE route = '/api/freshness' ORDER BY requested_at DESC LIMIT 1

Then run this in Application Insights, under Logs:

    requests | where name startswith "GET /api/freshness" | order by timestamp desc | take 1 | project timestamp, name, operation_Id

It worked if the two rows have the same time, to within a few seconds, and `operation_Id` equals `trace_id` (criterion 6, trace half).

Also check where a failed request's details go. The verifier found that once Azure Monitor starts, the server's own warning and error lines go to Application Insights and no longer to the App's log. After a request that fails, search the `traces` table in Application Insights for the reference in the error's answer. If the line is there and not in the App's log, tell the orchestrator. One `logging.basicConfig(level=logging.INFO)` line in `src/strata/server/__main__.py` would send it to both.

## Ticket 06, step 6 of 6: the Lakebase probe chooses where app state lives

The merger parked this step on October 23, 2026, after merge commit a976b81. Run it after the wizard and before ticket 15 starts, because ticket 15 writes the first app state. It needs the Databricks keys in `.env`.

Run this from the main checkout:

    uv run --script ops/app/probe_lakebase.py --env-file .env

It worked if the result block in `docs/app-state.md` reads `Status: run`, lists real times for both stores, names the chosen store, and gives today's date as the last run (criterion 7). If Lakebase wins, `docs/adr` also holds a new ADR named `NNNN-app-state-lives-in-lakebase.md`, numbered one after the highest ADR there. Commit both files on `build/strata` before ticket 15 starts, so its builder reads the choice.

## Ticket 17, step 1 of 3: every source's rows, the gap years and the size of structured data

The merger parked this step on October 23, 2026, after merge commit f5c933d. It needs the Databricks keys in `.env`. Run it after ticket 04's steps 1 and 2 and ticket 11's step 1. Then run the nightly job once more with `uv run --script ops/bundle/check.py job-run --env-file .env`, so that `strata.ops.table_sizes` measures the passage and vector tables with their rows. It is the same command as ticket 04's step 3, and one run covers every ticket.

Run this from the main checkout:

    uv run --script ops/bundle/check.py same-rows --env-file .env

It worked if it prints "... returned the same 11 rows, and they are the rows the file expects." for `every_source_holds_the_rows_its_api_reported.sql`, with `true` for each of `awards`, `awards_fy2001_2016`, `cpia`, `ibrd_loan_history`, `ibrd_loans`, `ida_credit_history`, `ida_credits`, `ieg_ratings`, `notices`, `projects` and `wgi` (criterion 1). It must print "... the same three rows ..." for `gap_years_contracts_from_award_notices.sql`, with `true,true` for 2017, 2018 and 2019 (criterion 2). It must print "... the same one row ..." for `structured_data_under_the_limit.sql`, with `true,true` under `measured,under_the_limit` (criterion 7).

Then run this in the workspace's SQL editor:

    SELECT table_name, structured, row_count FROM strata.ops.table_sizes WHERE run_id = (SELECT run_id FROM strata.ops.table_sizes ORDER BY measured_at DESC LIMIT 1) AND table_name IN ('strata.gold.passage', 'strata.silver.passage_embeddings')

It worked if it returns two rows, each with `structured` false and `row_count` above 0. Those tables hold passages and vectors, which PLAN.md section 3 leaves out of structured data.

Criterion 7 stays parked until you answer decision 18 in `docs/STATUS.md`. On the fixture, `strata.ops.table_sizes` recorded 36 structured tables with 11,010,048 bytes in all, and the size file returned `true,true`. At full scale the branch projects 1.57 GB: bronze 885 MB, silver 541 MB and gold 146 MB, and notices are 964 MB of it. So as built, expect the size file to return `true,false` and the command to exit 1. To see the bytes per table, run `SELECT table_name, row_count, bytes FROM strata.ops.table_sizes WHERE structured AND run_id = (SELECT run_id FROM strata.ops.table_sizes ORDER BY measured_at DESC LIMIT 1) ORDER BY bytes DESC`.

## Ticket 17, step 2 of 3: P156634's closing date moved three times since 2022

The merger parked this step on October 23, 2026, after merge commit f5c933d. Run it after ticket 04's step 2, because the job fills `strata.gold.project_closing_date` from the monthly loan history.

Run this in the workspace's SQL editor:

    SELECT closing_date, previous_closing_date, reported_on FROM strata.gold.project_closing_date WHERE project_id = 'P156634' AND previous_closing_date IS NOT NULL AND reported_on >= DATE '2022-01-01' ORDER BY reported_on

It worked if it returns three rows: 2024-04-30 after 2022-10-31, reported 2022-11-30; 2025-10-31 after 2024-04-30, reported 2024-04-30; and 2026-10-31 after 2025-10-31, reported 2025-11-30 (criterion 4). These match the fixture's loan history for both credits, IDA60290 and IDA60300. If the history now reports a newer month with another closing date, a fourth row after 2025-11-30 is not a failure.

## Ticket 17, step 3 of 3: a second night adds no pages it should not, and every count still holds

The merger parked this step on October 23, 2026, after merge commit f5c933d. Run it after step 1, on the next night or later.

First run this in the workspace's SQL editor, and note each count:

    SELECT source, count(*) AS pages FROM strata.bronze.api_pages GROUP BY source ORDER BY source

Then run the nightly job again from the main checkout, run the query again, and then run the same-rows check:

    uv run --script ops/bundle/check.py job-run --env-file .env
    uv run --script ops/bundle/check.py same-rows --env-file .env

It worked if the job run exits 0 and a source's page count grew only when its API changed between the two runs. Record how many pages `fetch_by_watermark` added for `awards`. `awards_fy2001_2016`, which has been frozen since March 2022, must add none. The monthly loan history (`ida_credit_history` and `ibrd_loan_history`) must add none unless a new month came out between the two runs (criterion 8).

Run the job a second night. `coverage_rows` for notices and projects still equals the reported total, and `every_source_holds_the_rows_its_api_reported.sql` returns true for every source. `strata.ops.table_sizes` marks `strata.gold.passage` and `strata.silver.passage_embeddings` as not structured. To read the first part, run:

    SELECT source, count, denominator FROM strata.ops.data_readiness WHERE measure = 'coverage_rows' AND subject = 'all' AND source IN ('notices', 'projects') AND run_id = (SELECT run_id FROM strata.ops.data_readiness WHERE measure = 'coverage_rows' ORDER BY measured_at DESC LIMIT 1)

It worked if both rows show `count` equal to `denominator`. On the fixture they read 418 of 418 for notices and 93 of 93 for projects. The same-rows check shows the second part, and the table sizes query in step 1 shows the last. If notices or projects read over the total, see ticket 17's third parked decision in its done comment: the job cannot see a record that a search source withdraws after Strata fetched it.

## Ticket 13, step 1 of 4: the Foundry agent and its guardrail match the repo

The merger parked this step on October 23, 2026, after merge commit c42d9ce. Run it after ticket 03's wizard. It needs `FOUNDRY_PROJECT_ENDPOINT` in `.env` and the `az` command line signed in to the subscription that holds the Foundry resource named in `ops/dayone/dayone.toml`.

Run this from the main checkout, and then run it again with `--check`:

    uv run --script ops/agent/sync.py --env-file .env
    uv run --script ops/agent/sync.py --env-file .env --check

It worked if the first run prints what differed, with a diff of the instructions, and ends "I made version N of strata-orchestrator, which matches the repo." The first run also makes the guardrail `strata-guardrail`: content filters, and Prompt Shields on the question and on tool results. The second run must exit 0 and print "Foundry's agent strata-orchestrator, version N, matches the repo: there is no difference in its model, instructions, tools, description or guardrail (strata-guardrail)." (criterion 5, live half). Exit 1 means `--check` found a difference, and exit 2 means it could not run. Run the pair again after any change to `src/strata/agent/instructions/orchestrator.md`, `config/agents.toml`, `config/models.toml` or a tool in `config/tools.toml`.

## Ticket 13, step 2 of 4: five passages with rule-like sentences reach the agent with no refusal

The merger parked this step on October 23, 2026, after merge commit c42d9ce. Run it after step 1 and after a gate run, because it reads the passages from the fixture database that the gate builds (`data/out/fixture.duckdb`). It needs `FOUNDRY_PROJECT_ENDPOINT` in `.env` and `az` signed in.

Run this from the main checkout:

    uv run --script ops/agent/shields_live.py --env-file .env

It worked if it exits 0, prints "passed" for each of the five passages in `evals/shield_passages.toml` (ICR P130164 ¶71 and ¶86, and P156634's PAD Annex 3 ¶51 and ¶52 and Annex 2 ¶46), and ends "All 5 passages reached the agent as tool results with no refusal." (criterion 7). Exit 1 means a content filter or Prompt Shields refused a passage, or the agent called no tool, and the lines above the exit name each one.

## Ticket 13, step 3 of 4: the showcase question through the live agent, logged with its trace

The merger parked this step on October 23, 2026, after merge commit c42d9ce. Run it after step 1, after ticket 11's step 1 (the live passage run, `ops/documents/run_live.py`), and after ticket 04's step 1 deployed from c42d9ce or later, because that deploy makes `strata.ops.agent_runs`. It needs `FOUNDRY_PROJECT_ENDPOINT`, `DATABRICKS_HOST`, `DATABRICKS_WAREHOUSE_ID`, `DATABRICKS_TOKEN` and `APPLICATIONINSIGHTS_CONNECTION_STRING` in `.env`, and `az` signed in. The connection string must hold `ApplicationId=`, because the script looks the trace up by it.

Run this from the main checkout:

    uv run --script ops/agent/ask_live.py --env-file .env

It sends "Why were works contracts in P130164 advertised again?" through the same `POST /api/ask` route and stream the App runs. It worked if it exits 0 and prints four lines that each start "Holds.": "1. Checks 1 to 3" with every number matched, every quote found, every source returned and nothing removed; "2. A kept sentence cites strata.gold.passage:31525018/v1/54."; "3. strata.ops.agent_runs holds run ..." with the run's row and its Application Insights trace id; and "4. Application Insights holds operation ..." (criterion 6). The fourth check waits up to 10 minutes for the trace to arrive. Then open that operation id in Application Insights, under Transaction search, and check that the trace opens.

## Ticket 13, step 4 of 4: re-record the scripted cases from the live agent

The merger parked this step on October 23, 2026, after merge commit c42d9ce. Run it after step 1 and after ticket 11's step 1, so the agent and the passages it cites are on the workspace. It needs `FOUNDRY_PROJECT_ENDPOINT`, `DATABRICKS_HOST`, `DATABRICKS_WAREHOUSE_ID` and `DATABRICKS_TOKEN` in `.env`, and `az` signed in.

Run this from the main checkout, then review the diff and run the gate:

    uv run --script ops/agent/record.py --env-file .env
    git diff tests/fixtures/agent
    .githooks/pre-commit

It worked if the recording exits 0 and prints a unified diff for each file in `tests/fixtures/agent/recorded`, with the verifier's counts for each answer, such as "The verifier kept 3 of 3 sentences; 2 of 2 numbers matched and 2 of 2 quotes were on their pages." Each file's `"recorded"` changes from `false` to `true`, and the agent version is filled in. The gate must then pass, because every scripted case replays from the new recordings on the fixture (criterion 8, live half). If it passes, commit the recordings on a branch. If a case no longer gets the answer its test expects, the live agent answers differently from the hand-written recording, so tell the orchestrator before you change a test.

## Ticket 10, step 1 of 1: the NWWDA plan check on the deployed App

The merger parked this step on October 23, 2026, after merge commit bd3c9cb. It needs the Databricks keys in `.env`. Run it after ticket 04's step 1 (the bundle deploy), after ticket 08's step 1 (`ops/plans/run_live.py`) has filled the plan tables on the warehouse, and after ticket 09's step 1 has turned on user authorization. Ticket 06's step 1 runs the same deploy command. Run it again here if that deploy came from a commit before bd3c9cb, because the Check a plan, project and All projects pages arrived in this merge.

Run this from the main checkout:

    uv run --script ops/app/deploy_app.py --env-file .env

Then sign in to the workspace in a browser as a user with USE CATALOG, USE SCHEMA and SELECT on `strata`, and open:

    <App url>/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09

It worked if the deploy exits 0 with its last line `Strata is running at https://...`, and on the page the pill reads "9 activities checked", the h2 reads "One needs a look and two are worth watching; three have data notes." and the count line reads "Showing 6 of 9 activities" (criterion 8, the first half of P1's exit criterion). Three things change with the date. The Watch for KE-NWWDA-541062-CW-RFQ says "N days before the project closes", and N counts down to October 31, 2026. After that date, the closing-date reasons change their wording. The App's as-of date is today's date in UTC.

## Ticket 16, step 1 of 4: deploy the Strata dashboard with the bundle

The merger parked this step on October 24, 2026, after merge commit 69e97c8. It needs the Databricks keys in `.env`, including `DATABRICKS_WAREHOUSE_ID`, because the dashboard's queries run on that SQL warehouse. Ticket 04's step 1 runs the same command. Run it again here if that deploy came from a commit before 69e97c8, because the dashboard and its snapshot table arrived in this merge.

Run this from the main checkout, and then run it a second time:

    uv run --script ops/bundle/deploy.py --env-file .env

It worked if both runs exit 0. The first run prints "The dashboard Strata is new." and lists `strata.ops.readiness_snapshot` as a new table. The second run prints "No changes." Then open the dashboard Strata in the workspace. Its first page must be Data readiness (criterion 6, deploy half). The page stays empty until the nightly job has run once after this deploy, because the job's readiness task writes the snapshot it reads. So run ticket 04's step 2 next: `uv run --script ops/bundle/check.py job-run --env-file .env`.

## Ticket 16, step 2 of 4: the Data readiness page's awards row against a direct query

The merger parked this step on October 24, 2026, after merge commit 69e97c8. Run it after step 1 and after the nightly job has run (ticket 04's step 2). It needs the Databricks keys in `.env`.

Run these from the main checkout, one after the other:

    uv run --script ops/bundle/check.py readiness --env-file .env
    uv run --script ops/bundle/check.py same-rows --env-file .env

It worked if the first command exits 0 and prints "The Data readiness page's awards row matches a direct query on strata.ops.data_readiness:", then two lines that each show the same numbers on the page and in the query: "award rows held: N on the page, N in the query" and "contracts with a STEP reference: A of B on the page, A of B in the query". It then prints Kenya's own measures on one line, "Kenya's own measures, for comparison: ...". On the fixture these were 632 award rows and 528 of 603 contracts with a STEP reference. On the workspace the page's awards row counts every country, so expect larger numbers there and Kenya's on the last line. The second command must print `true` for `kenya_step_reference_link_rate.sql` (criterion 1, workspace half). Exit 1 from the first command means the page and the query differ, and the two lines show by how much.

## Ticket 16, step 3 of 4: the plans' link measure is written with the kind linked

The merger parked this step on October 24, 2026, after merge commit 69e97c8. Run it after the next live plan run, which is ticket 08's step 1 (`uv run --script ops/plans/run_live.py --env-file .env`).

Run this in the workspace's SQL editor:

    SELECT subject, kind, count, denominator, measured_at FROM strata.ops.data_readiness WHERE source = 'documents' AND measure = 'step_rows_with_reference' ORDER BY measured_at DESC LIMIT 5

It worked if the newest row for each project carries kind `linked`. Rows written before this merge keep `read_well`, and that is not a failure: the page reads only the newest row for each source, subject and measure, by `measured_at`, so the new run corrects what it shows with no backfill.

## Ticket 16, step 4 of 4: the dashboard's Data readiness page beside /data on the same date

The merger parked this step on October 24, 2026, after merge commit 69e97c8. Run it after steps 1 to 3 and after the App is deployed from 69e97c8 or later with `uv run --script ops/app/deploy_app.py --env-file .env` (ticket 06's step 1).

Open the App's `/data` page and note its measure date. Then open the dashboard Strata, go to its Data readiness page and set its date to that measure date.

It worked if both show the same headline sentence, the same fixes in the same order with the same project counts, the same link counts, and the same status (Partial or Gap) for each source (criterion 6). If live data make the Procurement Plans' link the biggest gap, check that the headline spells STEP out before it uses the short form, and that no sentence ends in two periods ("lack an Activity Reference No.."). Design review round 8's P1 says the second one can happen only on live data.
