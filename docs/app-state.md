# App state: strata.ops or Lakebase

App state is what people make in Strata and expect to find again: the projects they follow, packages, drafts and their states, uploads and feedback. The spec keeps it in `strata.ops`, written with bound parameters through the SQL warehouse, unless a check shows that a Lakebase database (Databricks' managed Postgres) would be simpler on Free Edition (`docs/PLAN.md` section 18; spec, "The app"). Ticket 06 settles the question before any app state is written. Ticket 15 writes the first app state, the packages a person plans, so the probe below runs before it.

Usage events and agent runs are not app state. They are logs that the dashboard reads from `strata.ops`, so they stay there whatever the probe finds: usage events in `strata.ops.usage_events` from ticket 06, and agent runs from ticket 13. Ticket 14 adds `strata.ops.evidence_opened`, one row per viewer and source opened in the evidence drawer, which the evidence pack's export reads (ticket 35); the app writes it as its own service principal, with a `MERGE`. Ticket 19 adds `strata.ops.supplier_review_decisions` and `strata.ops.supplier_pair_labels`, where a person's merge or no merge on a candidate pair of supplier name matching is kept with the reviewer and the reason. The app writes both as its own service principal, and `ops/app/deploy_app.py` grants it SELECT and MODIFY on them and SELECT on `strata.ops.supplier_pairs`. Ticket 23 adds `strata.ops.disagreement_choices`, one row each time a person keeps one side of a disagreement for an answer or a draft, with their reason; rows are only added, so going back to Strata's choice adds a row, and the evidence pack reads the latest per viewer, disagreement and answer or draft. The app writes it as its own service principal, and `ops/app/deploy_app.py` grants it SELECT and MODIFY on it. Ticket 21 adds the first shared record staff make: `strata.ops.plan_baselines`, one row per project and implementing agency naming the plan version saved as the baseline, who saved it and when, and `strata.ops.plan_baseline_steps`, that version's planned dates copied when it is saved, because the plan reader rebuilds `strata.silver.plan_steps` on every run. The app writes both with the viewer's own token, so World Bank staff need SELECT and MODIFY on them. A save adds the new steps, then merges the baseline's one row with a `MERGE`, and only then deletes the earlier save's steps, so a write that fails part way leaves the baseline a check reads whole; removing a baseline is a `DELETE` with a `WHERE` that names the project and the agency.

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

## How the app reaches Lakebase

The probe chose Lakebase (ADR 0005), so ticket 15, which writes the first app state, set up how the app reaches it. `src/strata/appstate` holds the code.

- **One definition per table.** Each app state table is one `CREATE TABLE IF NOT EXISTS strata.app.<table>` statement in `src/strata/appstate/tables/app/`, in Databricks SQL like every other table. On the App, `LakebaseEngine` rewrites each statement for Postgres, drops the catalog part and binds each `:name` value as a parameter. On this computer and in the gate, the same statements run on a DuckDB file. The tables so far are `planned_packages`, `planned_package_saves`, `plan_checks_opened`, `criteria_checks` (ticket 31: each run of "Check your criteria", with a person's pasted qualification criteria, read only for its owner) and `risk_selections` (ticket 30: the risks each viewer selected for a package's PPSD, one row per viewer, package and risk, changed by a `MERGE`), `plan_date_choices` (tickets 26 and 27: the one choice of middle or cautious dates per viewer and package, which section 1's plan-date choice and section 2's "Date each step with" share) and `step_start_dates` (ticket 27: the date a viewer gave the first step of a package whose plan gives no planned dates), each changed by a `MERGE`.
- **The app signs in as itself.** `ops/app/deploy_app.py` makes or starts the Lakebase instance `strata-state` (`names.app_state_instance` in `ops/dayone/dayone.toml`) and gives the app its database as a resource, with CAN_CONNECT_AND_CREATE. The platform then sets `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER` and `PGSSLMODE`, and the server signs in as the app's own service principal, with the app's own OAuth token as the password. A viewer's token never reaches Lakebase.
- **Each person sees only their own rows.** Every read and write names the viewer it is for, bound per request, and the routes show a package only to the person who made it, as the drafts' routes do. The uploader's team rule (CLAUDE.md rule 8) will filter by team the same way when uploads arrive.
- **The app makes its tables.** The first time the server needs app state, it runs the definitions, which leave a table that exists as it is. A deploy needs to give the app only its database.

The drafts (ticket 35) were built before the probe ran, so they still live in `strata.ops`. Moving them to Lakebase is a follow-up. Ticket 37's follows sit beside them in `strata.ops.follows`, for the same reason: one row each time a World Bank staff viewer follows or unfollows a project, written as the app's own service principal, the latest row winning, and no row ever changed or removed. Ticket 38's uploads sit beside the drafts too, because an agency's planned dates and PPSD rows are drafts made from them: `strata.ops.uploads` and `strata.ops.upload_rows`, an implementing agency team's Procurement Plan read and checked, written as the app's own service principal only after the check, activities first and the upload's own row last, and read only through the one access rule. The deploy grants the app SELECT and MODIFY on both and masks the columns that hold the officer's words, and every draft's content, from every other reader (`strata.lakehouse.masks`). Moving uploads and drafts to Lakebase together is the same follow-up.

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
