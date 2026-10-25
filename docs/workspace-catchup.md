# Workspace catch-up

Some steps must run on the shared Databricks workspace or in Azure. They could not run when their ticket merged, because `.env` had no credentials yet. Run them in order once the wizard from ticket 03 has filled `.env`. Each block names the ticket, the command to run, and what shows that it worked.

Check which keys are set first:

    python3 .claude/hooks/guard.py --env-keys

The merger appends a block below each time it parks a step.

**While the user works through the wizard and the catch-up steps.** All ten keys were set by 10:58 PDT on October 24, 2026, and day-one test 7 passes. The user is running the wizard and the catch-up steps by hand in the main checkout, which means two things for a merger. First, do not run any workspace step during a merge, even though the keys are there: work on the shared workspace runs one at a time, and the user holds that turn today. Park your ticket's steps here as before, in order, and the orchestrator runs the backlog after the user's run. Second, if the main checkout holds staged or unstaged changes you did not make, do not commit, revert, unstage or set them aside; stop before `git merge`, and return merged false with the summary "blocked by uncommitted changes in the main checkout", naming the files. The orchestrator commits the user's work and the merge runs again. Never read or print `.env`.

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

**Ran on October 24, 2026 (orchestrator).** The user deployed gpt-5.4-nano as Global Standard, not Global Batch, so Azure reports a tokens-per-minute capacity for it and no enqueued-token limit. Nothing in the code calls the batch role yet. I set its capacity to 2,000, which the caps probe reads as 2,000,000 and counts as within the cap. `capacity_unit` stays 1000. Whether to recreate it as Global Batch is decision 19 in docs/STATUS.md.

The merger parked this step on October 23, 2026, after squash commit 43ed569. It needs the Azure sign-in.

Run this from the main checkout:

    az cognitiveservices account deployment show -g WorldBank-demo -n wb-strata --deployment-name gpt-5.4-nano --query sku -o json

It worked if the capacity in the output, times 1,000, equals the enqueued-token limit that the Azure portal shows for gpt-5.4-nano. If the two differ, change `capacity_unit` in `ops/dayone/dayone.toml` to the portal's limit divided by the capacity.

## Ticket 03, step 2 of 4: bound names and paths on the warehouse

**Ran on October 24, 2026 (orchestrator).** Test 3 passed (131 pages, statement 01f1cfd1-01d1-1d44-8cf5-2488192d3f30, 129 seconds) and test 4 passed (endpoint strata-search online; index workspace.strata_dayone.passages_index ready with three rows; the hybrid query returned p1, p2, p3). No evidence line says the warehouse refused a bound name or path.

The merger parked this step on October 23, 2026, after squash commit 43ed569. It needs the keys that the wizard writes to `.env`.

Run these two commands from the main checkout, one after the other:

    uv run --script ops/dayone/probe_parse_pad.py --env-file .env
    uv run --script ops/dayone/probe_ai_search.py --env-file .env

It worked if tests 3 and 4 in `docs/day-one-results.md` show a status other than "not run", and no evidence line says the warehouse refused `IDENTIFIER(:table)` or `READ_FILES(:path, ...)`. The wizard now always gives `AI_SEARCH_ENDPOINT` a value, so the test 4 probe has an endpoint name to use.

## Ticket 03, step 3 of 4: the probes' own schema

**Ran on October 24, 2026 (orchestrator).** `databricks schemas get workspace.strata_dayone` returned the schema, owned by chiraglakhanpal@gwu.edu.

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

**Ran on October 24, 2026 (orchestrator).** Two things stood in the way first. The Databricks CLI (v1.22.1) refused every command from the repo root because `bundle/dashboard.yml` and `bundle/catalog.yml` both used the resource key `strata`; the dashboard's key is now `strata_dashboard`. Then the bundle could not create the catalog: the Free Edition metastore has no storage root and uses Default Storage (400 INVALID_STATE). `CREATE CATALOG IF NOT EXISTS strata` on the SQL warehouse made it, `databricks bundle deployment bind strata strata` bound it, and the deploy then made the four schemas, the volume, the grants, the job `strata nightly` (730097284330653), the dashboard and every table and view. fairshare has no catalog of its own: its data is in `workspace`, so the second run used `--fairshare-catalog workspace`. It printed "No changes." and "workspace's catalog lists the same before and after the deploy: two schemas, two tables and one volume."

The merger parked this step on October 23, 2026, after merge commit 01a7286. It needs the Databricks keys in `.env` and the Databricks CLI 0.287.0 or later. If a catalog named `strata` already exists, run `databricks bundle deployment bind strata strata` first.

Run this command from the main checkout, and then run it a second time:

    uv run --script ops/bundle/deploy.py --env-file .env

It worked if both runs exit 0. The first run lists the catalog, the four schemas, `strata.bronze.files`, `strata.ops.pipeline_runs`, the grants and the job as new. Since ticket 08 merged, it also lists that ticket's 13 tables in `strata.bronze`, `strata.silver` and `strata.ops` as new. Since ticket 07 merged, it also lists that ticket's 13 tables as new: `strata.bronze.api_pages`, `strata.silver.awards`, `strata.silver.notices` (with its `fiscal_year` column), `strata.silver.projects`, `strata.silver.project_loans`, and the eight gold tables `strata.gold.country`, `project`, `project_loan`, `package`, `notice`, `contract`, `contract_supplier` and `supplier`. The line "Each of these exists now" also names the view `strata.silver.awards_current`, and `strata.ops.data_readiness` is created with ticket 07's `as_of` and `detail` columns. Since ticket 17 merged, it also lists that ticket's 12 tables as new: `strata.silver.awards_fy2001_2016`, `ieg_ratings`, `loans`, `loan_history`, `indicators` and `project_isr_ratings`, `strata.gold.ieg_rating`, `loan`, `project_closing_date`, `governance_score` and `project_isr_rating`, and `strata.ops.table_sizes`. It also creates `strata.gold.contract` keyed by `contract_id`, with `wb_contract_number` allowed to be empty, `strata.silver.awards` with `market_approach`, `strata.silver.notices` and `strata.gold.notice` with `contract_fiscal_year`, and `strata.silver.projects` and `strata.gold.project` with `major_sector_code`, `sector` and `sector_name`. Since ticket 13 merged, it also lists `strata.ops.agent_runs` as new, where each answer's run is logged. Since ticket 14 merged, it also lists `strata.ops.evidence_opened` as new, where the App records which sources each viewer opened. Since ticket 19 merged, it also lists that ticket's six tables as new (`strata.silver.notice_bidders` and `supplier_resolution`, and `strata.ops.supplier_pairs`, `supplier_review_decisions`, `supplier_pair_labels` and `supplier_match_quality`) and creates the view `strata.ops.supplier_review_list`. Ticket 19's step 1 below gives the three ALTER TABLE lines for `strata.gold.contract_supplier` and `strata.gold.supplier` when an earlier deploy made them. Each table is defined with `CREATE TABLE IF NOT EXISTS`, so if an earlier deploy already made one of these tables, add its missing columns with `ALTER TABLE ... ADD COLUMNS` before the job runs. The second run prints "No changes.". Each run also prints "fairshare's catalog lists the same before and after the deploy: ..." (criteria 1 and 7). If fairshare's catalog has another name, add `--fairshare-catalog <name>`.

## Ticket 04, step 2 of 4: run the nightly job by hand

**Two runs on October 24, 2026 (orchestrator), both failed.** Run 282381151628775 failed on every task before any work: splink 5.0.0 pulls in a pyarrow that serverless environment version 2 (numpy 1.23) cannot import, so `bundle/nightly.yml` now uses version 4. Run 344940414051390 then failed in `fetch_by_watermark` after 20 minutes, twice over: the notices search API answers 400 to an offset above 100,000 ("Value must be between 0 and 100000. Parameter name: $skip") and reports 424,135 notices. Bronze kept awards (296 pages), awards_fy2001_2016 (147), ieg_ratings (13), ida_credits (12), ibrd_loans (10), ida_credit_history (178), ibrd_loan_history (39) and notices (237). The source now names `max_offset = 100000` in `config/sources.toml`, where the fetch stops, with a limitation line for the readiness page. **Third run 556837544068999 (12:01 to 14:05):** `fetch_by_watermark` succeeded in 26 minutes, `bronze_to_gold` in 87, and the seven empty tasks passed, but `measure_data_readiness` failed twice: `storage.measure` reads `databricks.yml` and `bundle/*.yml` through `strata.lakehouse.bundle.load`, and the bundle synced only `src` and `config`. The sync paths now include `bundle` and `databricks.yml`. **Fourth run 855462503837945 (14:12 to 14:19):** the fetch succeeded in 8 minutes, then `bronze_to_gold` failed on the gold MERGE for notices (DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE): three country names carry two codes in `strata.gold.country` (Caribbean 6R and CB, Serbia RS and YF, World 1W and 99), and the notice and contract queries looked a country up by name, so 943 notices had two rows, which the third run had inserted into the empty table without complaint. The notice now takes its project's code first and a name gives one code at most; `gold.sync` refuses a source whose keys repeat. The 1,886 doubled rows were deleted from `strata.gold.notice` by hand (99,557 distinct notices stayed). The fifth run is recorded below when it finishes.

