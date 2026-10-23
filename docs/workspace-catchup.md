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
