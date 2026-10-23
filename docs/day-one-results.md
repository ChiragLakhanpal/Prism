# Day-one results

This document records what the day-one tests in PLAN.md section 14 found, and the path the build takes for each one. A later ticket that depends on a test reads its "Chosen path" line, or calls `path_kind()` in `ops/dayone/dayone.py`. Only the wizard and the probes change the marked blocks.

## Run the wizard first

The owner of the Databricks workspace and the Azure subscription runs the wizard first, in their own terminal, from the main checkout:

    bash ops/wizard/strata-setup.sh

The wizard fills `.env`, saves the app's secrets in the Databricks secret scope `strata`, walks through the Azure caps and the budget, and answers tests 6, 7, 8 and 9. Its last stage offers to run the probes, which answer tests 1, 2, 3, 4, 5 and 10 and read the caps behind test 8. To run all the probes later, run this from the main checkout:

    bash ops/dayone/run-probes.sh --env-file .env

Each probe also runs alone, with the command under its test. Every probe writes its result into this document, so commit the document on build/strata after a run.

## Summary

<!-- dayone:summary -->
| Test | What it checks | Status | Chosen path |
|---|---|---|---|
| 1 | The World Bank hosts from a notebook, a job and the app | not run | Default |
| 2 | Foundry and Azure OpenAI from a job | not run | Default |
| 3 | ai_parse_document on a long PAD | not run | Default |
| 4 | An AI Search endpoint and a hybrid index | not run | Default |
| 5 | The Genie conversation API as the token's user | not run | Default |
| 6 | An outside email joins the workspace and opens the app | not run | Default |
| 7 | A personal access token or a service principal | not run | Default |
| 8 | The four models within the subscription's quota | not run | Default |
| 9 | Foundry evaluations after an Entra sign-in | not run | Default |
| 10 | Traces from the app in Application Insights | not run | Default |
<!-- /dayone:summary -->

## Pay-as-you-go

The free Azure credit of about US$197 ends on November 10, 2026. The subscription moves to pay-as-you-go before then (PLAN.md section 2). The last Azure stage of the wizard records who takes this step and when.

<!-- dayone:payg -->
- Step: Move the Azure subscription from the free credit to pay-as-you-go.
- Deadline: Before November 10, 2026, when the free credit ends.
- Who: The subscription owner (the user)
- Status: Not done yet.
- Last updated: never
<!-- /dayone:payg -->

## Azure caps and budget

Budgets only send email, so hard caps stop the spend: a tokens-per-minute limit on each model deployment, and a daily cap on Application Insights. The probe reads each deployment's limit, the budget and its notifications, and the subscription's offer. The caps themselves are set in `ops/dayone/dayone.toml`.

Command: `uv run --script ops/dayone/probe_caps.py --env-file .env`

<!-- dayone:caps -->
- Status: not checked
- Deployments:
  - None checked yet. The command above fills this in.
- Budget: Not checked yet.
- Subscription offer: Not checked yet.
- Last checked: never
<!-- /dayone:caps -->

## The ten tests

### Test 1. The World Bank hosts from a notebook, a job and the app

Free Edition reaches `search.worldbank.org`, `documents1.worldbank.org`, `datacatalogapi.worldbank.org` and `api.worldbank.org` from a notebook, a job and the app.

- If it passes: Ingestion runs in Databricks, and jobs fetch from the World Bank hosts.
- If it fails: A Container Apps job fetches the files and pushes them into the volume.

Command: `uv run --script ops/dayone/probe_hosts.py --env-file .env`

<!-- dayone:test-1 -->
- Status: not run
- Result: Not run yet, because it needs the wizard first.
- Evidence:
  - None yet. The command above fills it.
- Chosen path: Default, until a result says otherwise. Ingestion runs in Databricks, and jobs fetch from the World Bank hosts.
- Last run: never
<!-- /dayone:test-1 -->

### Test 2. Foundry and Azure OpenAI from a job

Free Edition reaches the Foundry and Azure OpenAI endpoints from a job, not only from the app.

- If it passes: The nightly job calls Foundry and Azure OpenAI directly.
- If it fails: PLAN.md section 14 names no gap fill, so the user decides.

Command: `uv run --script ops/dayone/probe_azure_from_job.py --env-file .env`

<!-- dayone:test-2 -->
- Status: not run
- Result: Not run yet, because it needs the wizard first.
- Evidence:
  - None yet. The command above fills it.
- Chosen path: Default, until a result says otherwise. The nightly job calls Foundry and Azure OpenAI directly.
- Last run: never
<!-- /dayone:test-2 -->

### Test 3. ai_parse_document on a long PAD

`ai_parse_document` runs on a 120-page PAD.

- If it passes: `ai_parse_document` reads route B pages.
- If it fails: Content Understanding `prebuilt-layout` reads route B pages.

Command: `uv run --script ops/dayone/probe_parse_pad.py --env-file .env`

<!-- dayone:test-3 -->
- Status: not run
- Result: Not run yet, because it needs the wizard first.
- Evidence:
  - None yet. The command above fills it.
- Chosen path: Default, until a result says otherwise. `ai_parse_document` reads route B pages.
- Last run: never
<!-- /dayone:test-3 -->

### Test 4. An AI Search endpoint and a hybrid index

An AI Search endpoint and a hybrid index can be created.