**Fifth run on October 24, 2026 (orchestrator), 882867588506257, from 21:32 UTC:** `fetch_by_watermark` 9 minutes, `bronze_to_gold` 5 minutes with the gold fix (the notices MERGE took one row per country name), `parse_and_embed`, `sync_index`, `relink` and `propose_lessons` seconds each, all succeeded. `detect_disagreements` then ran 94 minutes without finishing and was cancelled by hand at 23:22 UTC, so `measure_data_readiness`, `score` and `refresh_drafts` were skipped. It was not stuck: the task rebuilds the assertions of every project with a document, a contract, a notice, a Procurement Plan or an IEG rating, with about seven warehouse queries per project (the project's dates, its key dates, its ISR ratings, its records, its IEG ratings and its reports), and the workspace holds 15,933 such projects (12,628 from the IEG ratings dataset, 8,228 with a contract, 2,071 with a notice, 1 with a plan, 0 with documents), where the fixture had 8. The query history showed the task's queries at about 0.4 seconds each, which is about eleven hours against the job's 150-minute stop.

Fix: `src/strata/knowledge/sql/assertions/projects.sql` now lists only the projects whose documents the passage reader read or whose Procurement Plan was read, which are the projects whose ISR, text and plan assertions exist. Projects known only from a contract, a notice or an IEG rating are left out; `tests/test_assertions.py` checks the list on the fixture and `tests/test_nightly.py` seeds one plan version so a local run still has a project to rebuild. Decision for the user: the contract-against-notice signing disagreements of record-only projects are no longer found. Finding them again at this scale needs the per-project queries rewritten to run once for every project (set-based), with the Statement Execution API's 25 MiB inline result cap in mind; that is a follow-up for ticket 20 or 43. The sixth run is recorded below when it finishes.

**Sixth run on October 24, 2026 (orchestrator), 626310583145231, 23:36 to 00:01 UTC:** every task succeeded. `fetch_by_watermark` failed once on "HTTP Error 417: Expectation Failed" from a World Bank host and Databricks tried it again at 23:40; the second try took 8 minutes and added no page. `bronze_to_gold` 5 minutes (2,259,404 rows), `detect_disagreements` 22 seconds (1,311 rows, with the project list above), `measure_data_readiness` 5 minutes (3,250 rows); `parse_and_embed`, `sync_index`, `relink`, `score` and `refresh_drafts` have no work yet (ticket 43). `ops/bundle/check.py job-run` first exited 1 because the retried task had two rows; it now counts a task by its last try and prints "fetch_by_watermark was tried 2 times; the first 1 failed and the last succeeded." (`ops/bundle/tests/test_check.py`). Passed: the job finishes inside its window with the fix, in 25 minutes.

The merger parked this step on October 23, 2026, after merge commit 01a7286. Run it after step 1, because the deploy makes the job and `strata.ops.pipeline_runs`.

Run this from the main checkout:

    uv run --script ops/bundle/check.py job-run --env-file .env

It worked if the command exits 0 and prints "Run <id> wrote one row per task to strata.ops.pipeline_runs, in the bundle's order." That means ten rows in the order of `docs/PLAN.md` section 11 (criterion 2). Since ticket 07 merged, three of the tasks do real work, so the run takes longer and needs the World Bank's public APIs. Since ticket 17 merged, `fetch_by_watermark` fetches every structured source in `config/sources.toml` into `strata.bronze.api_pages`, for every country: contract awards since FY2020, contract awards FY2001 to FY2016, IEG ratings, IDA credits and IBRD loans, procurement notices, projects, CPIA and WGI. Only the monthly loan history (`ida_credit_history` and `ibrd_loan_history`) is fetched for the slice's countries alone. `bronze_to_gold` fills ticket 07's silver and gold tables (`strata.silver.awards`, `notices`, `projects` and `project_loans`, and `strata.gold.country`, `project`, `project_loan`, `package`, `notice`, `contract`, `contract_supplier` and `supplier`) and ticket 17's tables, which step 1 lists. `measure_data_readiness` writes every source's measures to `strata.ops.data_readiness` and each table's size to `strata.ops.table_sizes`. The first run makes about 1,900 requests and may come close to the job's 2.5-hour timeout. If it stops, run the command again: bronze keeps each page as it arrives, and the watermark counts only fetches that finished. Ticket 07's steps below read what this run wrote.

## Ticket 04, step 3 of 4: the same rows on DuckDB and on the SQL warehouse

The merger parked this step on October 23, 2026, after merge commit 01a7286. Run it after step 2, because `pipeline_runs_columns.sql` reads the table that the job writes. Since ticket 08 merged, this command also checks `delay_from_first_published_planned_date.sql` and `data_notes_actual_amount_zero.sql`, which read the plan tables. Those tables stay empty until ticket 08's step 1 has run, and until then the command exits 1 on those two files even when the deploy is fine. So run this step after ticket 08's step 1, below. Since ticket 07 merged, it also checks `kenya_step_reference_link_rate.sql`, which reads what step 2's job run wrote. Since ticket 17 merged, it also checks that ticket's three files, which read what the job wrote for every country. Ticket 08's step 2 and ticket 07's step 2 are the same command, and one run covers all three tickets.

Run this from the main checkout:

    uv run --script ops/bundle/check.py same-rows --env-file .env

It worked if the command exits 0, and for each of `showcase_fiscal_years.sql`, `pipeline_runs_columns.sql`, `delay_from_first_published_planned_date.sql`, `data_notes_actual_amount_zero.sql` and `kenya_step_reference_link_rate.sql` in `tests/ground_truth/` it prints "DuckDB and the SQL warehouse returned the same ... rows, and they are the rows the file expects." (criterion 4). The same must hold for ticket 17's `every_source_holds_the_rows_its_api_reported.sql`, `gap_years_contracts_from_award_notices.sql` and `structured_data_under_the_limit.sql`. Ticket 17's step 1 below gives the rows each must return. Its projection puts structured data at 1.57 GB at full scale, over the 0.5 GB limit, so expect the size file to fail until you answer decision 18 in `docs/STATUS.md`.

**Ran on October 24, 2026 (orchestrator), after the sixth job run:** exit 1. Same rows on both engines, as the files expect: `showcase_fiscal_years.sql` (four rows), `pipeline_runs_columns.sql` (seven), `data_notes_actual_amount_zero.sql` (two: KE-NWWDA-503455-CW-RFQ Signed 0.00 and KE-NWWDA-541061-CW-RFQ Completed 0.00), `kenya_step_reference_link_rate.sql` (`linked_step_reference,true`), `gap_years_contracts_from_award_notices.sql` (three), `structured_data_under_the_limit.sql` (`true,true`: 67 structured tables, 352,460,954 bytes, under the limit; the 1.57 GB projection has not come true, because the notices stop at the 100,000 offset). Different, each with its reason:

- `delay_from_first_published_planned_date.sql`: no row on the warehouse. The October 9, 2026 plan (40132287) is the version the file reads, and its STEP tables are among the 195 pages the daily cap left for a later run (ticket 08's step 1). The March 5, 2026 version (40090127) already holds the row with 2021-04-21, 2021-07-01, 2022-01-03, 186 and 1245092.76. Run this check again after the next plan run.
- `data_readiness_fix_measures.sql`: the two gap-years measures read false for `all` and `KE` (the step-reference measure is true). `strata.gold.contract` holds no contract from notices for FY2017 to FY2019, and the run stored no gap-years rows: the notices fetch stops at the search API's 100,000 offset, newest first, so bronze holds notices from 2024 to 2026 only (100,092 Contract Award notices), and none of those carries a "Contract Signature Date" line in its text, which `silver/notices.py` reads the signature date from (8 of 253 pages say "Contract Signing Date" instead). This is the notices decision in ticket 04's step 2: fetch notices by country or by year.
- `every_source_holds_the_rows_its_api_reported.sql`: `notices` false (100,500 of 424,135, the offset cap), `wgi` false (33,696 of 34,992) and `ibrd_loan_history` false (36,431 of 36,686). The last two are not missing records: bronze holds every record (wgi 6 indicators × 5,832). `coverage_rows` counts distinct record keys, and wgi's key (`indicator_id`, `country_code`, `country_iso3`, `year`) folds the nine aggregate rows a year with no country code into one, 216 a series; the IBRD history API repeats some loan-and-period rows (IBRD80260 at 2014-12-31 three times). Follow-up for ticket 17: a key for code-less aggregates, and counting a repeated record once in the denominator too.
- `past_range_coverage_ke_works_rfb.sql` and `past_range_criteria_ke_works_rfb.sql` (ticket 12's step 1): the warehouse returned canceled 0, matched 298, no STEP reference 54, no notice 217, used 27, and two criteria rows (KE-KIAMBU COUNTY-510866-CW-RFB, KE-TAVEVO-466579-GO-RFB) against the file's fifteen. The warehouse holds every Kenya works package since FY2020 where the fixture held NWWDA's, and its notices are only those from 2024 on (the offset cap), so most packages have no notice. Not changed; the orchestrator decides with the notices decision.
- `icr_paragraph_54_passage.sql` and `slice_projects.sql`: the documents are not read yet (ticket 11's step 1 runs next). `p130164_isr_7_against_icr_paragraph_78.sql`: waits on ticket 20's step 1 (the batch deployment decision).

## Ticket 04, step 4 of 4: record both nightly schedules

The merger parked this step on October 23, 2026, after merge commit 01a7286. Run it after step 2, and after fairshare's nightly job has finished at least one run.

Run this from the main checkout:

    uv run --script ops/bundle/check.py schedules --env-file .env --write

If the name of fairshare's job does not contain "fairshare", add `--fairshare-job <name>`. It worked if the command exits 0 and the `bundle:schedules` block in `bundle/README.md` records both jobs with "- Overlap: none" (criterion 3). Then commit `bundle/README.md` on `build/strata`. If the check finds that the two windows meet, change the hour in `bundle/nightly.yml` and run step 1 again.

**Ran on October 24, 2026 (orchestrator):** the first run exited 1: fairshare's job runs daily at 06:00 America/Chicago (longest of 19 runs 21 minutes) and Strata's at 05:00 America/New_York with a 150-minute stop, so the two met on 366 of 366 days. The hour in `bundle/nightly.yml` moved to 03:00 (02:00 does not exist on the night the clocks go forward), the deploy was run again ("Updated jobs.nightly"), and the second run exited 0 with "Overlap: none. With these durations the two jobs share no minute on any day from October 24, 2026 to October 24, 2027, and the same holds if Strata's job runs to its limit." `bundle/README.md`'s window section, `bundle/nightly.yml`'s comment and `tests/test_nightly.py`'s window tests now say 03:00 to 05:30; the evening-hour test runs 18:00 to 22:00 (four hours from 23:00 end at 04:00 on the night the clocks go forward) and a new test checks fairshare's window itself. Passed.

## Ticket 08, step 1 of 2: read P156634's Procurement Plans on the warehouse

**First run on October 24, 2026 (orchestrator):** it stopped with "Parameterized query's parameters are too large: the combined size of parameters is 4911047, exceeding the limit of 1048576 characters." The warehouse engine sent 100 layout pages in one INSERT. `WarehouseEngine.insert_rows` now also splits a chunk when its values pass 900,000 characters (`tests/test_engine.py`). The pages parsed before the stop stayed in bronze, and the second run is recorded below when it finishes.

**Second run on October 24, 2026 (orchestrator):** it stopped with the same message, this time from a single Procurement Plan's text, not a chunk of pages: one version of P156634 has 4,910,702 characters of text, and the Statement Execution API takes a statement's parameters only up to 1,048,576 characters. `WarehouseEngine.insert_rows` now raises `RowTooLarge` for such a row, and `fetch_documents` in `src/strata/lakehouse/plans.py` skips the document, counts it in `Fetching.not_kept` and `Report.not_kept`, and the run prints "N plans were fetched but not kept ..." at the end (`tests/test_plans.py`). The skipped version counts as listed but not read, so `plan_versions_read` stops short of its denominator.

**Third run on October 24, 2026 (orchestrator):** exit 0, from 18:24 to 22:29 UTC. It printed "Run plans-P156634-20261024T182429249392 read 231 plan versions of P156634 and parsed 500 of the 695 pages waiting for ai_parse_document, under a cap of 500 pages a day. 149 versions have STEP rows." and "It stopped at the cap, at page 6 of document 30374121.", so `pages_read_route_b` at 500 of 695 is allowed. The other measures: `plan_versions_read` 231 of 240, `pages_read_route_a` 672 of 672, `step_rows_with_reference` 1284 of 4555, `latest_activities_with_step_rows` 81 of 1214, `latest_activities_with_confirmed_first_listing_read` 126 of 1214. Five versions were fetched but not kept (33211875, 33218784, 33212519, 33217573 and 34106903, from 4.9 million to 90.7 million characters of text each), so `plan_versions_read` is 9 short: those 5 and 4 more that the run did not reach. On the warehouse `strata.ops.parse_runs` holds the run's row with `pages_parsed` 500, and `strata.ops.data_readiness` holds its measures. Real `ai_parse_document` output had the shape the tests expect. The reader also listed about 120 column names it did not know, most of them a STEP section heading joined to a column name ("WORKS Market Approach") or an OCR misspelling ("Prequalification (V/N)"); those are left for a follow-up. The second same-day run is recorded below when it finishes.

**Fourth run, the same UTC day, on October 24, 2026 (orchestrator):** exit 0, from 22:30 to 23:18 UTC. It printed "Run plans-P156634-20261024T223020001503 read 231 plan versions of P156634 and parsed 0 of the 195 pages waiting for ai_parse_document, under a cap of 500 pages a day." and the same six measures as the third run; `strata.ops.parse_runs` holds its row with `pages_parsed` 0 and `pages_failed` 0 (criterion 5). Passed. Two things to carry: the 195 pages left wait for a later UTC day, and they share the 500-page cap with the document reader (ticket 18's step 3); and the five oversized versions were fetched again from the World Bank's host, about 190 million characters, because a version that is not kept has no bronze row to skip it by, so a run spends most of its time on them (follow-up).

**Fifth run, inside the documents run, on October 25, 2026 (orchestrator):** `ops/documents/run_live.py` runs this reader for each slice project first, so at 00:46 UTC it went on from page 6 of document 30374121 and parsed 102 more pages, 602 of the 695 Route B pages, until documents.worldbank.org answered 403 at 01:50 UTC (ticket 11's step 1 has the details). 93 pages wait, and `strata.ops.parse_runs` has no row for this part because the run stopped before it wrote one; the pages are in `strata.bronze.layout_pages`.

Decision for the user: the five oversized texts. Keeping them needs either the text split into parts across rows, a Delta write that does not go through statement parameters (a volume file plus COPY INTO), or a per-version character cap. `read_versions` also selects every text in one statement, and inline results are capped at 25 MiB, so a split alone does not settle it.

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

**Ran on October 24, 2026 (orchestrator):** three rows: awards 296, notices 253, projects 283. Passed.

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

**Ran on October 24, 2026 (orchestrator):** `awards` had 296 pages before the fourth run and 296 after the fourth, fifth and sixth; no source's newest `fetched_at` is later than the third run (19:28 UTC). Passed.

**Scheduled run on October 25, 2026 (orchestrator):** the 03:00 New York run (873581300211320, 07:00 to 07:38 UTC, every task succeeded) fetched 297 `awards` pages, so the count grew from 296 to 593. `newest_record_on` in the new rows is 2026-10-21 against 2026-10-20 before, and the pages hold 296,098 records against 295,969: Finances One published 129 awards between the runs, which is the case this block allows. Because the API lists newest first with no date filter, 129 new records shift every page, so every page's hash changed and all 297 were stored again; bronze keeps both days' copies. Follow-up for the orchestrator: a daily source whose records shift will add its whole page set to bronze on every day that it changes.

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

**First run on October 25, 2026 (orchestrator):** started at 00:01 UTC, right after the UTC day rolled, so the page cap was fresh. The script first runs the plan reader for every slice project, then the passage reader. P130164's plans went first: run `plans-P130164-20261025T000129723756` parsed 23 pages from 00:01 to 00:16 UTC, and `strata.ops.parse_runs` holds its row with `pages_parsed` 23, `pages_failed` 0 and `pages_waiting` 23. P156634's plans went on from page 6 of document 30374121 and parsed 102 more pages, so 602 of its 695 Route B pages are now in `strata.bronze.layout_pages` and 93 wait. At 01:50 UTC documents.worldbank.org answered "HTTP Error 403: Forbidden" for document 29750379's PDF (Plan-Archive-5.pdf), and the script stopped with urllib's traceback before the passage reader began. Since then the host's Cloudflare front answers 403 to every request from this computer, whatever the user agent, including a PDF it served minutes earlier, while search.worldbank.org still answers 200: a rate block after some hundreds of PDF and text requests, which Strata waits out rather than works around. The 125 pages parsed stay in bronze and count against the day's cap, so 375 pages are left for today. Two fixes: `AiParseDocument.parse` in `src/strata/reader/layout.py` now raises `NotFetched` naming the PDF, and `ops/documents/run_live.py` prints "The run stopped before it finished: ..." and exits 2, as `ops/plans/run_live.py` already did (`tests/test_plans.py`). The run is recorded again below when the host answers and it finishes. Follow-up for the orchestrator (now in ticket 43): a run over P156634 asks the host for about 240 plan texts and some hundreds of PDFs, and fetches the five oversized texts (about 190 million characters) again every run; a cached copy of each fetched PDF in the bronze files volume, or a pause between fetches, would keep the host from blocking.

**Second run on October 25, 2026 (orchestrator):** started at 02:05 UTC, a minute after the host answered a probe with 302 again (it had answered 403 at 01:53 and 302 at 02:03, so the block lasted under 15 minutes). The plan reader spent until 02:43 UTC fetching P156634's plan texts again, then parsed 87 more pages of 24 versions, until the host answered 403 at 03:25 UTC for document 27677290's PDF (Plan-Archive-2.pdf). The script printed "The run stopped before it finished: I could not fetch https://documents.worldbank.org/curated/en/313111498489351105/pdf/Plan-Archive-2.pdf: HTTP Error 403: Forbidden. The pages it parsed are kept, and the next run goes on from there." and exited 2, as a688a81 intended. A probe at 03:26 UTC got 302 again, so each block is a short burst after about 80 minutes of fetching. P156634 now has 689 of its 695 Route B pages in `strata.bronze.layout_pages`; the 6 left are in four versions from June 2017 (27677290, 27677163, 27677200, 27669055). 212 pages were tried today, under the cap of 500. The passage reader has still not started. A third run began at 03:26 UTC and is recorded below.

**Third run on October 25, 2026 (orchestrator):** started at 03:27 UTC. P130164's plan reader finished at 03:29 UTC with 0 pages to parse (`plans-P130164-20261025T032703552021`). P156634's plan reader then spent until 09:56 UTC, six and a half hours, fetching again the nine versions bronze does not hold (the five oversized texts and four more), where the second run had spent 38 minutes on the same fetches, so the host was answering slowly. At 09:56 UTC it stopped in pypdf: one of those PDFs has a font whose encoding pypdf cannot decode, `extract_text` raised `UnicodeDecodeError: 'utf-16-be' codec can't decode byte 0x14 in position 0: truncated data`, and `LiveDocuments.pages` in `src/strata/reader/documents.py` let it through. No page was parsed and no passage written. Fix: `LiveDocuments.pages` now reads a page whose text pypdf cannot decode as empty, like a scanned page, so the page router sends it to Route B, and raises `NotFetched` for a file pypdf cannot open at all (`tests/test_plans.py`). The fourth run is recorded below.

**Fourth run on October 25, 2026 (orchestrator):** started at 10:05 UTC and stopped at 10:22 UTC with exit 2, "The run stopped: The warehouse did not run the statement. Its state was FAILED: Failed on SQL Endpoint 882107b449dd59cd due to compute cluster maintenance": the SQL warehouse itself was under maintenance, not the host. Nothing parsed. A fifth run began at 10:23 UTC and is recorded below.

**Fifth run on October 25, 2026 (orchestrator):** started at 10:23 UTC and stopped by hand at 10:35 UTC, in the plan reader's fetch, because the SQL warehouse had reached Free Edition's free daily limit: at 10:33 UTC `databricks warehouses start` answered "Sorry, cannot run the resource because you have hit your free daily limit. Please come back again tomorrow.", the Serverless Starter Warehouse showed STOPPED, and the statements API answered nothing. The run would have fetched for hours and failed at its first write. Every warehouse step waits for the limit to reset. Decision for the user: Free Edition's daily compute limit caps how much catch-up runs in a day; today it went on three documents attempts, the scheduled nightly run, two deploys, two backtests and the SQL checks.

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

**Ran on October 24, 2026 (orchestrator).** `docs/app-state.md` reads `Status: run` and chooses Lakebase: strata.ops took 2,293 ms in the middle over the 1,000 ms budget, Lakebase 145 ms. The probe wrote `docs/adr/0005-app-state-lives-in-lakebase.md`. Both files are committed on `build/strata`.

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

**Ran on October 24, 2026 (orchestrator):** exactly the three rows: 2024-04-30 after 2022-10-31 reported 2022-11-30; 2025-10-31 after 2024-04-30 reported 2024-04-30; 2026-10-31 after 2025-10-31 reported 2025-11-30. Passed.

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

**Ran on October 24, 2026 (orchestrator):** across the fourth, fifth and sixth runs no source added a page (every source's newest `fetched_at` is from the third run): `awards_fy2001_2016` and the monthly loan histories added none, as required, and `awards` added none. `coverage_rows` after the sixth run: projects 28,211 of 28,211; notices 100,500 of 424,135, short by the search API's 100,000 offset cap (ticket 04's step 2 decision), not by a withdrawn record. The same-rows check is recorded under ticket 04's step 3; `strata.ops.table_sizes` marks `strata.gold.passage` and `strata.silver.passage_embeddings` as not structured, at 0 rows until ticket 11's step 1 runs. The second night's run is the scheduled one at 03:00 New York.

**Second night, October 25, 2026 (orchestrator):** the scheduled run at 03:00 New York (873581300211320, 07:00 to 07:38 UTC) succeeded in every task. `fetch_by_watermark` added 297 pages for `awards` (Finances One published 129 awards, newest 2026-10-21; see ticket 07's step 3), 13 for `ieg_ratings` and 1 for `projects`; `awards_fy2001_2016`, `ida_credit_history` and `ibrd_loan_history` added none. `coverage_rows` after the run: projects 28,211 of 28,212 (one project appeared in the API between fetches), notices 100,500 of 424,135 (the 100,000 offset cap, as before), ibrd_loan_history 36,431 of 36,686 (as before). The same-rows check runs again after the documents run finishes, since two of its files wait on that run.

## Ticket 13, step 1 of 4: the Foundry agent and its guardrail match the repo

**Ran on October 24, 2026 (orchestrator).** The first run printed the diff of the instructions and ended "I made version 1 of strata-orchestrator, which matches the repo." The `--check` run exited 0: "Foundry's agent strata-orchestrator, version 1, matches the repo: there is no difference in its model, instructions, tools, description or guardrail (strata-guardrail)."

The merger parked this step on October 23, 2026, after merge commit c42d9ce. Run it after ticket 03's wizard. It needs `FOUNDRY_PROJECT_ENDPOINT` in `.env` and the `az` command line signed in to the subscription that holds the Foundry resource named in `ops/dayone/dayone.toml`.

Run this from the main checkout, and then run it again with `--check`:

    uv run --script ops/agent/sync.py --env-file .env
    uv run --script ops/agent/sync.py --env-file .env --check

It worked if the first run prints what differed, with a diff of the instructions, and ends "I made version N of strata-orchestrator, which matches the repo." The first run also makes the guardrail `strata-guardrail`: content filters, and Prompt Shields on the question and on tool results. The second run must exit 0 and print "Foundry's agent strata-orchestrator, version N, matches the repo: there is no difference in its model, instructions, tools, description or guardrail (strata-guardrail)." (criterion 5, live half). Exit 1 means `--check` found a difference, and exit 2 means it could not run. Run the pair again after any change to `src/strata/agent/instructions/orchestrator.md`, `config/agents.toml`, `config/models.toml` or a tool in `config/tools.toml`.

## Ticket 13, step 2 of 4: five passages with rule-like sentences reach the agent with no refusal

**Ran on October 24, 2026 (orchestrator).** Exit 0. All five passages printed "passed" (31525018/v1/71, 31525018/v1/86, 27348420/v1/annex3.51, annex3.52 and annex2.46), and the run ended "All 5 passages reached the agent as tool results with no refusal."

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

**Ran on October 24, 2026 (orchestrator).** Ticket 04's step 1 ran this deploy from 3b96b34, after 69e97c8. The dashboard Strata (01f1cfd370f01f6ab7aafcb4fffadd48) is ACTIVE and its only page is Data readiness; `strata.ops.readiness_snapshot` was created. The second run printed "No changes." The page fills once the nightly job's readiness task has run.

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


**Ran on October 24, 2026 (orchestrator):** exit 0: "award rows held: 295969 on the page, 295969 in the query" and "contracts with a STEP reference: 121615 of 283744 on the page, 121615 of 283744 in the query". The Kenya line did not print: since ticket 17 the awards are fetched for every country at once, and the run writes no `coverage_rows` row for subject `KE` (its `linked_step_reference` row reads 3,971 of 4,697). The same-rows check printed true for `kenya_step_reference_link_rate.sql`. Passed.

## Ticket 16, step 3 of 4: the plans' link measure is written with the kind linked

The merger parked this step on October 24, 2026, after merge commit 69e97c8. Run it after the next live plan run, which is ticket 08's step 1 (`uv run --script ops/plans/run_live.py --env-file .env`).

Run this in the workspace's SQL editor:

    SELECT subject, kind, count, denominator, measured_at FROM strata.ops.data_readiness WHERE source = 'documents' AND measure = 'step_rows_with_reference' ORDER BY measured_at DESC LIMIT 5

It worked if the newest row for each project carries kind `linked`. Rows written before this merge keep `read_well`, and that is not a failure: the page reads only the newest row for each source, subject and measure, by `measured_at`, so the new run corrects what it shows with no backfill.

**Ran on October 24, 2026 (orchestrator):** the query returned one row, P156634, kind `linked`, count 1284, denominator 4555, measured at 2026-10-24T22:29:16Z, written by ticket 08's third run. Passed.

## Ticket 16, step 4 of 4: the dashboard's Data readiness page beside /data on the same date

The merger parked this step on October 24, 2026, after merge commit 69e97c8. Run it after steps 1 to 3 and after the App is deployed from 69e97c8 or later with `uv run --script ops/app/deploy_app.py --env-file .env` (ticket 06's step 1).

Open the App's `/data` page and note its measure date. Then open the dashboard Strata, go to its Data readiness page and set its date to that measure date.

It worked if both show the same headline sentence, the same fixes in the same order with the same project counts, the same link counts, and the same status (Partial or Gap) for each source (criterion 6). If live data make the Procurement Plans' link the biggest gap, check that the headline spells STEP out before it uses the short form, and that no sentence ends in two periods ("lack an Activity Reference No.."). Design review round 8's P1 says the second one can happen only on live data.

## Ticket 14, step 1 of 2: the showcase question from the box on the deployed App

The merger parked this step on October 24, 2026, after merge commit 069a6ca. Run it after ticket 04's step 1 deployed from 069a6ca or later, because that deploy makes `strata.ops.agent_runs` and `strata.ops.evidence_opened`, and the App deploy below grants its service principal MODIFY on both. Also run it after ticket 09's step 1 (user authorization), ticket 11's step 1 (the passages and the AI Search index) and ticket 13's step 1 (the Foundry agent). It needs the Databricks keys in `.env` and all four Foundry keys: `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_TENANT_ID`, `FOUNDRY_CLIENT_ID` and `FOUNDRY_CLIENT_SECRET`. The wizard does not make the last two yet, so `.env.example` keeps them as commented lines and `guard.py --env-keys` does not list them. Uncomment both in `.env` and fill them from the Entra app registration the App reaches the agent as, which needs the Azure AI User role on the Foundry project. Ticket 06's step 1 and ticket 10's step 1 run the same deploy command. Run it again here if that deploy came from a commit before 069a6ca, because the box's intents, the answer panel, the evidence drawer and the Foundry keys arrived in this merge.

Run this from the main checkout:

    uv run --script ops/app/deploy_app.py --env-file .env

It worked if the deploy exits 0, its step 3 prints "I saved the Foundry agent's four keys in the secret scope, so /api/ask answers through the agent." (not ".env has no ..."), and its last line is `Strata is running at https://...`. Then sign in to the workspace in a browser as a user with USE CATALOG, USE SCHEMA and SELECT on `strata`, open `<App url>/projects/P130164`, press "/", type "Why were works contracts in P130164 advertised again?" and choose "Ask this". It passes when the steps stream in one at a time and "In short" lands with a [1] marker (criterion 7). A click on [1] must open the drawer at ICR ¶54 with this meta line, word for word: "Implementation Completion and Results Report · Rajasthan Road Sector Modernization (P130164) · October 10, 2019 · Section III.B · ¶54 · PDF page 23 of 66". The check line's counts must equal the `checks` event in the browser's network tab for `POST /api/ask`. Then open "Show the four steps I took", copy its Answer ID, and run this in the workspace's SQL editor:

    SELECT run_id, status, sentences_kept, numbers_matched, numbers_total, quotes_found, quotes_total FROM strata.ops.agent_runs WHERE run_id = '<Answer ID>'

It must return one row whose counts match the check line. If the panel says there is no agent, the App started without the Foundry keys: check step 3's line above.

## Ticket 14, step 2 of 2: an opened source writes one row for the viewer

The merger parked this step on October 24, 2026, after merge commit 069a6ca. Run it right after step 1, in the same App and as the same user, because step 1's click on [1] is the first open.

Run this in the workspace's SQL editor:

    SELECT viewer_id, evidence_id, times_opened FROM strata.ops.evidence_opened WHERE evidence_id = 'strata.gold.passage:31525018/v1/54'

It worked if it returns one row for your user id with `times_opened` 1 (criterion 5, live write). Then press Escape to close the drawer, click [1] again and run the query again. It must still return one row for you, now with `times_opened` 2. This proves the MERGE runs on Delta as the App's own service principal. If the first query returns no row, check that the deploy's step 6 ran ("Letting the app's own service principal write usage events, agent runs and opened sources to strata.ops."), and that the address has no `?view=`, because a preview of another view records nothing.

## Ticket 19, step 1 of 5: deploy the bundle with the supplier tables

**Ran on October 24, 2026 (orchestrator).** Ticket 04's step 1 ran this deploy from 3b96b34, after a7bcc99, and no earlier deploy existed, so the ALTER TABLE lines were not needed. The six tables and the view were listed as new. `SHOW CREATE TABLE strata.gold.contract_supplier` shows `contract_id STRING NOT NULL` and `wb_contract_number STRING` with no NOT NULL; `strata.gold.supplier` shows `resolved_on STRING NOT NULL`.

The merger parked this step on October 24, 2026, after merge commit a7bcc99. It needs the Databricks keys in `.env`. Ticket 04's step 1 runs the same deploy. Run it again here if that deploy came from a commit before a7bcc99, because the supplier tables arrived in this merge.

If an earlier deploy already made `strata.gold.contract_supplier` and `strata.gold.supplier`, change them first in the workspace's SQL editor. `CREATE TABLE IF NOT EXISTS` leaves a table that exists as it is, so the deploy will not add these columns or drop the NOT NULL:

    ALTER TABLE strata.gold.contract_supplier ADD COLUMNS (contract_id STRING)
    ALTER TABLE strata.gold.contract_supplier ALTER COLUMN wb_contract_number DROP NOT NULL
    ALTER TABLE strata.gold.supplier ADD COLUMNS (resolved_on STRING)

Delta adds a new column to a table that holds rows as nullable. Step 2 sets NOT NULL on `contract_id` and `resolved_on` once the nightly job has filled them.

Then run this from the main checkout:

    uv run --script ops/bundle/deploy.py --env-file .env

It worked if it exits 0 and lists these six tables as new: `strata.silver.notice_bidders`, `strata.silver.supplier_resolution`, `strata.ops.supplier_pairs`, `strata.ops.supplier_review_decisions` (with `left_name` and `right_name`), `strata.ops.supplier_pair_labels` and `strata.ops.supplier_match_quality`. The line "Each of these exists now" must also name the view `strata.ops.supplier_review_list`. Then `SHOW CREATE TABLE strata.gold.contract_supplier` must show `contract_id` and no NOT NULL on `wb_contract_number`, and `SHOW CREATE TABLE strata.gold.supplier` must show `resolved_on`.

## Ticket 19, step 2 of 5: one nightly run resolves the suppliers on Databricks

The merger parked this step on October 24, 2026, after merge commit a7bcc99. Run it after step 1. It needs the Databricks keys in `.env`. Ticket 04's step 2 runs the same command, and one run after step 1 covers both.

Run this from the main checkout:

    uv run --script ops/bundle/check.py job-run --env-file .env

Then run these in the workspace's SQL editor:

    SELECT resolved_on, count(*) AS n FROM strata.silver.supplier_resolution GROUP BY resolved_on
    SELECT route, review_reason, count(*) AS n FROM strata.ops.supplier_pairs GROUP BY route, review_reason

It worked if the job run exits 0 with its line "Run <id> wrote one row per task to strata.ops.pipeline_runs, in the bundle's order." That shows serverless installed `splink==5.0.0` for `bronze_to_gold`. The first query must return rows for both `step_supplier_id` and `name`, and the second must return rows. Until ticket 43 passes `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` to `bronze_to_gold`, every pair in the uncertain middle reads route `person` with `no_model`. That is expected, and step 5 checks the model.

**Ran on October 24, 2026 (orchestrator):** the job's third run (556837544068999) and fifth run (882867588506257) ran `bronze_to_gold` with `splink==5.0.0` on environment version 4 (ticket 04's step 2 has the story). `strata.silver.supplier_resolution` by `resolved_on`: step_supplier_id 69,912, name 49,182, individual_consultant 38,146, unmatched 71,216, no_name 15. `strata.ops.supplier_pairs` by route and reason: auto_merge 83,689, kept_apart 103,699, person with no_model 277,042, person with two_step_supplier_ids 33. The uncertain middle reads `person` with `no_model`, as expected until ticket 43. Passed. The ALTER TABLE lines were not needed (the catalog was first made today), and ticket 19's step 4 records the judge recording.

If step 1 ran the ALTER TABLE lines, finish them now:

    ALTER TABLE strata.gold.contract_supplier ALTER COLUMN contract_id SET NOT NULL
    ALTER TABLE strata.gold.supplier ALTER COLUMN resolved_on SET NOT NULL

Both must succeed. The job's MERGE fills `resolved_on` on every supplier it keeps and writes `contract_id` on every contract_supplier row it keeps, so a failure here means a row the job did not rewrite. Do not delete rows to make it pass; tell the orchestrator.

## Ticket 19, step 3 of 5: a reviewer's decision through the deployed App

The merger parked this step on October 24, 2026, after merge commit a7bcc99. Run it after step 2, because the review list shows the pairs of the latest run, and after ticket 09's step 1 (user authorization). It needs the Databricks keys in `.env`. The App deploy grants the App's own service principal SELECT on `strata.ops.supplier_pairs`, and SELECT and MODIFY on `strata.ops.supplier_review_decisions` and `strata.ops.supplier_pair_labels`. Ticket 06's step 1 runs the same deploy. Run it again here if that deploy came from a commit before a7bcc99.

Run this from the main checkout:

    uv run --script ops/app/deploy_app.py --env-file .env

Sign in to the App in a browser and open `<App url>/api/suppliers/review`. Pick one pair and copy its `pair_id`. Decide it from the two names, countries and contracts shown, because the next nightly run applies your decision. Then, in the same tab, open the browser's console and run this, with `merge` or `no_merge` as you decided and a reason in your own words:

    await (await fetch("/api/suppliers/review", {method: "POST", headers: {"content-type": "application/json"}, body: JSON.stringify({pair_id: "<that pair>", decision: "no_merge", reason: "<why>"})})).json()

It worked if the POST answers `{"recorded": true}`. Then run this in the workspace's SQL editor:

    SELECT reviewer, decision, left_name, right_name FROM strata.ops.supplier_review_decisions WHERE pair_id = '<that pair>'

It must return one row whose reviewer is your user id, as `<App url>/api/me` shows it, with your decision and the pair's two names (criterion 4, live half). A 401 `no_identity` means the App got no forwarded viewer, so check ticket 09's step 1. A 503 `not_recorded` means the App has no service principal of its own.

## Ticket 19, step 4 of 5: the live judge on the fixture's uncertain pairs

**Ran on October 24, 2026 (orchestrator).** Exit 0. gpt-5.4 judged the three pairs the thresholds sent it: CHINA RAILWAY NO. 10 ENGINEERING GROUP against China Railway No.10 Engineering Group Co., Ltd. (merge, 0.98), and M/S INTERCONTINENTAL CONSULTANTS & TEC against INTERCONTINENTAL CONSULTANTS AND TECH twice (merge, 0.97 and 0.98). The first answer is saved over `tests/fixtures/azure/supplier_judge.json` with `"recorded": true`. The saved first answer is the Intercontinental pair's (0.97), and the hand-written fixture had said 0.93, so `tests/test_knowledge_adapters.py` now expects 0.97, with a comment; the test checks the adapter's wire format, and the pair in its question is unchanged. The gate passed on the commit that holds both.

The merger parked this step on October 24, 2026, after merge commit a7bcc99. It needs `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` in `.env`, and the fixture database at `data/out/fixture.duckdb`, which the gate builds. It writes nothing to any database.

Run this from the main checkout, then review the diff and run the gate:

    uv run --frozen python ops/suppliers/judge_live.py --env-file .env --record
    git diff tests/fixtures/azure/supplier_judge.json
    .githooks/pre-commit

The builder's note gave `uv run --script` for the first line. The script has no inline dependencies and imports Strata, so it runs in the project's environment, as its docstring says. It worked if it exits 0 and prints three judged pairs, each with the deployment's merge or no merge, and `tests/fixtures/azure/supplier_judge.json` then says `"recorded": true` (criterion 3, live half). The gate must then pass, because the adapter test replays the new recording. If it passes, commit the recording on a branch. Exit 1 means the model gave no judgement in the asked-for shape. Exit 2 means it could not ask, and the line it prints says why.

## Ticket 19, step 5 of 5: the nightly job asks the draft role's deployment

The merger parked this step on October 24, 2026, after merge commit a7bcc99. Run it after steps 1 and 2, and only after ticket 43 passes `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` to the `bronze_to_gold` task. Until then the job has no model to ask.

Run this from the main checkout:

    uv run --script ops/bundle/check.py job-run --env-file .env

Then run this in the workspace's SQL editor:

    SELECT DISTINCT model FROM strata.ops.supplier_pairs WHERE decided_by = 'model' OR review_reason = 'model_unsure'

It worked if the job run exits 0 and at least one row names `gpt-5.4`, the draft role's deployment in `config/models.toml`. If the query returns no rows and the middle pairs still read `no_model`, the task did not get the Azure OpenAI keys.

## Ticket 18, step 1 of 5: check that strata.gold.passage has no notice_url column

The merger parked this step on October 24, 2026, after merge commit a8d605c. It needs the Databricks keys in `.env`. Run it before step 2. The branch added a `notice_url` column to `strata.gold.passage` in commit d089fb6 and took it out in 73e1afe, so the gold query no longer writes it. No live run reached the workspace while the keys were missing, so the column should not be there.

Run this in the workspace's SQL editor:

    DESCRIBE strata.gold.passage

It worked if it shows no `notice_url`, and the gold sync MERGE in step 2 succeeds. If it does list `notice_url`, stop and tell the orchestrator before step 2. CLAUDE.md rule 5 changes a table only through `CREATE OR REPLACE`, and the guard blocks a statement that removes a column, so taking it out needs its own reviewed step.

**Ran on October 24, 2026 (orchestrator):** `DESCRIBE strata.gold.passage` lists 42 columns and no `notice_url`. The catalog was first created today, and every deploy came from 2cef566 or later, after a8d605c, so the five tables this merge added were made with their new columns. Passed.

## Ticket 18, step 2 of 5: read the document slice on the warehouse

**Second run on October 25, 2026 (orchestrator):** the same run as ticket 11's step 1, recorded there: it stopped at 03:25 UTC, again in P156634's plan reader, when the host answered 403 once more. The passage reader has still not started. A third run began at 03:26 UTC.

**Fourth run on October 25, 2026 (orchestrator):** 10:05 to 10:22 UTC, exit 2: "The run stopped: The warehouse did not run the statement. Its state was FAILED: Failed on SQL Endpoint 882107b449dd59cd due to compute cluster maintenance", in the plan reader's fetch. A fifth run began at 10:23 UTC.

**Third run on October 25, 2026 (orchestrator):** stopped at 09:56 UTC in pypdf on a plan PDF with a broken font encoding, after six and a half hours of fetching; recorded under ticket 11's step 1. The passage reader has still not started.

**First run on October 25, 2026 (orchestrator):** the same run as ticket 11's step 1, recorded there. It stopped at 01:50 UTC, in P156634's plan reader, when documents.worldbank.org began answering 403 to every request from this computer. The passage reader did not start, so the stress shelf, `strata.ops.documents_read` and the slice measures have no row yet. Recorded again below when the host answers and the run finishes.

The merger parked this step on October 24, 2026, after merge commit a8d605c. It needs `DATABRICKS_HOST`, `DATABRICKS_WAREHOUSE_ID`, a token or a service principal, `AI_SEARCH_ENDPOINT`, `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` in `.env`. At 08:24 on October 24, `.env` held the host, the warehouse and the AI Search endpoint, but no Databricks token and no Azure OpenAI keys, and day-one test 7 had just failed. It is the same command as ticket 11's step 1.

Run it after step 1, and after ticket 04's steps 1 and 2: the deploy makes the tables, and the nightly job fills `strata.gold.project`, which the slice is chosen from. The deploy must come from a8d605c or later. This merge adds `strata.ops.stress_shelf`, `strata.ops.documents_read` and `strata.silver.isr_ratings`, adds columns to `strata.bronze.layout_pages`, `strata.silver.document_page_routes`, `strata.silver.documents`, `strata.silver.passages` and `strata.gold.passage`, and adds the dashboard's tiles 5 and 7. If a deploy from an earlier commit already made those five tables, `CREATE TABLE IF NOT EXISTS` left them as they were. In that case stop and tell the orchestrator, because no one has written the changes for them yet.

Run this from the main checkout:

    uv run --script ops/documents/run_live.py --env-file .env

It worked if it exits 0, its first line starts "Run <run id> counted N projects in the slice", it prints five "stress shelf" lines, and its last line says the index `strata.gold.passage_index` "holds N of the N passages in strata.gold.passage and is ready", with both numbers the same. Exit 1 means the index did not catch up within 30 minutes; run it again. Then run these in the SQL editor with that run id:

    SELECT shelf_key, state, document_id, count, denominator, parts, longest_pages FROM strata.ops.stress_shelf WHERE run_id = '<run id>'
    SELECT measure, subject, count, denominator, detail FROM strata.ops.data_readiness WHERE run_id = '<run id>' AND measure IN ('slice_projects', 'slice_projects_read', 'documents_read_projects')
    SELECT document_type, fiscal_year, documents, pdf_pages FROM strata.ops.documents_read WHERE run_id = '<run id>' ORDER BY document_type, fiscal_year

The first query must return five rows. Its `over_parser_limit` row must be either `no_document` with the live slice's longest page count, or `read` with `parts` above 1 and `count` equal to `denominator` (criterion 6, live half). On the fixture it read `no_document` with 103 pages. The second must return `slice_projects`, `slice_projects_read` and one `documents_read_projects` row per project. The third must list Project Paper rows. The run's summary line must also say "Prompt Shields scanned N new passage texts and text-embedding-3-large embedded N", which covers the Prompt Shields scan and the embeddings of the new passages (Project Papers, PPARs and notice text).

## Ticket 18, step 3 of 5: a second run the same day parses nothing

The merger parked this step on October 24, 2026, after merge commit a8d605c. Run it right after step 2, on the same day. It needs the same keys as step 2.

Run this from the main checkout again:

    uv run --script ops/documents/run_live.py --env-file .env

Then run these in the SQL editor, the first with the new run id:

    SELECT project_id, parser, pages_parsed, pages_failed FROM strata.ops.parse_runs WHERE run_id = '<new run id>'
    SELECT to_date(started_at) AS day, sum(pages_parsed + pages_failed) AS pages_tried, max(daily_page_cap) AS cap FROM strata.ops.parse_runs GROUP BY to_date(started_at) ORDER BY day

It worked if every row of the first query shows `pages_parsed` 0 and `pages_failed` 0, the run's summary line says it embedded 0 passages, and every day in the second query has `pages_tried` at or under `cap`, which is `ingestion.daily_page_cap` in `config/thresholds.toml` (500 today) across both readers (criterion 2, live half). A page the layout parser failed on is tried again the next day and counts against that day's cap; ticket 18's first parked decision asks whether to keep that.

## Ticket 18, step 4 of 5: the slice's project count on DuckDB and on the SQL warehouse

The merger parked this step on October 24, 2026, after merge commit a8d605c. Run it after step 2. It needs the Databricks keys in `.env`. It is the same command as ticket 04's step 3, and one run after step 2 serves every block that names it.

Run this from the main checkout:

    uv run --script ops/bundle/check.py same-rows --env-file .env

It worked if it exits 0 and `slice_projects.sql` agrees on both engines (criterion 1, live half). Then read the live count and its difference from PLAN.md's 128:

    SELECT count, detail FROM strata.ops.data_readiness WHERE measure = 'slice_projects' ORDER BY measured_at DESC LIMIT 1

On the fixture the detail reads 17 projects ("Kenya 17, Bangladesh 0, Vietnam 0, Pakistan 0"), 111 fewer than 128. The PM copies the live detail sentence into `docs/STATUS.md`.

## Ticket 18, step 5 of 5: "similar experience" finds the notices through AI Search

The merger parked this step on October 24, 2026, after merge commit a8d605c. Run it after step 2, once the index holds every passage. It needs `DATABRICKS_TOKEN` to be a person's token, because the tool acts as the viewer, plus `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY`.

The builder named `ops/documents/search_live.py` for this step. That script asks only ticket 11's question (`search-passages-icr-rebidding`) and has no option for another one. So run it once as it is, then ask ticket 18's benchmark question through the same code. Run both from the main checkout:

    uv run --script ops/documents/search_live.py --env-file .env
    uv run --frozen python -c "import sys; sys.path.insert(0, 'ops/documents'); import search_live; search_live.QUESTION = 'search-passages-similar-experience'; sys.exit(search_live.main(['--env-file', '.env']))"

It worked if the first ends "1 of the 1 expected passages are in the top three." (the new passages did not push paragraph 54 out), and the second lists `strata.gold.passage:OP00118817/v1/s5` and `strata.gold.passage:OP00128730/v1/s6`, each with its notice id, and ends "2 of the 2 expected passages are in the top three." (criterion 8, live half). Both must start "search_passages ranked with AI Search". Exit 2 means it could not ask, and the line it prints says why.

## Ticket 35, step 1 of 5: the Foundry review notes writer matches the repo

**Ran on October 24, 2026 (orchestrator).** The first run printed the instructions' diff and ended "I made version 1 of strata-review-notes-writer, which matches the repo." The `--check` run exited 0 and printed that version 1 matches the repo, under the guardrail strata-guardrail.

The merger parked this step on October 24, 2026, after merge commit 0756ed6. It needs `FOUNDRY_PROJECT_ENDPOINT` in `.env` and the `az` command line signed in to the subscription that holds the Foundry resource named in `ops/dayone/dayone.toml`. At 08:46 on October 24 that key was set, but `DATABRICKS_TOKEN` and `APPLICATIONINSIGHTS_CONNECTION_STRING` were missing and day-one test 7 had failed, so the build's standing rule kept all five of this ticket's steps here. Run it after ticket 13's step 1, which makes the guardrail `strata-guardrail`. The writer runs under the same guardrail.

Run this from the main checkout, and then run it again with `--check`:

    uv run --script ops/agent/sync.py --env-file .env --agent review_notes_writer
    uv run --script ops/agent/sync.py --env-file .env --agent review_notes_writer --check

It worked if the first run prints what differed and ends "I made version N of strata-review-notes-writer, which matches the repo." The second run must exit 0 and print "Foundry's agent strata-review-notes-writer, version N, matches the repo: there is no difference in its model, instructions, tools, description or guardrail (strata-guardrail)." Exit 1 means `--check` found a difference, and exit 2 means it could not run. Run the pair again after any change to `src/strata/agent/instructions/review_notes_writer.md`, the `draft` role in `config/models.toml` or the writer's entry in `config/agents.toml`.

## Ticket 35, step 2 of 5: re-record the review notes writer's cases from the live writer

The merger parked this step on October 24, 2026, after merge commit 0756ed6. Run it after step 1, after ticket 04's step 1 deployed the bundle from 0756ed6 or later, and after ticket 08's step 1 filled the plan tables on the warehouse, because the writer drafts from check_plan's rows, read as you. It needs `FOUNDRY_PROJECT_ENDPOINT`, `DATABRICKS_HOST`, `DATABRICKS_WAREHOUSE_ID` and `DATABRICKS_TOKEN` in `.env`, and `az` signed in.

Run this from the main checkout, then review the diff:

    uv run --script ops/agent/record.py --env-file .env --writers
    git diff tests/fixtures/agent

It worked if the recording exits 0 and prints a diff for `tests/fixtures/agent/recorded/review-notes-nwwda-2026-10-09.json` with the verifier's counts, such as "The verifier kept 6 of 6 sentences; ...". The file's `"recorded"` changes from `false` to `true`. Read the diff before you keep it: it must hold three notes, on KE-NWWDA-541055-CW-RFB, KE-NWWDA-229129-CW-RFB and KE-NWWDA-541062-CW-RFQ, each citing its own row in `strata.silver.plan_rows`, with no sentence removed. The draft screens play answers made from this recording, so write them again and run the gate:

    uv run --frozen python tests/record_drafts_api.py
    git diff tests/fixtures/api
    .githooks/pre-commit

The gate must pass, because the route tests and the screen tests replay the new recordings (criterion 1, live half). If it passes, commit the recordings on a branch. If a test no longer gets what it expects, the live writer answers differently from the hand-written note, so tell the orchestrator before you change a test. Criterion 1's "six checks" also waits on ticket 24: once 24 merges, a new draft's `checks_run` must read `[1, 2, 3, 4, 5, 6]`, with check 4's judge call wired into `runtime.write`.

## Ticket 35, step 3 of 5: redeploy the App with the draft routes

The merger parked this step on October 24, 2026, after merge commit 0756ed6. It needs the Databricks keys in `.env`, and the four Foundry keys that ticket 14's step 1 names, because the App reaches the writer through Foundry. Run it after step 1, and after ticket 04's step 1 deployed the bundle from 0756ed6 or later, because that deploy makes `strata.ops.drafts`, `strata.ops.draft_states`, `strata.ops.draft_exports` and `strata.ops.draft_files`, and this deploy grants the App's own service principal SELECT and MODIFY on them. Ticket 06's step 1 runs the same command. Run it again here if that deploy came from a commit before 0756ed6.

Run this from the main checkout:

    uv run --script ops/app/deploy_app.py --env-file .env

It worked if the deploy exits 0, its step 6 prints "6. Letting the app's own service principal write usage events, agent runs, opened sources and drafts to strata.ops.", and its last line is `Strata is running at https://...`. Then sign in to the App in a browser and open:

    <App url>/api/drafts/existing?kind=review_notes&project_id=P156634&agency_id=northern-water-works-development-agency

It must answer `{"by_plan_date": {...}}`, with no `plan_date` in the address: `{"by_plan_date": {}}` before anyone drafts on that plan, and a `"2026-10-09"` key naming the draft after step 4.

## Ticket 35, step 4 of 5: two acts on one draft at the same moment

The merger parked this step on October 24, 2026, after merge commit 0756ed6. Run it after step 3, after ticket 09's step 1 (user authorization) and after ticket 08's step 1 (the plan tables). It needs the Databricks keys in `.env`.

First make the team, because a draft keeps the team its author was on when it was saved, and step 5 reads it. In the workspace's admin settings, make a group named exactly `strata-team-kenya-water` (`config/roles.toml`), with you and one other user as direct members. The App reads groups through SCIM `/Me`, which lists only direct groups, so a nested group does not count.

Then sign in to the App as a user with USE CATALOG, USE SCHEMA and SELECT on `strata`, open `<App url>/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09`, choose "Draft review notes (3 rows)", and wait for the draft page. Copy the draft id from the address (`/drafts/<draft id>`). Click one citation marker in a note and close the drawer: the bar must read "You opened 1 of 3 sources." (criterion 3, live half). Then open the browser's console on that tab and run:

    const act = (name, state) => fetch(`/api/drafts/<draft id>/${name}`, {method: "POST", headers: {"content-type": "application/json"}, body: JSON.stringify({expected_state: state, view: "staff"})}).then(async (r) => [r.status, (await r.json()).error])
    await Promise.all([act("check", "draft"), act("check", "draft")])

It worked if one answer is 200 and the other is `[409, "stale"]`, in either order. Then run this in the workspace's SQL editor:

    SELECT step, state, from_state, actor_id, changed_at FROM strata.ops.draft_states WHERE draft_id = '<draft id>' ORDER BY step

It must return exactly two rows: the saved draft, and one `checked` row (criterion 2, live half). Then try the same with two exports at once:

    await Promise.all([act("export", "checked"), act("export", "checked")])
    SELECT export_id, exported_at, footnotes FROM strata.ops.draft_exports WHERE draft_id = '<draft id>'

One answer must be 200 and the other `[409, "stale"]`, and the query must return exactly one row. The verifier read the code and expects that two exports at once may each save an export row before one is refused. If the query returns two rows, tell the orchestrator. Last, run `DESCRIBE HISTORY strata.ops.draft_states LIMIT 5`: the MERGE rows' `userName` must be the App's own service principal (its application id, shown on the App's page in the workspace), not your user. That shows drafts are written by the App's account, as built.

## Ticket 35, step 5 of 5: teams come from workspace groups

The merger parked this step on October 24, 2026, after merge commit 0756ed6. Run it right after step 4, with the draft step 4 saved. It needs a second user in `strata-team-kenya-water` and a third user outside it.

Each of the other two users signs in to the App in their own browser profile and opens `<App url>/api/drafts`. It worked if the member's answer lists step 4's draft under `exported` with your name as its author, and the non-member's answer lists only their own drafts, which is none unless they made one (criterion 6, live half). Then each opens `<App url>/drafts/<draft id>`. The member sees the draft and cannot act on it. The non-member gets "not found" (404). If the member sees only their own drafts, the App's token could not read SCIM `/Me`, so every viewer was on a team of their own. The App asks only for the `sql` user scope (`ops/app/deploy_app.py`), which may not cover `/api/2.0/preview/scim/v2/Me`. Tell the orchestrator, because the review's parked decision 2 covers this.

## Ticket 12, step 1 of 3: the past range's rows on DuckDB and on the SQL warehouse

The merger parked this step on October 24, 2026, after merge commit bbab425. It needs the Databricks keys in `.env`, and at 09:45 on October 24 `DATABRICKS_TOKEN` was still missing. Run it after ticket 04's steps 1 and 2, ticket 07's step 1 and ticket 08's step 1, because the two files read the notices, the contracts and the plan rows those steps write. It is the same command as ticket 04's step 3, and one run after those steps serves every block that names it.

Run this from the main checkout:

    uv run --script ops/bundle/check.py same-rows --env-file .env

It worked if it exits 0 and prints "DuckDB and the SQL warehouse returned the same ... rows, and they are the rows the file expects." for both `past_range_criteria_ke_works_rfb.sql` and `past_range_coverage_ke_works_rfb.sql` (criteria 1 and 3, live half). As of October 22, 2026, the coverage file's rows are canceled 3, matched 65, no STEP reference 3, no notice 10 and used 49. The warehouse returns every value as text, and this is the first time find_comparables' date and amount handling runs there. If the warehouse holds Kenya works packages that the fixture does not record, the command prints the DuckDB rows, the warehouse rows and the expected rows side by side. Tell the orchestrator before you change a file's expected rows.

## Ticket 12, step 2 of 3: the Foundry agent offers find_comparables

**Ran on October 24, 2026 (orchestrator).** Ticket 13's step 1 ran from the tree after bbab425, so the first sync printed find_comparables among the tools and the sentence about citing a tool's summary, and made version 1. The `--check` run exited 0.

The merger parked this step on October 24, 2026, after merge commit bbab425. It needs `FOUNDRY_PROJECT_ENDPOINT` in `.env` and the `az` command line signed in to the subscription that holds the Foundry resource named in `ops/dayone/dayone.toml`. Run it after ticket 13's step 1, which makes the guardrail `strata-guardrail`. Ticket 12 adds the find_comparables tool to `config/tools.toml` and changes `src/strata/agent/instructions/orchestrator.md`, so the agent in Foundry no longer matches the repo. If ticket 13's step 1 ran from bbab425 or later, the first command below has nothing to change, and the `--check` run is enough.

Run this from the main checkout, and then run it again with `--check`:

    uv run --script ops/agent/sync.py --env-file .env
    uv run --script ops/agent/sync.py --env-file .env --check

It worked if the first run prints what differed, with find_comparables among the tools and the sentence about citing a tool's summary in the instructions, and ends "I made version N of strata-orchestrator, which matches the repo." The second run must exit 0 and print "Foundry's agent strata-orchestrator, version N, matches the repo: there is no difference in its model, instructions, tools, description or guardrail (strata-guardrail)." Exit 1 means `--check` found a difference, and exit 2 means it could not run.

## Ticket 12, step 3 of 3: the package workspace on the deployed App

The merger parked this step on October 24, 2026, after merge commit bbab425. It needs the Databricks keys in `.env`. Run it after step 1, after ticket 08's step 1 has filled the plan tables on the warehouse, and after ticket 09's step 1 has turned on user authorization. Ticket 06's step 1 runs the same deploy command. Run it again here if that deploy came from a commit before bbab425, because the package workspace and its two routes arrived in this merge.

Run this from the main checkout:

    uv run --script ops/app/deploy_app.py --env-file .env

Then sign in to the workspace in a browser as a user with USE CATALOG, USE SCHEMA and SELECT on `strata`, and open:

    <App url>/packages/KE-NWWDA-541055-CW-RFB

It worked if the deploy exits 0 with its last line `Strata is running at https://...`, and the page shows the "Planning" eyebrow over "1 · How long it took", with a title that counts the comparable packages signed within the plan's 1.5 months. On the fixture, as of October 24, 2026, the server's answer was 49 comparable packages (45 signed and 4 still open), a middle half of 3.3 to 7.9 months, a middle of 4.4 months, 8 in 10 signed within 9.1 months, and 2 signed within the plan's 1.5 months. Its coverage line began "Based on 49 of 65 matching packages". The four still-open packages gain a day each day, so the quartiles can move by a tenth of a month as the date moves. Then open `<App url>/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09` and choose "See the past range" on the KE-NWWDA-541055-CW-RFB row. It must open the same page, with focus on its heading.

## Ticket 20, step 1 of 4: the live batch model reads the reports, and ISR 7 meets paragraph 78

The merger parked this step on October 24, 2026, after merge commit da1ab20. All ten keys were set, but the header above holds workspace steps back while the user runs the backlog. It needs `DATABRICKS_HOST`, `DATABRICKS_WAREHOUSE_ID`, `DATABRICKS_TOKEN`, `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` in `.env`.

Run it after these steps. Ticket 07's step 1 fills the contracts and notices. Ticket 17's step 1 fills the IEG ratings dataset. Ticket 18's step 2 reads the documents into passages and fills `strata.silver.isr_ratings`. Then deploy again from da1ab20 or later with ticket 04's command, `uv run --script ops/bundle/deploy.py --env-file .env`. The deploy on October 24 came before this merge, and this merge adds four tables: `strata.bronze.batch_answers`, `strata.gold.assertion`, `strata.gold.disagreement` and `strata.ops.assertion_rejections`. The deploy must list those four as new, and it changes no existing table.

**Deploy part ran on October 24, 2026 (orchestrator):** ticket 29's step 1 deploy listed the four tables as new and changed no existing table. The `batch_live.py` run itself stays parked on decision 2 (gpt-5.4-nano is Global Standard, not Global Batch).

The batch role's deployment is gpt-5.4-nano (`config/models.toml`, `[roles.batch]`). Day-one test 8 found it deployed as GlobalStandard, and Azure's Batch API takes only a Global Batch (or Data Zone Batch) deployment. Until decision 2 in `docs/STATUS.md` is answered, expect this step to stop with exit 2 and the error Azure gives. Do not change `config/models.toml` to get past it; tell the orchestrator.

Run this from the main checkout:

    uv run --script ops/assertions/batch_live.py --env-file .env

It worked if it exits 0 and prints "Run <run id> holds N assertions and N disagreements", then a line that names `strata.gold.passage:26733307/v1/s4` and `strata.gold.passage:31525018/v1/78` with "I lean on strata.gold.passage:31525018/v1/78 (outcome)", and ends "The showcase disagreement came back as the benchmark expects." (criteria 1 and 7, live half). Exit 1 means the run finished without that row, or the batch was still running when the script stopped waiting after an hour. Run the same command again later: it waits for the same batch, and answers already held are not asked for again. Exit 2 means it could not run, and the line it prints says why. On the fixture the run wrote 1,261 assertions, 1 rejection (`quote_not_on_page`, the planted 31525018/v1/45) and 34 disagreements. The warehouse's counts may differ if the World Bank's hosts list newer documents.

## Ticket 20, step 2 of 4: the morning after a nightly run, the text assertions are still there

The merger parked this step on October 24, 2026, after merge commit da1ab20. Run it the morning after the first nightly run that follows step 1. It needs the same keys as step 1.

The nightly job's `detect_disagreements` task has no Azure keys until ticket 43 passes them, so it replays the answers that step 1's live model gave (`HeldAnswers`, the review's B2 fix) rather than deleting the assertions read from text. Check first that the night's run finished:

    SELECT task_key, state, finished_at FROM strata.ops.pipeline_runs WHERE task_key = 'detect_disagreements' ORDER BY finished_at DESC LIMIT 1

Then run this from the main checkout:

    uv run --script ops/assertions/batch_live.py --env-file .env

It worked if the query shows the task finished after step 1, and the command again exits 0 and ends "The showcase disagreement came back as the benchmark expects." That proves the night's run kept what the live model read. If `config/evidence_ladder.toml` changed between step 1 and the night, every request changes and the night's run finds no held answer (the review's F5, parked decision 1 in ticket 20's done comment). In that case run step 1 again before you read this result.

## Ticket 20, step 3 of 4: the showcase disagreement on DuckDB and on the SQL warehouse

The merger parked this step on October 24, 2026, after merge commit da1ab20. Run it after step 1. It needs the Databricks keys in `.env`. It is the same command as ticket 04's step 3, and one run after step 1 serves every block that names it.

Run this from the main checkout:

    uv run --script ops/bundle/check.py same-rows --env-file .env

It worked if it exits 0 and prints "DuckDB and the SQL warehouse returned the same ... rows, and they are the rows the file expects." for `p130164_isr_7_against_icr_paragraph_78.sql`. Its one expected row is ISR 7's side `strata.gold.passage:26733307/v1/s4` (Satisfactory, made 2016-08-26) against `strata.gold.passage:31525018/v1/78` (PDF page 27, public 2019-11-02), for the period from the mid-term review on 2016-05-16, leaning on paragraph 78 under the `outcome` rule. If the warehouse's row differs, the command prints the DuckDB, warehouse and expected rows side by side. Tell the orchestrator before you change the file's expected row.

## Ticket 20, step 4 of 4: re-record the batch answers from the live model

The merger parked this step on October 24, 2026, after merge commit da1ab20. It needs only `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY`, and a Global Batch deployment for the batch role (see step 1). It reads `data/out/fixture.duckdb`, which the gate builds, so run `.githooks/pre-commit` once first if that file is missing.

Run this from the main checkout:

    uv run --script ops/assertions/batch_live.py --record --env-file .env
    .githooks/pre-commit

If the first command prints a batch id because the batch was still running after an hour, run it again with `--batch <id>` to wait for the same batch instead of asking again. It worked if the first command exits 0 and ends "I wrote N answers to tests/fixtures/azure/batch_assertions.json. Run the gate next.", and the gate then passes on the live recording, which now also asks about the P130164 PAD. The recording keeps the planted assertion, so the gate still proves the rejection. A live answer that reads more than the hand-written one (such as item 8.b of the ICR Reviews) can move a value the tests expect, and the failing test names it. Do not edit the test to match; tell the orchestrator. The new recording is a tracked file, so the orchestrator commits it once the gate passes.

## Ticket 29, step 1 of 5: deploy the lesson tables and the quarterly cross-check job

The merger parked this step on October 24, 2026, after merge commit 65293cd. All ten keys were set, but the header above holds workspace steps back while the user runs the backlog. It needs the Databricks keys in `.env`. It is ticket 04's deploy command, and one deploy from 65293cd or later also serves ticket 20's step 1, which needs a deploy from da1ab20 or later.

Run this from the main checkout, twice:

    uv run --script ops/bundle/deploy.py --env-file .env

It worked if both runs exit 0. The first run lists these ten tables as new and changes no existing table: `strata.bronze.lesson_batches`; `strata.silver.lesson_proposals`, `strata.silver.lesson_evidence` and `strata.silver.lesson_restatements`; `strata.ops.lesson_versions`, `strata.ops.lesson_review_items`, `strata.ops.lesson_review_acts`, `strata.ops.lesson_sources`, `strata.ops.lesson_review_notes` and `strata.ops.lesson_uses`. It also lists the new job "strata lesson cross-check" (`bundle/lessons.yml`, at 06:00 New York time on the second day of January, April, July and October). The second run prints "No changes."

**Ran on October 24, 2026 (orchestrator):** both runs exited 0, with `--fairshare-catalog workspace`. The first listed the ten lesson tables as new, and ticket 20's four (`strata.bronze.batch_answers`, `strata.gold.assertion`, `strata.gold.disagreement` and `strata.ops.assertion_rejections`), and changed no existing table. The job "strata lesson cross-check" (849400525894800) was not listed as new because the plain `databricks bundle deploy` runs of ticket 04's step 2 had already made it from 65293cd. The second run printed "No changes." Both printed "workspace's catalog lists the same before and after the deploy: two schemas, three tables and one volume." Passed.

## Ticket 29, step 2 of 5: the Foundry lesson review writer matches the repo

The merger parked this step on October 24, 2026, after merge commit 65293cd. It needs the four Foundry keys that ticket 14's step 1 names.

Run this from the main checkout, twice:

    uv run --script ops/agent/sync.py --env-file .env --agent lesson_review_writer

It worked if the first run creates or updates the Foundry agent `lesson_review_writer` from `config/agents.toml` and `lesson_review_writer.md`, and the second run reports no difference.

**Ran on October 24, 2026 (orchestrator):** the first run printed the instructions diff and "I made version 1 of strata-lesson-review-writer, which matches the repo."; the second printed "Foundry's agent strata-lesson-review-writer, version 1, matches the repo: there is no difference in its model, instructions, tools, description or guardrail (strata-guardrail)." Both exited 0. Passed.

## Ticket 29, step 3 of 5: redeploy the App, which writes the lesson review record as itself

The merger parked this step on October 24, 2026, after merge commit 65293cd. It needs the Databricks keys in `.env`, and the four Foundry keys. Run it after step 1, because this deploy grants the App's own service principal SELECT and MODIFY on five tables that step 1 makes. Ticket 06's step 1 runs the same command. Run it again here if that deploy came from a commit before 65293cd.

Run this from the main checkout:

    uv run --script ops/app/deploy_app.py --env-file .env

Step 6 runs the grants without printing each one, and its line still names only usage events, agent runs, opened sources and drafts. So check the grants on the SQL warehouse after the deploy:

    SHOW GRANTS ON TABLE strata.ops.lesson_review_acts

and the same for `strata.ops.lesson_review_items`, `strata.ops.lesson_versions`, `strata.ops.lesson_sources` and `strata.ops.lesson_review_notes`.

It worked if the deploy exits 0 and prints "Strata is running at <url>", and each of the five tables shows SELECT and MODIFY for the App's own service principal and no grant to `strata-accredited-procurement-specialists` or `strata-lead-procurement-specialists` (criteria 3 and 4, workspace half). On the deployed App, a person in neither group who opens `<App url>/api/lessons/review` gets 403 `not_a_reviewer`.

## Ticket 29, step 4 of 5: propose lessons with the live batch model, until no batch is still running

The merger parked this step on October 24, 2026, after merge commit 65293cd. It needs `DATABRICKS_HOST`, `DATABRICKS_WAREHOUSE_ID`, `DATABRICKS_TOKEN`, `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY`, and the four Foundry keys for the review notes. Run it after steps 1 and 2, and after ticket 18's step 2 has read the slice's ICRs, ICR Reviews and PPARs into `strata.silver.passages`.

The batch role's deployment is gpt-5.4-nano (`config/models.toml`, `[roles.batch]`). Day-one test 8 found it deployed as GlobalStandard, and Azure's Batch API takes only a Global Batch (or Data Zone Batch) deployment. Until decision 2 in `docs/STATUS.md` is answered, expect this step to stop with exit 2 and the error Azure gives. Do not change `config/models.toml` to get past it; tell the orchestrator.

Run this from the main checkout:

    uv run --script ops/lessons/run_live.py --env-file .env

A batch can take up to a day. The first run sends the documents, and a later run collects the answers. Run the same command again until this query shows no request whose newest row is `submitted`:

    SELECT status, count(*) FROM (SELECT custom_id, status, row_number() OVER (PARTITION BY custom_id ORDER BY recorded_at DESC) AS n FROM strata.bronze.lesson_batches) WHERE n = 1 GROUP BY status

It worked if each run exits 0 and prints "Run <run id> changed N rows and wrote N lesson review notes.", and then:

- `strata.bronze.lesson_batches` holds every request as `completed` (a `failed` request goes again on the next run);
- `strata.silver.lesson_proposals` holds the proposal from passage `31525018/v1/54` with `quote_check = 'passed'`, and `strata.silver.lesson_evidence` holds its restatement from `34056616/v2/10.b` with `restated_by_ieg = true` (criterion 1, live half);
- `SELECT source, subject, count, denominator FROM strata.ops.data_readiness WHERE measure = 'lessons_verified'` returns the row for get_lessons with a denominator, and any proposal whose quote is not on its page is counted out of it. On the fixture the row was 3 of 4 for P130164;
- `strata.ops.lesson_review_notes` holds live notes, and any sentence the verifier removed is listed with its reason.

If the run prints "The env file names no Foundry project, so the review notes wait.", run step 2 first, then this step again. The warehouse's counts may differ from the fixture's if the World Bank's hosts list newer documents.

## Ticket 29, step 5 of 5: two reviewers act on the deployed App, and the quarterly job draws its sample

The merger parked this step on October 24, 2026, after merge commit 65293cd. Run it after step 4, and after the owner fills `config/roles.toml` with the workspace group names and the reviewers (each `[[people]]` entry's email, name, groups, regions and projects) and the App is deployed again with them.

1. Open `<App url>/lessons/review` as a named reviewer, open a lesson in "Waiting for review", and recommend it with a reason. Then open the same lesson as a different person who is a lead procurement specialist for that region, and decide it with a reason.
2. On the SQL warehouse, as a person in one of the reviewer groups (check with `SELECT current_user()`), try an `INSERT INTO strata.ops.lesson_review_acts`.
3. Ask the benchmark question `get-lessons-cost-estimates` through `WarehouseEngine` once the library holds the decided lesson.
4. After the job "strata lesson cross-check" first runs on January 2, 2027 (or start it by hand with "Run now" on the workspace's Jobs page), read `strata.ops.lesson_review_items` where `kind = 'cross_check'`. Start it by hand once more in the same quarter.

It worked if:

- `strata.ops.lesson_review_acts` holds both acts, each naming its own person as the actor, and `strata.ops.lesson_versions` holds version 1 with both names, both reasons and `days_from_publication` (criteria 4 and 5, workspace half);
- the reviewer's `INSERT` is refused for lack of permission;
- get_lessons returns the decided lesson with its evidence ids, `restated` and the edition `guidelines_2011`;
- the January run writes `cross_check` items assigned to another region (one tenth of the quarter's decisions, rounded up, at least one), and the second run in the same quarter writes none (criterion 7, workspace half). A quarter with no decisions writes nothing.

## Ticket 15, step 1 of 4: the Foundry package reader matches the repo

**Ran on October 25, 2026 (orchestrator).** Both runs exited 0. The first printed "Foundry's agent strata-package-reader differed from the repo:", the diff, and "I made version 1 of strata-package-reader, which matches the repo." The second printed "Foundry's agent strata-package-reader, version 1, matches the repo: there is no difference in its model, instructions, tools, description or guardrail (strata-guardrail)." Passed. After step 2 changed the instructions, the same pair of runs made version 2 and confirmed it.

The merger parked this step on October 24, 2026, after merge commit d356ba7. All ten keys were set, but the header above holds workspace steps back while the user runs the backlog. It needs the four Foundry keys that ticket 14's step 1 names, and the `az` command line signed in to the subscription that holds the Foundry resource. Run it after ticket 13's step 1, which makes the guardrail `strata-guardrail`. Ticket 15 adds the agent `package_reader` to `config/agents.toml`, with its instructions in `package_reader.md`.

Run this from the main checkout, twice:

    uv run --script ops/agent/sync.py --env-file .env --agent package_reader

It worked if both runs exit 0. The first run prints what differed and ends "I made version 1 of strata-package-reader, which matches the repo." The second run reports no difference: "Foundry's agent strata-package-reader, version 1, matches the repo: there is no difference in its model, instructions, tools, description or guardrail (strata-guardrail)."

## Ticket 15, step 2 of 4: re-record the package reader's cases from the live reader

**Ran on October 25, 2026 (orchestrator):** the record command exited 0 and printed a diff for each of the three recordings, each now `"recorded": true` with `"recorded_on": "2026-10-25"` and agent version 1. `package-no-package` and `package-dividing` came back with the same answers as the hand-written ones, down to the fields. `package-rural-roads-kenya` came back without the guess: the live reader answered category Works, description "Rural roads", estimated amount 15,000,000 (approximate) and country KE, and no `lots` field, where the hand-written answer guessed `lots` 2 with `stated` false. Five tests in `tests/test_planned_packages.py` then failed, among them `test_the_sentence_yields_the_wireframe_s_chips_with_two_computed_and_one_guess`: the first (`test_the_screens_recorded_package_answers_are_what_the_routes_answer`) because `tests/fixtures/api/package-plan-rural-roads.sse` carries "count": 5, "guesses": 1 and the live answer gives 4 and 0. As this block asks, nothing was changed by hand: the three tracked recordings were restored, the live recordings and their diff are kept in the orchestrator's scratchpad (`recorded15/`), and strata-eb was told. Decision for the orchestrator: either the reader's instructions (`package_reader.md`) should ask for a guessed lot count when the sentence gives none, so the wireframe's "two computed and one guess" holds, or the fixture, the SSE recording and the five tests follow the live answer with no guess. Not passed yet.

**Second run on October 25, 2026 (orchestrator):** strata-eb chose the first path: keep the wireframe's one guess. `src/strata/agent/instructions/package_reader.md` now tells the reader to guess a field marked may_guess from the amount and the category when the sentence does not give it, with `stated` false and a `basis` clause, and gives the rule of thumb for lots (about one lot for each US$5 to 10 million of works, so "about US$15 million" of roads reads as 2 lots; goods or services 1 lot unless the sentence names several items or places). The sync then made version 2 of strata-package-reader, and the second sync run reported no difference. The record command exited 0 again; the rural-roads recording now answers `lots` 2 with `stated` false and `basis` "the amount and the category", the other two are unchanged in substance, and all 30 tests in `tests/test_planned_packages.py` pass with `"recorded": true` on each file. The prompt and the recordings are committed together. Passed.

The merger parked this step on October 24, 2026, after merge commit d356ba7. It needs the four Foundry keys. Run it after step 1. The three package reader recordings in `tests/fixtures/agent/recorded/` were written by hand (`"recorded": false`), because no live reader existed when the ticket was built (criterion 1, live half).

Run this from the main checkout:

    uv run --script ops/agent/record.py --env-file .env --packages
    uv run --frozen pytest tests/test_planned_packages.py

It worked if the record command exits 0 and prints a unified diff for each of the three recordings named in `tests/fixtures/agent/packages.toml`, each recording now carries `"recorded": true`, and the tests pass, `test_the_sentence_yields_the_wireframe_s_chips_with_two_computed_and_one_guess` among them. The recordings change tracked files, so commit them on `build/strata` through the gate. If the live reader reads "rural roads, Kenya, about US$15 million" differently from the hand-written answer (for example, with no guessed "2 lots"), the test fails and the diff shows why. Tell the orchestrator before you change a test or a recording by hand.

## Ticket 15, step 3 of 4: the Lakebase instance and a planned package on the deployed App

The merger parked this step on October 24, 2026, after merge commit d356ba7. It needs the Databricks keys in `.env`, and the four Foundry keys so that `/api/ask` and the package reader answer through Foundry. Run it after step 1, after ticket 12's step 3, and after ticket 09's step 1 has turned on user authorization. Ticket 06's step 1 runs the same deploy command. Run it again here if that deploy came from a commit before d356ba7, because the Lakebase resource and the planned package routes arrived in this merge (criterion 6, live half).

Run this from the main checkout:

    uv run --script ops/app/deploy_app.py --env-file .env

It worked if the deploy exits 0, its step 3 prints "The Lakebase instance strata-state is running, so the app keeps app state there." (not "I could not make or start the Lakebase instance"), and its last line is `Strata is running at https://...`. The app makes the tables `planned_packages`, `planned_package_saves` and `plan_checks_opened` in its Lakebase database the first time it needs them.

Then sign in to the workspace in a browser as a user with USE CATALOG, USE SCHEMA and SELECT on `strata`:

1. Open `<App url>/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09` to check the NWWDA plan of October 9, 2026.
2. Type "rural roads, Kenya, about US$15 million" into the box and choose "Plan a package from this sentence".
3. Change one chip, for example the method to "ICB", and wait for the "Saved" stamp. Then reload the page.
4. Open the Packages tab.
5. Open the package's address as a second person.

It worked if the chips after the reload are the same as before it, with Request for Bids (RFB) and Open international after "ICB"; the Packages tab lists "Rural roads, Kenya" and "Northern Water Works Development Agency, plan of October 9, 2026" with "Plan check", newest first; and the second person sees "I can't find this package." and none of the first person's rows on their Packages tab.

## Ticket 15, step 4 of 4: find_comparables for a planned package on the SQL warehouse

The merger parked this step on October 24, 2026, after merge commit d356ba7. It needs the Databricks keys in `.env`. Run it after ticket 12's step 1. It is the same command as ticket 12's step 1 and ticket 04's step 3, and one run after d356ba7 serves every block that names it. Ticket 15 adds the benchmark question `find-comparables-planned-ke-works-rfb`, which asks find_comparables about a package with no STEP row (method Request for Bids, category Works, country KE, as of October 22, 2026), and names `tests/ground_truth/past_range_coverage_ke_works_rfb.sql` as its ground truth.

Run this from the main checkout:

    uv run --script ops/bundle/check.py same-rows --env-file .env

Then ask the benchmark question `find-comparables-planned-ke-works-rfb` through `WarehouseEngine`, with the arguments `evals/benchmark.yaml` gives it.

It worked if the check exits 0 and prints "DuckDB and the SQL warehouse returned the same ... rows, and they are the rows the file expects." for `past_range_coverage_ke_works_rfb.sql`, and the question's answer holds the same 49 comparables, with the quartiles 3.3, 4.4, 7.9 and 9.1 months, and the four still-open packages and three canceled packages left out that the benchmark lists. If the warehouse holds Kenya works packages that the fixture does not record, the rows differ. Tell the orchestrator before you change a file's expected rows.

## Ticket 25, step 1 of 2: backtest 2025 alone on the workspace and register the champion

**Deploy on October 25, 2026 (orchestrator):** the deploy recorded under ticket 21's step 1 listed `strata.ops.evaluation_result` as new and changed no existing table. The backtest for 2025 started at 10:09 UTC and is recorded below when it finishes.

**First run on October 25, 2026 (orchestrator):** exit 2 at 10:06 UTC: "The backtest stopped before it finished: RestException: NOT_FOUND: Parent directory does not exist: /Shared/strata." MLflow makes the experiment but not its folder, and this workspace had no `/Shared/strata`. Fix in d39f1fc: `MlflowTracker` makes the folder first, through the workspace client's `mkdirs`, and both backtest scripts pass it (`tests/test_tracking.py`).

**Second run on October 25, 2026 (orchestrator):** 10:17 to 10:20 UTC. The experiment `/Shared/strata/time_estimate` (3069387630686205) was made, the run `time_estimate_backtest 2025` logged (MLflow run ac32115b01cd44dca042bc073f9c23c2) and a `time_estimate model` run beside it. `strata.ops.evaluation_result` holds run `time_estimate_backtest-20261025T101702Z-f5a49d56` with four rows for 2025: `abstention`, `training_packages` 8, `calibration_packages` 2 and `min_calibration_packages` 20. So on the warehouse's data the 2025 backtest had 8 packages to train on and 2 to calibrate on, under the minimum of 20, no model was trained, and nothing was registered: "Registered strata.gold.time_estimate version 1 as champion." was not printed, and `get_model_version_by_alias` has no champion to return. The script then stopped with `NameError: name 'engine' is not defined` in its printing step, a slip from d39f1fc's edit, fixed in the commit that carries this note; the run's rows and MLflow runs are complete. Decision for the user: the training set joins `strata.gold.package` to its first notice, and the warehouse holds notices from 2024 to 2026 only (the search API's 100,000 offset cap, ticket 04's step 2 decision) and plan rows for P156634 and P130164 alone, so the live time estimate has almost no packages with both a first notice and an outcome. Until more notices or more plans are read, the time estimate abstains, as its model card says it should. Step 2 is run next for the record of every year.

**Third run on October 25, 2026 (orchestrator):** 10:32 UTC, exit 2, "The backtest stopped before it finished: BadRequest: The request could not be processed by the warehouse.": the warehouse had reached its free daily limit (ticket 11's step 1, fifth run). The rerun with the fixed script, and step 2, wait for the limit to reset.

The merger parked this step on October 24, 2026, after merge commit e7c6e38. All ten keys were set, but the header above holds workspace steps back while the user runs the backlog. It needs the Databricks keys in `.env`. This merge adds the table `strata.ops.evaluation_result`, so first deploy from e7c6e38 or later with ticket 04's command, `uv run --script ops/bundle/deploy.py --env-file .env`, which must list `strata.ops.evaluation_result` as new and change no existing table. Run this step after that deploy and after a nightly run has filled gold and silver (ticket 04's step 2, `uv run --script ops/bundle/check.py job-run --env-file .env`). The merge already ran the builder's local step: `scripts/install` exited 0 and `uv run --frozen python -c 'import xgboost'` exited 0 (xgboost 3.4.1).

Run this from the main checkout:

    uv run --script ops/estimates/backtest_live.py --env-file .env --years 2025

It worked if it exits 0 and prints the 2025 line with an MLflow run id, "Registered strata.gold.time_estimate version 1 as champion.", the track-record sentence, the model card's coverage section, and "Run time_estimate_backtest-... is in strata.ops.evaluation_result. It took N seconds." Each package the year had not seen calls find_comparables once on the warehouse, so note N before step 2. Then (criterion 4, Unity Catalog half): `MlflowClient().get_model_version_by_alias("strata.gold.time_estimate", "champion")` returns a version, that version's run holds `model_card.md`, and its description gives the track-record sentence.

## Ticket 25, step 2 of 2: backtest 2021 to 2025 on the workspace

The merger parked this step on October 24, 2026, after merge commit e7c6e38. It needs the Databricks keys in `.env`. Run it after step 1, and only if step 1's year took a reasonable time.

Run this from the main checkout:

    uv run --script ops/estimates/backtest_live.py --env-file .env

It worked if it exits 0 and prints five test-year lines, 2021 to 2025, each with its own MLflow run id, then the track-record sentence and the card's coverage section (criterion 2). Then this query:

    SELECT segment, measure, value, mlflow_run_id FROM strata.ops.evaluation_result
    WHERE scorer = 'time_estimate_backtest' AND segment_kind = 'test_year'
      AND measure IN ('coverage', 'width_80_months', 'error_past_range_months', 'error_plan_months')

must return rows for 2021 to 2025, and each `mlflow_run_id` must be a run in the experiment `/Shared/strata/time_estimate`. Criterion 3, workspace half: the `model_card.md` this run logged has a line for each test year, and each year outside 75 to 85 percent gives its gap and a cause sentence (or "The stored results do not show the cause."). This run registers version 2 as challenger, because version 1 from step 1 already holds champion, and the champion's card lists only 2025. Moving champion to version 2 is the user's call; ticket 25's merge comment names it.

## Ticket 21, step 1 of 4: deploy the baseline tables and the Summary's two silver tables

**Ran on October 25, 2026 (orchestrator).** `ops/bundle/deploy.py --fairshare-catalog workspace` from 106c7da, twice. The first run exited 0 and listed five new tables and no changed one: `strata.ops.plan_baseline_steps`, `strata.ops.plan_baselines`, `strata.silver.project_environment`, `strata.silver.project_sectors`, and ticket 25's `strata.ops.evaluation_result`. The second printed "No changes." The column query returned the four rows (ops.plan_baseline_steps, ops.plan_baselines, silver.project_environment, silver.project_sectors). Passed. `SELECT count(*) FROM strata.silver.project_sectors WHERE project_id = 'P130164'` returned 0 at 10:08 UTC, before any nightly run since the deploy; it is checked again after the next run.

The merger parked this step on October 24, 2026, after merge commit d596000. All ten keys were set, but the header above holds workspace steps back while the user runs the backlog. It needs the Databricks keys in `.env`. It is ticket 04's deploy command, and one deploy from d596000 or later also serves ticket 25's step 1, which needs a deploy from e7c6e38 or later.

Run this from the main checkout, twice:

    uv run --script ops/bundle/deploy.py --env-file .env

It worked if both runs exit 0. The first run lists these four tables as new and changes no existing table: `strata.ops.plan_baselines` and `strata.ops.plan_baseline_steps` (the baseline), and `strata.silver.project_sectors` and `strata.silver.project_environment` (the Summary's sectors and its environmental category or ESF risk). The second run prints "No changes." Then run this in the workspace's SQL editor:

    SELECT table_schema, table_name FROM strata.information_schema.columns
    WHERE column_name = 'public_from'
      AND table_name IN ('plan_baselines', 'plan_baseline_steps', 'project_sectors', 'project_environment')

It must return four rows (ADR 0002). The builder named `ops/bundle/check.py same-rows` as the proof, but that command compares ground-truth queries and lists no tables, so this query takes its place. After the next nightly run (ticket 04's `uv run --script ops/bundle/check.py job-run --env-file .env`), `SELECT count(*) FROM strata.silver.project_sectors WHERE project_id = 'P130164'` must return more than 0, because the bronze_to_gold task's projects transform fills both silver tables. If it returns 0, tell the orchestrator before anyone shows the Summary on the App.

## Ticket 21, step 2 of 4: a staff viewer saves a baseline on the deployed App

The merger parked this step on October 24, 2026, after merge commit d596000. It needs the Databricks keys in `.env`. Run it after step 1, and after ticket 09's step 1 has turned on user authorization, because the App writes the baseline with the viewer's own token (`src/strata/server/baseline.py`; criterion 7, live half). Viewers already read `strata.ops` through the bundle's `USE_SCHEMA, SELECT` grant to `account users`. Saving also needs MODIFY on the two tables, and no file grants it yet (ticket 21's done comment names this), so run this once in the workspace's SQL editor, as a user who owns the `strata` catalog:

    GRANT MODIFY ON TABLE strata.ops.plan_baselines TO `account users`;
    GRANT MODIFY ON TABLE strata.ops.plan_baseline_steps TO `account users`;
    SHOW GRANTS ON TABLE strata.ops.plan_baselines;

It worked if `SHOW GRANTS` lists MODIFY for `account users`. Run `SHOW GRANTS` again after any later bundle deploy. Then deploy the App from d596000 or later, so it serves ticket 21's routes. Ticket 06's step 1 and ticket 15's step 3 run the same command, and one deploy from d596000 or later serves them all:

    uv run --script ops/app/deploy_app.py --env-file .env

It worked if the deploy exits 0 and its last line is `Strata is running at https://...`. Then sign in to the App in a browser as a World Bank staff viewer:

1. Open `<App url>/projects/P156634/procurement/northern-water-works-development-agency/2025-07-21` to check NWWDA's plan of July 21, 2025.
2. Choose "Save as the baseline".
3. Open `<App url>/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09`.

It worked if the panel says "I saved the plan of July 21, 2025 as the baseline. The reasons below now also give delay against it."; the October 9, 2026 check names the plan of July 21, 2025 as the baseline and gives a late activity's delay both ways, each labeled ("... days after its first published planned date" and "That was ... days after its baseline date of ..."); and this query returns one row, with `plan_date` 2025-07-21 and your own user id in `saved_by`:

    SELECT project_id, agency_id, plan_date, saved_by, saved_at FROM strata.ops.plan_baselines
    WHERE project_id = 'P156634' AND agency_id = 'northern-water-works-development-agency'

If the save answers 403 with the code `permission`, the grant above did not reach your account.

## Ticket 21, step 3 of 4: the Summary's Fast 3G budget through the Databricks Apps proxy

The merger parked this step on October 24, 2026, after merge commit d596000. It needs the App deployed from d596000 or later (step 2). It is a measurement in your own browser, so it has no command (criterion 9, live half). On the local server the verifier measured 3.50 s cold, 0.80 s from another tab and a 10,087-byte Summary; the proxy adds its own time.

In Chrome, signed in to the App:

1. Open DevTools, then its Network tab. Set throttling to "Fast 3G" and tick "Disable cache".
2. Open `<App url>/projects/P130164` and note the time until the Summary's facts show. That is the cold load.
3. Untick "Disable cache", keep "Fast 3G", and open the same address in a new tab. Note the time again. That is the load from another tab.

It worked if the Summary showed in 5 s or less cold and in 2 s or less from another tab, and the Network tab shows `GET /api/projects/P130164/summary` once, with at most 15 KB transferred, and no request to `POST /api/ask`. If a budget is missed, note both times and tell the orchestrator. The budgets are brief 21's decision 11.

## Ticket 21, step 4 of 4: time All projects' search on the workspace

The merger parked this step on October 24, 2026, after merge commit d596000. It needs the App deployed from d596000 or later (step 2). All projects filters the project list in Python on each search (`src/strata/server/projects.py`), and the fixture holds only 93 projects, so how fast it is on the workspace's full list is not known yet (review round 3, item 9).

In Chrome, signed in to the App, with no throttling, open `<App url>/api/projects?q=ind` three times and read each request's time in DevTools' Network tab.

It worked if each answer took under 1 s and counts the projects whose name, ID or country holds "ind", India's among them. If any took 1 s or more, tell the orchestrator, who files a ticket to move the search into a SQL filter in `src/strata/server/sql/projects/`.

## Ticket 30, step 1 of 2: sync the agent, since get_lessons changed

The merger parked this step on October 24, 2026, after merge commit 7da272f. All ten keys were set, but the header above holds workspace steps back while the user runs the backlog. It needs the four Foundry keys in `.env`. Ticket 30 changed get_lessons' description and parameters in `config/tools.toml` (it now counts the completion reports behind each risk factor), and the agent's tool list is generated from that file, so the orchestrator agent in Foundry is out of date until this runs. Ticket 13's sync runs the same command, and one sync from 7da272f or later serves every block that names it.

Run this from the main checkout:

    uv run --script ops/agent/sync.py --env-file .env
    uv run --script ops/agent/sync.py --env-file .env --check

It worked if the first run ends "I made version N of strata-orchestrator, which matches the repo." and the `--check` run exits 0 (it exits 1 when it still finds a difference, and 2 when it could not run).

## Ticket 30, step 2 of 2: section 3, procurement risks and what helped, on the deployed App

The merger parked this step on October 24, 2026, after merge commit 7da272f. It needs the Databricks keys in `.env`. Run it after step 1, and after ticket 15's step 3, which starts the Lakebase instance. It is ticket 06's deploy command, and one deploy from 7da272f or later serves every block that names it. This merge adds the routes `GET /api/packages/{step_reference}/risks` and `PUT /api/packages/{step_reference}/risk-selection`, the same two under `/api/planned-packages/{package_id}/`, and the Lakebase table `strata.app.risk_selections`, which the App makes the first time a viewer selects a risk.

Run this from the main checkout:

    uv run --script ops/app/deploy_app.py --env-file .env

It worked if the deploy exits 0, its step 3 prints "The Lakebase instance strata-state is running, so the app keeps app state there.", and its last line is `Strata is running at https://...`. Then sign in to the App in a browser and open `<App url>/packages/KE-NWWDA-541055-CW-RFB`.

It worked if section 3, "Procurement risks and what helped", loads under the eyebrow "Planning · PPSD section 3", and DevTools' Network tab shows `GET /api/packages/KE-NWWDA-541055-CW-RFB/risks` answering 200. Until decided lessons and a comparable project with an ICR exist on the workspace, the section may show its empty state (no completion report, or no decided lessons), and that still passes this step. Once a row shows, tick its checkbox, wait for the save, and reload: the row must still be ticked. The first save makes `strata.app.risk_selections` in the App's Lakebase database, with one row for you, that package and that risk, and `selected` true. Unticking sets `selected` to false and deletes nothing (criterion 6, live half).

## Ticket 24, step 1 of 4: re-record check 4's judge from the live model

The merger parked this step on October 24, 2026, after merge commit c7d226a. All ten keys were set, but the header above holds workspace steps back while the user runs the backlog. It needs `FOUNDRY_PROJECT_ENDPOINT`, `DATABRICKS_HOST`, `DATABRICKS_WAREHOUSE_ID`, `DATABRICKS_TOKEN`, `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` in `.env`, and `az` signed in. Run it after ticket 13's step 4, because the judge is asked about the recorded answers. Every file in `tests/fixtures/agent/judged/` is hand-written today and reads `"recorded": false`, including the two that ticket 24's round 3 added, `p156634-plan-not-yet-public.json` and `p156634-uncited-blame.json`.

Run this from the main checkout, then review the diff and run the gate:

    uv run --script ops/agent/record.py --judge --env-file .env
    git diff tests/fixtures/agent/judged
    .githooks/pre-commit

It worked if the recording exits 0, every `tests/fixtures/agent/judged/*.json` reads `"recorded": true`, and the gate still passes, so every case keeps its removals (criterion 1, live half). In `p156634-uncited-blame.json`, the live judge must keep the abstention sentence and remove "The agency was late in publishing its plan." If it passes, commit the recordings on a branch. If a case loses a removal its test expects, the live judge answers differently from the hand-written file, so tell the orchestrator before you change a test.

## Ticket 24, step 2 of 4: sync the agent, since its instructions changed

The merger parked this step on October 24, 2026, after merge commit c7d226a. It needs the four Foundry keys in `.env`. Ticket 24 added the refusal list ("What you turn down") and the rule that every sentence cites a source to `src/strata/agent/orchestrator.md`, so the orchestrator agent in Foundry is out of date until this runs. Ticket 13's and ticket 30's syncs run the same command. One sync from c7d226a or later serves every block that names it, and a sync from an earlier commit does not serve this one.

Run this from the main checkout:

    uv run --script ops/agent/sync.py --env-file .env
    uv run --script ops/agent/sync.py --env-file .env --check

It worked if the first run ends "I made version N of strata-orchestrator, which matches the repo." and the `--check` run exits 0 (it exits 1 when it still finds a difference, and 2 when it could not run).

## Ticket 24, step 3 of 4: the must-refuse set through the live agent

The merger parked this step on October 24, 2026, after merge commit c7d226a. Run it after step 2, so the live agent has the refusal list. It needs `FOUNDRY_PROJECT_ENDPOINT`, `DATABRICKS_HOST`, `DATABRICKS_WAREHOUSE_ID` and `DATABRICKS_TOKEN` in `.env`, and `az` signed in. With `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` set too, it also runs the judge. It asks each of the ten questions of kind `refusals` in `evals/benchmark.yaml` through the same route and stream the App runs.

Run this from the main checkout:

    uv run --script ops/agent/refuse_live.py --env-file .env

It worked if it prints ten lines, one per question, and exits 0, with no refusal problem on any line and no restricted value (a notice's contact name, email or phone number, or an individual consultant's supplier id) in any stream (criterion 4, live half). It exits 1 when a refusal does not hold, and 2 when it could not run.

## Ticket 24, step 4 of 4: the judge and the ISR 7 disagreement on the deployed App

The merger parked this step on October 24, 2026, after merge commit c7d226a. It needs the Databricks keys, the four Foundry keys, and `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` in `.env`. Run it after step 2, and after ticket 20's steps, so ISR 7 and ICR paragraph 78 are on the workspace. It is ticket 06's deploy command, and one deploy from c7d226a or later serves every block that names it. From this merge on, the deploy gives the App the judge's two keys. Without them, the App removes every sentence that needs the judge.

Run this from the main checkout:

    uv run --script ops/app/deploy_app.py --env-file .env

It worked if the deploy exits 0 and its last line is `Strata is running at https://...`. Then sign in to the App in a browser, scope it to P130164, and ask "How did the status reports rate P130164's progress towards its development objective in 2016?"

It worked if DevTools' Network tab shows the `/api/ask` stream's checks event carrying a `judge` object, and the ICR paragraph 78 card appears under ISR 7's sentence with both sides: ISR 7 (August 26, 2016, "Satisfactory") and ICR paragraph 78 (October 10, 2019), marked "Two reports disagree".

## Ticket 31, step 1 of 3: re-record the criteria reader from the live model

The merger parked this step on October 25, 2026, after merge commit 27cf144. All ten keys were set, but the header above holds workspace steps back while the user runs the backlog. It needs `FOUNDRY_PROJECT_ENDPOINT`, `DATABRICKS_HOST`, `DATABRICKS_WAREHOUSE_ID` and `DATABRICKS_TOKEN` in `.env`, and `az` signed in. Section 5, "Check your criteria", sends pasted qualification criteria to a new Foundry agent, `strata-criteria-reader` (`config/agents.toml`, `[agents.criteria_reader]`). Its six answers in `tests/fixtures/agent/recorded/criteria-*.json` were written by hand and say `"recorded": false`.

Run this from the main checkout, in this order:

    uv run --script ops/agent/sync.py --env-file .env --agent criteria_reader
    uv run --script ops/agent/sync.py --env-file .env --agent criteria_reader --check
    uv run --script ops/agent/record.py --env-file .env --criteria
    uv run --frozen python tests/record_criteria_api.py
    .githooks/pre-commit

It worked if the sync ends "I made version N of strata-criteria-reader, which matches the repo." (or says the agent already matches the repo) and its `--check` run exits 0; every file in `tests/fixtures/agent/recorded/criteria-*.json`, including the new `criteria-swapped-reading.json`, says `"recorded": true`; and the gate passes, which includes `tests/test_check_criteria.py`. Also check the new files by eye: `criteria-live-tender.json` still refuses with the key `live_tenders`, and every item in `criteria-similar-experience.json` has a `reading` (verify note O1 in `.notes/31-verify-r3.md`).

## Ticket 31, step 2 of 3: re-record check 4's judge on section 5's readings

The merger parked this step on October 25, 2026, after merge commit 27cf144. All ten keys were set, but the header above holds workspace steps back while the user runs the backlog. Run it after step 1, since the judge is asked about the recorded readings. It needs the keys of step 1 and `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY`. From this merge on, the judge run also replays every case in `tests/fixtures/agent/criteria.toml` through section 5's comparison. Ticket 24's step 1 runs the same command, and one run from 27cf144 or later serves both blocks.

Run this from the main checkout:

    uv run --script ops/agent/record.py --judge --env-file .env
    uv run --frozen python tests/record_criteria_api.py
    .githooks/pre-commit

It worked if `tests/fixtures/agent/judged/criteria-similar-experience.json`, `criteria-partial-refusal.json` and `criteria-swapped-reading.json` say `"recorded": true`, the swapped reading is still judged not to follow (if the live judge lets it through, replace that case's reading in `tests/fixtures/agent/criteria.toml` with one the judge rejects and run steps 1 and 2 again), and the gate passes after `tests/record_criteria_api.py` re-records.

## Ticket 31, step 3 of 3: section 5 on the deployed App keeps pasted text private

The merger parked this step on October 25, 2026, after merge commit 27cf144, from the verifier's live follow-ups. All ten keys were set, but the header above holds workspace steps back while the user runs the backlog. It needs the Databricks keys, the four Foundry keys, and `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` in `.env`. Run it after steps 1 and 2. It is ticket 06's deploy command, and one deploy from 27cf144 or later serves every block that names it.

Run this from the main checkout:

    uv run --script ops/app/deploy_app.py --env-file .env

It worked if the deploy exits 0 and its last line is `Strata is running at https://...`. Then sign in to the App as one viewer, open `/packages/KE-CWSB-224323-CS-QCBS`, open section 5, and paste "at least two contracts of similar works of US$10 million each". It worked if the comparison shows its counts under "Asked for it" and "Asked for the same or less", with "Judged by a model" on the check line, the pasted text is in Lakebase's `strata.app.criteria_checks` with that viewer as its owner, and a second viewer's `GET /api/packages/KE-CWSB-224323-CS-QCBS/criteria` shows no comparison and none of the first viewer's words (CLAUDE.md rule 8).

## Ticket 27, step 1 of 2: backtest the planned date for each step for 2025 alone on the workspace

The merger parked this step on October 25, 2026, after merge commit abadca3. All ten keys were set, but the header above holds workspace steps back while the user runs the backlog. It needs the Databricks keys in `.env`. Run it after the live plan run has filled `strata.silver.plan_step_delays` on the warehouse: ticket 08's step 1 (`uv run --script ops/plans/run_live.py --env-file .env`) and ticket 18's run of the slice. It writes to `strata.ops.evaluation_result`, which ticket 25's deploy adds, so run it after that deploy too. Ticket 27 is criterion 1's live half: the offline half passed in `.notes/27-verify-r2.md`.

Run this from the main checkout:

    uv run --script ops/estimates/step_backtest_live.py --env-file .env --years 2025

It worked if it exits 0 and prints the 2025 line with its counts and an MLflow run id, then one line for each step the year scored. Note how long it took before step 2: each step first planned in 2025 calls find_comparables once on the warehouse.

## Ticket 27, step 2 of 2: backtest the planned date for each step for 2021 to 2025 on the workspace

The merger parked this step on October 25, 2026, after merge commit abadca3. It needs the Databricks keys in `.env`. Run it after step 1, and only if step 1's year took a reasonable time.

Run this from the main checkout:

    uv run --script ops/estimates/step_backtest_live.py --env-file .env

It worked if it exits 0 and prints a line for each test year 2021 to 2025, each with its counts and its own MLflow run id (criterion 1). Then this query:

    SELECT segment, measure, value, mlflow_run_id FROM strata.ops.evaluation_result
    WHERE scorer = 'step_dates_backtest' AND measure LIKE '%.n'

must return rows for each test year 2021 to 2025, one `<family>.<step>.n` measure for each step of each family, each with a non-null `mlflow_run_id`, and each of those ids must be a run in the experiment `/Shared/strata/time_estimate` (`config/models.toml`, `experiment`) with the same id the script printed for that year.

## Ticket 32, step 1 of 6: deploy the retrieval loop's tables and the weekly retrieval job

The merger parked this step on October 25, 2026, after merge commit 5909913. All ten keys were set, but the header above holds workspace steps back while the user runs the backlog. It needs the Databricks keys in `.env`. It is ticket 04's deploy command, and one deploy from 5909913 or later serves every block that needs these tables. This workspace's earlier deploys passed `--fairshare-catalog workspace`, so this one does too.

Run this from the main checkout, twice:

    uv run --script ops/bundle/deploy.py --env-file .env --fairshare-catalog workspace

It worked if both runs exit 0. The first run lists these eleven tables as new and changes no existing table: `strata.ops.answer_citations`, `strata.ops.candidate_labels`, `strata.ops.label_decisions`, `strata.ops.retrieval_agreement`, `strata.ops.retrieval_feedback_viewers`, `strata.ops.retrieval_feedback_weekly`, `strata.ops.retrieval_grades`, `strata.ops.retrieval_label_builds`, `strata.ops.retrieval_labels`, `strata.ops.retrieval_pool` and `strata.ops.retrieval_queries`. The job "strata retrieval weekly" (`bundle/retrieval.yml`, Mondays at 06:30 New York time) is on the workspace's Jobs page. The second run prints "No changes."

## Ticket 32, step 2 of 6: redeploy the App, which writes the retrieval loop's rows as itself

The merger parked this step on October 25, 2026, after merge commit 5909913. All ten keys were set, but the header above holds workspace steps back while the user runs the backlog. Run it after step 1, so the tables exist to grant. It needs the Databricks keys in `.env`. It is ticket 06's deploy command, and one deploy from 5909913 or later serves every block that names it. From this merge on, the deploy grants the App's service principal SELECT and MODIFY on `strata.ops.retrieval_queries`, `candidate_labels`, `label_decisions`, `answer_citations` and `retrieval_grades` (`ops/app/deploy_app.py`, `RETRIEVAL_TABLES`).

Run this from the main checkout:

    uv run --script ops/app/deploy_app.py --env-file .env

It worked if the deploy exits 0 and its last line is `Strata is running at https://...`, and `SHOW GRANTS ON TABLE strata.ops.retrieval_queries` on the SQL warehouse lists the App's service principal with SELECT and MODIFY. The same query on the other four tables shows the same two grants.

## Ticket 32, step 3 of 6: run the weekly retrieval job once by hand

The merger parked this step on October 25, 2026, after merge commit 5909913. Run it after step 1, and after the documents run has filled `strata.gold.passage` on the warehouse (ticket 11's `uv run --script ops/documents/run_live.py --env-file .env`). It needs the Databricks keys in `.env`. Its first scheduled run is the next Monday at 06:30 New York time. Start it by hand instead with "Run now" on the Jobs page, or from the repo root:

    databricks bundle run retrieval_weekly

It worked if the run succeeds and this query on the SQL warehouse gives a row for each query set (criterion 1, workspace half):

    SELECT query_set, queries, labels, documents FROM strata.ops.retrieval_label_builds ORDER BY built_at DESC

The two silver sets read 12 queries, 13 labels and 1 document for `icr_review_citations`, and 2, 7 and 2 for `pad_lessons`, if the workspace holds the fixture's documents, or more if the documents run read more. `notice_queries` and `feedback` read 0 until step 4 and later reviews add to them.

## Ticket 32, step 4 of 6: load the queries written from award notices, with their pools

The merger parked this step on October 25, 2026, after merge commit 5909913. Run it after steps 1 to 3, and after the documents run has synced the AI Search index (ticket 11's step that runs `ops/documents/run_live.py`). It needs `DATABRICKS_HOST`, `DATABRICKS_WAREHOUSE_ID`, `DATABRICKS_TOKEN`, `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` in `.env`. It runs as a person's token, because the weekly job's own identity has no AI Search token.

Run this from the main checkout:

    uv run --script ops/retrieval/evaluate_live.py --env-file .env --load-queries

It worked if it prints how many queries it loaded (3, from `evals/retrieval_queries.toml`), and `strata.ops.retrieval_queries` and `strata.ops.retrieval_pool` hold their rows. Then, once `config/roles.toml` maps `strata-query-judges` to real people and the App is deployed again with them (step 2's command), a query judge's first grade on one of these queries answers 200 on the App, not 403 permission.

## Ticket 32, step 5 of 6: measure retrieval live

The merger parked this step on October 25, 2026, after merge commit 5909913. Run it after step 4. It needs the keys of step 4. It ranks with AI Search's hybrid query and its reranker, logs each query set's run to the MLflow experiment `/Shared/strata/retrieval` (the tracker makes the folder first, as d39f1fc added), and appends its rows to `strata.ops.evaluation_result`, which ticket 25's deploy added.

Run this from the main checkout:

    uv run --script ops/retrieval/evaluate_live.py --env-file .env

It worked if it exits 0 and prints precision at 10, recall at 20 and nDCG at 10 for each query set, with the run id, and this query returns the three measures for each query set (criterion 2, workspace half):

    SELECT segment, measure, value FROM strata.ops.evaluation_result
    WHERE scorer = 'retrieval_evaluation' AND run_id = '<the printed run id>'

## Ticket 32, step 6 of 6: the tuning gate blocks a worse setup live

The merger parked this step on October 25, 2026, after merge commit 5909913. Run it after step 5. It needs the keys of step 4.

Run this from the main checkout:

    uv run --script ops/retrieval/evaluate_live.py --env-file .env --gate --no-rerank

It worked if it prints "Held-out set: lost. Hindsight set: not compared. The gate blocks the candidate." and exits 1 (criterion 3, live half). If the labeled set has no held-out query yet, it prints "Held-out set: not compared" and also exits 1, which means step 3 or step 4 has not filled the set.

## Ticket 28, step 1 of 6: deploy the two rebidding tables, then check the label counts after a nightly run

The merger parked this step on October 25, 2026, after merge commit 6044bd4. All ten keys were set, but the Free Edition SQL warehouse reached its free daily limit at 10:33 UTC on October 25, and the header above holds workspace steps back during a merge. It needs the Databricks keys in `.env`. It is ticket 04's deploy command, and one deploy from 6044bd4 or later serves every block that needs these tables. This workspace's earlier deploys passed `--fairshare-catalog workspace`, so this one does too.

Run this from the main checkout:

    uv run --script ops/bundle/deploy.py --env-file .env --fairshare-catalog workspace

It worked if it exits 0, lists `strata.ops.rebidding_labels` and `strata.ops.rebidding_scores` as new, changes no existing table, and `SHOW TABLES IN strata.ops` lists both. Then start the nightly job by hand (or wait for its scheduled run):

    uv run --script ops/bundle/check.py job-run --env-file .env

It worked if the check exits 0 and this query, with that job run's id, returns four rows, `no_award`, `same_reference`, `canceled_row` and `any`, which match `tests/ground_truth/rebidding_label_counts.sql` run on the warehouse with `as_of` set to that day (criterion 1, workspace half):

    SELECT source, count, denominator, as_of FROM strata.ops.rebidding_labels WHERE run_id = '<job run id>'

## Ticket 28, step 2 of 6: backtest the rebidding models for 2025 alone on the workspace

The merger parked this step on October 25, 2026, after merge commit 6044bd4. The warehouse limit and the header above held it back. It needs the Databricks keys in `.env`. Run it after step 1, which adds `strata.ops.rebidding_scores`, and after ticket 25's deploy, which added `strata.ops.evaluation_result`. Each package it tests calls rebidding_risk once on the warehouse, so time this one year before step 3. Ticket 25's live run found few packages on the warehouse with both a first notice and an outcome, so this run may also train no model.

Run this from the main checkout:

    uv run --script ops/estimates/rebidding_backtest_live.py --env-file .env --years 2025

It worked if it exits 0 and prints a 2025 line with the packages tested and the Brier score and calibration error for gbm, logistic and the baseline, with its MLflow run id. Then it prints "The better calibrated model is ... Registered strata.gold.rebidding_risk version N as champion." and "Run ... is in strata.ops.evaluation_result." If the warehouse had too few decided packages, it prints "No champion was trained, so none was registered. The model card says why." instead. Either way the model card states the results, whether or not the model beat its baseline. Note how long it took before step 3.

## Ticket 28, step 3 of 6: backtest the rebidding models for 2021 to 2025 on the workspace

The merger parked this step on October 25, 2026, after merge commit 6044bd4. It needs the Databricks keys in `.env`. Run it after step 2, and only if step 2's year took a reasonable time.

Run this from the main checkout:

    uv run --script ops/estimates/rebidding_backtest_live.py --env-file .env

It worked if it exits 0 and prints one line for each test year 2021 to 2025, each with its own MLflow run id, and this query returns, for each test year, `gbm_brier`, `gbm_calibration_error`, `logistic_brier`, `logistic_calibration_error`, `baseline_brier` and `baseline_calibration_error`, each with an MLflow run id (criterion 2, workspace half):

    SELECT segment, measure, value, mlflow_run_id FROM strata.ops.evaluation_result
    WHERE scorer = 'rebidding_backtest' AND segment_kind = 'test_year'

Then `strata.gold.rebidding_risk` in Unity Catalog has a version under the champion alias, and that version's run holds `model_card.md`. The script registers a model as champion only when no version holds that alias yet. So if step 2 registered a champion, this run registers its model as challenger and prints "as challenger". Whether to move the champion alias to this run's version, which was tested on every year, is a decision for the user.

## Ticket 28, step 4 of 6: score the planned packages with the champion, and see the estimate on the deployed App

The merger parked this step on October 25, 2026, after merge commit 6044bd4. Run it after step 3 has registered a champion. It needs the Databricks keys in `.env`. The nightly job's `score` task scores every planned activity with the champion, so run the job by hand (step 1's `job-run` command) or wait for its scheduled run. The route below is new in 6044bd4, so the deployed App must run 6044bd4 or later. If it is older, redeploy it first with `uv run --script ops/app/deploy_app.py --env-file .env` (one deploy from 6044bd4 or later serves every block that names it).

It worked if this query returns one row per planned activity, all with the champion's version:

    SELECT version, learner, count(*) FROM strata.ops.rebidding_scores
    WHERE run_id = '<job run id>' GROUP BY version, learner

and `GET /api/packages/KE-NWWDA-541055-CW-RFB/rebidding` on the deployed App returns `model.shown` true with "about k in 10" only when the stored `beat_baseline` is 1 and there are 20 or more comparable packages. Otherwise it returns `not_better` with the track record, or another `not_shown_reason` (criterion 4, workspace half).

## Ticket 28, step 5 of 6: sync the agent, since rebidding_risk is a new tool

**Ran on October 25, 2026 (orchestrator).** From 23df355. The sync printed "Foundry's agent strata-orchestrator differed from the repo:", a diff with `### rebidding_risk` added to the tools, and "I made version 2 of strata-orchestrator, which matches the repo." The `--check` run exited 0: "Foundry's agent strata-orchestrator, version 2, matches the repo: there is no difference in its model, instructions, tools, description or guardrail (strata-guardrail)." Passed. Step 6 waits for the SQL warehouse, because the agent's tools run their queries there.

The merger parked this step on October 25, 2026, after merge commit 6044bd4. It needs the four Foundry keys in `.env`. Ticket 28 added rebidding_risk to `config/tools.toml`, and the agent's tool list is generated from that file, so the orchestrator agent in Foundry is out of date until this runs. Ticket 13's sync runs the same command, and one sync from 6044bd4 or later serves every block that names it.

Run this from the main checkout:

    uv run --script ops/agent/sync.py --env-file .env
    uv run --script ops/agent/sync.py --env-file .env --check

It worked if the first run ends "I made version N of strata-orchestrator, which matches the repo." and the `--check` run exits 0 (it exits 1 when it still finds a difference, and 2 when it could not run).

## Ticket 28, step 6 of 6: the must-refuse set through the live agent, with rebidding_risk among its tools

The merger parked this step on October 25, 2026, after merge commit 6044bd4. The verify notes (`.notes/28-verify.md`) parked it: the scripted must-refuse set passed in the gate, and the live run needs Foundry. Run it after step 5, so the live agent has the new tool. It needs the keys of ticket 24's step 3. Before the live agent answers questions about rebidding, the verify notes' findings F1 and F2 should be fixed: the verifier removes a true quoted reason, and it can pass a made-up "about k in 10". Both are listed for a follow-up ticket.

Run this from the main checkout:

    uv run --script ops/agent/refuse_live.py --env-file .env

It worked if it prints one line per question of kind `refusals` in `evals/benchmark.yaml` (11 at 6044bd4) and exits 0, with no refusal problem on any line and no restricted value in any stream.

## Ticket 37, step 1 of 6: deploy the follows table

The merger parked this step on October 25, 2026, after merge commit 568dbc0. All ten keys were set, but the header above holds workspace steps back during a merge. It needs the Databricks keys in `.env`. Ticket 37 adds `strata.ops.follows` (`src/strata/lakehouse/tables/ops/follows.sql`): one row each time a World Bank staff viewer follows or unfollows a project. It is ticket 04's deploy command, and one deploy from 568dbc0 or later serves every block that needs this table. This workspace's earlier deploys passed `--fairshare-catalog workspace`, so this one does too.

Run this from the main checkout:

    uv run --script ops/bundle/deploy.py --env-file .env --fairshare-catalog workspace

It worked if it exits 0, lists `strata.ops.follows` as new, changes no existing table, and `SHOW TABLES IN strata.ops` lists `follows`.

## Ticket 37, step 2 of 6: redeploy the App, then a follow survives a restart and a viewer outside the staff role is refused

The merger parked this step on October 25, 2026, after merge commit 568dbc0. It needs the Databricks keys in `.env`, and the four Foundry keys, because the App reaches the mission brief writer through Foundry. Run it after step 1: this deploy grants the App's own service principal SELECT and MODIFY on `strata.ops.follows`, and a grant on a table that does not exist fails. Ticket 06's step 1 runs the same command, and one deploy from 568dbc0 or later serves every block that names it (criterion 5, workspace half).

Run this from the main checkout:

    uv run --script ops/app/deploy_app.py --env-file .env

It worked if the deploy exits 0, its last line is `Strata is running at https://...`, and `SHOW GRANTS ON TABLE strata.ops.follows` in the SQL editor lists SELECT and MODIFY for the App's service principal. Then, signed in to the App as a World Bank staff viewer:

1. Open `<App url>/projects/P156634` and choose "Follow this project". Open `<App url>/projects/following`: P156634's row shows, with its status first.
2. Stop the App and start it again from the workspace's Apps page, then open `<App url>/projects/following` again.

It worked if P156634 is still listed after the restart, and `SELECT viewer_id, project_id, following, changed_at FROM strata.ops.follows WHERE project_id = 'P156634'` shows your row with `following` true. The refusal half needs a workspace identity outside `[staff].groups` in `config/roles.toml`. That list is `["users"]` until ticket 38 narrows it (a parked decision), and every workspace user is in `users`, so until then only an identity outside that group can show it. Such an identity must get HTTP 403 with the code `not_staff` from `GET <App url>/api/following` and from `PUT <App url>/api/projects/P156634/follow`.

## Ticket 37, step 3 of 6: sync the mission brief writer and the orchestrator

The merger parked this step on October 25, 2026, after merge commit 568dbc0. It needs the four Foundry keys in `.env`, and `az` signed in. Ticket 37 adds the Foundry agent `strata-mission-brief-writer` (`config/agents.toml`, `src/strata/agent/instructions/mission_brief_writer.md`). It also adds the tools project_signals and project_records to `config/tools.toml`, and the orchestrator's tool list is generated from that file, so `strata-orchestrator` (version 2, synced from 23df355) is out of date too. The builder named the writer's sync and a plain `--check`, which checks the orchestrator, so this block syncs both. One sync from 568dbc0 or later serves every block that names it.

Run this from the main checkout:

    uv run --script ops/agent/sync.py --env-file .env --agent mission_brief_writer
    uv run --script ops/agent/sync.py --env-file .env --agent mission_brief_writer --check
    uv run --script ops/agent/sync.py --env-file .env
    uv run --script ops/agent/sync.py --env-file .env --check

It worked if the first run ends "I made version N of strata-mission-brief-writer, which matches the repo.", the third ends "I made version N of strata-orchestrator, which matches the repo.", and both `--check` runs exit 0 and print "Foundry's agent ..., version N, matches the repo: there is no difference in its model, instructions, tools, description or guardrail (strata-guardrail)." Exit 1 means `--check` found a difference, and exit 2 means it could not run.

**Ran on October 25, 2026 (orchestrator), from c0a9db0.** All four passed. The first run made version 1 of `strata-mission-brief-writer`, and its `--check` printed that version 1 matches the repo with no difference in its model, instructions, tools, description or guardrail (strata-guardrail). The plain run found that `strata-orchestrator` version 2 differed in its instructions and its tools (the project_signals and project_records sections were missing) and made version 3, which matches the repo; the plain `--check` confirmed version 3 with no difference. Both checks exited 0. Note for the next catch-up: zsh does not split an unquoted variable into words, so pass the script's flags as separate arguments rather than through a loop variable, or argparse sees one unrecognized argument.

## Ticket 37, step 4 of 6: re-record the mission brief from the live writer

The merger parked this step on October 25, 2026, after merge commit 568dbc0. Run it after steps 1 and 3, and after the nightly job has filled the plans, awards, ISR ratings and loan history on the warehouse, because the writer drafts from project_records' rows, read as you. It needs `FOUNDRY_PROJECT_ENDPOINT`, `DATABRICKS_HOST`, `DATABRICKS_WAREHOUSE_ID` and `DATABRICKS_TOKEN` in `.env`, and `az` signed in. It re-records every writer case in `tests/fixtures/agent/writers.toml`, so it also serves ticket 35's step 2 (criterion 6, live half).

Run this from the main checkout, then review the diff:

    uv run --script ops/agent/record.py --env-file .env --writers
    git diff tests/fixtures/agent

It worked if the recording exits 0 and prints a diff for `tests/fixtures/agent/recorded/mission-brief-p156634.json` with the verifier's counts, and that file's `"recorded"` changes from `false` to `true`. Read the diff before you keep it: it must hold the five parts (plans, awards, ratings, disbursement, closing), each sentence citing a record project_records returned, every amount taken from a `_millions` column (such as `signed_millions` or `estimated_millions`), and no sentence removed. The screens play answers made from this recording, so write them again and run the gate:

    uv run --frozen python tests/record_following_api.py
    git diff tests/fixtures/api
    uv run --frozen pytest tests/test_mission_brief.py
    .githooks/pre-commit

`tests/test_mission_brief.py` and the gate must pass. If they pass, commit the recordings on a branch. If a test no longer gets what it expects, the live writer answers differently from the hand-written brief, so tell the orchestrator before you change a test.

## Ticket 37, step 5 of 6: replay the signals on the full slice for the track record

The merger parked this step on October 25, 2026, after merge commit 568dbc0. It needs the Databricks keys in `.env`. Run it after ticket 25's deploy, which made `strata.ops.evaluation_result`, and after the nightly job has filled the loan history, the plans and the ISRs on the warehouse. It replays project_signals on each of the thresholds file's `signals.track_record_dates`, so it calls the warehouse many times; note how long it took (criterion 4, live half).

Run this from the main checkout:

    uv run --script ops/signals/replay_live.py --env-file .env

It worked if it exits 0, prints "Replayed on <dates>, N projects, MLflow run <id>." and one line per status, "<status>: k of n projects later extended their closing date.", and this query returns that run's rows:

    SELECT run_id, segment_kind, segment, measure, value, mlflow_run_id FROM strata.ops.evaluation_result
    WHERE scorer = 'signals_track_record' ORDER BY ran_at DESC

Then, with the App deployed from 568dbc0 or later (step 2), `GET <App url>/api/following` as a staff viewer must return a `track_record` with that run's `run_id` and the same k and n for each status, and the Following page must state them instead of "I haven't replayed these checks on past dates yet". Exit 2 means the replay could not run, and it prints why.

## Ticket 37, step 6 of 6: a mission brief through the live writer on the deployed App

The merger parked this step on October 25, 2026, after merge commit 568dbc0. Run it after steps 2, 3 and 4. It is a check in your own browser, so it has no command.

Signed in to the App as a World Bank staff viewer, open `<App url>/projects/following` and choose "Add to mission brief" on P156634's row.

It worked if the writing page shows its steps, then the draft opens with its five parts in order (plans, awards, ratings, disbursement, closing), each with its sentences, its table and its citation markers, and the check line removes no sentence for a number or date missing from the records. Every number in a sentence must match the record its marker opens. Choose "Mark as checked", then "Export to Word": the Word file must hold a Heading 2 for each part and one footnote per citation. The nightly job's score task does not run the signals replay yet; ticket 43 adds that, and its own block will say how to check it.

## Ticket 22, step 1 of 2: deploy the edge tables, then relink builds strata.gold.edge at a nightly run

The merger parked this step on October 25, 2026, after merge commit d8bdbb7. All ten keys were set, but the header above holds workspace steps back during a merge. It needs the Databricks keys in `.env`. Ticket 22 adds three tables: `strata.gold.edge` (every link between strata, `src/strata/lakehouse/tables/gold/edge.sql`), `strata.silver.contract_passage_links` and `strata.silver.notice_bids`. The nightly job's `relink` task rebuilds the edge table (`strata.knowledge.links`), so the tables must exist first. Ticket 37's step 1 runs the same deploy command, and one deploy from d8bdbb7 or later serves both. The relink has live inputs only once ticket 43 lands. It scores contracts against passages, so the warehouse must hold P130164's contracts and its ICR's passages (ticket 11's `ops/documents/run_live.py`) before the check below can find the showcase edge. The scorer's word lists moved into `config/thresholds.toml` [links] with the same values, so links already scored do not change.

Run this from the main checkout:

    uv run --script ops/bundle/deploy.py --env-file .env --fairshare-catalog workspace

It worked if it exits 0, lists `strata.gold.edge`, `strata.silver.contract_passage_links` and `strata.silver.notice_bids` as new, and changes no existing table.

Then wait for the next scheduled run of the nightly job (`bundle/nightly.yml`), or start one by hand and check it:

    uv run --script ops/bundle/check.py job-run --env-file .env

It worked if `relink` succeeded in that run, this query returns a count above 0:

    SELECT count(*) FROM strata.gold.edge WHERE kind = 'appeared_together'

and this one returns 0, because no link may be public before both of its ends are (ADR 0002):

    SELECT count(*) FROM strata.gold.edge AS e
    JOIN strata.gold.contract AS c ON e.from_id = concat('strata.gold.contract:', c.contract_id)
    JOIN strata.gold.passage AS p ON e.to_id = concat('strata.gold.passage:', p.passage_id)
    WHERE e.kind = 'appeared_together' AND (e.public_from < c.public_from OR e.public_from < p.public_from)

On the fixture the first query returns 1,169 and the second returns 0. Once P130164's records are on the warehouse, `SELECT score, score_project, score_sector, score_time, score_text, score_mentions FROM strata.gold.edge WHERE from_id = 'strata.gold.contract:OP00044090' AND to_id = 'strata.gold.passage:31525018/v1/54'` should return one row: 0.53, made of 0.10, 0.10, 0.11, 0.02 and 0.20, as on the fixture.

## Ticket 22, step 2 of 2: the four-hop recursive SQL on the SQL warehouse

The merger parked this step on October 25, 2026, after merge commit d8bdbb7. It needs the Databricks keys in `.env`. Run it after step 1, once `strata.gold.edge` on the warehouse holds the path from AMIT CONSTRUCTION through contract OP00044090 and project P130164 to ICR paragraph 31525018/v1/54. Criterion 2 is already proved on DuckDB in the gate. This step checks that the warehouse runs the same `WITH RECURSIVE` query.

First change line 17 of `tests/ground_truth/four_hop_supplier_to_completion_report.sql` from `-- engines: duckdb` to `-- engines: duckdb, databricks`, so `same-rows` picks it up. Then run this from the main checkout:

    uv run --script ops/bundle/check.py same-rows --env-file .env

It worked if it exits 0 and reports that DuckDB and the SQL warehouse returned the same one row for `four_hop_supplier_to_completion_report.sql`: AMIT CONSTRUCTION, OP00044090, P130164, 31525018, 31525018/v1/54, 4. Then commit the changed engines line on a branch and run the gate. If the warehouse rejects `WITH RECURSIVE`, change the line back to `-- engines: duckdb`, and write the warehouse's error message here and in the file's header comment.

## Ticket 34, step 1 of 4: deploy the hindsight test's four tables

The merger parked this step on October 25, 2026, after merge commit 2b5e5f9. All ten keys were set, but the header above holds workspace steps back during a merge. It needs the Databricks keys in `.env`. Ticket 34 adds four tables under `src/strata/lakehouse/tables/ops/`: `strata.ops.hindsight_codings` (each coder's reading of an ICR or ICR Review), `strata.ops.hindsight_blamed` (each project's reconciled blamed risks), `strata.ops.hindsight_agreement` (each pair of coders' agreement) and `strata.ops.exposed_projects` (empty until ticket 44 writes it). Tickets 37 and 22 run the same deploy command, and one deploy from 2b5e5f9 or later serves every block that names it. This workspace's earlier deploys passed `--fairshare-catalog workspace`, so this one does too.

Run this from the main checkout:

    uv run --script ops/bundle/deploy.py --env-file .env --fairshare-catalog workspace

It worked if it exits 0, lists `strata.ops.hindsight_codings`, `strata.ops.hindsight_blamed`, `strata.ops.hindsight_agreement` and `strata.ops.exposed_projects` as new, changes no existing table, and `SHOW TABLES IN strata.ops` lists all four.

## Ticket 34, step 2 of 4: see the hindsight test's gate set

The merger parked this step on October 25, 2026, after merge commit 2b5e5f9. It needs the Databricks keys in `.env`. Run it after step 1, and after a nightly run has filled gold and silver with the pilot projects' documents. It only reads.

Run this from the main checkout:

    uv run --script ops/hindsight/code.py --env-file .env status

It worked if it exits 0 and prints "Pilot projects with an ICR on <date>: N. The hindsight test replays 0.", with N near PLAN.md's 49, then lists each project as waiting ("not coded yet" or "ICR not read yet"), and lists any project left out with its reason (an extraction example, or exposed to Strata).

## Ticket 34, step 3 of 4: two people code the blamed risks (a human step)

The merger parked this step on October 25, 2026, after merge commit 2b5e5f9. It needs the Databricks keys in `.env`, and two people. It waits on docs/STATUS.md decision 5 (labeling time), which must name the two coders, or accept model-drafted codings that you spot-check. Run it after step 2. N in the hindsight test rises above zero only after this step.

For each project that step 2 lists, each of the two coders reads the ICR on their own and runs this from the main checkout, with the blamed risk factors' keys from the closed list in `config/lessons.toml`:

    uv run --script ops/hindsight/code.py --env-file .env code --project P123456 --coder <email> --name "<name>" --blamed <keys, separated by commas>

Where the two differ, one person reads the ICR Review on the factors they differ on and runs:

    uv run --script ops/hindsight/code.py --env-file .env review --project P123456 --coder <email> --name "<name>" --blamed <keys>

Then:

    uv run --script ops/hindsight/code.py --env-file .env reconcile

It worked if each `code` and `review` run exits 0, and `reconcile` exits 0 and prints "Reconciled N projects", one line per project still waiting, and one agreement line per pair of coders, with Cohen's kappa once they have 20 pairs of answers (`retrieval.min_pairs` in `config/thresholds.toml`). A project with no ICR Review keeps only what both coders blamed (a parked decision).

## Ticket 34, step 4 of 4: run the release gate live (criteria 6 and 7, live)

The merger parked this step on October 25, 2026, after merge commit 2b5e5f9. It needs the Databricks keys in `.env`, and MLflow on the workspace. Run it after step 1. Before step 3 it exits 3, because there are no blamed risks to compare yet; run it again after step 3, when it exits 0 or 1.

Run this from the main checkout:

    uv run --script ops/hindsight/release_gate.py --env-file .env --release 2026.11

It worked if it prints the gate-set line, one line per replayed project with its MLflow run id, the report sentence ("I expected 49 pilot projects ... and could use N" when it found fewer), the gate's verdict, and "Run hindsight_test-... is in strata.ops.evaluation_result, with the release's MLflow run ...". The runs must appear in the `/Shared/strata/hindsight_test` experiment, and this query, with the run id it printed, must return the release's rows, including `hindsight_recall` with its "X of Y" text (criterion 7):

    SELECT segment_kind, segment, measure, value, value_text, mlflow_run_id FROM strata.ops.evaluation_result WHERE scorer = 'hindsight_test' AND run_id = '<run id>' ORDER BY segment_kind, segment, measure

Before step 3, N is reported as 0 of 49 and the command exits 3 ("no blamed risks to compare yet"). After step 3 it exits 0 when the run passed and became the champion, or 1 when the gate blocks the release.
