# 123: The plan reader reads a project's plan versions in statements that fit the warehouse's inline limit

**What to build:** On October 28, 2026, ticket 122's live step `ops/plans/run_live.py --rewrite` rewrote the rows of 13 projects and then stopped with `The warehouse did not run the statement. Its state was FAILED: Inline byte limit exceeded. Statements executed with disposition=INLINE can have a result size of at most 26214400 bytes` at the fourteenth, P156634, whose 236 plan versions in bronze (`strata.bronze.document_texts`) come back in one statement from `plans.read_versions`; the 12 projects after it, P156634 among them, kept their tagged sections (144 rows), and the demo package's tracker stayed empty until the orchestrator cleaned those rows by hand. The nightly's plan reader has the same read, so a project with hundreds of superseded plans is one bad night away from the same stop (ticket 108 supersedes older plans but does not shrink what bronze holds). Make every read of a project's plan texts fit the limit: `plans.read_versions` (and the rewrite's read) select only the versions the run needs (the newest listed plan for a nightly run, as ticket 108 chooses it; the versions `strata.silver.plan_versions` holds for a rewrite), by document id, and when the texts it needs still exceed the limit, it reads them one version at a time; the limit is one number in `config/thresholds.toml` (`ingestion.inline_result_bytes`, 26214400) and the reader measures against it before it asks, never after. Prove it on the fixture with a project given 300 plan versions in a fake bronze (a test that counts statements and bytes), and the recorded `--rewrite` probe of ticket 122 unchanged. The live proof is the orchestrator's: `--rewrite` runs to its end on the paid workspace, prints a line for every project with plan rows, P156634 included, and ends "No section in strata.silver.plan_rows holds a tag."

Read first: `src/strata/lakehouse/plans.py` (`read_versions`, `rewrite`, `projects_with_rows`), `ops/plans/run_live.py`, `src/strata/lakehouse/engine.py` (how a statement runs and what it returns), `config/thresholds.toml` [ingestion], the catch-up file's blocks "Ticket 122, step 2 of 2" and the orchestrator's record of October 28 under it, ticket 108 (the newest-only choice) and ticket 78 (the first rewrite).

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** data
**Phase:** P4
**Design review:** no

- [ ] `plans.read_versions` reads only the versions the run needs, by document id, and splits a read that would exceed `ingestion.inline_result_bytes` into one statement per version; a fixture test with 300 fake versions counts the statements and proves no statement asks for more than the limit.
- [ ] `--rewrite` and the nightly's plan reader share that read (one place), the recorded rewrite probe is unchanged, and the gate adds at most one second.
- [ ] On the paid workspace, after the merge and the bundle deploy, `ops/plans/run_live.py --rewrite` runs to its end with a line per project (P156634 included) and ends "No section in strata.silver.plan_rows holds a tag." (recorded in the catch-up file under this ticket).

## Comments

- October 28, 2026, orchestrator: opened at 08:15 PDT on the orchestrator's judgment from ticket 122's live step; it builds in wave 4u.
