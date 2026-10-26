# 79: The bundle's grants keep the App's principal, so a bundle deploy no longer takes the App's catalog access away

**What to build:** Every bundle deploy (`ops/bundle/deploy.py`, `bundle/databricks.yml`) writes the grants on the catalog `strata` and the schema `strata.ops` from the bundle's own list, which does not name the App's service principal, so each deploy removes the App's USE CATALOG on strata and USE SCHEMA on strata.ops (the table grants stay), as the warning under 06-1 in `docs/workspace-catchup.md` says. On October 26, 2026 the second session's bundle deploy at 10:21 UTC did it again, and the App redeploy that put the grants back (10:25 to 10:33 UTC) cost nine minutes of 502 answers. On demo day a bundle deploy would take the App down the same way. Make the bundle's grants carry the App's principal: `ops/bundle/deploy.py` reads the App's service principal from `apps get` (the App `ops/dayone/dayone.toml` names) and passes it to the bundle as a variable the grants block uses, or writes the grant right after the deploy if a bundle variable cannot hold a principal, so a bundle deploy leaves the App with USE CATALOG on strata, USE SCHEMA on strata.ops and its table grants; when no App exists yet, the deploy says so and grants nothing for it. Prove it with the bundle tests (the fake workspace or the rendered bundle configuration): the grants hold the App's principal when an App exists and are unchanged when none does. The live proof is the second session's next bundle deploy from a snapshot, after which the catalog's grants show the App's principal still holding USE CATALOG and USE SCHEMA and /api/health answers 200 without an App redeploy. Also make the deploy's "What changed" report name a dashboard that was rewritten, not only a new one: the 10:21 deploy rewrote both dashboards and reported only the grants.

Read first: `ops/bundle/deploy.py` (the grants and the "What changed" report), `bundle/databricks.yml` (grants, variables), `ops/bundle/tests/`, `ops/app/deploy_app.py` (`resources()`, how the App's principal gets its grants), the catch-up file's 06-1 warning and the blocks of ticket 68 step 2 and ticket 70 step 1 of October 26.

**Blocked by:** None (can start immediately)

**Status:** in-progress
**Area:** ops
**Phase:** P2
**Design review:** no

- [ ] With an App in the fake workspace, the bundle's grants (or the grant the deploy writes after it) hold the App's service principal with USE CATALOG on strata and USE SCHEMA on strata.ops; with no App, the grants are as today and the deploy says no App exists.
- [ ] The deploy's "What changed" report names a dashboard that changed as well as a new one, proven by a test on the report.
- [ ] After the second session's next bundle deploy from a snapshot, the App's principal still holds USE CATALOG and USE SCHEMA and /api/health answers 200 with no App redeploy (recorded in the catch-up file under this ticket).

## Comments

- October 26, 2026, orchestrator: opened at 03:35 PDT from the second session's finding after ticket 68's bundle deploy. Built in a side run while wave 4o runs; the next wave merges it first.
