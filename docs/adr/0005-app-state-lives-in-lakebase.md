# App state lives in Lakebase

On October 24, 2026, the Lakebase probe (`ops/app/probe_lakebase.py`) timed a write and a read of one row in each store. strata.ops: getting ready, with its first statement, took 2,197 ms. Of 10 tries at a write and a read, the middle time was 2,293 ms and the longest was 2,545 ms. Lakebase: getting ready, with its first statement, took 8,194 ms. Of 10 tries at a write and a read, the middle time was 145 ms and the longest was 375 ms. The budget for following a project or marking a draft as checked is 1,000 ms (`app_state.round_trip_budget_ms` in `config/thresholds.toml`), so app state lives in a Lakebase database instead of `strata.ops`, as the rule in `docs/app-state.md` says.

## Consequences

- Follows, packages, drafts and their states, uploads and feedback live in Lakebase. Usage events, agent runs and every measure stay in `strata.ops`, because the dashboard reads them there.
- Ticket 15 designs how the app reaches Lakebase as each viewer, and keeps the uploader's team rule (CLAUDE.md rule 8).
- Every row still keeps the day it became public (ADR 0002), and the deploy creates the tables from one definition each.