- If it passes: Strata's own AI Search endpoint holds a hybrid index of passages.
- If it fails: PLAN.md section 14 names no gap fill, so the user decides.

Command: `uv run --script ops/dayone/probe_ai_search.py --env-file .env`

<!-- dayone:test-4 -->
- Status: not run
- Result: Not run yet, because it needs the wizard first.
- Evidence:
  - None yet. The command above fills it.
- Chosen path: Default, until a result says otherwise. Strata's own AI Search endpoint holds a hybrid index of passages.
- Last run: never
<!-- /dayone:test-4 -->

### Test 5. The Genie conversation API as the token's user

The Genie conversation API answers as the token's user.

- If it passes: The Genie conversation API answers structured questions as the viewer.
- If it fails: PLAN.md section 14 names no gap fill, so the user decides.

Command: `uv run --script ops/dayone/probe_genie.py --env-file .env`

<!-- dayone:test-5 -->
- Status: not run
- Result: Not run yet, because it needs the wizard first.
- Evidence:
  - None yet. The command above fills it.
- Chosen path: Default, until a result says otherwise. The Genie conversation API answers structured questions as the viewer.
- Last run: never
<!-- /dayone:test-5 -->

### Test 6. An outside email joins the workspace and opens the app

An outside email can join the workspace and open the app.

- If it passes: Reviewers join the workspace and open the Databricks App.
- If it fails: A Container Apps copy of the app runs behind Entra sign-in for reviewers.

Command: `bash ops/wizard/strata-setup.sh`

<!-- dayone:test-6 -->
- Status: not run
- Result: Not run yet, because it needs the wizard first.
- Evidence:
  - None yet. The command above fills it.
- Chosen path: Default, until a result says otherwise. Reviewers join the workspace and open the Databricks App.
- Last run: never
<!-- /dayone:test-6 -->

### Test 7. A personal access token or a service principal

A personal access token or a service principal can be created.

- If it passes: Scripts and probes reach Databricks with a personal access token.
- If it fails: PLAN.md section 14 names no gap fill, so the user decides.

Command: `bash ops/wizard/strata-setup.sh`

<!-- dayone:test-7 -->
- Status: not run
- Result: Not run yet, because it needs the wizard first.
- Evidence:
  - None yet. The command above fills it.
- Chosen path: Default, until a result says otherwise. Scripts and probes reach Databricks with a personal access token.
- Last run: never
<!-- /dayone:test-7 -->

### Test 8. The four models within the subscription's quota

The four models deploy within the subscription's quota.

- If it passes: The four deployments named in .env serve Strata, each with the cap set in `ops/dayone/dayone.toml`.
- If it fails: PLAN.md section 14 names no gap fill, so the user decides.

Command: `uv run --script ops/dayone/probe_caps.py --env-file .env`

<!-- dayone:test-8 -->
- Status: not run
- Result: Not run yet, because it needs the wizard first.
- Evidence:
  - None yet. The command above fills it.
- Chosen path: Default, until a result says otherwise. The four deployments named in .env serve Strata, each with the cap set in `ops/dayone/dayone.toml`.
- Last run: never
<!-- /dayone:test-8 -->

### Test 9. Foundry evaluations after an Entra sign-in

Foundry evaluations run after an Entra sign-in.

- If it passes: Foundry runs the evaluations: groundedness, relevance, task adherence and tool use.
- If it fails: PLAN.md section 14 names no gap fill, so the user decides.

Command: `bash ops/wizard/strata-setup.sh`

<!-- dayone:test-9 -->
- Status: not run
- Result: Not run yet, because it needs the wizard first.
- Evidence:
  - None yet. The command above fills it.
- Chosen path: Default, until a result says otherwise. Foundry runs the evaluations: groundedness, relevance, task adherence and tool use.
- Last run: never
<!-- /dayone:test-9 -->

### Test 10. Traces from the app in Application Insights

Traces reach Application Insights from the app.

- If it passes: The app sends its traces to Application Insights.
- If it fails: PLAN.md section 14 names no gap fill, so the user decides.

Command: `uv run --script ops/dayone/probe_traces.py --env-file .env`

<!-- dayone:test-10 -->
- Status: not run
- Result: Not run yet, because it needs the wizard first.
- Evidence:
  - None yet. The command above fills it.
- Chosen path: Default, until a result says otherwise. The app sends its traces to Application Insights.
- Last run: never
<!-- /dayone:test-10 -->

## What the probes leave in the workspace

The probes make these things and leave them in place. Most of them make a second run quicker. They change nothing else in the workspace.

- The app `strata`, which runs the probe app until the app shell ticket deploys Strata over it.
- The folder `strata-dayone` in your user folder, with the code that the jobs and the app run.
- The schema `workspace.strata_dayone`, with the volume `files` for the PAD, the table `passages` and the index `passages_index`.
- The AI Search endpoint `strata-search`, which Strata keeps for its own index.
- One-time job runs whose names start with `strata-dayone`, in the workspace's job run history.
- A conversation in the Genie space you chose in the wizard, which asks "How many trips are in the table?"
- Read access for the app `strata` to the secret scope `strata`. The app reads only `APPLICATIONINSIGHTS_CONNECTION_STRING`, but Databricks grants access to the whole scope, which also holds `AZURE_OPENAI_API_KEY`.
