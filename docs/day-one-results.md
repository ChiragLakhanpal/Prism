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
| 1 | The World Bank hosts from a notebook, a job and the app | passed | Default |
| 2 | Foundry and Azure OpenAI from a job | passed | Default |
| 3 | ai_parse_document on a long PAD | passed | Default |
| 4 | An AI Search endpoint and a hybrid index | passed | Default |
| 5 | The Genie conversation API as the token's user | passed | Default |
| 6 | An outside email joins the workspace and opens the app | partly | Gap fill |
| 7 | A personal access token or a service principal | passed | Default |
| 8 | The four models within the subscription's quota | passed | Default |
| 9 | Foundry evaluations after an Entra sign-in | passed | Default |
| 10 | Traces from the app in Application Insights | passed | Default |
<!-- /dayone:summary -->

## Pay-as-you-go

The free Azure credit of about US$197 ends on November 10, 2026. The subscription moves to pay-as-you-go before then (PLAN.md section 2). The last Azure stage of the wizard records who takes this step and when.

<!-- dayone:payg -->
- Step: Move the Azure subscription from the free credit to pay-as-you-go.
- Deadline: Before November 10, 2026, when the free credit ends.
- Who: The subscription owner (the user)
- Status: The subscription showed pay-as-you-go on October 26, 2026.
- Last updated: October 26, 2026
<!-- /dayone:payg -->

## Azure caps and budget

Budgets only send email, so hard caps stop the spend: a tokens-per-minute limit on each model deployment, and a daily cap on Application Insights. The probe reads each deployment's limit, the budget and its notifications, and the subscription's offer. The caps themselves are set in `ops/dayone/dayone.toml`.

Command: `uv run --script ops/dayone/probe_caps.py --env-file .env`

<!-- dayone:caps -->
- Status: capped
- Deployments:
  - gpt-5.4-mini: 100,000 tokens per minute, as Global Standard.
  - gpt-5.4: 30,000 tokens per minute, as Global Standard.
  - gpt-5.4-nano: 2,000,000 enqueued tokens, as Global Standard. A Global Standard deployment has no tokens-per-minute limit, so Azure caps the tokens it holds in the queue instead.
  - text-embedding-3-large: 150,000 tokens per minute, as Global Standard.
- Budget: strata-monthly: US$50 a month, with four alerts (actual cost at 50, 80, 100 percent; forecast cost at 100 percent), sent to one email address.
- Subscription offer: Azure subscription 1 is on pay-as-you-go (quota ID PayAsYouGo_2014-09-01, spending limit Off).
- Last checked: October 26, 2026
<!-- /dayone:caps -->

## The ten tests

### Test 1. The World Bank hosts from a notebook, a job and the app

Free Edition reaches `search.worldbank.org`, `documents1.worldbank.org`, `datacatalogapi.worldbank.org` and `api.worldbank.org` from a notebook, a job and the app.

- If it passes: Ingestion runs in Databricks, and jobs fetch from the World Bank hosts.
- If it fails: A Container Apps job fetches the files and pushes them into the volume.

Command: `uv run --script ops/dayone/probe_hosts.py --env-file .env`

