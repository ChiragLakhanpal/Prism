# 107: The cost pull retries a throttled Azure answer and records it, instead of failing the job

**What to build:** The daily cost pull (job `strata cost pull`, `bundle/costs.yml`, 05:40 New York) failed its first scheduled run on the paid workspace (run 679380286409718, October 27, 2026, 09:40 UTC) and a rerun by hand (run 404010923973841, 12:14 UTC) the same way: Azure's Cost Management query API answered `429 {"error":{"code":"429","message":"Too many requests. Please retry."}}` on the one query `AzureCostManagement.charges` makes (`src/strata/lakehouse/costs.py`, the `query` call with daily granularity grouped by ServiceName and ResourceId). `_http` in that file classes a 429 as `throttled` and raises `CostError` at once, so `pull` fails the task and the job, and the dashboard's cost tile stays empty. Azure throttles that API on new subscriptions and names the wait in the answer's `Retry-After` header (or the `x-ms-ratelimit-microsoft.costmanagement-*-retry-after` headers). Make `_http` (or `charges`) retry a 429 up to three times, waiting the time the header names (a default from `config/thresholds.toml`, `costs.retry_seconds`, when no header comes; never less than one second; the tries and the default are config, rule 9), and when the third try is throttled too, make `pull` record the outcome `throttled` in its run row with the Azure message, write no charge, and end the task succeeded, so the job's other tasks and the next day's pull go on; `not_authorized`, `bad_answer` and `unreachable` keep failing the task as they do today. The App's cost page and the dashboard show the throttled day the way they show a day with no charges, with the reason from the run row. Prove it on the fixture with a fake transport: three 429 answers then a good one gives the charges with the waits taken from the headers (a fake clock, no sleep); four 429 answers give the throttled run row and no charge; a 403 still raises. The live proof is the next pull on the paid workspace (the scheduled run, or `run-now` on job 528900661133114) ending succeeded, with its run row recorded in the catch-up file under this ticket.

Read first: `src/strata/lakehouse/costs.py` (`_http`, `AzureCostManagement.charges`, `pull`, the run row it writes), `bundle/costs.yml`, `config/thresholds.toml`, the tests beside `costs.py` (`tests/test_costs*.py`), the catch-up file's blocks for ticket 54 (the cost pull's first live run) and "The App's stop of October 27, 2026".

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** data
**Phase:** P4
**Design review:** no

- [ ] With a fake transport and a fake clock, three 429 answers followed by a good answer give the charges, with the waits taken from the `Retry-After` header and the config default when it is missing; four 429 answers give a run row with the outcome `throttled` and the Azure message, no charge, and a task that ends succeeded; a 403 still raises `CostError` with `not_authorized`.
- [ ] The tries and the default wait live in `config/thresholds.toml` under `[costs]` and nowhere else; `GLOSSARY.md` or the dashboard's copy names the throttled day in the same words the run row uses.
- [ ] On the paid workspace, the next cost pull after the merge and a bundle deploy ends succeeded, with its run row (charges, or throttled with the message) recorded in the catch-up file under this ticket.

## Comments

- October 27, 2026, orchestrator: opened at 05:40 PDT with the user's yes ("please retry the ticket"), from the two 429 failures of the morning; a side run builds it and its merge waits for wave 4r's merge lock.
