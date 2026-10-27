# 87: The bundle deploy's table check skips the search index's own objects, so a deploy after the first index sync creates its tables

**What to build:** `ops/bundle/deploy.py`'s step 2 creates the tables from `src/strata/lakehouse/tables/` and first runs `check_public_from` in `src/strata/lakehouse/catalog.py`, which reads every table of the catalog outside the skipped schemas and stops when one has no `public_from` column of type DATE. Since the nightly's `sync_index` task made the vector index on the paid workspace (October 27, 2026, 01:33 UTC), the catalog also holds the index's own three objects, which the index service makes and which carry no such column: `strata.gold.passage_index` (the index named in `config/models.toml`, listed as FOREIGN) and its `strata.gold.event_log_<id>` and `strata.gold.__<id>___online_index_view` tables (MANAGED). So the deploy of ticket 85's code at 01:39 UTC exited 1 at step 2 with "I could not create the tables. These tables have no public_from column of type DATE: ..." after step 1 had deployed the bundle, and step 2's CREATE TABLE IF NOT EXISTS statements and step 3's "What changed" report did not run; no table change was due that time, but the next ticket that adds a table would not get it created on any workspace whose index exists. Make the check skip the index named in `config/models.toml` and the objects the index service makes beside it (the `event_log_` and `online_index_view` names that carry the index's id), and nothing else, with a test on the fake workspace listing those three objects beside a table that really lacks the column (the check still names that one). Say in `bundle/README.md` which objects the check leaves out and why. The live proof is the second session's or the orchestrator's next bundle deploy from a snapshot on the paid workspace: it passes step 2 and prints step 3's report, recorded in the catch-up file.

Read first: `src/strata/lakehouse/catalog.py` (`check_public_from`, the skipped schemas), `ops/bundle/deploy.py` (step 2 and step 3), `config/models.toml` (the index's name), `src/strata/lakehouse/nightly.py` (`sync_index`), `ops/bundle/tests/test_deploy.py` (the fake workspace), the catch-up file's block for ticket 85 (the deploy of October 27, 01:39 UTC).

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** ops
**Phase:** P4
**Design review:** no

- [ ] With the fake workspace holding the index's three objects beside the catalog's tables, the check passes, and with one real table lacking `public_from` it still names that table; the existing bundle tests pass unchanged.
- [ ] `bundle/README.md` says which objects the check leaves out and why.
- [ ] `measure_data_readiness` (the table sizes measure and any other pass over every table of the catalog) skips the same three objects, proven on the fake workspace, so the nightly task no longer fails on the index's view.
- [ ] The next bundle deploy from a snapshot on the paid workspace passes step 2 and prints step 3's report (recorded in the catch-up file under this ticket).

## Comments

- October 26, 2026, orchestrator: opened at 21:05 PDT with the user's go-ahead for the overnight build, from the second session's deploy of October 27, 01:39 UTC.
- October 26, 2026, orchestrator (21:35 PDT, while the ticket builds): the same objects break the nightly. On the paid workspace `measure_data_readiness` run alone (run 1023673043723265, 04:18 to 04:27 UTC on October 27) failed with `[DELTA_READ_TABLE_WITHOUT_COLUMNS] You are trying to read a Delta table strata.gold.__cd8058ce_42aa_4722_ac9a_3ee310032e31___online_index_view that does not have any columns`, because its table sizes measure reads every table of the catalog. So the skip belongs in one place the deploy's check and the readiness measure both use (the catalog listing in `src/strata/lakehouse/catalog.py`), with a criterion added above; until it lands, the dashboard's Data readiness page stays empty on the paid workspace and tonight's scheduled run fails at that task.
