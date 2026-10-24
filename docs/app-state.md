# App state: strata.ops or Lakebase

App state is what people make in Strata and expect to find again: the projects they follow, packages, drafts and their states, uploads and feedback. The spec keeps it in `strata.ops`, written with bound parameters through the SQL warehouse, unless a check shows that a Lakebase database (Databricks' managed Postgres) would be simpler on Free Edition (`docs/PLAN.md` section 18; spec, "The app"). Ticket 06 settles the question before any app state is written. Ticket 15 writes the first app state, the packages a person plans, so the probe below runs before it.

Usage events and agent runs are not app state. They are logs that the dashboard reads from `strata.ops`, so they stay there whatever the probe finds: usage events in `strata.ops.usage_events` from ticket 06, and agent runs from ticket 13. Ticket 14 adds `strata.ops.evidence_opened`, one row per viewer and source opened in the evidence drawer, which the evidence pack's export reads (ticket 35); the app writes it as its own service principal, with a `MERGE`. Ticket 19 adds `strata.ops.supplier_review_decisions` and `strata.ops.supplier_pair_labels`, where a person's merge or no merge on a candidate pair of supplier name matching is kept with the reviewer and the reason. The app writes both as its own service principal, and `ops/app/deploy_app.py` grants it SELECT and MODIFY on them and SELECT on `strata.ops.supplier_pairs`.

## How the probe decides

The probe times the same small job in each store: write one row, then read it back. It does this ten times in each store, after it gets each store ready, which it times on its own. For Lakebase, that includes starting or making the database. Following a project or marking a draft as checked must feel immediate, so the budget for a write and a read is one second (`app_state.round_trip_budget_ms` in `config/thresholds.toml`, from Nielsen's limit for a person's flow of thought).

- `strata.ops` wins when its middle time is within the budget. It needs no second store, no second set of credentials and no second copy of the access rules.
- Lakebase wins only when `strata.ops`'s middle time is over the budget, and Free Edition lets the probe create a Lakebase database whose middle time is within it.
- When neither store is within the budget, `strata.ops` still wins, because Lakebase would add a second store without making state feel immediate.

When Lakebase wins, the probe also writes an ADR in `docs/adr`, named `app-state-lives-in-lakebase.md` and numbered one after the highest ADR there, so the switch is recorded before any app state is written. It never overwrites a file, and a later run that Lakebase wins again leaves the first ADR as it is.

The probe writes its rows to the day-one probes' own schema, `workspace.strata_dayone`, on the same SQL warehouse, so `strata.ops` holds no probe rows. In Lakebase it uses a small database instance named `strata-state-probe`, and it stops the instance when it is done, so the instance costs nothing while it waits.

Run it from the main checkout after the wizard:

    uv run --script ops/app/probe_lakebase.py --env-file .env

`--dry-run` prints what a run would write, with canned times, and writes nothing.

## Result

Only the probe changes this block.

<!-- app-state:result -->
- Status: run
- Chosen store: Lakebase. strata.ops took 2,293 ms in the middle, over the budget of 1,000 ms, and Lakebase took 145 ms, within it.
- Times:
  - strata.ops: getting ready, with its first statement, took 2,197 ms. Of 10 tries at a write and a read, the middle time was 2,293 ms and the longest was 2,545 ms.
  - Lakebase: getting ready, with its first statement, took 8,194 ms. Of 10 tries at a write and a read, the middle time was 145 ms and the longest was 375 ms.
- Last run: October 24, 2026
<!-- /app-state:result -->