<!-- dayone:test-1 -->
- Status: passed
- Result: The notebook, the job and the app each reached all four World Bank hosts.
- Evidence:
  - This computer: search.worldbank.org 200; documents1.worldbank.org 200; datacatalogapi.worldbank.org 200; api.worldbank.org 200.
  - The notebook (https://adb-7405609289499029.9.azuredatabricks.net/?o=7405609289499029#job/728958432808114/run/646817633445246): search.worldbank.org 200; documents1.worldbank.org 200; datacatalogapi.worldbank.org 200; api.worldbank.org 200.
  - The job (https://adb-7405609289499029.9.azuredatabricks.net/?o=7405609289499029#job/1018775688105798/run/216880754587085): search.worldbank.org 200; documents1.worldbank.org 200; datacatalogapi.worldbank.org 200; api.worldbank.org 200.
  - The app (https://strata-7405609289499029.9.azure.databricksapps.com): search.worldbank.org 200; documents1.worldbank.org 200; datacatalogapi.worldbank.org 200; api.worldbank.org 200.
- Chosen path: Default. Ingestion runs in Databricks, and jobs fetch from the World Bank hosts.
- Last run: October 26, 2026
<!-- /dayone:test-1 -->

### Test 2. Foundry and Azure OpenAI from a job

Free Edition reaches the Foundry and Azure OpenAI endpoints from a job, not only from the app.

- If it passes: The nightly job calls Foundry and Azure OpenAI directly.
- If it fails: PLAN.md section 14 names no gap fill, so the user decides.

Command: `uv run --script ops/dayone/probe_azure_from_job.py --env-file .env`

<!-- dayone:test-2 -->
- Status: passed
- Result: The job reached Foundry and Azure OpenAI, and Azure OpenAI accepted the key.
- Evidence:
  - Job run: https://adb-7405609289499029.9.azuredatabricks.net/?o=7405609289499029#job/109502183789487/run/155700649679184
  - Foundry project endpoint, asked without a key: 404.
  - Azure OpenAI model list, asked without a key: 401.
  - Azure OpenAI model list, asked with the key from the secret scope: 200.
- Chosen path: Default. The nightly job calls Foundry and Azure OpenAI directly.
- Last run: October 26, 2026
<!-- /dayone:test-2 -->

### Test 3. ai_parse_document on a long PAD

`ai_parse_document` runs on a 120-page PAD.

- If it passes: `ai_parse_document` reads route B pages.
- If it fails: Content Understanding `prebuilt-layout` reads route B pages.

Command: `uv run --script ops/dayone/probe_parse_pad.py --env-file .env`

<!-- dayone:test-3 -->
- Status: passed
- Result: ai_parse_document read all 131 pages of the PAD.
- Evidence:
  - P160009 PAD: https://documents.worldbank.org/curated/en/212451501293669530/pdf/Kenya-off-grid-PAD-07072017.pdf, 131 pages.
  - Uploaded to /Volumes/workspace/strata_dayone/files/P160009-pad.pdf.
  - Statement 01f1d17d-3efe-1d08-8524-a84aa1011071 took 159 seconds and read 131 pages.
- Chosen path: Default. `ai_parse_document` reads route B pages.
- Last run: October 26, 2026
<!-- /dayone:test-3 -->

### Test 4. An AI Search endpoint and a hybrid index

An AI Search endpoint and a hybrid index can be created.

- If it passes: Prism's own AI Search endpoint holds a hybrid index of passages.
- If it fails: PLAN.md section 14 names no gap fill, so the user decides.

Command: `uv run --script ops/dayone/probe_ai_search.py --env-file .env`

<!-- dayone:test-4 -->
- Status: passed
- Result: The endpoint is online, and the hybrid index answered a hybrid query with three passages.
- Evidence:
  - Endpoint strata-search: ONLINE.
  - Index workspace.strata_dayone.passages_index: ready, three rows, over workspace.strata_dayone.passages. Index is currently online, pipeline update is pending setup of pipeline resources. Check latest status: https://adb-7405609289499029.9.azuredatabricks.net/explore/data/workspace/strata_dayone/passages_index
  - Hybrid query "advertised again after the bids were rejected" returned p1, p2, p3, best first.
- Chosen path: Default. Prism's own AI Search endpoint holds a hybrid index of passages.
- Last run: October 26, 2026
<!-- /dayone:test-4 -->

### Test 5. The Genie conversation API as the token's user

The Genie conversation API answers as the token's user.

- If it passes: The Genie conversation API answers structured questions as the viewer.
- If it fails: PLAN.md section 14 names no gap fill, so the user decides.

Command: `uv run --script ops/dayone/probe_genie.py --env-file .env`

<!-- dayone:test-5 -->
- Status: passed
- Result: Genie answered as the token's user.
- Evidence:
  - Space 01f1d17269a81cfdbf2dc585f916e592, conversation 01f1d17c3ab01ca9b149c32169852322, message 01f1d17c3acf1dce860c3fdffec2b35a.
  - Question: How many contracts were signed in each fiscal year, and for how much in US dollars?
  - Status: COMPLETED.
  - Answer: This database only contains NYC taxi trip data in `samples`.`nyctaxi`.`trips`, with columns like pickup/dropoff timestamps, distance, fare amount, and ZIP codes. It does not contain contracts, fiscal years, or contract values, so I can’t fetch that from this schema.
  - The message's user ID, 146827166867001, is the token's user.
- Chosen path: Default. The Genie conversation API answers structured questions as the viewer.
- Last run: October 26, 2026
<!-- /dayone:test-5 -->

### Test 6. An outside email joins the workspace and opens the app

An outside email can join the workspace and open the app.

- If it passes: Reviewers join the workspace and open the Databricks App.
- If it fails: A Container Apps copy of the app runs behind Entra sign-in for reviewers.

Command: `bash ops/wizard/strata-setup.sh`

<!-- dayone:test-6 -->
- Status: partly
- Result: On the paid workspace the owner's account opens the Databricks App; no outside email has been added yet (the panel's names arrive later, decision 94).
- Evidence:
  - App: https://strata-7405609289499029.9.azure.databricksapps.com
  - GET /api/health answered 200 with the owner's token at 12:31 and 20:11 UTC on October 27, 2026 (the catch-up file's block on the App's stop)
- Chosen path: Gap fill. A Container Apps copy of the app runs behind Entra sign-in for reviewers.
- Last run: October 27, 2026
<!-- /dayone:test-6 -->

### Test 7. A personal access token or a service principal

A personal access token or a service principal can be created.

- If it passes: Scripts and probes reach Databricks with a personal access token.
- If it fails: PLAN.md section 14 names no gap fill, so the user decides.

Command: `bash ops/wizard/strata-setup.sh`

<!-- dayone:test-7 -->
- Status: passed
- Result: A personal access token works.
- Evidence:
  - databricks current-user me returned the user ID 146827166867001. It used a new personal access token.
- Chosen path: Default. Scripts and probes reach Databricks with a personal access token.
- Last run: October 26, 2026
<!-- /dayone:test-7 -->

### Test 8. The four models within the subscription's quota

The four models deploy within the subscription's quota.

- If it passes: The four deployments named in `config/models.toml` serve Prism, each with the cap set in `ops/dayone/dayone.toml`.
- If it fails: PLAN.md section 14 names no gap fill, so the user decides.

Command: `uv run --script ops/dayone/probe_caps.py --env-file .env`

<!-- dayone:test-8 -->
- Status: passed
- Result: Every deployment with a cap in dayone.toml exists and finished deploying.
- Evidence:
  - gpt-5.4-mini: 100,000 tokens per minute, as Global Standard.
  - gpt-5.4: 30,000 tokens per minute, as Global Standard.
  - gpt-5.4-nano: 2,000,000 enqueued tokens, as Global Standard. A Global Standard deployment has no tokens-per-minute limit, so Azure caps the tokens it holds in the queue instead.
  - text-embedding-3-large: 150,000 tokens per minute, as Global Standard.
- Chosen path: Default. The four deployments named in `config/models.toml` serve Prism, each with the cap set in `ops/dayone/dayone.toml`.
- Last run: October 26, 2026
<!-- /dayone:test-8 -->

### Test 9. Foundry evaluations after an Entra sign-in

Foundry evaluations run after an Entra sign-in.

- If it passes: Foundry runs the evaluations: groundedness, relevance, task adherence and tool use.
- If it fails: PLAN.md section 14 names no gap fill, so the user decides.

Command: `bash ops/wizard/strata-setup.sh`

<!-- dayone:test-9 -->
- Status: passed
- Result: A Foundry evaluation ran after an Entra sign-in and returned scores.
- Evidence:
  - Evaluation: https://ai.azure.com/nextgen/r/ACfuFirFSVyem53VMfBRGg,WorldBank-demo,,wb-strata,Strata/build/evaluations/eval_18b902f1929147a38b271d27e1da7176/run/evalrun_1ed31c81295f43f7822432da8e12672c?tid=08fda299-c7b4-4235-a795-3837cac06b4c
- Chosen path: Default. Foundry runs the evaluations: groundedness, relevance, task adherence and tool use.
- Last run: October 24, 2026
<!-- /dayone:test-9 -->

### Test 10. Traces from the app in Application Insights

Traces reach Application Insights from the app.

- If it passes: The app sends its traces to Application Insights.
- If it fails: PLAN.md section 14 names no gap fill, so the user decides.

Command: `uv run --script ops/dayone/probe_traces.py --env-file .env`

<!-- dayone:test-10 -->
- Status: passed
- Result: A trace the app sent reached Application Insights.
- Evidence:
  - Marker: strata-dayone-6307e88ee4cd.
  - App: https://strata-7405609289499029.9.azure.databricksapps.com.
  - The app sent trace 872e45cac676e66e878a6016fcc85c3f.
  - Application Insights holds it: 2026-10-26T20:47:11.156268Z, dependency, 872e45cac676e66e878a6016fcc85c3f.
- Chosen path: Default. The app sends its traces to Application Insights.
- Last run: October 26, 2026
<!-- /dayone:test-10 -->

## What the probes leave in the workspace

The probes make these things and leave them in place. Most of them make a second run quicker. They change nothing else in the workspace.

- The app `strata`, which runs the probe app until the app shell ticket deploys Prism over it.
- The folder `strata-dayone` in your user folder, with the code that the jobs and the app run.
- The schema `workspace.strata_dayone`, with the volume `files` for the PAD, the table `passages` and the index `passages_index`.
- The AI Search endpoint `strata-search`, which Prism keeps for its own index.
- One-time job runs whose names start with `strata-dayone`, in the workspace's job run history.
- A conversation in the Genie space that GENIE_SPACE_ID names, which asks "How many contracts were signed in each fiscal year, and for how much in US dollars?"
- Read access for the app `strata` to the secret scope `strata`. The app reads only `APPLICATIONINSIGHTS_CONNECTION_STRING`, but Databricks grants access to the whole scope, which also holds `AZURE_OPENAI_API_KEY`.
