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

It worked if both runs exit 0. The first run lists the catalog, the four schemas, `strata.bronze.files`, `strata.ops.pipeline_runs`, the grants and the job as new. The second run prints "No changes.". Each run also prints "fairshare's catalog lists the same before and after the deploy: ..." (criteria 1 and 7). If fairshare's catalog has another name, add `--fairshare-catalog <name>`.

## Ticket 04, step 2 of 4: run the nightly job by hand

The merger parked this step on October 23, 2026, after merge commit 01a7286. Run it after step 1, because the deploy makes the job and `strata.ops.pipeline_runs`.

Run this from the main checkout:

    uv run --script ops/bundle/check.py job-run --env-file .env

It worked if the command exits 0 and prints "Run <id> wrote one row per task to strata.ops.pipeline_runs, in the bundle's order." That means ten rows in the order of `docs/PLAN.md` section 11 (criterion 2).

## Ticket 04, step 3 of 4: the same rows on DuckDB and on the SQL warehouse

The merger parked this step on October 23, 2026, after merge commit 01a7286. Run it after step 2, because `pipeline_runs_columns.sql` reads the table that the job writes.

Run this from the main checkout:

    uv run --script ops/bundle/check.py same-rows --env-file .env

It worked if the command exits 0, and for both `tests/ground_truth/showcase_fiscal_years.sql` and `tests/ground_truth/pipeline_runs_columns.sql` it prints "DuckDB and the SQL warehouse returned the same ... rows, and they are the rows the file expects." (criterion 4).

## Ticket 04, step 4 of 4: record both nightly schedules

The merger parked this step on October 23, 2026, after merge commit 01a7286. Run it after step 2, and after fairshare's nightly job has finished at least one run.

Run this from the main checkout:

    uv run --script ops/bundle/check.py schedules --env-file .env --write

If the name of fairshare's job does not contain "fairshare", add `--fairshare-job <name>`. It worked if the command exits 0 and the `bundle:schedules` block in `bundle/README.md` records both jobs with "- Overlap: none" (criterion 3). Then commit `bundle/README.md` on `build/strata`. If the check finds that the two windows meet, change the hour in `bundle/nightly.yml` and run step 1 again.
